"""Production-side model, theorem bounds, and strict corpus validation."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Iterable

class ContractError(ValueError):
    pass

def require_int(value: Any, name: str, lo: int | None = None, hi: int | None = None) -> int:
    if type(value) is not int:
        raise ContractError(f"{name} must be an integer (booleans and equal-valued floats are rejected)")
    if lo is not None and value < lo: raise ContractError(f"{name} below lower bound")
    if hi is not None and value > hi: raise ContractError(f"{name} above upper bound")
    return value

def upper_bound(h: Iterable[int], cardinality: int) -> int:
    return sum(min(value, cardinality) for value in h)

def lower_bound(n: int, h: Iterable[int], cardinality: int) -> int:
    return sum(max(0, value - (n - cardinality)) for value in h)

@dataclass(frozen=True)
class Classification:
    compatible: bool
    kind: str | None
    cardinality: int | None
    core_ports: tuple[int, ...]
    lhs: int | None
    rhs: int | None

def classify(n: int, h: list[int], selected: dict[int, int]) -> Classification:
    descending = sorted(selected.items(), key=lambda item: (-item[1], item[0]))
    ascending = sorted(selected.items(), key=lambda item: (item[1], item[0]))
    running_upper = running_lower = 0
    for size in range(1, len(selected)+1):
        running_upper += descending[size-1][1]
        running_lower += ascending[size-1][1]
        ub, lb = upper_bound(h, size), lower_bound(n, h, size)
        if running_upper > ub:
            return Classification(False,"upper",size,tuple(p for p,_ in descending[:size]),running_upper,ub)
        if running_lower < lb:
            return Classification(False,"lower",size,tuple(p for p,_ in ascending[:size]),running_lower,lb)
    return Classification(True,None,None,(),None,None)

def _vector(value: Any, n: int, width: int | None, name: str) -> list[int]:
    if type(value) is not list or not value: raise ContractError(f"{name} must be a nonempty list")
    if width is not None and len(value) != width: raise ContractError(f"{name} has wrong width")
    return [require_int(v,f"{name}[{i}]",0,n) for i,v in enumerate(value)]

def _traces(value: Any, n: int, root_h: list[int]) -> list[dict[str,Any]]:
    if type(value) is not list or not value: raise ContractError("traces must be a nonempty list")
    width=len(root_h); ids=set(); saw_root=False; parsed=[]
    for ti,raw in enumerate(value):
        if type(raw) is not dict or set(raw)!={"id","target_h","path"}: raise ContractError("trace entry has wrong shape")
        tid=raw["id"]
        if type(tid) is not str or not tid or tid in ids: raise ContractError("trace id invalid or duplicated")
        ids.add(tid); target=_vector(raw["target_h"],n,width,f"traces[{ti}].target_h")
        if type(raw["path"]) is not list: raise ContractError("path must be a list")
        current=list(root_h); path=[]
        for si,s in enumerate(raw["path"]):
            if type(s) is not dict or set(s)!={"from_col","to_col","before","after"}: raise ContractError("path step has wrong shape")
            prefix=f"traces[{ti}].path[{si}]"
            p=require_int(s["from_col"],f"{prefix}.from_col",0,width-1); q=require_int(s["to_col"],f"{prefix}.to_col",0,width-1)
            if p==q: raise ContractError("balancing move must use distinct columns")
            before=_vector(s["before"],n,width,f"{prefix}.before"); after=_vector(s["after"],n,width,f"{prefix}.after")
            if before!=current: raise ContractError("path is not contiguous")
            if before[p] < before[q]+2: raise ContractError("move is not a strict Robin-Hood transfer")
            expected=list(before); expected[p]-=1; expected[q]+=1
            if after!=expected: raise ContractError("path after-state is incorrect")
            current=after; path.append({"from_col":p,"to_col":q,"before":before,"after":after})
        if current!=target: raise ContractError("path does not end at target_h")
        if tid=="root":
            if path or target!=root_h: raise ContractError("root trace must have empty path and root_h target")
            saw_root=True
        parsed.append({"id":tid,"target_h":target,"path":path})
    if not saw_root: raise ContractError("trace family must contain its root")
    return parsed

def validate_case(case: Any) -> dict[str,Any]:
    if type(case) is not dict: raise ContractError("case must be an object")
    required={"id","n","root_h","selected","traces","expected"}
    if set(case)!=required: raise ContractError(f"case keys must be exactly {sorted(required)}")
    if type(case["id"]) is not str or not case["id"]: raise ContractError("case id must be a nonempty string")
    n=require_int(case["n"],"n",1); root_h=_vector(case["root_h"],n,None,"root_h"); width=len(root_h)
    if type(case["selected"]) is not list: raise ContractError("selected must be a list")
    selected={}
    for i,item in enumerate(case["selected"]):
        if type(item) is not dict or set(item)!={"port","count"}: raise ContractError("selected entry has wrong shape")
        p=require_int(item["port"],f"selected[{i}].port",0,n-1); c=require_int(item["count"],f"selected[{i}].count",0,width)
        if p in selected: raise ContractError("duplicate selected port")
        selected[p]=c
    traces=_traces(case["traces"],n,root_h)
    if type(case["expected"]) is not str or case["expected"] not in {"compatible","upper","lower"}: raise ContractError("expected invalid")
    return {"id":case["id"],"n":n,"root_h":root_h,"selected":selected,"traces":traces,"expected":case["expected"]}
