"""Canonical vocabularies shared across the whole system.

The catalog defines the workflow archetypes the recommendation head predicts,
the regulatory regimes the feature extractor detects and the workflow
adjustments the customizer can apply. Keeping them in one module guarantees
that the knowledge base generator, the models and the API all speak the same
language.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Archetype:
    key: str
    display_name: str
    family: str
    summary: str


ARCHETYPES = (
    Archetype(
        "scrum_product_delivery",
        "Agile Scrum Product Delivery",
        "iterative",
        "Fixed length sprints for evolving product features with a single accountable product owner.",
    ),
    Archetype(
        "kanban_continuous_flow",
        "Kanban Continuous Flow",
        "flow",
        "Pull based flow with explicit WIP limits and classes of service for maintenance and support.",
    ),
    Archetype(
        "regulated_compliance_pipeline",
        "Regulated Compliance Pipeline",
        "controlled",
        "Traceable, signature gated lifecycle for modules subject to strict regulatory oversight.",
    ),
    Archetype(
        "stage_gate_waterfall",
        "Stage Gate Phased Delivery",
        "phased",
        "Sequential phases separated by formal governance gates for fixed scope and hardware work.",
    ),
    Archetype(
        "scaled_release_train",
        "Scaled Agile Release Train",
        "iterative",
        "Programme increment planning across many teams with shared cadence and dependency control.",
    ),
    Archetype(
        "dual_track_discovery",
        "Dual Track Discovery and Delivery",
        "experimental",
        "Hypothesis driven discovery feeding a delivery track, suited to research and ML work.",
    ),
    Archetype(
        "scrumban_hybrid",
        "Scrumban Hybrid Flow",
        "flow",
        "Planning on demand with flow limits for teams that mix roadmap work with interrupts.",
    ),
    Archetype(
        "incident_change_control",
        "Change Controlled Operations",
        "controlled",
        "Risk assessed, CAB approved change lifecycle for production infrastructure and migrations.",
    ),
)

ARCHETYPE_KEYS = tuple(a.key for a in ARCHETYPES)
ARCHETYPE_BY_KEY = {a.key: a for a in ARCHETYPES}


@dataclass(frozen=True)
class Regime:
    key: str
    display_name: str
    strictness: int
    jurisdiction: str
    patterns: tuple


REGIMES = (
    Regime("gdpr", "UK GDPR and the Data Protection Act 2018", 1, "UK and EU",
           ("gdpr", "data protection act", "general data protection")),
    Regime("hipaa", "HIPAA Privacy and Security Rules", 2, "United States",
           ("hipaa", "protected health information")),
    Regime("sox", "Sarbanes Oxley Section 404 internal controls", 2, "United States",
           ("sarbanes oxley", "sox ", "sox,", "sox.", "section 404")),
    Regime("pci_dss", "PCI DSS v4.0", 2, "Global card schemes",
           ("pci dss", "cardholder data", "payment card industry")),
    Regime("iso_27001", "ISO/IEC 27001 information security controls", 1, "International",
           ("iso/iec 27001", "iso 27001", "information security management system")),
    Regime("cfr_part_11", "FDA 21 CFR Part 11 electronic records and signatures", 3, "United States",
           ("21 cfr part 11", "part 11", "electronic signatures")),
    Regime("iec_62304", "IEC 62304 medical device software lifecycle", 3, "International",
           ("iec 62304", "software of unknown provenance", "medical device software")),
    Regime("iso_13485", "ISO 13485 quality management system", 3, "International",
           ("iso 13485", "design history file", "quality management system")),
    Regime("dora", "the EU Digital Operational Resilience Act", 2, "European Union",
           ("digital operational resilience", "dora ", "dora,", "dora.")),
    Regime("nis2", "the NIS2 Directive", 2, "European Union",
           ("nis2", "network and information systems directive")),
    Regime("fca_consumer_duty", "the FCA Consumer Duty", 1, "United Kingdom",
           ("consumer duty", "fca ")),
    Regime("wcag", "WCAG 2.2 AA and the Public Sector Bodies Accessibility Regulations", 1, "United Kingdom",
           ("wcag", "accessibility regulations", "public sector bodies accessibility")),
    Regime("mifid", "MiFID II record keeping obligations", 2, "European Union and UK",
           ("mifid", "markets in financial instruments")),
)

REGIME_BY_KEY = {r.key: r for r in REGIMES}


@dataclass(frozen=True)
class Adjustment:
    code: str
    title: str
    kind: str
    description: str
    feature_cue: str


ADJUSTMENTS = (
    Adjustment("ADD_SECURITY_REVIEW", "Security review gate", "gate",
               "Insert an independent security review state before release with a security engineer approval.",
               "security_sensitive"),
    Adjustment("ADD_PRIVACY_REVIEW", "Privacy impact assessment gate", "gate",
               "Insert a data protection impact assessment state before personal data processing goes live.",
               "personal_data"),
    Adjustment("ADD_UAT_STAGE", "User acceptance testing stage", "gate",
               "Insert a client facing acceptance testing state with formal signoff by the accepting party.",
               "external_client"),
    Adjustment("ADD_DATA_MIGRATION_REHEARSAL", "Migration rehearsal stage", "gate",
               "Insert a full dress rehearsal of the data migration with reconciliation evidence.",
               "data_migration"),
    Adjustment("ADD_ACCESSIBILITY_REVIEW", "Accessibility review gate", "gate",
               "Insert an accessibility audit against WCAG 2.2 AA before public release.",
               "public_facing"),
    Adjustment("ADD_PERFORMANCE_TEST", "Performance testing stage", "gate",
               "Insert load and soak testing against forecast peak demand before release.",
               "high_traffic"),
    Adjustment("ADD_MODEL_VALIDATION", "Model validation gate", "gate",
               "Insert independent model validation covering bias, drift and performance thresholds.",
               "ml_component"),
    Adjustment("ADD_VENDOR_CHECKPOINT", "Vendor acceptance checkpoint", "gate",
               "Insert a vendor deliverable acceptance state with contract conformance checks.",
               "vendor_dependency"),
    Adjustment("ADD_DEPENDENCY_SYNC", "Cross team dependency synchronisation", "trigger",
               "Schedule a weekly dependency sync and escalate items blocked on another team.",
               "multi_team"),
    Adjustment("TIGHTEN_WIP", "Tighter WIP limits", "parameter",
               "Reduce work in progress limits by a quarter to protect flow under interrupt load.",
               "unplanned_work"),
    Adjustment("ADD_SPIKE_TIMEBOX", "Timeboxed research spikes", "trigger",
               "Attach a timebox to research items and force a continue or stop decision on expiry.",
               "research_uncertainty"),
    Adjustment("ADD_ROLLBACK_PLAN", "Mandatory rollback plan", "guard",
               "Require a tested rollback plan before any production release transition.",
               "production_critical"),
    Adjustment("ADD_FEATURE_FLAGS", "Feature flag release control", "guard",
               "Require customer facing changes to ship dark behind a feature flag.",
               "continuous_deployment"),
    Adjustment("ADD_DEFINITION_OF_READY", "Definition of ready guard", "guard",
               "Require acceptance criteria and an estimate before work is pulled into delivery.",
               "requirements_volatility"),
    Adjustment("ADD_STAKEHOLDER_DEMO", "Stakeholder demonstration ceremony", "ceremony",
               "Add a recurring demonstration for the wider stakeholder group.",
               "many_stakeholders"),
)

ADJUSTMENT_CODES = tuple(a.code for a in ADJUSTMENTS)
ADJUSTMENT_BY_CODE = {a.code: a for a in ADJUSTMENTS}

# Regimes that make particular adjustments mandatory regardless of evidence.
REGIME_MANDATED_ADJUSTMENTS = {
    "gdpr": ("ADD_PRIVACY_REVIEW",),
    "hipaa": ("ADD_PRIVACY_REVIEW", "ADD_SECURITY_REVIEW"),
    "pci_dss": ("ADD_SECURITY_REVIEW",),
    "iso_27001": ("ADD_SECURITY_REVIEW",),
    "dora": ("ADD_ROLLBACK_PLAN",),
    "nis2": ("ADD_SECURITY_REVIEW",),
    "wcag": ("ADD_ACCESSIBILITY_REVIEW",),
}
