"""Three-strategy evaluation through app.agent; preserves all answers and failures."""
import argparse,json,sys,math,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app import agent,store
from app.config import settings

def main():
    p=argparse.ArgumentParser();group=p.add_mutually_exclusive_group(required=True)
    group.add_argument('--mock',action='store_true');group.add_argument('--real',action='store_true')
    p.add_argument('--limit',type=int,default=0);p.add_argument('--output-dir',default='docs/evidence/revision_eval')
    args=p.parse_args();settings.mock_mode=args.mock
    out=ROOT/args.output_dir;out.mkdir(parents=True,exist_ok=True)
    settings.db_path=str(out/'runs.db');store.init()
    cases=[json.loads(l) for l in (ROOT/'eval/testset.jsonl').read_text('utf-8').splitlines() if l.strip()]
    if args.limit:cases=cases[:args.limit]
    summaries=[];all_rows=[]
    for name,force,escalate in [('local','easy',False),('cloud','hard',False),('hybrid',None,True)]:
        settings.enable_escalation=escalate;rows=[]
        for c in cases:
            result=agent.run(c['q'],force);row={'strategy':name,'case':c,'result':result,'mock':args.mock}
            rows.append(row);all_rows.append(row)
        successful=[x['result']['latency_ms'] for x in rows if not x['result'].get('error')]
        summaries.append({'strategy':name,'n':len(rows),'errors':sum(bool(x['result'].get('error')) for x in rows),
            'degraded':sum(bool(x['result'].get('degraded')) for x in rows),
            'escalated':sum(bool(x['result'].get('escalated')) for x in rows),
            'escalation_failed':sum(bool(x['result'].get('escalation_failed')) for x in rows),
            'cost_cny':round(sum(x['result'].get('cost_cny',0) for x in rows),6),
            'mean_latency_ms':statistics.mean(successful) if successful else None,
            'p95_nearest_ms':sorted(successful)[math.ceil(.95*len(successful))-1] if successful else None,
            'routing_accuracy':sum(x['result'].get('route')==x['case']['difficulty'] for x in rows)/len(rows) if name=='hybrid' else None})
    cloud=summaries[1];valid=not args.mock and not cloud['errors'] and not cloud['degraded'] and cloud['cost_cny']>0
    result={'mock':args.mock,'warning':'MOCK data is not GPU/quality evidence' if args.mock else '',
        'independent_cloud_baseline_valid':valid,'summaries':summaries,
        'hybrid_vs_independent_cloud':summaries[2]['cost_cny']/cloud['cost_cny'] if valid else None}
    (out/'all_strategies.jsonl').write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in all_rows),encoding='utf-8')
    (out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return int(any(s['errors'] for s in summaries))
if __name__=='__main__':sys.exit(main())
