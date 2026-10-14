"""Retrieval, recommendation, customization and persistence."""

import math

import numpy as np

from charterloom.catalog import ARCHETYPE_KEYS
from charterloom.pipeline import CharterloomPipeline


def test_bm25_and_dense_retrieval_find_methodology(pipeline):
    hits = pipeline.retriever.search("segregation of duties electronic signatures audit trail", top_k=3,
                                     doc_types=["methodology"])
    assert hits
    assert any("Regulat" in h.title or "Compliance" in h.title for h in hits)


def test_retrieval_respects_exclusions(pipeline, kb):
    record = kb.blueprints[0]
    hits = pipeline.retriever.search(record["charter"], top_k=10, doc_types=["blueprint"],
                                     exclude_project_ids={record["project_id"]})
    assert all(h.metadata["project_id"] != record["project_id"] for h in hits)


def test_blend_weights_lie_on_simplex(pipeline):
    weights = pipeline.recommender.weights
    assert math.isclose(sum(weights.values()), 1.0, abs_tol=0.000001)
    assert all(w >= 0 for w in weights.values())


def test_probabilities_are_normalised(pipeline, example_charters):
    texts = list(example_charters.values())
    emb = pipeline.embedder.transform(texts)
    feats = pipeline.extractor.transform(texts)
    probs = pipeline.recommender.predict_proba(emb, feats)
    assert probs.shape == (len(texts), len(ARCHETYPE_KEYS))
    assert np.allclose(probs.sum(axis=1), 1.0)


def test_recommendation_payload_is_complete(pipeline, example_charters):
    result = pipeline.recommend(example_charters["clinical_trial_ecrf_module"])
    assert result["recommendation"]["workflow"] in ARCHETYPE_KEYS
    assert result["configuration"]["validation"]["valid"]
    assert result["rationale"]["methodology_citations"]
    assert result["evidence"]["post_mortems"]
    assert "cfr_part_11" in result["charter_profile"]["regimes"]


def test_regulated_charter_gets_signature_and_audit_controls(pipeline, example_charters):
    config = pipeline.recommend(example_charters["clinical_trial_ecrf_module"])["configuration"]
    release = next(t for t in config["transitions"] if t["key"] == config["anchors"]["release_transition"])
    assert any(g["type"] == "electronic_signature" for g in release["guards"])
    assert any(t["key"] == "audit_trail_every_transition" for t in config["triggers"])


def test_every_example_produces_valid_configuration(pipeline, example_charters):
    for name, text in example_charters.items():
        result = pipeline.recommend(text)
        assert result["configuration"]["validation"]["valid"], (name, result["configuration"]["validation"])


def test_adjustment_threshold_is_calibrated(pipeline):
    calibration = pipeline.customizer.calibration
    assert 0.2 <= calibration["threshold"] <= 0.7
    assert calibration["f1_on_observed_post_mortems"] > 0.4


def test_save_and_load_round_trip(pipeline, settings, example_charters, tmp_path):
    pipeline.save(tmp_path)
    restored = CharterloomPipeline.load(tmp_path)
    text = example_charters["legacy_billing_support"]
    assert restored.recommend(text)["recommendation"]["workflow"] == pipeline.recommend(text)["recommendation"]["workflow"]
