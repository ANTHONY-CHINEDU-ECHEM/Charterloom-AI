"""Central configuration for Charterloom AI.

Every tunable value used by the knowledge base generator, the retriever, the
recommendation head and the customizer lives in a single ``Settings`` object.
Values can be overridden through ``configs/charterloom.json`` or through a JSON
file referenced by the ``CHARTERLOOM_CONFIG`` environment variable.
"""

import json
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "charterloom.json"
SCHEMA_VERSION = "1.2"


@dataclass
class Settings:
    """Runtime settings for every stage of the Charterloom pipeline."""

    # Locations
    project_root: Path = PROJECT_ROOT
    knowledge_base_dir: Path = PROJECT_ROOT / "data" / "knowledge_base"
    artifacts_dir: Path = PROJECT_ROOT / "artifacts"
    reports_dir: Path = PROJECT_ROOT / "reports"
    examples_dir: Path = PROJECT_ROOT / "examples"

    # Knowledge base synthesis
    random_seed: int = 1014
    n_projects: int = 2400
    first_year: int = 2019
    last_year: int = 2026

    # Semantic embedding (TF IDF followed by latent semantic analysis)
    tfidf_max_features: int = 80000
    tfidf_min_df: int = 2
    tfidf_max_df: float = 0.85
    embedding_dim: int = 256
    svd_iterations: int = 7

    # Hybrid retrieval
    chunk_words: int = 170
    chunk_overlap: int = 40
    bm25_k1: float = 1.4
    bm25_b: float = 0.72
    rrf_k: int = 60
    candidate_pool: int = 200
    evidence_top_k: int = 8
    methodology_top_k: int = 4

    # Recommendation head
    classifier_c: float = 3.0
    classifier_max_iter: int = 4000
    calibration_folds: int = 5
    neighbour_k: int = 30
    neighbour_temperature: float = 0.20
    precedent_feature_weight: float = 2.0
    blend_grid_step: float = 0.05
    abstention_threshold: float = 0.50
    high_performance_quantile: float = 0.50

    # Customizer
    post_mortem_top_k: int = 15
    adjustment_threshold: float = 0.42
    adjustment_evidence_weight: float = 0.55
    adjustment_prior_weight: float = 0.45

    # Evaluation
    test_fraction: float = 0.20

    extra: dict = field(default_factory=dict)

    @property
    def figures_dir(self):
        return self.reports_dir / "figures"

    def to_dict(self):
        payload = asdict(self)
        for key, value in payload.items():
            if isinstance(value, Path):
                payload[key] = str(value)
        return payload


_PATH_FIELDS = {"project_root", "knowledge_base_dir", "artifacts_dir", "reports_dir", "examples_dir"}


def load_settings(path=None, **overrides):
    """Build a ``Settings`` object from defaults, an optional JSON file and keyword overrides.

    Relative paths in the JSON file are resolved against the project root so the
    configuration behaves identically regardless of the working directory.
    """
    settings = Settings()
    candidate = path or os.environ.get("CHARTERLOOM_CONFIG") or DEFAULT_CONFIG_PATH
    candidate = Path(candidate)
    values = {}
    if candidate.exists():
        values.update(json.loads(candidate.read_text(encoding="utf8")))
    values.update(overrides)
    known = {f.name for f in fields(Settings)}
    for key, value in values.items():
        if key.startswith("_"):
            continue
        if key not in known:
            settings.extra[key] = value
            continue
        if key in _PATH_FIELDS and value is not None:
            value = Path(value)
            if not value.is_absolute():
                value = PROJECT_ROOT / value
        setattr(settings, key, value)
    return settings
