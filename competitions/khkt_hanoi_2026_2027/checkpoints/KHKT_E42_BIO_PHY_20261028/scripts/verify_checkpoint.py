#!/usr/bin/env python3
"""Independent offline verification of the frozen KHKT E42 archive."""
import argparse,hashlib,io,json,sys,zipfile
from pathlib import Path

def digest(b): return hashlib.sha256(b).hexdigest()
def fail(msg): raise ValueError(msg)
def check(ok,msg):
    if not ok: fail(msg)
def jsonbytes(b): return json.loads(b.decode('utf-8-sig'))
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default=str(Path(__file__).resolve().parents[1]));a=p.parse_args()
    root=Path(a.root); m=json.loads((root/'checkpoint/MANIFEST.json').read_text(encoding='utf-8'))
    for rec in m['contents']:
        q=root/rec['path'];check(q.is_file(),'missing '+str(q));check(q.stat().st_size==rec['size'],'size mismatch '+str(q));check(digest(q.read_bytes())==rec['sha256'],'sha mismatch '+str(q))
    archive=(root/'checkpoint/evidence/EXAMTRUST_E42_VERIFIED_CROSS_SUBJECT_FINAL.zip').read_bytes()
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        check(z.testzip() is None,'final ZIP CRC'); cross=jsonbytes(z.read('VERIFIED/CROSS_SUBJECT_VERIFICATION.json'))
        check(cross==json.loads((root/'checkpoint/CROSS_SUBJECT_VERIFICATION.json').read_text(encoding='utf-8')),'snapshot JSON mismatch')
        e42=z.read('VERIFIED/E42_ORIGINAL_UNMODIFIED.zip'); check(digest(e42)==m['original_e42_sha256'],'E42 SHA mismatch')
        with zipfile.ZipFile(io.BytesIO(e42)) as ez:
            check(ez.testzip() is None,'E42 CRC')
            e10=ez.read('E42/02_PHYSICS_HISTORICAL/EXAMTRUST_E10_PHYSICS_COMPARISON.zip')
            check(digest(e10)==m['physics_e10_sha256'],'E10 SHA mismatch')
            v=jsonbytes(ez.read('E42/01_BIOLOGY_APPROVED/ENGINE_RUN/05_POST_VERIFICATION/QC_PILOT_01_A1_VERIFICATION.json'))
            t=jsonbytes(ez.read('E42/01_BIOLOGY_APPROVED/ENGINE_RUN/07_HUMAN_REVIEW/QC_PILOT_01_A1_REVIEW_RECORD.json'))
            s=jsonbytes(ez.read('E42/01_BIOLOGY_APPROVED/ENGINE_RUN/STATE/QC_PILOT_01.json'))
            check(v['result']['verdict']=='PASS' and v['result']['grounding_verdict']=='PASS','BIO verification')
            check(t['teacher_status']=='TEACHER_APPROVED' and t['ready_for_use'] is True,'BIO teacher review')
            check(s['status']=='APPROVED','BIO state')
            check(t['final_item']['correct_answer']=='A','BIO answer')
        with zipfile.ZipFile(io.BytesIO(e10)) as pz:
            check(pz.testzip() is None,'E10 CRC')
            phys=jsonbytes(pz.read('E10/ORIGINAL_JSON/BTC_ADVANCED_FINAL_V2.json'))
            manifest10=jsonbytes(pz.read('E10/E10_SHA256_MANIFEST.json'))
            # Show original manifest as evidence, do not assume unknown schema.
            print('E10 manifest structure:',type(manifest10).__name__)
    check(cross['biology']['postgen_verdict']=='PASS' and cross['biology']['teacher_status']=='TEACHER_APPROVED','cross BIO summary')
    check(cross['physics']['v1_postgen']=='SOURCE_EVIDENCE_FAIL' and cross['physics']['v2_postgen']=='SOURCE_EVIDENCE_PASS','cross PHY summary')
    print('PASS: checkpoint file hashes, nested ZIP CRC, E42/E10 SHA, BIO verifier/approval, PHY archive summary')
    print('NOTE: archival verification only; not a new engine run or Gemini regeneration.')
    return 0
if __name__=='__main__':
    try: sys.exit(main())
    except Exception as e: print('HOLD:',str(e),file=sys.stderr);sys.exit(1)
