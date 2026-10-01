from __future__ import annotations
import ast,copy,json,random,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; SRC=ROOT/"src"; sys.path.insert(0,str(SRC))
from checker import Rejection,verify,verify_files
from common import load_json
from dp_oracle import feasible,minimum_violating_subset
from model import ContractError,classify,lower_bound,upper_bound
from mutations import generate
from producer import construct_matrix,produce

class ContractTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.corpus=load_json(ROOT/"data/corpus.json"); cls.cases=cls.corpus["cases"]; cls.by={c["id"]:c for c in cls.cases}
 def test_directed_bounds(self):
  h=[6,6,5,4,3,2,1,0,0,0]; self.assertEqual([upper_bound(h,k) for k in range(1,5)],[7,13,18,22]); self.assertEqual([lower_bound(6,h,k) for k in range(1,5)],[2,5,9,14])
 def test_directed_core_sizes(self):
  h=[6,6,5,4,3,2,1,0,0,0]
  for kind,patterns in [("upper",{1:[8],2:[7,7],3:[7,6,6],4:[6,6,6,5]}),("lower",{1:[1],2:[2,2],3:[2,3,3],4:[3,3,3,4]})]:
   for size,counts in patterns.items():
    s=dict(enumerate(counts)); r=classify(6,h,s); self.assertFalse(r.compatible); self.assertEqual((r.kind,r.cardinality),(kind,size)); self.assertFalse(feasible(6,h,s)); self.assertEqual(len(minimum_violating_subset(6,h,s)),size)
 def test_all_cases_produce_verify(self):
  for c in self.cases: self.assertTrue(verify(c,produce(c))["accepted"])
 def test_flow_constructor_random_oracle(self):
  rng=random.Random(20260918)
  for _ in range(1200):
   n=rng.randint(1,6); w=rng.randint(1,8); h=[rng.randint(0,n) for _ in range(w)]; ports=list(range(n)); rng.shuffle(ports); ports=ports[:rng.randint(0,n)]; s={p:rng.randint(0,w) for p in ports}; oracle=feasible(n,h,s); m=construct_matrix(n,h,s); self.assertEqual(m is not None,oracle)
   if m is not None:
    self.assertEqual([sum(m[r][j] for r in range(n)) for j in range(w)],h)
    for p,c in s.items(): self.assertEqual(sum(m[p]),c)
 def test_exact_bool_alias_regressions(self):
  c=self.by["case-000"]; z=produce(c); z["selected"][0]["port"]=False
  with self.assertRaises(Rejection): verify(c,z)
  c=self.by["case-011"]; z=produce(c); self.assertEqual(z["traces"][1]["path"][0]["from_col"],1); z["traces"][1]["path"][0]["from_col"]=True
  with self.assertRaises(Rejection): verify(c,z)
 def test_equal_float_metadata(self):
  c=self.by["case-011"]; z=produce(c)
  edits=[lambda q:q.__setitem__("n",float(q["n"])),lambda q:q["root_h"].__setitem__(0,float(q["root_h"][0])),lambda q:q["selected"][0].__setitem__("port",float(q["selected"][0]["port"])),lambda q:q["selected"][0].__setitem__("count",float(q["selected"][0]["count"])),lambda q:q["traces"][1]["target_h"].__setitem__(0,float(q["traces"][1]["target_h"][0])),lambda q:q["traces"][1]["path"][0].__setitem__("from_col",float(q["traces"][1]["path"][0]["from_col"])),lambda q:q["traces"][1]["path"][0]["before"].__setitem__(0,float(q["traces"][1]["path"][0]["before"][0])),lambda q:q["traces"][1]["path"][0]["after"].__setitem__(0,float(q["traces"][1]["path"][0]["after"][0]))]
  for edit in edits:
   q=copy.deepcopy(z); edit(q)
   with self.assertRaises(Rejection): verify(c,q)
 def test_production_path_vectors_strict(self):
  for name in ("before","after"):
   c=copy.deepcopy(self.by["case-011"]); s=c["traces"][1]["path"][0]; s[name][0]=float(s[name][0])
   with self.assertRaises(ContractError): produce(c)
 def test_remaining_ports_strict(self):
  c=next(x for x in self.cases if x["expected"]=="upper" and len(produce(x)["core_ports"])==4); z=produce(c)
  for v in (True,1.0):
   q=copy.deepcopy(z); q["deletion_witnesses"][0]["remaining_ports"][0]=v
   with self.assertRaises(Rejection): verify(c,q)
 def test_selected_order_semantic(self):
  c=copy.deepcopy(self.by["case-001"]); c["selected"]=list(reversed(c["selected"])); z=produce(c); self.assertTrue(verify(c,z)["accepted"]); z["selected"]=list(reversed(z["selected"])); self.assertTrue(verify(c,z)["accepted"])
 def test_nonminimum_core_rejected(self):
  c=copy.deepcopy(next(x for x in self.cases if x["expected"]=="upper" and len(x["selected"])==1)); c["selected"]=[{"port":0,"count":8},{"port":1,"count":7}]; z=produce(c); q=copy.deepcopy(z); q["core_ports"]=[0,1]; q["violation"]={"kind":"upper","cardinality":2,"lhs":15,"rhs":13}
  with self.assertRaises(Rejection): verify(c,q)
 def test_row_sums_preserved(self):
  for c in (x for x in self.cases if x["expected"]=="compatible"):
   z=produce(c); root=z["root_matrix"]; sums=[sum(r) for r in root]
   for tr in c["traces"]:
    m=[list(r) for r in root]
    for s in tr["path"]:
     p,q=s["from_col"],s["to_col"]; r=next(i for i in range(c["n"]) if m[i][p]==1 and m[i][q]==0); m[r][p]=0; m[r][q]=1
    self.assertEqual([sum(r) for r in m],sums); self.assertEqual([sum(m[r][j] for r in range(c["n"])) for j in range(len(c["root_h"]))],tr["target_h"])
 def test_mutation_coverage(self):
  comp=produce(self.by["case-000"]); inc=produce(next(c for c in self.cases if c["expected"]=="upper" and len(produce(c)["core_ports"])==4))
  common={"schema","identity","metadata-types","trace-values","trace-direction","trace-continuity"}
  for z,specific in [(comp,{"matrix-witness"}),(inc,{"core","deletion-witness"})]:
   muts=generate(z); names=[n for _,n,_ in muts]; payloads=[json.dumps(x,sort_keys=True) for _,_,x in muts]; self.assertEqual(len(names),len(set(names))); self.assertEqual(len(payloads),len(set(payloads))); self.assertTrue(common|specific <= {c for c,_,_ in muts}); self.assertIn("swapped-first-transfer-direction",names)
   if z["status"]=="incompatible":
    for n in ("missing-deletion-witness","boolean-dropped-port","forged-remaining-ports","forged-witness-column"): self.assertIn(n,names)
 def test_import_boundaries(self):
  for fn,forbidden in [("checker.py",{"producer","flow","model","dp_oracle","generate_corpus","mutations"}),("dp_oracle.py",{"producer","flow","model","checker","generate_corpus","mutations"})]:
   tree=ast.parse((SRC/fn).read_text()); imports=set()
   for node in ast.walk(tree):
    if isinstance(node,ast.Import): imports.update(a.name.split('.')[0] for a in node.names)
    elif isinstance(node,ast.ImportFrom) and node.module: imports.add(node.module.split('.')[0])
   self.assertFalse(imports & forbidden)
 def test_duplicate_json_key(self):
  c=self.by["case-000"]; z=produce(c)
  with tempfile.TemporaryDirectory() as d:
   cp=Path(d)/"c.json"; zp=Path(d)/"z.json"; cp.write_text(json.dumps(c)); valid=json.dumps(z); zp.write_text(valid[:-1]+',"n":6}')
   with self.assertRaises(Rejection): verify_files(cp,zp)
if __name__=="__main__": unittest.main(verbosity=2)
