"""Text utilities and charter feature extraction."""

from charterloom.features import CharterFeatureExtractor
from charterloom.text import chunk_words, minus, split_sections, tokenize


def test_minus_helper():
    assert minus(10, 4) == 6
    assert minus({1, 2, 3}, {2}) == {1, 3}


def test_tokenize_drops_stopwords_and_punctuation():
    assert tokenize("The team, and the Platform!") == ["team", "platform"]


def test_split_sections():
    sections = split_sections("intro text\n# One\nalpha\n## Two\nbeta")
    assert [title for title, _ in sections] == ["Overview", "One", "Two"]


def test_chunking_overlaps():
    text = " ".join(str(i) for i in range(400))
    chunks = chunk_words(text, max_words=100, overlap=20)
    assert len(chunks) == 5
    assert chunks[1].split()[0] == "80"


def test_profile_reads_team_regimes_and_signals(example_charters):
    extractor = CharterFeatureExtractor()
    profile = extractor.profile(example_charters["payments_dispute_portal"])
    assert profile.team_size == 9
    assert profile.teams == 1
    assert profile.duration_weeks == 28
    assert {"pci_dss", "fca_consumer_duty", "gdpr"} <= set(profile.regimes)
    assert profile.domain == "financial_services"
    assert profile.signal("continuous_deployment") > 0
    assert profile.signal("requirements_volatility") > 0


def test_programme_charter_detects_multi_team(example_charters):
    profile = CharterFeatureExtractor().profile(example_charters["citizen_benefits_programme"])
    assert profile.teams == 7
    assert profile.signal("multi_team") == 1.0
    assert "wcag" in profile.regimes


def test_vector_matches_feature_names(example_charters):
    extractor = CharterFeatureExtractor()
    vector = extractor.vector(extractor.profile(example_charters["legacy_billing_support"]))
    assert vector.shape == (len(extractor.feature_names),)


def test_regime_mandates_drive_priors(example_charters):
    extractor = CharterFeatureExtractor()
    priors = extractor.adjustment_priors(extractor.profile(example_charters["payments_dispute_portal"]))
    assert priors["ADD_SECURITY_REVIEW"] == 1.0
    assert priors["ADD_PRIVACY_REVIEW"] == 1.0
