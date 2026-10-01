"""Deterministic malformed-certificate generator; no tail truncation."""
from __future__ import annotations
import copy, json
from typing import Any, Callable
Mutation = tuple[str,str,dict[str,Any]]

def _enc(v: dict[str,Any]) -> str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def _first_step(c: dict[str,Any]) -> dict[str,Any]:
    for tr in c["traces"]:
        if tr["path"]: return tr["path"][0]
    raise ValueError("no path")

def _bool_in_list(xs:list[Any])->None:
    for i,v in enumerate(xs):
        if type(v) is int and v in (0,1): xs[i]=bool(v); return
    raise ValueError("no 0/1")

def _float_in_list(xs:list[Any])->None:
    for i,v in enumerate(xs):
        if type(v) is int: xs[i]=float(v); return
    raise ValueError("no int")

def _bool_path_index(c:dict[str,Any])->None:
    for tr in c["traces"]:
        for s in tr["path"]:
            for key in ("from_col","to_col"):
                if type(s[key]) is int and s[key] in (0,1):
                    s[key]=bool(s[key]); return
    s=_first_step(c)
    s["from_col"]=bool(s["from_col"])

def generate(certificate:dict[str,Any])->list[Mutation]:
    out=[]; names=set(); payloads=set(); original=_enc(certificate)
    def add(category:str,name:str,edit:Callable[[dict[str,Any]],None])->None:
        if name in names: raise AssertionError(f"duplicate name {name}")
        c=copy.deepcopy(certificate); edit(c); e=_enc(c)
        if e==original: raise AssertionError(f"unchanged mutation {name}")
        if e in payloads: raise AssertionError(f"duplicate payload {name}")
        names.add(name); payloads.add(e); out.append((category,name,c))
    add("schema","wrong-version-type",lambda c:c.__setitem__("version",2))
    add("identity","wrong-case-id",lambda c:c.__setitem__("case_id",c["case_id"]+"-forged"))
    add("schema","unexpected-top-level-key",lambda c:c.__setitem__("comment","untrusted"))
    add("schema","missing-root-h",lambda c:c.pop("root_h"))
    add("metadata-types","boolean-n",lambda c:c.__setitem__("n",True))
    add("metadata-types","equal-float-n",lambda c:c.__setitem__("n",float(c["n"])))
    add("metadata-types","equal-bool-root-height",lambda c:_bool_in_list(c["root_h"]))
    add("metadata-types","equal-float-root-height",lambda c:_float_in_list(c["root_h"]))
    add("metadata-types","equal-bool-selected-port",lambda c:c["selected"][0].__setitem__("port",bool(c["selected"][0]["port"])))
    add("metadata-types","equal-float-selected-port",lambda c:c["selected"][0].__setitem__("port",float(c["selected"][0]["port"])))
    add("metadata-types","equal-float-selected-count",lambda c:c["selected"][0].__setitem__("count",float(c["selected"][0]["count"])))
    add("metadata-types","equal-float-trace-target",lambda c:_float_in_list(c["traces"][1]["target_h"]))
    add("metadata-types","boolean-path-index",_bool_path_index)
    add("metadata-types","equal-float-path-index",lambda c:_first_step(c).__setitem__("from_col",float(_first_step(c)["from_col"])))
    add("metadata-types","equal-bool-path-before",lambda c:_bool_in_list(_first_step(c)["before"]))
    add("metadata-types","equal-float-path-before",lambda c:_float_in_list(_first_step(c)["before"]))
    add("metadata-types","equal-bool-path-after",lambda c:_bool_in_list(_first_step(c)["after"]))
    add("metadata-types","equal-float-path-after",lambda c:_float_in_list(_first_step(c)["after"]))
    add("trace-values","forged-trace-target",lambda c:c["traces"][1]["target_h"].__setitem__(0,(c["traces"][1]["target_h"][0]+1)%(c["n"]+1)))
    def swap(c):
        s=_first_step(c); s["from_col"],s["to_col"]=s["to_col"],s["from_col"]
    add("trace-direction","swapped-first-transfer-direction",swap)
    add("trace-values","forged-path-after",lambda c:_first_step(c)["after"].__setitem__(0,_first_step(c)["after"][0]+1))
    add("trace-continuity","missing-first-transfer",lambda c:c["traces"][1]["path"].pop(0))
    if certificate["status"]=="compatible":
        add("matrix-witness","boolean-matrix-cell",lambda c:c["root_matrix"][0].__setitem__(0,True))
        add("matrix-witness","equal-float-matrix-cell",lambda c:c["root_matrix"][0].__setitem__(0,float(c["root_matrix"][0][0])))
        add("matrix-witness","nonbinary-matrix-cell",lambda c:c["root_matrix"][0].__setitem__(0,2))
        add("matrix-witness","missing-matrix-row",lambda c:c["root_matrix"].pop())
        add("matrix-witness","short-matrix-row",lambda c:c["root_matrix"][0].pop())
        def flip(c): c["root_matrix"][0][0]=1-c["root_matrix"][0][0]
        add("matrix-witness","forged-column-sum",flip)
        add("schema","wrong-status-compatible",lambda c:c.__setitem__("status","incompatible"))
    else:
        add("core","boolean-core-port",lambda c:c["core_ports"].__setitem__(0,bool(c["core_ports"][0])))
        add("core","equal-float-core-port",lambda c:c["core_ports"].__setitem__(0,float(c["core_ports"][0])))
        add("core","duplicate-core-port",lambda c:c["core_ports"].append(c["core_ports"][0]))
        add("core","wrong-core-cardinality",lambda c:c["violation"].__setitem__("cardinality",c["violation"]["cardinality"]+1))
        add("core","boolean-violation-lhs",lambda c:c["violation"].__setitem__("lhs",True))
        add("core","equal-float-violation-lhs",lambda c:c["violation"].__setitem__("lhs",float(c["violation"]["lhs"])))
        add("core","wrong-violation-lhs",lambda c:c["violation"].__setitem__("lhs",c["violation"]["lhs"]+1))
        add("core","wrong-violation-rhs",lambda c:c["violation"].__setitem__("rhs",c["violation"]["rhs"]+1))
        add("core","swapped-violation-kind",lambda c:c["violation"].__setitem__("kind","lower" if c["violation"]["kind"]=="upper" else "upper"))
        add("deletion-witness","missing-deletion-witness",lambda c:c["deletion_witnesses"].pop())
        add("deletion-witness","boolean-dropped-port",lambda c:c["deletion_witnesses"][0].__setitem__("dropped_port",bool(c["deletion_witnesses"][0]["dropped_port"])))
        add("deletion-witness","equal-float-dropped-port",lambda c:c["deletion_witnesses"][0].__setitem__("dropped_port",float(c["deletion_witnesses"][0]["dropped_port"])))
        add("deletion-witness","forged-remaining-ports",lambda c:c["deletion_witnesses"][0]["remaining_ports"].append(c["core_ports"][0]))
        def br(c):
            xs=c["deletion_witnesses"][0]["remaining_ports"]
            if xs: xs[0]=bool(xs[0])
            else: xs.append(False)
        def fr(c):
            xs=c["deletion_witnesses"][0]["remaining_ports"]
            if xs: xs[0]=float(xs[0])
            else: xs.append(0.0)
        add("deletion-witness","boolean-remaining-port",br)
        add("deletion-witness","equal-float-remaining-port",fr)
        add("deletion-witness","boolean-witness-cell",lambda c:c["deletion_witnesses"][0]["matrix"][0].__setitem__(0,True))
        add("deletion-witness","equal-float-witness-cell",lambda c:c["deletion_witnesses"][0]["matrix"][0].__setitem__(0,float(c["deletion_witnesses"][0]["matrix"][0][0])))
        def fw(c):
            m=c["deletion_witnesses"][0]["matrix"]; m[0][0]=1-m[0][0]
        add("deletion-witness","forged-witness-column",fw)
        add("deletion-witness","missing-witness-row",lambda c:c["deletion_witnesses"][0]["matrix"].pop())
        add("schema","wrong-status-incompatible",lambda c:c.__setitem__("status","compatible"))
    return out
