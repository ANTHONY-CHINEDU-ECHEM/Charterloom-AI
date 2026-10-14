"""Structured feature extraction from free text project charters.

The extractor turns a charter into an interpretable feature vector: delivery
signals (volatility, interrupt load, research uncertainty, criticality and so
on), team shape, duration, detected regulatory regimes and the business domain.
These features complement the semantic embedding inside the recommendation head
and act as priors for the customizer.
"""

import math
import re
from dataclasses import dataclass, field

import numpy as np

from charterloom.catalog import ADJUSTMENTS, REGIME_BY_KEY, REGIMES, REGIME_MANDATED_ADJUSTMENTS
from charterloom.knowledge.vocabulary import DOMAINS, PROJECT_TYPES
from charterloom.text import normalise

SIGNAL_CUES = {
    "requirements_volatility": ("evolve", "reprioriti", "shaped by usage", "shift every", "emerge through",
                                "do not yet know", "learn from early", "priorities are likely", "competitor"),
    "volatility_medium": ("broadly agreed", "secondary features", "handful expected", "refined as they approach",
                          "core scope is understood"),
    "scope_fixed": ("contractually fixed", "baselined", "fully specified", "formal approval", "agreed in detail",
                    "signed off by the steering", "requirements are stable"),
    "unplanned_work": ("unplanned", "incident", "service request", "service desk", "interrupt", "urgent fix",
                       "support request", "operational request", "without notice", "priority one"),
    "research_uncertainty": ("feasibility", "hypothes", "experiment", "unproven", "approach works",
                             "cannot predict", "data supports", "establish quickly"),
    "multi_team": ("product teams", "platform teams", "teams across", "contribute to the same release",
                   "integrate continuously"),
    "dependencies": ("depend", "cross team", "integration points", "shared services", "programme office"),
    "production_critical": ("outage", "downtime", "critical service", "recovery time objective", "transactions per day",
                            "service levels", "visible to the regulator", "financial penalties"),
    "change_risk": ("change freeze", "change advisory board", "change control", "change window", "implementation plan",
                    "major incidents"),
    "data_migration": ("migrat", "cutover", "legacy platform", "reconciled", "switched off", "decommission"),
    "ml_component": ("machine learning", "model", "predict", "classification", "drift", "trained"),
    "vendor_dependency": ("vendor", "supplier", "technology partner", "fixed price contract", "off the shelf",
                          "hardware partner"),
    "public_facing": ("members of the public", "public channel", "own devices", "citizen", "wide range of needs"),
    "personal_data": ("personal data", "personal information", "identity", "contact details", "patient",
                      "health information", "financial data"),
    "high_traffic": ("requests per second", "peak load", "traffic", "million sessions", "seasonal", "launch day"),
    "many_stakeholders": ("departments", "stakeholder group", "business owners", "executive sponsors",
                          "frontline managers"),
    "fixed_deadline": ("fixed go live", "immovable", "deadline", "penalties apply", "effective date"),
    "continuous_deployment": ("several times per day", "feature flag", "release continuously", "progressive rollout",
                              "shipped daily", "automated pipeline"),
    "external_client": ("client will formally accept", "external customer", "commissioning client",
                        "acceptance environment", "payment milestones", "client"),
    "hardware": ("firmware", "hardware", "physical devices", "tooling is cut", "field deployment",
                 "prototypes arrive"),
}

SIGNAL_NAMES = tuple(SIGNAL_CUES)
DOMAIN_LABELS = {key: spec["label"].lower() for key, spec in DOMAINS.items()}
INITIATIVE_LABELS = {key: spec["label"].lower() for key, spec in PROJECT_TYPES.items()}
SECURITY_REGIMES = {"pci_dss", "iso_27001", "hipaa", "dora", "nis2"}

_TEAM_SIZE = re.compile(r"(\d{1,4})\s+(?:people|engineers|developers|staff|members|colleagues)")
_TEAM_COUNT = re.compile(r"(\d{1,3})\s+(?:product\s+|delivery\s+|platform\s+)?(?:teams|squads)")
_TEAM_COUNT_ALT = re.compile(r"into\s+(\d{1,3})\s+teams?")
_WEEKS = re.compile(r"(\d{1,3})\s+weeks")
_MONTHS = re.compile(r"(\d{1,2})\s+months")
_PERCENT_CAPACITY = re.compile(r"(\d{1,3})\s+percent\s+of\s+(?:team\s+)?capacity")
_SPRINT = re.compile(r"(one|two|three|four|1|2|3|4)\s+week\s+sprints?")
_WORD_NUMBERS = {"one": 1, "two": 2, "three": 3, "four": 4, "1": 1, "2": 2, "3": 3, "4": 4}


@dataclass
class CharterProfile:
    """Interpretable facts extracted from a charter."""

    signals: dict
    team_size: int = None
    teams: int = None
    duration_weeks: int = None
    unplanned_pct: int = None
    sprint_length_days: int = None
    regimes: list = field(default_factory=list)
    domain: str = None
    initiative_type: str = None
    word_count: int = 0

    def signal(self, name):
        return self.signals.get(name, 0.0)

    def to_dict(self):
        return {
            "signals": {k: round(v, 3) for k, v in self.signals.items() if v > 0},
            "team_size": self.team_size,
            "teams": self.teams,
            "duration_weeks": self.duration_weeks,
            "unplanned_pct": self.unplanned_pct,
            "sprint_length_days": self.sprint_length_days,
            "regimes": self.regimes,
            "domain": self.domain,
            "initiative_type": self.initiative_type,
            "word_count": self.word_count,
        }


class CharterFeatureExtractor:
    """Rule based, fully interpretable feature extraction."""

    def __init__(self):
        self.feature_names = self._build_feature_names()

    @staticmethod
    def _build_feature_names():
        names = [f"signal_{s}" for s in SIGNAL_NAMES]
        names += ["log_team_size", "team_size_known", "teams", "small_team", "log_duration_weeks", "long_duration",
                  "unplanned_share", "regime_count", "strict_regime_count", "max_strictness", "security_sensitive",
                  "log_word_count"]
        names += [f"regime_{r.key}" for r in REGIMES]
        names += [f"domain_{d}" for d in DOMAINS]
        names += [f"initiative_{t}" for t in PROJECT_TYPES]
        return names

    def profile(self, text):
        clean = normalise(text)
        signals = {}
        for name, cues in SIGNAL_CUES.items():
            hits = sum(clean.count(cue) for cue in cues)
            signals[name] = min(1.0, hits / 2.0)

        team_size = _first_int(_TEAM_SIZE, clean)
        teams = _first_int(_TEAM_COUNT_ALT, clean) or _first_int(_TEAM_COUNT, clean)
        if teams and teams >= 3:
            signals["multi_team"] = 1.0
        weeks = _first_int(_WEEKS, clean)
        if weeks is None:
            months = _first_int(_MONTHS, clean)
            weeks = int(round(months * 4.33)) if months else None
        unplanned = _first_int(_PERCENT_CAPACITY, clean)
        if unplanned is not None and unplanned >= 35:
            signals["unplanned_work"] = 1.0
        sprint_match = _SPRINT.search(clean)
        sprint_days = _WORD_NUMBERS[sprint_match.group(1)] * 7 if sprint_match else None

        regimes = sorted(r.key for r in REGIMES if any(p in clean + " " for p in r.patterns))
        domain = next((k for k, label in DOMAIN_LABELS.items() if f"domain: {label}" in clean), None)
        initiative = next((k for k, label in INITIATIVE_LABELS.items() if f"initiative type: {label}" in clean), None)

        return CharterProfile(signals=signals, team_size=team_size, teams=teams, duration_weeks=weeks,
                              unplanned_pct=unplanned, sprint_length_days=sprint_days, regimes=regimes,
                              domain=domain, initiative_type=initiative, word_count=len(clean.split()))

    def security_sensitive(self, profile):
        personal = profile.signal("personal_data") > 0
        exposed = profile.signal("public_facing") > 0 or bool(set(profile.regimes) & SECURITY_REGIMES)
        critical_finance = profile.signal("production_critical") > 0 and profile.domain in (
            "financial_services", "insurance", "energy_utilities")
        return 1.0 if (personal and exposed) or critical_finance else 0.0

    def vector(self, profile):
        strictness = [REGIME_BY_KEY[r].strictness for r in profile.regimes]
        values = [profile.signals.get(s, 0.0) for s in SIGNAL_NAMES]
        team_size = profile.team_size or 0
        weeks = profile.duration_weeks or 0
        values += [
            math.log1p(team_size),
            1.0 if profile.team_size else 0.0,
            float(min(profile.teams or 1, 15)),
            1.0 if 0 < team_size <= 6 else 0.0,
            math.log1p(weeks),
            1.0 if weeks >= 40 else 0.0,
            (profile.unplanned_pct or 0) / 100.0,
            float(len(profile.regimes)),
            float(sum(1 for s in strictness if s >= 2)),
            float(max(strictness) if strictness else 0) / 3.0,
            self.security_sensitive(profile),
            math.log1p(profile.word_count),
        ]
        values += [1.0 if r.key in profile.regimes else 0.0 for r in REGIMES]
        values += [1.0 if profile.domain == d else 0.0 for d in DOMAINS]
        values += [1.0 if profile.initiative_type == t else 0.0 for t in PROJECT_TYPES]
        return np.asarray(values, dtype=np.float64)

    def transform(self, texts):
        return np.vstack([self.vector(self.profile(t)) for t in texts])

    def adjustment_priors(self, profile):
        """Evidence strength in [0, 1] for each adjustment based purely on the charter."""
        priors = {}
        for adj in ADJUSTMENTS:
            cue = adj.feature_cue
            if cue == "security_sensitive":
                value = self.security_sensitive(profile)
            elif cue == "multi_team":
                value = max(profile.signal("multi_team"), profile.signal("dependencies"),
                            1.0 if (profile.teams or 1) >= 3 else 0.0)
            elif cue == "unplanned_work":
                value = profile.signal("unplanned_work")
            elif cue == "research_uncertainty":
                value = profile.signal("research_uncertainty")
            elif cue == "requirements_volatility":
                value = profile.signal("requirements_volatility") * (1.0 if (profile.teams or 1) >= 2 else 0.6)
            elif cue == "personal_data":
                value = profile.signal("personal_data") * (1.0 if {"gdpr", "hipaa"} & set(profile.regimes) else 0.5)
            elif cue == "public_facing":
                accessible_context = profile.domain in ("public_sector", "education") or "wcag" in profile.regimes
                value = profile.signal("public_facing") * (1.0 if accessible_context else 0.3)
            elif cue == "continuous_deployment":
                value = profile.signal("continuous_deployment") * (1.0 if profile.signal("public_facing") else 0.5)
            else:
                value = profile.signal(cue)
            priors[adj.code] = float(min(1.0, value))
        for regime in profile.regimes:
            for code in REGIME_MANDATED_ADJUSTMENTS.get(regime, ()):
                priors[code] = 1.0
        return priors


def _first_int(pattern, text):
    match = pattern.search(text)
    return int(match.group(1)) if match else None
