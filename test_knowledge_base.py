"""Knowledge base generation and loading."""

from charterloom.catalog import ADJUSTMENT_CODES, ARCHETYPE_KEYS
from charterloom.knowledge.generator import KnowledgeBaseGenerator
from charterloom.knowledge.loader import load_ground_truth


def test_generation_is_deterministic(settings):
    first = KnowledgeBaseGenerator(settings).generate()
    second = KnowledgeBaseGenerator(settings).generate()
    assert [b["charter"] for b in first["blueprints"][:20]] == [b["charter"] for b in second["blueprints"][:20]]


def test_documents_cover_all_families(kb):
    stats = kb.stats()
    assert set(stats["by_type"]) == {"blueprint", "post_mortem", "methodology", "workflow_template"}
    assert stats["by_type"]["methodology"] >= 20
    assert stats["by_type"]["workflow_template"] == len(ARCHETYPE_KEYS)


def test_every_archetype_has_high_performers(kb):
    present = {b["workflow_archetype"] for b in kb.blueprints if b["high_performing"]}
    assert present == set(ARCHETYPE_KEYS)


def test_post_mortems_align_with_blueprints(kb):
    for b in kb.blueprints[:50]:
        pm = kb.post_mortem_for(b["project_id"])
        assert pm is not None
        assert set(pm["recommended_adjustments"]) <= set(ADJUSTMENT_CODES)


def test_ground_truth_is_separate_and_complete(settings, kb):
    truth = load_ground_truth(settings.knowledge_base_dir)
    assert set(truth) == set(kb.project_ids())
    assert all(row["optimal_workflow"] in ARCHETYPE_KEYS for row in truth.values())
    assert all("optimal_workflow" not in b for b in kb.blueprints)


def test_subset_keeps_shared_documents(kb):
    ids = kb.project_ids()[:10]
    small = kb.subset(ids)
    assert len(small.blueprints) == 10
    assert len(small.methodologies) == len(kb.methodologies)
