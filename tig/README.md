# TIG: Timing Invariant Generator

TIG proposes timing invariants and complete Cloq proof scripts for binary functions on RISC-V, ARMv6-M, and x86-64 (§5.3 of the paper). It extracts basic blocks with Ghidra, explores paths with angr, guesses loop invariants from a few unrolled iterations, and emits a Rocq proof. The output is untrusted: the Rocq kernel checks every proof.

## Running the evaluation (Appendix B)

From the repository root:

```bash
docker build -f cloq/Dockerfile -t cloq .
docker build -f tig/Dockerfile -t cloq-tig .
docker run --rm -v "$PWD/results:/artifact/results" cloq-tig
```

`run_artifact.sh` does the following:

1. Extracts basic blocks with Ghidra for every binary (`eval/prefetch_blocks.py`).
2. For each of the 46 proofs in `eval/entries_riscv.json` and `eval/entries_wcet.json`, generates a proof with TIG and compiles it with Rocq (`eval/run_eval.py`).
3. Classifies each proof as fully, partially, or not automated (`eval/summarize.py`).

It writes these files to `results/`:

| File | Contents |
|---|---|
| `results_*.jsonl` | One record per proof: TIG's status, explored paths, loop count, admitted goals, Rocq result |
| `tig_*.v` | The generated proofs |
| `summary.txt` | The classification |

## Running TIG on one function

Inside the `cloq-tig` container:

```bash
.venv/bin/python -m tig.cloq_main BINARY FUNCTION --arch {riscv,armv6m,amd64} \
    --header-from HAND_PROOF.v --out OUT.v
```

`--header-from` takes the imports and the lifted `binary` definition from an existing proof file.

## Layout

| Path | Contents |
|---|---|
| `tig/cloq_main.py` | Entry point for the Cloq backend |
| `tig/loops.py` | Loop detection and invariant guessing |
| `tig/cloq.py` | Proof emission for each ISA |
| `tig/liveness.py` | Detects registers the proof can ignore |
| `tig/symbolic_execution.py` | angr path exploration |
| `ghidra_scripts/GetBasicBlocks.java` | Ghidra basic-block extraction |
| `eval/` | Evaluation driver, entry lists, summary |
| `eval/examples/elfs/` | RISC-V binaries |
| `tig/tig.py`, `tig/proof_synthesis.py` | The original legacy front end, not used by the evaluation |

`eval/synth_elf.py` rebuilt some of these binaries from lifted Rocq listings, so that TIG analyzes exactly the code each proof verifies.
