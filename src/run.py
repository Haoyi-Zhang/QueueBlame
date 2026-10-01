"""Generate and independently verify one candidate result directory."""
from __future__ import annotations
import argparse,json,platform,sys
from collections import Counter,defaultdict
from pathlib import Path
from checker import Rejection,verify
from common import load_json,write_json
from dp_oracle import feasible,minimum_violating_subset
from mutations import generate
from producer import produce

def run(corpus_path:Path, output:Path)->dict:
    corpus=load_json(corpus_path)
    if type(corpus) is not dict or set(corpus)!={"schema","description","cases"}: raise ValueError("corpus shape invalid")
    if corpus["schema"]!="cbcqv-corpus-v2" or type(corpus["cases"]) is not list: raise ValueError("corpus schema invalid")
    if output.exists() and any(output.iterdir()): raise ValueError(f"output directory must be absent or empty: {output}")
    output.mkdir(parents=True,exist_ok=True); certdir=output/"certificates"; certdir.mkdir()
    outcomes=[]; records=[]; status=Counter(); violations=Counter(); hist=Counter(); cats=defaultdict(Counter)
    agg=matrix_steps=disagreements=0
    for case in corpus["cases"]:
        selected={x["port"]:x["count"] for x in case["selected"]}
        oracle_ok=feasible(case["n"],case["root_h"],selected); oracle_core=minimum_violating_subset(case["n"],case["root_h"],selected)
        cert=produce(case); checked=verify(case,cert); producer_ok=cert["status"]=="compatible"
        bad=producer_ok!=oracle_ok or (not producer_ok and (oracle_core is None or len(oracle_core)!=len(cert["core_ports"])))
        disagreements+=int(bad); write_json(certdir/f"{case['id']}.json",cert)
        status[cert["status"]]+=1
        if not producer_ok:
            violations[cert["violation"]["kind"]]+=1; hist[len(cert["core_ports"])]+=1
        steps=sum(len(t["path"]) for t in case["traces"]); agg+=steps; matrix_steps+=checked["matrix_transport_steps"]
        outcomes.append({"case_id":case["id"],"status":cert["status"],"violation":None if producer_ok else cert["violation"]["kind"],"core_size":None if producer_ok else len(cert["core_ports"]),"trace_count":len(case["traces"]),"trace_steps":steps,"matrix_transport_steps":checked["matrix_transport_steps"],"checker":checked["accepted"],"oracle_feasible":oracle_ok,"oracle_core_size":None if oracle_core is None else len(oracle_core),"oracle_agrees":not bad})
        seen=set()
        for category,name,mutant in generate(cert):
            if name in seen: raise AssertionError(f"duplicate mutation name {case['id']}:{name}")
            seen.add(name); accepted=False; reason=None
            try: verify(case,mutant); accepted=True
            except Rejection as exc: reason=str(exc)
            cats[category]["attempted"]+=1; cats[category]["accepted" if accepted else "rejected"]+=1
            records.append({"case_id":case["id"],"category":category,"mutation":name,"rejected":not accepted,"reason":reason})
    accepted_count=sum(not r["rejected"] for r in records); rejected_count=len(records)-accepted_count
    summary={"schema":"cbcqv-results-v3","python":platform.python_version(),"platform":platform.platform(),"cases":len(corpus["cases"]),"trace_families":len(corpus["cases"]),"traces":sum(len(c["traces"]) for c in corpus["cases"]),"aggregate_path_steps_validated":agg,"matrix_transport_steps_replayed":matrix_steps,"compatible":status["compatible"],"incompatible":status["incompatible"],"upper_cores":violations["upper"],"lower_cores":violations["lower"],"core_size_histogram":{str(k):hist[k] for k in sorted(hist)},"certificates_accepted":len(outcomes),"mutations_attempted":len(records),"mutations_rejected":rejected_count,"mutations_accepted":accepted_count,"mutation_categories":{k:{"attempted":v["attempted"],"rejected":v["rejected"],"accepted":v["accepted"]} for k,v in sorted(cats.items())},"oracle_disagreements":disagreements,"scientific_work_units":{"corpus_oracle_instances":len(corpus["cases"]),"certificate_replays":len(outcomes),"aggregate_path_steps":agg,"matrix_transport_steps":matrix_steps,"malformed_certificate_checks":len(records)},"provenance":{"kind":"fresh deterministic regeneration from retained corpus and source","lost_prior_run_recovered":False}}
    write_json(output/"summary.json",summary); write_json(output/"outcomes.json",outcomes); write_json(output/"mutations.json",records)
    if disagreements: raise AssertionError(f"producer/oracle disagreements: {disagreements}")
    if accepted_count: raise AssertionError(f"checker accepted {accepted_count} malformed certificates")
    return summary

def main()->None:
    p=argparse.ArgumentParser(); p.add_argument("--corpus",default="data/corpus.json"); p.add_argument("--output",default="results/frozen"); a=p.parse_args()
    json.dump(run(Path(a.corpus),Path(a.output)),sys.stdout,indent=2,sort_keys=True); sys.stdout.write("\n")
if __name__=="__main__": main()
