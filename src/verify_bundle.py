"""Replay frozen certificates and deterministic negative tests.
Micro-exhaustive statistics are only read here; run_all.sh recomputes them.
"""
from __future__ import annotations
import argparse,json
from collections import Counter
from pathlib import Path
from checker import Rejection,verify
from common import load_json
from mutations import generate

def main()->None:
    p=argparse.ArgumentParser(); p.add_argument("--corpus",default="data/corpus.json"); p.add_argument("--results",default="results/frozen"); a=p.parse_args()
    corpus=load_json(a.corpus); cases={c["id"]:c for c in corpus["cases"]}; root=Path(a.results)
    certs={}; accepted=steps=0
    for cid,case in sorted(cases.items()):
        cert=load_json(root/"certificates"/f"{cid}.json"); certs[cid]=cert; result=verify(case,cert); accepted+=1; steps+=result["matrix_transport_steps"]
    summary=load_json(root/"summary.json")
    if accepted!=summary["certificates_accepted"] or steps!=summary["matrix_transport_steps_replayed"]: raise AssertionError("certificate summary mismatch")
    ledger=load_json(root/"mutations.json"); lm={}
    for r in ledger:
        key=(r["case_id"],r["mutation"])
        if key in lm: raise AssertionError(f"duplicate ledger key {key}")
        lm[key]=r
    generated=set(); payloads=set(); replayed=accepted_mut=0; cats=Counter()
    for cid,case in sorted(cases.items()):
        for category,name,mutant in generate(certs[cid]):
            key=(cid,name); payload=(cid,json.dumps(mutant,sort_keys=True,separators=(",",":")))
            if key in generated or payload in payloads: raise AssertionError(f"duplicate generated mutation {key}")
            generated.add(key); payloads.add(payload)
            if key not in lm or lm[key]["category"]!=category: raise AssertionError(f"mutation ledger mismatch {key}")
            rejected=False; reason=None
            try: verify(case,mutant)
            except Rejection as exc: rejected=True; reason=str(exc)
            replayed+=1; cats[category]+=1; accepted_mut+=int(not rejected)
            if lm[key]["rejected"]!=rejected or (rejected and lm[key]["reason"]!=reason): raise AssertionError(f"mutation replay differs {key}")
    if generated!=set(lm): raise AssertionError("mutation set mismatch")
    if accepted_mut or replayed!=summary["mutations_attempted"] or replayed!=summary["mutations_rejected"]: raise AssertionError("mutation summary mismatch")
    for cat,v in summary["mutation_categories"].items():
        if cats[cat]!=v["attempted"] or v["attempted"]!=v["rejected"] or v["accepted"]: raise AssertionError(f"category mismatch {cat}")
    micro=load_json(root/"micro-exhaustive.json")
    if micro["feasibility_mismatches"] or micro["core_size_mismatches"]: raise AssertionError("recorded micro mismatch")
    print(json.dumps({"status":"ACCEPT","certificates_replayed_now":accepted,"aggregate_path_steps_recorded":summary["aggregate_path_steps_validated"],"matrix_transport_steps_replayed_now":steps,"negative_mutations_replayed_now":replayed,"negative_mutation_categories":dict(sorted(cats.items())),"micro_instances_recorded_not_recomputed":micro["instances"],"micro_core_instances_recorded_not_recomputed":micro["sampled_core_instances"]},sort_keys=True))
if __name__=="__main__": main()
