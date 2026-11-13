"""Classify run_eval.py results as in Appendix B of the paper.

  fully automated:     the generated proof checks in Rocq unchanged, with no
                       admitted goals and no existentially quantified loop count;
  partially automated: TIG generated a proof, but it does not check, checks only
                       with admitted goals, or leaves the loop count existential;
  not automated:       TIG did not generate a proof.

    python eval/summarize.py RESULTS.jsonl [RESULTS.jsonl ...]
"""
import json
import sys

rows = []
for path in sys.argv[1:]:
    rows += [json.loads(l) for l in open(path) if l.strip()]

counts = {"full": 0, "partial": 0, "none": 0}
print(f"{'proof':32} {'arch':7} {'paths':>5}  {'loop count':16} result")
for r in rows:
    g = r.get("generate", {})
    if g.get("status") != "generated":
        res = "none"
    else:
        ok = r.get("standalone", {}).get("rc") == 0
        loop = g.get("header") is not None
        res = "full" if ok and not g.get("admitted") and (not loop or g.get("count")) else "partial"
    counts[res] += 1
    print(f"{r['id']:32} {r.get('arch', 'riscv'):7} {str(g.get('paths', '-')):>5}  "
          f"{str(g.get('count') or '-'):16} {res}"
          + (f"  ({g.get('status')}: {g.get('detail', '')[:60]})" if res == "none" else ""))
n = len(rows)
print(f"\n{n} proofs: {counts['full']} fully automated, {counts['partial']} partially, "
      f"{counts['none']} not automated")
