"""Service-time sensitivity analysis. All service times are explicit assumptions."""
import argparse,json,math

def calculate(daily, service_s, *, hours=8, local_ratio=.6, peak=5, util=.7,
              classifier_ratio=.3, classifier_s=.05, escalation_ratio=.2, card_price=4):
    qps=daily/(hours*3600)*peak
    demand=local_ratio*service_s+classifier_ratio*classifier_s
    cards=max(1,math.ceil(qps*demand/util))+(1 if daily>=50000 else 0)
    cloud_fraction=1-local_ratio+local_ratio*escalation_ratio
    cloud_request_price=.6*.005+.3*.015
    cloud_cost=daily*30*cloud_fraction*cloud_request_price
    total=cards*hours*30*card_price+cloud_cost
    baseline=daily*30*cloud_request_price
    return {"daily":daily,"service_s_assumption":service_s,"peak_qps":qps,
            "cards_including_redundancy":cards,"monthly_total_cny":round(total,2),
            "cloud_baseline_cny":round(baseline,2),"saved_percent":round((1-total/baseline)*100,1)}

def main():
    p=argparse.ArgumentParser();p.add_argument("--service-seconds",required=True)
    args=p.parse_args();times=[float(x) for x in args.service_seconds.split(",")]
    if any(t<=0 for t in times):p.error("service times must be positive")
    print(json.dumps({"kind":"scenario assumptions, not new GPU measurements",
        "assumptions":{"active_hours":8,"local_ratio":.6,"peak_factor":5,"util":.7,
         "classifier_ratio":.3,"classifier_s":.05,"escalation_ratio_of_local":.2,"card_cny_per_hour":4},
        "rows":[calculate(n,t) for n in [500,5000,50000] for t in times]},ensure_ascii=False,indent=2))
if __name__=="__main__":main()
