"""Classification and recommendation head.

Three complementary experts estimate the probability that each workflow
archetype is the right one for a charter:

  semantic expert     calibrated multinomial logistic regression over the LSA
                      embedding concatenated with standardised charter features
  structural expert   gradient boosted trees over the interpretable charter
                      features, which capture threshold effects such as team
                      count or interrupt share
  precedent expert    similarity and outcome weighted vote over the nearest
                      historical high performing projects (retrieval augmented
                      classification) in a hybrid project space that joins the
                      semantic embedding with the standardised charter features

Out of fold predictions from all three experts are produced during training and
the blend weights are chosen on the probability simplex to minimise log loss.
This stacks the experts without leaking training labels into the weights.
"""

import itertools

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.preprocessing import StandardScaler

from charterloom.catalog import ARCHETYPE_KEYS
from charterloom.text import minus

EXPERTS = ("semantic", "structural", "precedent")


class PrecedentVoter:
    """Similarity and outcome weighted nearest neighbour vote over historical projects."""

    def __init__(self, k=30, temperature=0.08, n_classes=len(ARCHETYPE_KEYS)):
        self.k = k
        self.temperature = temperature
        self.n_classes = n_classes

    def fit(self, embeddings, labels, quality, project_ids):
        self.embeddings = np.asarray(embeddings, dtype=np.float32)
        self.labels = np.asarray(labels, dtype=int)
        self.quality = np.asarray(quality, dtype=np.float64)
        self.project_ids = list(project_ids)
        return self

    def _vote_from_similarities(self, sims):
        k = min(self.k, sims.size)
        top = np.argpartition(np.negative(sims), k)[:k] if k < sims.size else np.arange(sims.size)
        top = top[np.argsort(np.negative(sims[top]))]
        top_sims = sims[top].astype(np.float64)
        weights = np.exp(minus(top_sims, top_sims.max()) / self.temperature) * self.quality[top]
        distribution = np.full(self.n_classes, 0.002)
        np.add.at(distribution, self.labels[top], weights)
        distribution /= distribution.sum()
        return distribution, top, top_sims

    def vote(self, query_embedding, exclude=None):
        sims = self.embeddings @ np.asarray(query_embedding, dtype=np.float32)
        if exclude is not None:
            sims = sims.copy()
            sims[exclude] = np.finfo(np.float32).min
        distribution, top, top_sims = self._vote_from_similarities(sims)
        neighbours = [
            {"project_id": self.project_ids[i], "workflow_archetype": ARCHETYPE_KEYS[self.labels[i]],
             "similarity": round(float(s), 4), "outcome_score": round(float(self.quality[i]), 3)}
            for i, s in zip(top, top_sims)
        ]
        return distribution, neighbours

    def vote_matrix(self, query_embeddings, exclude_self=False):
        sims = np.asarray(query_embeddings, dtype=np.float32) @ self.embeddings.T
        if exclude_self:
            np.fill_diagonal(sims, np.finfo(np.float32).min)
        return np.vstack([self._vote_from_similarities(row)[0] for row in sims])


class WorkflowRecommender:
    """Stacked three expert recommender over workflow archetypes."""

    def __init__(self, settings, feature_names):
        self.settings = settings
        self.feature_names = list(feature_names)
        self.classes = list(ARCHETYPE_KEYS)
        self.scaler = StandardScaler()
        self.weights = {"semantic": 1 / 3, "structural": 1 / 3, "precedent": 1 / 3}
        self.diagnostics = {}

    def _semantic_estimator(self):
        base = LogisticRegression(C=self.settings.classifier_c, max_iter=self.settings.classifier_max_iter,
                                  class_weight="balanced")
        return CalibratedClassifierCV(base, method="sigmoid", cv=self.settings.calibration_folds)

    def _structural_estimator(self):
        return HistGradientBoostingClassifier(max_depth=4, learning_rate=0.07, max_iter=250, l2_regularization=1.0,
                                              class_weight="balanced", random_state=self.settings.random_seed)

    def _design(self, embeddings, features):
        return np.hstack([embeddings, self.scaler.transform(features)])

    def fit(self, embeddings, features, labels, quality, project_ids, space):
        self.space = space
        y = np.array([self.classes.index(label) for label in labels])
        missing = set(range(len(self.classes))) ^ set(y.tolist())
        if missing:
            raise ValueError(f"Training data lacks examples for: {[self.classes[i] for i in sorted(missing)]}")
        self.scaler.fit(features)
        X = self._design(embeddings, features)
        folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=self.settings.random_seed)

        oof = {
            "semantic": cross_val_predict(self._semantic_estimator(), X, y, cv=folds, method="predict_proba"),
            "structural": cross_val_predict(self._structural_estimator(), features, y, cv=folds, method="predict_proba"),
        }
        self.semantic = self._semantic_estimator().fit(X, y)
        self.structural = self._structural_estimator().fit(features, y)
        self.attribution = LogisticRegression(C=1.0, max_iter=self.settings.classifier_max_iter,
                                              class_weight="balanced").fit(self.scaler.transform(features), y)
        self.precedent = PrecedentVoter(k=self.settings.neighbour_k, temperature=self.settings.neighbour_temperature)
        vectors = space.transform(embeddings, features)
        self.precedent.fit(vectors, y, quality, project_ids)
        oof["precedent"] = self.precedent.vote_matrix(vectors, exclude_self=True)

        self.weights, scores = self._optimise_weights(oof, y)
        self.diagnostics = {
            "training_examples": int(len(y)),
            "oof_log_loss": {name: round(float(log_loss(y, oof[name], labels=range(len(self.classes)))), 4)
                             for name in EXPERTS},
            "oof_accuracy": {name: round(float((oof[name].argmax(axis=1) == y).mean()), 4) for name in EXPERTS},
            "blend_log_loss": round(scores, 4),
            "blend_weights": {k: round(v, 3) for k, v in self.weights.items()},
        }
        return self

    def _optimise_weights(self, oof, y):
        step = self.settings.blend_grid_step
        grid = np.round(np.arange(0.0, 1.0 + step / 2, step), 6)
        best, best_loss = None, None
        for w_sem, w_str in itertools.product(grid, grid):
            w_pre = round(minus(1.0, w_sem + w_str), 6)
            if w_pre < 0.0:
                continue
            blended = w_sem * oof["semantic"] + w_str * oof["structural"] + w_pre * oof["precedent"]
            loss = log_loss(y, blended, labels=range(len(self.classes)))
            if best_loss is None or loss < best_loss:
                best, best_loss = (w_sem, w_str, w_pre), loss
        return dict(zip(EXPERTS, (float(v) for v in best))), float(best_loss)

    def expert_probabilities(self, embeddings, features, exclude_indices=None):
        """Return each expert's probability matrix for a batch of charters."""
        X = self._design(embeddings, features)
        out = {
            "semantic": self.semantic.predict_proba(X),
            "structural": self.structural.predict_proba(features),
        }
        rows = []
        for i, vector in enumerate(self.space.transform(embeddings, features)):
            exclude = None if exclude_indices is None else exclude_indices[i]
            rows.append(self.precedent.vote(vector, exclude=exclude)[0])
        out["precedent"] = np.vstack(rows)
        return out

    def blend(self, experts):
        total = sum(self.weights[name] * experts[name] for name in EXPERTS)
        return total / total.sum(axis=1, keepdims=True)

    def predict_proba(self, embeddings, features):
        return self.blend(self.expert_probabilities(embeddings, features))

    def recommend(self, embedding, feature_row, top_n=3):
        """Recommend workflows for a single charter with evidence from every expert."""
        embedding = np.asarray(embedding)[None, :]
        feature_row = np.asarray(feature_row)[None, :]
        experts = self.expert_probabilities(embedding, feature_row)
        probs = self.blend(experts)[0]
        order = np.argsort(np.negative(probs), kind="stable")
        _, neighbours = self.precedent.vote(self.space.transform(embedding, feature_row)[0])
        top = order[0]
        margin = float(minus(probs[order[0]], probs[order[1]]))
        return {
            "workflow": self.classes[top],
            "confidence": round(float(probs[top]), 4),
            "margin": round(margin, 4),
            "needs_human_review": bool(probs[top] < self.settings.abstention_threshold),
            "ranking": [{"workflow": self.classes[i], "probability": round(float(probs[i]), 4)} for i in order[:top_n]],
            "probabilities": {self.classes[i]: round(float(probs[i]), 4) for i in order},
            "experts": {name: {self.classes[i]: round(float(experts[name][0][i]), 4) for i in order}
                        for name in EXPERTS},
            "blend_weights": {k: round(v, 3) for k, v in self.weights.items()},
            "precedents": neighbours,
            "feature_drivers": self.feature_drivers(feature_row[0], top),
        }

    def feature_drivers(self, feature_row, class_index, top=6):
        """Signed contribution of each interpretable feature to the chosen class (linear attribution)."""
        scaled = self.scaler.transform(feature_row[None, :])[0]
        contributions = self.attribution.coef_[class_index] * scaled
        order = np.argsort(np.negative(contributions), kind="stable")
        drivers = []
        for i in order[:top]:
            if contributions[i] <= 0:
                break
            drivers.append({"feature": self.feature_names[i], "contribution": round(float(contributions[i]), 4),
                            "value": round(float(feature_row[i]), 4)})
        return drivers
