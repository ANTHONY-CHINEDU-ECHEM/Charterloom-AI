"""End to end Charterloom pipeline: retrieve, recommend, customise, explain."""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib

from charterloom import __version__
from charterloom.catalog import ARCHETYPE_BY_KEY
from charterloom.customizer import WorkflowCustomizer
from charterloom.embeddings import LsaEmbedder
from charterloom.explain import SIGNAL_DESCRIPTIONS, build_rationale
from charterloom.features import CharterFeatureExtractor
from charterloom.recommender import WorkflowRecommender
from charterloom.retrieval import HybridRetriever, ProjectIndex, ProjectSpace
from charterloom.text import fingerprint, minus

LOGGER = logging.getLogger("charterloom.pipeline")
ARTIFACT_NAME = "charterloom_pipeline.joblib"
MANIFEST_NAME = "manifest.json"


class CharterloomPipeline:
    """Fit once on the knowledge base, then serve recommendations for new charters."""

    def __init__(self, settings):
        self.settings = settings
        self.extractor = CharterFeatureExtractor()
        self.embedder = LsaEmbedder(
            dimension=settings.embedding_dim, max_features=settings.tfidf_max_features,
            min_df=settings.tfidf_min_df, max_df=settings.tfidf_max_df, n_iter=settings.svd_iterations,
            random_state=settings.random_seed,
        )
        self.retriever = None
        self.space = None
        self.project_index = None
        self.recommender = None
        self.customizer = WorkflowCustomizer(settings)
        self.manifest = {}

    # Training

    def fit(self, kb):
        started = time.perf_counter()
        documents = kb.documents()
        LOGGER.info("Fitting semantic embedder on %d documents", len(documents))
        self.embedder.fit([d.text for d in documents])
        LOGGER.info("Indexing hybrid retriever")
        self.retriever = HybridRetriever(
            self.embedder, k1=self.settings.bm25_k1, b=self.settings.bm25_b, rrf_k=self.settings.rrf_k,
            candidate_pool=self.settings.candidate_pool, chunk_size=self.settings.chunk_words,
            chunk_overlap=self.settings.chunk_overlap,
        ).index(documents)

        LOGGER.info("Building hybrid project space over %d historical charters", len(kb.blueprints))
        all_charters = [b["charter"] for b in kb.blueprints]
        all_embeddings = self.embedder.transform(all_charters)
        all_features = self.extractor.transform(all_charters)
        self.space = ProjectSpace(self.settings.precedent_feature_weight).fit(all_features)
        self.project_index = ProjectIndex(self.space).fit(
            self.space.transform(all_embeddings, all_features), kb.blueprints,
            {p["project_id"]: p for p in kb.post_mortems},
        )

        high = [i for i, b in enumerate(kb.blueprints) if b["high_performing"]]
        LOGGER.info("Training recommendation head on %d high performing projects", len(high))
        self.recommender = WorkflowRecommender(self.settings, self.extractor.feature_names).fit(
            all_embeddings[high], all_features[high], [kb.blueprints[i]["workflow_archetype"] for i in high],
            [kb.blueprints[i]["outcome_score"] for i in high], [kb.blueprints[i]["project_id"] for i in high],
            self.space,
        )
        self.customizer.calibrate_threshold(self._calibration_samples(kb, all_embeddings, all_features))
        LOGGER.info("Adjustment threshold calibrated to %.2f", self.customizer.threshold)
        self.manifest = {
            "name": "Charterloom AI",
            "version": __version__,
            "trained_at": datetime.now(timezone.utc).strftime("%d %B %Y %H:%M UTC"),
            "knowledge_base_fingerprint": kb.fingerprint(),
            "knowledge_base": kb.stats(),
            "training_projects": len(kb.blueprints),
            "high_performing_training_projects": len(high),
            "chunks_indexed": len(self.retriever),
            "projects_indexed": len(kb.blueprints),
            "embedding_dimension": self.embedder.dimension,
            "vocabulary_size": self.embedder.vocabulary_size(),
            "lsa_explained_variance": round(self.embedder.explained_variance_, 4),
            "recommender": self.recommender.diagnostics,
            "adjustment_calibration": {k: v for k, v in self.customizer.calibration.items() if k != "curve"},
            "training_seconds": round(minus(time.perf_counter(), started), 2),
            "settings": self.settings.to_dict(),
        }
        return self

    def _calibration_samples(self, kb, embeddings, features, limit=800):
        """Leave one out post mortem evidence for a sample of training projects."""
        vectors = self.space.transform(embeddings, features)
        step = max(1, len(kb.blueprints) // limit)
        samples = []
        for i in range(0, len(kb.blueprints), step):
            record = kb.blueprints[i]
            profile = self.extractor.profile(record["charter"])
            hits = self.project_index.post_mortem_hits(vectors[i], self.settings.post_mortem_top_k,
                                                       exclude_project_ids={record["project_id"]})
            observed = kb.post_mortem_for(record["project_id"])["recommended_adjustments"]
            samples.append((self.extractor.adjustment_priors(profile), hits, profile.regimes, observed))
        return samples

    # Inference

    def profile(self, charter_text):
        return self.extractor.profile(charter_text)

    def recommend(self, charter_text, project_name=None, exclude_project_ids=None, include_configuration=True):
        if self.recommender is None:
            raise RuntimeError("Pipeline is not trained. Run 'charterloom build' first.")
        started = time.perf_counter()
        profile = self.extractor.profile(charter_text)
        feature_row = self.extractor.vector(profile)
        embedding = self.embedder.transform([charter_text])[0]
        recommendation = self.recommender.recommend(embedding, feature_row)
        archetype = ARCHETYPE_BY_KEY[recommendation["workflow"]]
        exclude = set(exclude_project_ids or [])

        project_vector = self.space.transform(embedding, feature_row)[0]
        blueprint_hits = self.project_index.blueprint_hits(project_vector, self.settings.evidence_top_k, exclude)
        post_mortem_hits = self.project_index.post_mortem_hits(project_vector, self.settings.post_mortem_top_k, exclude)
        signal_text = " ".join(SIGNAL_DESCRIPTIONS[n] for n, v in profile.signals.items()
                               if v >= 0.5 and n in SIGNAL_DESCRIPTIONS)
        methodology_query = f"{archetype.display_name}. {archetype.summary} {signal_text}"
        methodology_hits = self.retriever.search(methodology_query, top_k=self.settings.methodology_top_k,
                                                 doc_types=["methodology", "workflow_template"])
        name = project_name or _infer_name(charter_text)
        charter_hash = fingerprint(charter_text)[:16]
        result = {
            "project_name": name,
            "charter_fingerprint": charter_hash,
            "recommendation": recommendation,
            "charter_profile": profile.to_dict(),
            "evidence": {
                "similar_blueprints": [h.to_dict() for h in blueprint_hits],
                "post_mortems": [h.to_dict() for h in post_mortem_hits[:6]],
                "methodology": [h.to_dict() for h in methodology_hits],
            },
        }
        if include_configuration:
            priors = self.extractor.adjustment_priors(profile)
            configuration = self.customizer.customise(
                recommendation["workflow"], profile, priors, post_mortem_hits, project_name=name,
                confidence=recommendation["confidence"], charter_fingerprint=charter_hash,
            )
            result["configuration"] = configuration
            result["rationale"] = build_rationale(recommendation, profile, methodology_hits, configuration["adjustments"])
        result["latency_ms"] = round(minus(time.perf_counter(), started) * 1000.0, 1)
        return result

    # Persistence

    def save(self, directory=None):
        directory = Path(directory or self.settings.artifacts_dir)
        directory.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, directory / ARTIFACT_NAME, compress=3)
        (directory / MANIFEST_NAME).write_text(json.dumps(self.manifest, indent=2), encoding="utf8")
        return directory

    @classmethod
    def load(cls, directory):
        path = Path(directory) / ARTIFACT_NAME
        if not path.exists():
            raise FileNotFoundError(f"No trained pipeline at {path}. Run 'charterloom build' first.")
        return joblib.load(path)


def _infer_name(charter_text):
    for line in charter_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            return title.split(":", 1)[1].strip() if ":" in title else title
    return "Untitled project"
