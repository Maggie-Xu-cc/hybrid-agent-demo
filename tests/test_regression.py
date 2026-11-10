"""Regression checks: deterministic provider responses, no paid API calls."""
import os,sys,tempfile,sqlite3,json,threading,urllib.request,urllib.error,unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ.update(MOCK_MODE='1',CLOUD_API_KEY='EMPTY',LOCAL_API_KEY='EMPTY')
from app import agent,store,router,clients
from app.config import settings

class Regression(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.old_db=settings.db_path
        settings.db_path=str(Path(self.temp.name)/'test.db');store.init()
        self.old_escalation=settings.enable_escalation;settings.enable_escalation=True
    def tearDown(self):
        settings.db_path=self.old_db;settings.enable_escalation=self.old_escalation;self.temp.cleanup()
    def row(self):
        with closing(sqlite3.connect(settings.db_path)) as c:
            c.row_factory=sqlite3.Row;return dict(c.execute('SELECT * FROM runs ORDER BY id DESC LIMIT 1').fetchone())
    def test_empty_query_rejected(self):self.assertEqual(agent.run(' '),{'error':'empty query'});self.assertEqual(store.stats()['runs'],0)
    def test_greeting_rule(self):self.assertEqual(router.decide('你好').difficulty,'easy')
    def test_sql_review_guard(self):self.assertEqual(router.decide('帮我 review 这段 SQL：select * from orders where status = 1').difficulty,'hard')
    def test_sql_multiline_guard(self):self.assertEqual(router.decide('SELECT id\nFROM orders').difficulty,'hard')
    def test_sql_definition_not_overmatched(self):self.assertEqual(router.decide('什么是SQL？').difficulty,'easy')
    def test_code_rule(self):self.assertEqual(router.decide('```python\nx=1\n```').difficulty,'hard')
    def test_long_rule(self):self.assertEqual(router.decide('测'*301).difficulty,'hard')
    def test_bad_json_preserves_usage(self):
        with patch.object(router,'call_local',return_value=('not JSON',71,9)):
            r=router._model_route('普通请求内容'*6)
        self.assertEqual((r.by,r.tokens_in,r.tokens_out),('default',71,9))
    def test_bad_label_preserves_usage(self):
        with patch.object(router,'call_local',return_value=('{"difficulty":"maybe"}',51,6)):
            r=router._model_route('普通请求内容'*6)
        self.assertEqual((r.by,r.tokens_in,r.tokens_out),('default',51,6))
    def test_failed_classification_falls_back(self):
        with patch.object(router,'call_local',side_effect=clients.ProviderError('offline')):
            self.assertIsNone(router._model_route('普通请求内容'*6))
    def test_forced_baseline_skips_router(self):
        with patch.object(agent,'decide',side_effect=AssertionError('router should not run')):
            r=agent.run('你好',force_route='hard')
        self.assertEqual(r['decided_by'],'forced')
    def test_successful_escalation_counts_both(self):
        with patch.object(agent,'call_local',return_value=('太短',10,2)),patch.object(agent,'call_cloud',return_value=('这是一次成功的完整云端重答。',20,30)):
            r=agent.run('你好')
        self.assertTrue(r['escalated']);self.assertFalse(r['escalation_failed'])
        self.assertEqual((r['tokens_in'],r['tokens_out']),(30,32))
        self.assertEqual(self.row()['cloud_tokens_out'],30)
    def test_failed_escalation_not_success(self):
        with patch.object(agent,'call_local',return_value=('太短',10,2)),patch.object(agent,'call_cloud',side_effect=clients.ProviderError('offline')):
            r=agent.run('你好')
        self.assertFalse(r['escalated']);self.assertTrue(r['escalation_failed']);self.assertEqual(r['answer'],'太短')
        self.assertEqual((self.row()['escalated'],self.row()['escalation_attempted'],self.row()['escalation_failed']),(0,1,1))
    def test_cloud_to_local_degradation_saved(self):
        with patch.object(agent,'call_cloud',side_effect=clients.ProviderError('offline')),patch.object(agent,'call_local',return_value=('这是一条足够长的本地兜底回答。',10,20)):
            r=agent.run('证明一个定理',force_route='hard')
        self.assertTrue(r['degraded']);self.assertEqual(self.row()['degraded'],1)
    def test_local_to_cloud_degradation_saved(self):
        with patch.object(agent,'call_local',side_effect=clients.ProviderError('offline')),patch.object(agent,'call_cloud',return_value=('这是一条云端兜底回答。',10,20)):
            r=agent.run('你好')
        self.assertTrue(r['degraded']);self.assertEqual(self.row()['cloud_tokens_out'],20)
    def test_both_failures_saved(self):
        with patch.object(agent,'call_local',side_effect=clients.ProviderError('offline')),patch.object(agent,'call_cloud',side_effect=clients.ProviderError('offline')):
            r=agent.run('你好')
        self.assertTrue(r['error']);self.assertTrue(self.row()['error']);self.assertEqual(store.stats()['errors'],1)
    def test_legacy_schema_migration_preserves_rows(self):
        legacy=Path(self.temp.name)/'legacy.db';settings.db_path=str(legacy)
        with closing(sqlite3.connect(legacy)) as c:
            c.executescript(store.SCHEMA)
            c.execute("INSERT INTO runs(ts,query,route) VALUES ('old','keep','easy')")
            c.commit()
        store.init();store.init()
        with closing(sqlite3.connect(legacy)) as c:
            self.assertEqual(c.execute('SELECT query FROM runs').fetchone()[0],'keep')
            self.assertEqual(len(c.execute('PRAGMA table_info(runs)').fetchall()),21)
    def test_local_price_formula(self):
        with patch.object(agent,'call_local',return_value=('这是一条足够长而无需升级的本地回答。',100,50)):
            r=agent.run('你好')
        self.assertAlmostEqual(r['cost_cny'],round(.15*settings.price_local_per_1k,6))
    def test_cloud_price_formula(self):
        with patch.object(agent,'call_cloud',return_value=('这是云端回答',100,50)):
            r=agent.run('你好',force_route='hard')
        self.assertAlmostEqual(r['cost_cny'],round(.1*settings.price_cloud_in_per_1k+.05*settings.price_cloud_out_per_1k,6))
    def test_classification_included_in_total(self):
        route=router.Route('easy','case','model',0,80,12)
        with patch.object(agent,'decide',return_value=route),patch.object(agent,'call_local',return_value=('这是一条足够长的真实格式测试回答。',100,40)):
            r=agent.run('ordinary')
        self.assertEqual((r['local_tokens_in'],r['local_tokens_out']),(180,52))
    def test_summary_separates_attempt_and_success(self):
        with patch.object(agent,'call_local',return_value=('太短',10,2)),patch.object(agent,'call_cloud',side_effect=clients.ProviderError('offline')):agent.run('你好')
        s=store.stats();self.assertEqual((s['escalation_attempted'],s['escalated'],s['escalation_failed']),(1,0,1))
    def test_24_mock_cases_persisted(self):
        cases=[json.loads(l) for l in (ROOT/'eval/testset.jsonl').read_text('utf-8').splitlines() if l.strip()]
        for c in cases:self.assertTrue(agent.run(c['q'])['answer'])
        self.assertEqual(store.stats()['runs'],24)
    def test_concurrent_requests_keep_rows_isolated(self):
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(lambda _:agent.run('你好'),range(20)))
        self.assertTrue(all(r['answer'] for r in results));self.assertEqual(store.stats()['runs'],20)
    def test_stdlib_provider_authentication_and_usage(self):
        class Provider(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                if self.headers.get('Authorization')!='Bearer unit-test-key':
                    self.send_response(401);self.end_headers();return
                self.rfile.read(int(self.headers['Content-Length']))
                body=json.dumps({'choices':[{'message':{'content':'provider stub answer'}}],
                    'usage':{'prompt_tokens':17,'completion_tokens':8}}).encode()
                self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        server=ThreadingHTTPServer(('127.0.0.1',0),Provider)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        old=settings.mock_mode;settings.mock_mode=False
        try:
            base=f'http://127.0.0.1:{server.server_port}/v1'
            result=clients.chat(None,'test',[{'role':'user','content':'hello'}],20,base_url=base,api_key='unit-test-key')
            self.assertEqual(result,('provider stub answer',17,8))
            with self.assertRaises(clients.ProviderError):
                clients.chat(None,'test',[{'role':'user','content':'hello'}],20,base_url=base,api_key='invalid')
        finally:
            settings.mock_mode=old;server.shutdown();server.server_close();thread.join()

class HTTP(Regression):
    # Only HTTP-specific tests: inherited regression methods are filtered below.
    def setUp(self):
        super().setUp()
        from tools.serve_stdlib import Handler
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.base=f'http://127.0.0.1:{self.server.server_port}'
    def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join();super().tearDown()
    def request(self,path,data=None):
        request=urllib.request.Request(self.base+path,data=json.dumps(data).encode('utf-8') if data is not None else None,headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=5) as r:return json.loads(r.read())
    def test_http_health(self):self.assertTrue(self.request('/healthz')['mock'])
    def test_http_chat_and_stats(self):
        self.assertTrue(self.request('/api/chat',{'query':'你好'})['answer']);self.assertEqual(self.request('/api/stats')['summary']['runs'],1)
    def test_http_invalid_type(self):
        with self.assertRaises(urllib.error.HTTPError) as c:self.request('/api/chat',{'query':3})
        self.assertEqual(c.exception.code,400)
    def test_http_empty_input(self):
        with self.assertRaises(urllib.error.HTTPError) as c:self.request('/api/chat',{'query':' '})
        self.assertEqual(c.exception.code,400)
    def test_http_index(self):
        with urllib.request.urlopen(self.base,timeout=5) as r:self.assertIn(b'<html',r.read().lower())

if __name__=='__main__':
    suite=unittest.TestSuite()
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(Regression))
    suite.addTests(HTTP(n) for n in sorted(HTTP.__dict__) if n.startswith('test_http'))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    out=ROOT/'docs/evidence/revision';out.mkdir(exist_ok=True)
    (out/'regression_summary.json').write_text(json.dumps({'date':'2026-11-09','python':sys.version.split()[0],
        'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'scope':'deterministic provider stubs, MOCK_MODE and real loopback HTTP; no new GPU quality measurements',
        'external_user_validation':False},ensure_ascii=False,indent=2),encoding='utf-8')
    sys.exit(not result.wasSuccessful())
