from __future__ import annotations
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from checker import verify
from common import load_json
class FrozenResultsTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.corpus=load_json(ROOT/"data/corpus.json"); cls.results=ROOT/"results/frozen"
 def test_summary(self):
  s=load_json(self.results/"summary.json"); self.assertEqual(s["schema"],"cbcqv-results-v3"); self.assertEqual((s["cases"],s["traces"],s["aggregate_path_steps_validated"],s["matrix_transport_steps_replayed"]),(96,384,864,1728)); self.assertEqual((s["compatible"],s["upper_cores"],s["lower_cores"]),(32,32,32)); self.assertEqual(s["mutations_attempted"],s["mutations_rejected"]); self.assertEqual((s["mutations_accepted"],s["oracle_disagreements"]),(0,0)); self.assertFalse(s["provenance"]["lost_prior_run_recovered"])
  for v in s["mutation_categories"].values(): self.assertEqual(v["attempted"],v["rejected"]); self.assertEqual(v["accepted"],0)
 def test_certificates(self):
  ps=sorted((self.results/"certificates").glob("case-*.json")); self.assertEqual(len(ps),96); self.assertEqual((ps[0].name,ps[-1].name),("case-000.json","case-095.json"))
  for c in self.corpus["cases"]: self.assertTrue(verify(c,load_json(self.results/"certificates"/f"{c['id']}.json"))["accepted"])
 def test_micro(self):
  m=load_json(self.results/"micro-exhaustive.json"); self.assertEqual(m["instances"],69421); self.assertEqual((m["feasibility_mismatches"],m["core_size_mismatches"]),(0,0))
 def test_mutation_ledger(self):
  s=load_json(self.results/"summary.json"); ms=load_json(self.results/"mutations.json"); self.assertEqual(len(ms),s["mutations_attempted"]); self.assertEqual(len({(x["case_id"],x["mutation"]) for x in ms}),len(ms)); self.assertTrue(all(x["rejected"] and x["reason"] for x in ms))
if __name__=="__main__": unittest.main(verbosity=2)
