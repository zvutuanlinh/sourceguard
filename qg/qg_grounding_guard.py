"""
ExamTrust QG Grounding Guard V1

Blocks model generation unless the mandatory grounding review passes.
"""

from pathlib import Path
import json
import hashlib

RULE_ID = "QG_SOURCE_GROUNDING_AND_COMPOSITION_RULE_V1"

REQUIRED_PREGEN_CHECKS = [
    "approved_evidence_verified",
    "coherent_evidence_bundle_confirmed",
    "fact_ledger_complete",
    "number_unit_quantity_ledger_complete",
    "relation_ledger_complete",
    "question_opportunity_valid",
    "multi_source_composition_valid_if_applicable",
    "no_unsupported_fact",
    "no_unsupported_number",
    "no_unsupported_unit",
    "no_unsupported_quantity",
    "no_unsupported_relation",
    "no_external_bridge",
    "no_artificial_complexity",
]

class QGGroundingBlocked(RuntimeError):
    pass

def sha256_file(path):
    path = Path(path)
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def validate_rule(rule):
    if rule.get('rule_id') != RULE_ID:
        raise QGGroundingBlocked('GROUNDING_RULE_ID_MISMATCH')
    if rule.get('state') != 'ACTIVE_RULE':
        raise QGGroundingBlocked('GROUNDING_RULE_NOT_ACTIVE')
    gate = rule.get('pre_generation_grounding_gate', {})
    if gate.get('mandatory') is not True:
        raise QGGroundingBlocked('PREGEN_GROUNDING_GATE_NOT_MANDATORY')
    return True

def validate_grounding_review(review):
    if review.get('schema') != 'examtrust.qg.pregeneration_grounding_review.v1':
        raise QGGroundingBlocked('GROUNDING_REVIEW_SCHEMA_INVALID')
    if review.get('rule_id') != RULE_ID:
        raise QGGroundingBlocked('GROUNDING_REVIEW_RULE_ID_MISMATCH')
    checks = review.get('pre_generation_checks', {})
    missing = [k for k in REQUIRED_PREGEN_CHECKS if k not in checks]
    if missing:
        raise QGGroundingBlocked('GROUNDING_CHECKS_MISSING: ' + ', '.join(missing))
    failed = [k for k in REQUIRED_PREGEN_CHECKS if checks.get(k) is not True]
    if failed:
        raise QGGroundingBlocked('GENERATION_BLOCKED: ' + ', '.join(failed))
    if review.get('decision') != 'PASS_FOR_GENERATION':
        raise QGGroundingBlocked('GROUNDING_REVIEW_NOT_PASS_FOR_GENERATION')
    if review.get('generation_allowed') is not True:
        raise QGGroundingBlocked('GROUNDING_REVIEW_GENERATION_NOT_ALLOWED')
    source_ids = review.get('source_ids', [])
    if not source_ids:
        raise QGGroundingBlocked('NO_APPROVED_SOURCE_IDS')
    if not review.get('fact_ledger'):
        raise QGGroundingBlocked('FACT_LEDGER_EMPTY')
    if not review.get('relation_ledger'):
        raise QGGroundingBlocked('RELATION_LEDGER_EMPTY')
    if len(source_ids) > 1:
        ms = review.get('multi_source_composition_review', {})
        if ms.get('required') is not True:
            raise QGGroundingBlocked('MULTI_SOURCE_REVIEW_REQUIRED')
        required_ms = [
            "M1_each_source_interpretable",
            "M2_relation_source_supported",
            "M3_question_genuinely_requires_relation",
            "M4_no_missing_semantic_bridge",
            "M5_no_quantity_reassignment",
            "M6_no_fragment_stitching",
            "M7_full_solution_path_source_reconstructable",
            "M8_declared_sources_actually_necessary",
        ]
        failed_ms = [k for k in required_ms if ms.get(k) is not True]
        if failed_ms:
            raise QGGroundingBlocked('MULTI_SOURCE_COMPOSITION_FAIL: ' + ', '.join(failed_ms))
        if ms.get('decision') != 'PASS':
            raise QGGroundingBlocked('MULTI_SOURCE_COMPOSITION_NOT_PASS')
    return True

def assert_generation_allowed(rule_path, grounding_review_path):
    rule_path = Path(rule_path)
    grounding_review_path = Path(grounding_review_path)
    rule = load_json(rule_path)
    review = load_json(grounding_review_path)
    validate_rule(rule)
    validate_grounding_review(review)
    return {
        'generation_allowed': True,
        'rule_id': RULE_ID,
        'rule_path': str(rule_path),
        'rule_sha256': sha256_file(rule_path),
        'grounding_review_path': str(grounding_review_path),
        'grounding_review_sha256': sha256_file(grounding_review_path),
        'item_id': review.get('item_id'),
        'source_ids': review.get('source_ids'),
    }
