#!/usr/bin/env python3

from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]

CP = (
    ROOT
    / 'docs'
    / 'btc'
    / 'final_question_pipeline_v1'
    / 'BTC_FINAL_QUESTION_PIPELINE_CHECKPOINT_V1.json'
)

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''):
            h.update(b)
    return h.hexdigest()

def fail(msg):
    print('FAIL :', msg)
    print('RESULT = HOLD')
    sys.exit(1)

if not CP.exists():
    fail('checkpoint missing')

obj = json.loads(CP.read_text(encoding='utf-8'))

if obj.get('checkpoint_id') != 'BTC-FINAL-P06-P07-P08-QUESTION-PIPELINE-V1':
    fail('checkpoint ID mismatch')

fs = obj.get('final_state', {})

if fs.get('pregen') != 'PASS_FOR_GENERATION':
    fail('pregen mismatch')
if fs.get('postgen') != 'SOURCE_EVIDENCE_PASS':
    fail('postgen mismatch')
if fs.get('cognitive_validation') != 'PASS':
    fail('cognitive validation mismatch')
if fs.get('teacher_review') != 'APPROVED':
    fail('teacher mismatch')
if fs.get('ready_for_use') is not True:
    fail('ready_for_use mismatch')

sha = obj.get('important_sha256', {})

if sha.get('candidate_v1') != 'af504a8336ef754ffa28c7fab0d7fc7d6075572b89e8adbfcf01f87820814dca':
    fail('Candidate V1 SHA mismatch')
if sha.get('postgen_v1_fail') != '7460b8f0ea93f0d7a2a1407c5349230712d326055df0a9f64354bb2437bc4d12':
    fail('Postgen V1 SHA mismatch')
if sha.get('candidate_v2') != '7b5a6a69cf0cc56f55584074faec8d2a1cba8df4029a24d94db42f7fbc59b862':
    fail('Candidate V2 SHA mismatch')
if sha.get('postgen_v2_pass') != 'f0719db4f4256628fb56a580dddc6000fe713b11d90dbd78ff78e660a21ca669':
    fail('Postgen V2 SHA mismatch')

pipeline = obj.get('pipeline', [])

required_states = {
    'RAW_SOURCE_TRUTH': 'PASS',
    'SOURCE_UNIT_CANDIDATE_UNIVERSE': 'PASS',
    'HUMAN_SOURCE_SELECTION': 'PASS',
    'MULTI_SOURCE_COMPOSITION': 'PASS',
    'QUESTION_CONTRACT': 'PASS',
    'PREGEN_GROUNDING': 'PASS_FOR_GENERATION',
    'CONTROLLED_GENERATION_V1': 'STRUCTURAL_PASS',
    'POSTGEN_V1': 'SOURCE_EVIDENCE_FAIL',
    'CONTROLLED_REGENERATION_V2': 'GENERATED',
    'SYNTAX_ONLY_JSON_REPAIR': 'PASS',
    'CANDIDATE_V2_FINALIZATION': 'STRUCTURAL_PASS',
    'POSTGEN_V2': 'SOURCE_EVIDENCE_PASS',
    'COGNITIVE_AND_TEACHER_GATE': 'APPROVED',
    'READY_FOR_USE': 'READY_FOR_USE',
}

actual = {
    row.get('stage'): row.get('result')
    for row in pipeline
}

for stage, wanted in required_states.items():
    if actual.get(stage) != wanted:
        fail(f'{stage}: expected {wanted}, got {actual.get(stage)}')

print('=' * 104)
print('EXAMTRUST AI — FINAL QUESTION PIPELINE CHECKPOINT VERIFIED')
print('=' * 104)
print('RAW SOURCE TRUTH ............. PASS')
print('SOURCE UNIT UNIVERSE ......... PASS')
print('HUMAN SOURCE SELECTION ....... PASS')
print('COMPOSITION .................. PASS')
print('QUESTION CONTRACT ............ PASS')
print('PREGEN ....................... PASS_FOR_GENERATION')
print('CANDIDATE V1 ................. STRUCTURAL_PASS')
print('POSTGEN V1 ................... SOURCE_EVIDENCE_FAIL')
print('CANDIDATE V2 ................. STRUCTURAL_PASS')
print('POSTGEN V2 ................... SOURCE_EVIDENCE_PASS')
print('COGNITIVE .................... PASS')
print('TEACHER ...................... APPROVED')
print('READY FOR USE ................ TRUE')
print()
print('CHECKPOINT SHA256 ............', sha256_file(CP))
print()
print('RESULT = PASS / FINAL_QUESTION_PIPELINE_VERIFIED')
print('=' * 104)
