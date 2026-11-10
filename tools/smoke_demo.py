"""Launch a separate stdlib demo process and verify its HTTP workflow."""
import json,os,socket,subprocess,sys,tempfile,time,urllib.request,urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    start=time.perf_counter()
    with tempfile.TemporaryDirectory() as folder:
        env=os.environ.copy();env.update(MOCK_MODE='1',CLOUD_API_KEY='EMPTY',DB_PATH=str(Path(folder)/'smoke.db'))
        flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
        proc=subprocess.Popen([sys.executable,str(ROOT/'tools/serve_stdlib.py'),'--port',str(port)],cwd=ROOT,env=env,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=flags)
        base=f'http://127.0.0.1:{port}'
        try:
            while True:
                try:
                    with urllib.request.urlopen(base+'/healthz',timeout=1) as r:health=json.load(r)
                    break
                except (OSError,urllib.error.URLError):
                    if time.perf_counter()-start>10:raise RuntimeError('demo did not start within 10 seconds')
                    time.sleep(.05)
            rows=[]
            for query in ['你好','用 Python 写一个带超时的进程池','帮我 review 这段 SQL：select * from orders where status=1']:
                req=urllib.request.Request(base+'/api/chat',data=json.dumps({'query':query}).encode(),headers={'Content-Type':'application/json'})
                with urllib.request.urlopen(req,timeout=5) as r:row=json.load(r)
                assert row['answer'];rows.append({'query':query,'route':row['route'],'model':row['model']})
            with urllib.request.urlopen(base+'/api/stats',timeout=5) as r:stats=json.load(r)
            assert stats['summary']['runs']==3
            result={'date':'2026-11-09','mode':'MOCK, separate process, loopback HTTP',
                'elapsed_seconds':round(time.perf_counter()-start,3),'python':sys.version.split()[0],
                'health':health,'three_inputs':rows,'persisted_requests':3,
                'external_user_validation':False,'fresh_dependency_install':False}
            out=ROOT/'docs/evidence/revision';out.mkdir(exist_ok=True)
            (out/'smoke_demo.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(result,ensure_ascii=False,indent=2))
        finally:
            proc.terminate();proc.communicate(timeout=5)
if __name__=='__main__':main()
