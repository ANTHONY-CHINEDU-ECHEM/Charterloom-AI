"""Leakage safe evaluation of every stage of Charterloom.

Protocol
  * Projects are split 80/20, stratified by the latent optimal workflow. Entire
    projects are held out: their charters, blueprints and post mortems never
    enter the embedder, the indexes or the recommendation head.
  * Recommendation is evaluated on held out high performing projects against the
    workflow they actually used (the same target the head is trained on), and on
    all held out projects against the latent optimal workflow (oracle agreement).
  * Retrieval is evaluated on whether the nearest historical precedents used the
    same workflow and performed well.
  * Customization is evaluated on whether the adjustments it applies match the
    adjustments each held out project genuinely needed.
  * Generated configurations are checked by the state machine validator.
"""

import json
import logging
import time
from collections import Counter

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split

from charterloom.catalog import ADJUSTMENT_CODES, ARCHETYPE_BY_KEY, ARCHETYPE_KEYS, REGIME_BY_KEY
from charterloom.knowledge.loader import load_ground_truth
from charterloom.pipeline import CharterloomPipeline
from charterloom.recommender import EXPERTS
from charterloom.retrieval import mean_reciprocal_rank, ndcg_at_k
from charterloom.text import minus

LOGGER = logging.getLogger("charterloom.evaluation")


def rule_baseline(profile):
    """Hand written heuristic baseline mirroring the selection guide."""
    s = profile.signals
    strict = [r for r in profile.regimes if REGIME_BY_KEY[r].strictness >= 2]
    very_strict = [r for r in profile.regimes if REGIME_BY_KEY[r].strictness >= 3]
    if s.get("research_uncertainty", 0) >= 1 or profile.initiative_type == "ml_research":
        return "dual_track_discovery"
    if very_strict or profile.initiative_type == "regulatory_module" or len(strict) >= 2:
        return "regulated_compliance_pipeline"
    if (profile.teams or 1) >= 4:
        return "scaled_release_train"
    if s.get("unplanned_work", 0) >= 1:
        return "kanban_continuous_flow"
    if s.get("change_risk", 0) >= 0.5 or s.get("data_migration", 0) >= 0.5:
        return "incident_change_control"
    if s.get("scope_fixed", 0) >= 0.5 or s.get("hardware", 0) >= 0.5 or s.get("vendor_dependency", 0) >= 1:
        return "stage_gate_waterfall"
    if 0 < (profile.team_size or 0) <= 6 and s.get("unplanned_work", 0) > 0:
        return "scrumban_hybrid"
    return "scrum_product_delivery"


def expected_calibration_error(probs, y, bins=15):
    confidence = probs.max(axis=1)
    correct = (probs.argmax(axis=1) == y).astype(float)
    edges = np.linspace(0.0, 1.0, bins + 1)
    ece, table = 0.0, []
    for lo, hi in zip(edges[:bins], edges[1:]):
        mask = (confidence > lo) & (confidence <= hi)
        if mask.any():
            gap = abs(minus(correct[mask].mean(), confidence[mask].mean()))
            ece += mask.mean() * gap
            table.append({"bin_low": round(float(lo), 3), "bin_high": round(float(hi), 3), "count": int(mask.sum()),
                          "confidence": round(float(confidence[mask].mean()), 4),
                          "accuracy": round(float(correct[mask].mean()), 4)})
    return float(ece), table


def multiclass_brier(probs, y):
    onehot = np.eye(probs.shape[1])[y]
    return float(np.mean(np.sum(np.square(minus(probs, onehot)), axis=1)))


def classification_summary(probs, y):
    pred = probs.argmax(axis=1)
    order = np.argsort(np.negative(probs), axis=1)
    ece, _ = expected_calibration_error(probs, y)
    return {
        "accuracy": round(float(accuracy_score(y, pred)), 4),
        "macro_f1": round(float(f1_score(y, pred, average="macro")), 4),
        "weighted_f1": round(float(f1_score(y, pred, average="weighted")), 4),
        "top2_accuracy": round(float(np.mean([y[i] in order[i, :2] for i in range(len(y))])), 4),
        "top3_accuracy": round(float(np.mean([y[i] in order[i, :3] for i in range(len(y))])), 4),
        "log_loss": round(float(log_loss(y, probs, labels=range(probs.shape[1]))), 4),
        "brier": round(multiclass_brier(probs, y), 4),
        "ece": round(ece, 4),
    }


def hard_summary(pred, y):
    return {
        "accuracy": round(float(accuracy_score(y, pred)), 4),
        "macro_f1": round(float(f1_score(y, pred, average="macro")), 4),
        "weighted_f1": round(float(f1_score(y, pred, average="weighted")), 4),
    }


def set_metrics(predicted_sets, true_sets, codes=ADJUSTMENT_CODES):
    tp = fp = fn = 0
    per_code = {c: Counter() for c in codes}
    for pred, true in zip(predicted_sets, true_sets):
        for c in codes:
            p, t = c in pred, c in true
            per_code[c]["tp"] += p and t
            per_code[c]["fp"] += p and not t
            per_code[c]["fn"] += t and not p
        tp += len(pred & true)
        fp += len(minus(pred, true))
        fn += len(minus(true, pred))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    exact = float(np.mean([p == t for p, t in zip(predicted_sets, true_sets)]))
    codes_out = {}
    for c, k in per_code.items():
        cp = k["tp"] / (k["tp"] + k["fp"]) if k["tp"] + k["fp"] else 0.0
        cr = k["tp"] / (k["tp"] + k["fn"]) if k["tp"] + k["fn"] else 0.0
        codes_out[c] = {"precision": round(cp, 4), "recall": round(cr, 4),
                        "f1": round(2 * cp * cr / (cp + cr), 4) if cp + cr else 0.0,
                        "support": int(k["tp"] + k["fn"])}
    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4),
            "exact_set_match": round(exact, 4), "per_adjustment": codes_out}


def run_evaluation(settings, kb, max_configurations=None):
    started = time.perf_counter()
    truth = load_ground_truth(settings.knowledge_base_dir)
    if not truth:
        raise FileNotFoundError("Latent ground truth labels are missing; regenerate the knowledge base.")
    ids = kb.project_ids()
    strata = [truth[i]["optimal_workflow"] for i in ids]
    train_ids, test_ids = train_test_split(ids, test_size=settings.test_fraction, stratify=strata,
                                           random_state=settings.random_seed)
    LOGGER.info("Training on %d projects, holding out %d", len(train_ids), len(test_ids))
    train_kb = kb.subset(train_ids)
    pipeline = CharterloomPipeline(settings).fit(train_kb)

    test_records = [b for b in kb.blueprints if b["project_id"] in set(test_ids)]
    charters = [b["charter"] for b in test_records]
    profiles = [pipeline.extractor.profile(c) for c in charters]
    features = np.vstack([pipeline.extractor.vector(p) for p in profiles])
    embeddings = pipeline.embedder.transform(charters)
    experts = pipeline.recommender.expert_probabilities(embeddings, features)
    blended = pipeline.recommender.blend(experts)

    high_mask = np.array([b["high_performing"] for b in test_records])
    y_used = np.array([ARCHETYPE_KEYS.index(b["workflow_archetype"]) for b in test_records])
    y_opt = np.array([ARCHETYPE_KEYS.index(truth[b["project_id"]]["optimal_workflow"]) for b in test_records])
    rules = np.array([ARCHETYPE_KEYS.index(rule_baseline(p)) for p in profiles])
    train_high = [b for b in train_kb.blueprints if b["high_performing"]]
    majority = Counter(b["workflow_archetype"] for b in train_high).most_common(1)[0][0]
    majority_pred = np.full(len(test_records), ARCHETYPE_KEYS.index(majority))

    yh = y_used[high_mask]
    models = {"Charterloom blended": classification_summary(blended[high_mask], yh)}
    for name in EXPERTS:
        models[f"{name.capitalize()} expert only"] = classification_summary(experts[name][high_mask], yh)
    models["Keyword rules baseline"] = hard_summary(rules[high_mask], yh)
    models["Majority class baseline"] = hard_summary(majority_pred[high_mask], yh)

    pred = blended.argmax(axis=1)
    precision, recall, f1, support = precision_recall_fscore_support(yh, pred[high_mask], labels=range(len(ARCHETYPE_KEYS)),
                                                                     zero_division=0)
    per_class = {ARCHETYPE_KEYS[i]: {"precision": round(float(precision[i]), 4), "recall": round(float(recall[i]), 4),
                                     "f1": round(float(f1[i]), 4), "support": int(support[i])}
                 for i in range(len(ARCHETYPE_KEYS))}
    cm = confusion_matrix(yh, pred[high_mask], labels=range(len(ARCHETYPE_KEYS)))
    ece, reliability = expected_calibration_error(blended[high_mask], yh)

    confidence = blended.max(axis=1)
    review = confidence < settings.abstention_threshold
    keep = high_mask & ~review
    abstention = {
        "threshold": settings.abstention_threshold,
        "coverage": round(float(keep.sum() / max(1, high_mask.sum())), 4),
        "accuracy_when_confident": round(float((pred[keep] == y_used[keep]).mean()) if keep.any() else 0.0, 4),
        "accuracy_when_flagged": round(float((pred[high_mask & review] == y_used[high_mask & review]).mean())
                                       if (high_mask & review).any() else 0.0, 4),
    }
    oracle = {
        "blended_vs_optimal_all_projects": round(float((pred == y_opt).mean()), 4),
        "rules_vs_optimal_all_projects": round(float((rules == y_opt).mean()), 4),
        "historical_adoption_vs_optimal": round(float((y_used == y_opt).mean()), 4),
    }

    retrieval = evaluate_retrieval(pipeline, test_records, embeddings, features, high_mask)
    adjustments = evaluate_adjustments(pipeline, test_records, profiles, embeddings, features, truth)
    configs = evaluate_configurations(pipeline, test_records, max_configurations)

    report = {
        "protocol": {
            "projects": len(ids), "train_projects": len(train_ids), "test_projects": len(test_ids),
            "test_high_performing": int(high_mask.sum()),
            "training_high_performing": len(train_high),
            "split": "stratified by latent optimal workflow, whole projects held out",
            "seed": settings.random_seed,
        },
        "recommendation": {
            "models": models,
            "per_class": per_class,
            "confusion_matrix": {"labels": list(ARCHETYPE_KEYS), "matrix": cm.tolist()},
            "reliability": reliability,
            "ece": round(ece, 4),
            "abstention": abstention,
            "oracle_agreement": oracle,
            "blend_weights": pipeline.recommender.weights,
            "training_diagnostics": pipeline.recommender.diagnostics,
        },
        "retrieval": retrieval,
        "customization": adjustments,
        "configurations": configs,
        "evaluation_seconds": round(minus(time.perf_counter(), started), 1),
    }
    return report, pipeline


def evaluate_retrieval(pipeline, test_records, embeddings, features, high_mask, k=10):
    """Precedent retrieval quality: do neighbours share the workflow and perform well?"""
    index = pipeline.project_index
    train_labels = np.array([b["workflow_archetype"] for b in index.blueprints])
    train_high = np.array([b["high_performing"] for b in index.blueprints])
    charter_embeddings = np.vstack([index.vectors])
    dense_only = pipeline.embedder.transform([b["charter"] for b in index.blueprints])
    project_vectors = pipeline.space.transform(embeddings, features)
    variants = {"Hybrid project space": [], "Semantic embedding only": [], "BM25 plus dense text RRF": []}
    for i in np.flatnonzero(high_mask):
        label = test_records[i]["workflow_archetype"]
        relevant_total = int(((train_labels == label) & train_high).sum())
        sims = charter_embeddings @ project_vectors[i]
        top = np.argsort(np.negative(sims), kind="stable")[:k]
        variants["Hybrid project space"].append([bool(train_labels[j] == label and train_high[j]) for j in top])
        sims = dense_only @ embeddings[i]
        top = np.argsort(np.negative(sims), kind="stable")[:k]
        variants["Semantic embedding only"].append([bool(train_labels[j] == label and train_high[j]) for j in top])
        hits = pipeline.retriever.search(test_records[i]["charter"], top_k=k, doc_types=["blueprint"],
                                         query_embedding=embeddings[i])
        variants["BM25 plus dense text RRF"].append(
            [bool(h.metadata["workflow_archetype"] == label and h.metadata["high_performing"]) for h in hits])
        variants.setdefault("_totals", []).append(relevant_total)
    totals = variants.pop("_totals")
    out = {}
    for name, lists in variants.items():
        out[name] = {
            "precision_at_5": round(float(np.mean([sum(l[:5]) / 5 for l in lists])), 4),
            "precision_at_10": round(float(np.mean([sum(l[:10]) / 10 for l in lists])), 4),
            "mrr": round(mean_reciprocal_rank(lists), 4),
            "ndcg_at_10": round(float(np.mean([ndcg_at_k(l, 10, t) for l, t in zip(lists, totals)])), 4),
        }
    return out


def evaluate_adjustments(pipeline, test_records, profiles, embeddings, features, truth):
    """Adjustment selection versus the adjustments each project genuinely needed."""
    customizer = pipeline.customizer
    vectors = pipeline.space.transform(embeddings, features)
    variants = {"Charterloom evidence plus priors": [], "Charter priors only": [], "Post mortem evidence only": []}
    true_sets = []
    for record, profile, vector in zip(test_records, profiles, vectors):
        priors = pipeline.extractor.adjustment_priors(profile)
        hits = pipeline.project_index.post_mortem_hits(vector, pipeline.settings.post_mortem_top_k)
        scored = customizer.score_adjustments(priors, hits, profile.regimes)
        variants["Charterloom evidence plus priors"].append({a["code"] for a in scored if a["applied"]})
        variants["Charter priors only"].append({a["code"] for a in scored
                                                if a["mandated_by_regime"] or a["charter_prior"] >= 0.5})
        variants["Post mortem evidence only"].append({a["code"] for a in scored
                                                      if a["mandated_by_regime"] or a["evidence_support"] >= 0.35})
        true_sets.append(set(truth[record["project_id"]]["needed_adjustments"]))
    return {name: set_metrics(sets, true_sets) for name, sets in variants.items()}


def evaluate_configurations(pipeline, test_records, limit=None):
    records = test_records if limit is None else test_records[:limit]
    valid, latencies, added_states, added_triggers, review_flags, warnings = 0, [], [], [], 0, 0
    archetype_counts = Counter()
    for record in records:
        result = pipeline.recommend(record["charter"])
        config = result["configuration"]
        valid += config["validation"]["valid"]
        warnings += len(config["validation"]["warnings"])
        latencies.append(result["latency_ms"])
        base_states = len(pipeline_template_states(config["workflow"]["archetype"]))
        added_states.append(minus(len(config["states"]), base_states))
        added_triggers.append(sum(1 for c in config["changelog"] if c["change"].startswith("Added automation")))
        review_flags += result["recommendation"]["needs_human_review"]
        archetype_counts[config["workflow"]["archetype"]] += 1
    return {
        "configurations_generated": len(records),
        "valid_rate": round(valid / max(1, len(records)), 4),
        "warnings_total": warnings,
        "mean_gates_added": round(float(np.mean(added_states)), 3),
        "mean_automations_added": round(float(np.mean(added_triggers)), 3),
        "flagged_for_review_rate": round(review_flags / max(1, len(records)), 4),
        "latency_ms_p50": round(float(np.percentile(latencies, 50)), 1),
        "latency_ms_p95": round(float(np.percentile(latencies, 95)), 1),
        "recommended_archetypes": {ARCHETYPE_BY_KEY[k].display_name: v for k, v in archetype_counts.most_common()},
    }


def pipeline_template_states(archetype):
    from charterloom.knowledge.templates import build_template

    return build_template(archetype)["states"]


def write_report(report, reports_dir):
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / "evaluation.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf8")
    return path
