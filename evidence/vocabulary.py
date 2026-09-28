"""The evidence vocabulary: one place that defines what each word is allowed to mean.

Every label the reviewer prints comes from here. Evidence classes form a ladder,
but a higher rung is never reached by relabeling: physical classes only count
toward a claim's support when a human-accepted session backs them (see
records.validate), and synthetic data never supports physical behavior.
"""

# Artifact evidence classes. "rank" orders what an artifact can demonstrate.
# Physical ranks are only honored for artifacts tied to a human-accepted session.
EVIDENCE_CLASSES = {
    "specification": {
        "rank": 0, "label": "SPECIFICATION", "physical": False,
        "meaning": "Authored requirement, boundary, note, or historical claim. States intent; demonstrates nothing."},
    "implementation": {
        "rank": 1, "label": "IMPLEMENTATION", "physical": False,
        "meaning": "Source code, CAD source, model input, or configuration. Shows what was built, not how it behaves."},
    "test_procedure": {
        "rank": 1, "label": "TEST PROCEDURE", "physical": False,
        "meaning": "Automated test source. A procedure, not a record that it ran or passed."},
    "synthetic": {
        "rank": 1, "label": "SYNTHETIC", "physical": False,
        "meaning": "Fabricated data that exercises tooling. Can never support a physical or performance claim."},
    "analytical": {
        "rank": 2, "label": "ANALYTICAL", "physical": False,
        "meaning": "Output of a deterministic calculation. Only as good as its formulation and inputs."},
    "simulated": {
        "rank": 2, "label": "SIMULATED", "physical": False,
        "meaning": "Output of a numerical or stochastic simulation. Not an observation of hardware."},
    "execution_record": {
        "rank": 3, "label": "SOFTWARE VERIFIED", "physical": False,
        "meaning": "A recorded run of automated checks. Shows software checks ran and passed, not that hardware works."},
    "bench_observed": {
        "rank": 4, "label": "BENCH OBSERVED", "physical": True,
        "meaning": "Inert physical observation without a calibrated instrument (photo, video, operator log)."},
    "bench_measured": {
        "rank": 5, "label": "BENCH MEASURED", "physical": True,
        "meaning": "Inert physical measurement with a named instrument, method, and uncertainty."},
}

# Classes the catalog refuses outright: they sit outside the validation boundary.
FORBIDDEN_CLASSES = {
    "field_measured": "Field, flight, and live-propulsion data are outside this repository's validation boundary.",
    "flight": "Field, flight, and live-propulsion data are outside this repository's validation boundary.",
    "physical": "Use bench_observed or bench_measured, each backed by a human-accepted session record.",
    "verified": "'Verified' names no scope. Use a class that says what was checked.",
}

# Derived support level for a claim: the strongest rung its *accepted* evidence reaches.
SUPPORT_LEVELS = [
    ("none", "NO SUPPORTING EVIDENCE"),
    ("implementation", "IMPLEMENTATION ONLY"),
    ("model", "MODEL ONLY"),
    ("software", "SOFTWARE VERIFIED"),
    ("bench_observed", "BENCH OBSERVED"),
    ("bench_measured", "BENCH MEASURED"),
    ("independently_reviewed", "INDEPENDENTLY REVIEWED"),
]
SUPPORT_LABELS = dict(SUPPORT_LEVELS)

# Authored claim status. Validated against requirements, concerns, and discrepancies.
CLAIM_STATUSES = {
    "open": ("UNRESOLVED", "An open question, conflict, or missing measurement blocks a stronger statement."),
    "contradicted": ("CONTRADICTED", "Current evidence contradicts the claim or one of its requirements."),
    "supported_within_limits": ("SUPPORTED WITHIN STATED LIMITS",
                                "Evidence supports the statement as worded, at its evidence class only."),
    "superseded": ("SUPERSEDED", "Replaced by another claim; retained for history."),
}

# Validation gates. A claim's authored gate may not exceed what its records show.
GATES = [
    ("analytical_model", "ANALYTICAL MODEL"),
    ("software_reproduction", "SOFTWARE REPRODUCTION"),
    ("synthetic_test", "SYNTHETIC TEST"),
    ("inert_bench_setup", "INERT BENCH SETUP"),
    ("inert_physical_measurement", "INERT PHYSICAL MEASUREMENT"),
    ("repeated_measurement", "REPEATED MEASUREMENT"),
    ("independent_review", "INDEPENDENT REVIEW"),
]
GATE_INDEX = {key: index for index, (key, _) in enumerate(GATES)}
GATE_LABELS = dict(GATES)
# Gates at or beyond this index require human-accepted physical evidence.
PHYSICAL_GATE = GATE_INDEX["inert_physical_measurement"]

# Review freshness, computed by comparing the current tree to the last review record.
FRESHNESS = {
    "current": "CURRENT",
    "never_reviewed": "NEVER REVIEWED",
    "source_changed": "SOURCE CHANGED",
    "statement_changed": "STATEMENT CHANGED",
    "assumption_changed": "ASSUMPTION CHANGED",
    "missing_dependency": "MISSING DEPENDENCY",
}
REVIEW_KINDS = {
    "snapshot": "Recorded by tooling. Detects later change; is not an engineering review.",
    "human": "Recorded by a named human reviewer who inspected the claim and its evidence.",
}

# How a requirement can be checked, and the results each check can produce.
CHECK_TYPES = {
    "machine": "Evaluated automatically from a committed artifact value.",
    "test": "Evaluated from an attached execution record of named automated tests.",
    "human_review": "Needs engineering judgement; software cannot close it.",
    "physical_measurement": "Needs an inert physical measurement; software cannot close it.",
}
REQUIREMENT_RESULTS = {
    "satisfied": "SATISFIED",
    "not_satisfied": "NOT SATISFIED",
    "conflicting": "MODELS DISAGREE",
    "not_evaluable": "NOT EVALUABLE",
    "not_evaluated": "NOT EVALUATED IN THIS BUILD",
    "not_measured": "NOT MEASURED",
    "requires_human_review": "REQUIRES HUMAN REVIEW",
}

# Prediction-versus-measurement comparison results. "Not measured" is never zero.
COMPARISON_RESULTS = {
    "not_measured": "NOT MEASURED",
    "pending_acceptance": "MEASUREMENT PENDING HUMAN ACCEPTANCE",
    "within_criterion": "WITHIN CRITERION",
    "outside_criterion": "OUTSIDE CRITERION",
    "no_criterion": "NO PRE-REGISTERED CRITERION",
    "not_comparable": "NOT COMPARABLE",
}

DISCREPANCY_KINDS = {
    "claim_vs_artifact": "What a claim or note says differs from what its artifact contains.",
    "requirement_vs_model": "A model result does not meet a stated requirement.",
    "model_vs_model": "Two models of the same quantity disagree.",
    "model_vs_input": "A model's inputs differ from the design source it claims to use.",
    "model_tuned_to_target": "Model inputs were revised until a target was met.",
    "implementation_defect": "Software produced values that do not follow from its inputs.",
    "test_vs_requirement": "A test does not check what its name or claim says.",
    "documentation_vs_implementation": "Documentation disagrees with firmware or software behavior.",
    "design_logic": "Two implemented rules cannot both be satisfied in the intended sequence.",
    "simulation_vs_cad": "Simulation or model geometry disagrees with CAD geometry.",
    "cad_vs_as_built": "CAD disagrees with assembled hardware.",
    "telemetry_vs_expected": "Recorded telemetry disagrees with its documented meaning or rate.",
    "bom_vs_design": "The bill of materials disagrees with the design or firmware.",
    "predicted_vs_measured": "A physical measurement disagrees with its registered prediction.",
    "provenance_gap": "An artifact cannot be traced to the model revision that produced it.",
    "measurement_method": "A measurement procedure cannot establish what it is meant to measure.",
}
DISCREPANCY_STATUSES = {
    "open": "OPEN",
    "resolved": "RESOLVED",
    "accepted_limitation": "ACCEPTED LIMITATION",
}
DISCREPANCY_EFFECTS = {
    "contradicts_claim": "Contradicts a claim or requirement",
    "weakens_claim": "Weakens a claim's support",
    "informational": "Informational",
}

# Bench-session ingestion stages. Only a human moves a session to human_accepted.
SESSION_STAGES = {
    "raw": "RAW SESSION — captured, not examined",
    "audited": "AUDITED — data-quality audit attached",
    "review_candidate": "REVIEW CANDIDATE — declaration and audit present; awaiting a human",
    "human_accepted": "HUMAN-ACCEPTED EVIDENCE — a named reviewer accepted it for claim review",
    "rejected": "REJECTED — retained with the reason",
}
SESSION_ORIGINS = {
    "unknown": "Origin not declared",
    "synthetic": "Operator declares the data synthetic",
    "bench": "Operator declares an inert bench capture (a declaration, not proof)",
}

PREREGISTRATION_STATUSES = {
    "proposed": "PROPOSED — drafted by software or a contributor; not yet adopted by a human",
    "registered": "REGISTERED — a named human adopted the question, prediction, and rule before testing",
    "executed": "EXECUTED — a measurement was recorded against the registered rule",
    "withdrawn": "WITHDRAWN — retained with the reason",
}

# What a portable review can and cannot say. Each scope is reported separately.
VERIFICATION_SCOPES = [
    ("bundle_integrity", "BUNDLE INTEGRITY"),
    ("record_schema", "RECORD SCHEMA VALID"),
    ("record_consistency", "RECORD CONSISTENCY"),
    ("requirements_evaluated", "REQUIREMENTS EVALUATED FROM ARTIFACTS"),
    ("software_tests", "SOFTWARE TESTS"),
    ("model_reproduction", "MODEL REPRODUCTION"),
    ("firmware_build", "FIRMWARE BUILD"),
    ("physical_performance", "PHYSICAL PERFORMANCE"),
    ("flight_readiness", "FLIGHT READINESS"),
]

PRINCIPLES = [
    "If the repository says it happened, point to the artifact.",
    "A model is not a measurement.",
    "A clean dataset is not proof of a physical event.",
    "A passing test is not a qualification result.",
    "Unknown is not zero. Missing is not false. Unmeasured is not passed.",
    "Unresolved is a valid engineering state.",
    "The claim works for the evidence, not the other way round.",
]

AI_BOUNDARY = [
    "Automated tools, including AI assistants, may summarize, compare, explain, and propose.",
    "They may not create measurements, relabel synthetic data as physical, edit raw evidence, "
    "fill missing records, register a pre-registration, accept a session, or record a human review.",
    "They have no authority over arming, ignition, launch, or any safety gate.",
    "Confidence is not authority: only a recorded inert measurement accepted by a named human enters the record.",
]


def label(table, key):
    value = table[key]
    return value[0] if isinstance(value, tuple) else value["label"] if isinstance(value, dict) else value
