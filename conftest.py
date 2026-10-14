"""Shared fixtures: a small, fast knowledge base and a pipeline trained on it."""

import shutil
from pathlib import Path

import pytest

from charterloom.config import PROJECT_ROOT, load_settings
from charterloom.knowledge.generator import KnowledgeBaseGenerator
from charterloom.knowledge.loader import KnowledgeBase
from charterloom.pipeline import CharterloomPipeline

EXAMPLES = PROJECT_ROOT / "examples" / "charters"


@pytest.fixture(scope="session")
def settings(tmp_path_factory):
    root = tmp_path_factory.mktemp("charterloom")
    kb_dir = root / "knowledge_base"
    shutil.copytree(PROJECT_ROOT / "data" / "knowledge_base" / "methodologies", kb_dir / "methodologies")
    return load_settings(knowledge_base_dir=kb_dir, artifacts_dir=root / "artifacts", reports_dir=root / "reports",
                         n_projects=700, embedding_dim=96, neighbour_k=15, calibration_folds=3)


@pytest.fixture(scope="session")
def kb(settings):
    KnowledgeBaseGenerator(settings).write()
    return KnowledgeBase.load(settings.knowledge_base_dir)


@pytest.fixture(scope="session")
def pipeline(settings, kb):
    return CharterloomPipeline(settings).fit(kb)


@pytest.fixture(scope="session")
def example_charters():
    return {p.stem: p.read_text(encoding="utf8") for p in sorted(Path(EXAMPLES).glob("*.md"))}
