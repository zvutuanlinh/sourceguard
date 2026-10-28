#!/usr/bin/env python3
"""ExamTrust E46 reproduction; no changes to original source index or approvals."""
import argparse, hashlib, html, json, os, re, shutil, sys, tempfile, urllib.parse, urllib.request, zipfile
from pathlib import Path
from datetime import datetime, timezone

def digest(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()

def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p, v):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(v, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
def ensure(c, s):
    if not c: raise RuntimeError('HOLD: ' + s)

def unpack_checked(archive, dst):
    with zipfile.ZipFile(archive) as z:
        ensure(z.testzip() is None, 'Archive CRC failure')
        for info in z.infolist():
            p = Path(info.filename)
            mode = (info.external_attr >> 16) & 0o170000
            ensure(not p.is_absolute() and '..' not in p.parts and mode in (0, 0o100000, 0o040000), 'Unsafe archive member')
        z.extractall(dst)

def manifest_check(root):
    manifest = read(root/'REPLAY_MANIFEST.json')
    files = manifest['files']
    for rel, meta in files.items():
        p = root/'REPLAY'/rel
        ensure(p.is_file() and digest(p) == meta['sha256'] and p.stat().st_size == meta['bytes'], f'Snapshot integrity: {rel}')
    return manifest

def source_check(root):
    map_data = read(root/'REPLAY'/'SOURCE_PATH_MAP.json')
    for item in map_data:
        original = Path(item['original_path'])
        archive = root/'REPLAY'/item['snapshot_path']
        ensure(archive.is_file() and digest(archive)==item['sha256'], 'Saved page mismatch '+item['source_id'])
        # Do not mutate the frozen index. A missing external original is an explicit HOLD.
        ensure(original.is_file() and digest(original)==item['sha256'],
               f'Original page path missing or changed: {original}. Use a controlled path-restoration copy; never overwrite a mismatched file.')

def render_html(item, verdict, root, dest, mode, model=None):
    e = lambda x: html.escape(str(x))
    options = ''.join('<p><strong>'+e(k)+'.</strong> '+e(v)+'</p>' for k,v in item['options'].items())
    imgs = []
    for entry in read(root/'REPLAY'/'SOURCE_PATH_MAP.json'):
        image = root/'REPLAY'/entry['snapshot_path']
        target = dest/'images'/(entry['source_id'] + image.suffix)
        target.parent.mkdir(exist_ok=True,parents=True)
        shutil.copy2(image,target)
        imgs.append(f'<figure><img src="images/{e(target.name)}" style="max-width:100%;max-height:320px"><figcaption>{e(entry["source_id"])}</figcaption></figure>')
    text = f'''<!doctype html><html lang="vi"><meta charset="utf-8"><title>ExamTrust reproduction</title><style>body{{font:16px/1.6 Arial;max-width:1000px;margin:35px auto;padding:12px;color:#17243a}}figure{{display:inline-block;width:30%;vertical-align:top}}code{{background:#eee;padding:2px}}</style><h1>ExamTrust AI - Reproduction</h1><p>Chế độ: <strong>{e(mode)}</strong>; model: {e(model or 'không gọi API')}</p><p>Verifier gốc: <strong>{e(verdict)}</strong></p><h2>Câu hỏi</h2><p>{e(item['question'])}</p>{options}<p><strong>Đáp án: {e(item['correct_answer'])}</strong></p><h2>Giải thích</h2><p>{e(item.get('short_explanation',''))}</p><h2>Các bước giải</h2><ol>{''.join('<li>'+e(s)+'</li>' for s in item.get('minimum_solution_path',[]))}</ol><h2>Ảnh nguồn</h2>{''.join(imgs)}<p>Online outputs are REVIEW_ONLY until independent teacher approval. Offline verifier PASS checks saved, edited item, not independent Gemini regeneration.</p></html>'''
    (dest/'RESULT.html').write_text(text, encoding='utf-8')

def model_list(key):
    result=[]; token=None
    while True:
        q={'pageSize':1000}
        if token: q['pageToken']=token
        request=urllib.request.Request('https://generativelanguage.googleapis.com/v1beta/models?'+urllib.parse.urlencode(q),headers={'x-goog-api-key':key})
        with urllib.request.urlopen(request,timeout=45) as f: data=json.load(f)
        result.extend(data.get('models',[])); token=data.get('nextPageToken')
        if not token: break
    def rank(m):
        name=m.get('name','').lower()
        v=re.search(r'gemini-(\d+)(?:\.(\d+))?',name)
        return (int('flash' in name),int(not any(s in name for s in ['preview','exp'])),int(v.group(1)) if v else 0,int(v.group(2) or 0) if v else 0,name)
    return [x['name'].removeprefix('models/') for x in sorted(result,key=rank,reverse=True) if x.get('name','').startswith('models/gemini-') and 'flash' in x.get('name','').lower() and not any(t in x.get('name','').lower() for t in ['image','audio','tts','live','embedding']) and 'generateContent' in x.get('supportedGenerationMethods',[])]

def main():
    a=argparse.ArgumentParser()
    a.add_argument('--mode',choices=['offline','online'],default='offline')
    a.add_argument('--archive',type=Path,default=Path(__file__).parent/'E45_REPLAY.zip')
    a.add_argument('--output',type=Path,default=Path('E46_OUTPUT'))
    a.add_argument('--max-models',type=int,default=4)
    args=a.parse_args()
    out=args.output.resolve()
    ensure(not out.exists(), 'Output directory exists; do not overwrite')
    out.mkdir(parents=True)
    report={'mode':args.mode,'status':'HOLD','original_replay_archive_sha256':None,'gate':'UNKNOWN','engine_verdict':'NOT_RUN','gemini_called':False,'teacher_approved':False,'ready_for_use':False,'errors':[]}
    try:
        ensure(args.archive.is_file(), 'Missing E45 archive')
        report['original_replay_archive_sha256']=digest(args.archive)
        root=out/'extracted';root.mkdir()
        unpack_checked(args.archive,root)
        manifest=manifest_check(root)
        source_check(root)
        sys.path.insert(0,str(root/'REPLAY'/'engine'))
        from examtrust_qg.pipeline import Pipeline
        from examtrust_qg.source_index import SourceIndex
        index_dir=root/'REPLAY'/'frozen_index'
        ix=SourceIndex(index_dir)
        ensure(ix.index_sha256==manifest['frozen_index_sha256'],'Frozen index hash mismatch')
        cid=manifest['contract_id']
        if args.mode=='offline':
            work=out/'engine_work';shutil.copytree(root/'REPLAY'/'replay_input',work)
            class NoLLM:
                def __getattr__(self,n): raise RuntimeError('Offline prohibits LLM: '+n)
            pipeline=Pipeline(root=work,index_dir=index_dir,client=NoLLM())
            result=pipeline.verify(cid,llm_cross_check=False)
            save(out/'VERIFICATION.json',result)
            v=result['result']; report['engine_verdict']=v.get('verdict','UNKNOWN')
            ensure(v.get('structural_verdict')=='PASS' and v.get('grounding_verdict')=='PASS' and v.get('verdict')=='PASS' and not v.get('findings'), 'Offline verifier FAIL')
            generated=read(work/'04_RAW_GENERATION'/'items'/f'{cid}_A1_GENERATED.json')
            item=generated['generated_item']
            report['status']='OFFLINE_REVERIFICATION_PASS';report['gate']='HISTORICAL_PASS';report['ready_for_use']=False
            render_html(item,report['engine_verdict'],root,out,'offline')
            save(out/'QUESTION.json',item)
            print('QUESTION:',item['question'])
            for k,val in item['options'].items():print(f'{k}. {val}')
            print('ANSWER:',item['correct_answer']);print('REVERIFICATION: PASS')
        else:
            initial=root/'REPLAY'/'online_grounding_pass_run'
            ensure(initial.is_dir(),'Online pre-generation runtime is not included. HOLD: cannot call Gemini from GENERATED state')
            key=os.environ.get('GEMINI_API_KEY')
            ensure(key,'GEMINI_API_KEY environment variable missing')
            available=model_list(key)
            ensure(available,'API returned no supported Flash model')
            from examtrust_qg.llm import GeminiClient
            attempts=[]
            for i,model in enumerate(available[:max(1,min(args.max_models,6))],1):
                work=out/f'online_attempt_{i:02d}';shutil.copytree(initial,work)
                pipe=Pipeline(root=work,index_dir=index_dir,client=None)
                gate=pipe.grounding_gate(cid)
                save(out/f'GATE_{i:02d}.json',gate)
                ensure(gate.get('decision')=='PASS' and gate.get('generation_allowed') is True and not gate.get('failures'),'Pre-generation gate HOLD')
                report['gate']='PASS'
                pipe.client=GeminiClient(model=model,api_key=key,temperature=0.2,retries=1,backoff_s=1)
                report['gemini_called']=True
                try:
                    pipe.generate(cid)
                    result=pipe.verify(cid,llm_cross_check=False)
                    save(out/'VERIFICATION.json',result)
                    item=read(work/'04_RAW_GENERATION'/'items'/f'{cid}_A1_GENERATED.json')['generated_item']
                    save(out/'QUESTION.json',item)
                    report['engine_verdict']=result['result'].get('verdict','UNKNOWN')
                    report['status']='ONLINE_REVIEW_ONLY_'+report['engine_verdict'];report['model']=model
                    render_html(item,report['engine_verdict'],root,out,'online',model)
                    print('ONLINE MODEL:',model,'VERDICT:',report['engine_verdict'])
                    break
                except Exception as exc:
                    message=str(exc);attempts.append({'model':model,'error':message[:400]})
                    if not re.search(r'\b(404|429|503)\b|NOT_FOUND|UNAVAILABLE|RESOURCE_EXHAUSTED',message,re.I):raise
            report['attempts']=attempts
            ensure(report['status'].startswith('ONLINE_REVIEW_ONLY_'),'All models failed')
    except Exception as exc:
        report['errors'].append(str(exc));print('HOLD:',str(exc))
    finally:
        save(out/'RUN_REPORT.json',report)
        print('STATUS:',report['status']);print('OUTPUT:',out/'RESULT.html')
        return 0 if report['status'] in ('OFFLINE_REVERIFICATION_PASS','ONLINE_REVIEW_ONLY_PASS','ONLINE_REVIEW_ONLY_FAIL') else 2
if __name__=='__main__':raise SystemExit(main())
