#!/bin/bash
# Regenerate TIG's timing proofs for every proof in the paper and check them
# against the compiled Cloq development.  Results go to $RESULTS.
set -euo pipefail
cd /artifact/tig
RESULTS=${RESULTS:-/artifact/results}
mkdir -p "$RESULTS" /artifact/cloq/timing/examples/tig_out /artifact/cloq/timing/examples/tig_sub
.venv/bin/python eval/prefetch_blocks.py eval/entries_riscv.json eval/entries_wcet.json
for set in riscv wcet; do
    .venv/bin/python eval/run_eval.py "eval/entries_$set.json" "$RESULTS/results_$set.jsonl"
done
cp /artifact/cloq/timing/examples/tig_out/*.v "$RESULTS/"
.venv/bin/python eval/summarize.py "$RESULTS/results_riscv.jsonl" "$RESULTS/results_wcet.jsonl" \
    | tee "$RESULTS/summary.txt"
