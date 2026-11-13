# Cloq: Formally Verifying Timing Properties of Native Code

This repository contains Cloq and TIG, the two artifacts presented in our paper.
Included in the Cloq artifact are all evaluation scripts and logs.

| Directory | Contents | Docker image |
|---|---|---|
| `cloq/` | The Rocq development, including the Picinae IL, symbolic interpreter and ISA models, Cloq's timing modules and cpu timing models, and every timing proof in the paper | compiles all proofs |
| `tig/` | The Timing Invariant Generator (TIG) | regenerates TIG's proofs for the paper's 46 timing proofs and checks them in Rocq |

## Quick start

Both images are built from the repository root. The TIG image builds on the Cloq image, because it checks the proofs it generates against the compiled development.

```bash
# 1. Compile Cloq and all timing proofs. The build fails if any proof fails.
docker build -f cloq/Dockerfile -t cloq .

# 2. Regenerate the TIG proofs (Appendix B, Table 6)
docker build -f tig/Dockerfile -t cloq-tig .
docker run --rm -v "$PWD/results:/artifact/results" cloq-tig
cat results/summary.txt
```

`JOBS` sets the number of parallel Rocq jobs (default 2), for example `docker build --build-arg JOBS=4 ...`. Allow about 4 GB of memory per job.

## Where things are

| Paper | Location |
|---|---|
| IL syntax and semantics (Section 3, Fig. 2) | `cloq/Picinae_core.v` |
| Verified symbolic interpreter | `cloq/Picinae_finterp.v`, `cloq/Picinae_theory.v` |
| ISA models | `cloq/Picinae_riscv.v`, `cloq/Picinae_armv6m.v`, `cloq/Picinae_amd64.v` |
| `TimingAutomation`, `cycle_count_of_trace`, `hammer` (Section 5.2) | `cloq/timing/TimingAutomation.v` |
| cpu timing models (Section 5.2) | `cloq/timing/riscv/NEORV32.v`, `cloq/timing/armv6m/CortexM0NoWait.v`, `cloq/timing/amd64/i5_7300u.v` |
| Password checker (Section 4) | `cloq/timing/examples/crypto/passwordCheck/` |
| WCET comparison, RapiTime / i5-7300U (Section 6.2.1, Table 1) | `cloq/timing/examples/x86_wcet_comparison/` |
| WCET comparison, aiT / Cortex-M0 (Section 6.2.2, Table 2) | `cloq/timing/examples/arm_wcet_comparison/` |
| FreeRTOS `task.c` and `list.c` (Section 6.3.1, Section 6.3.2) | `cloq/timing/examples/FreeRTOS/` |
| Algorithms and data structures (Section 6.3.3–6.3.6) | `cloq/timing/examples/data_structures/` |
| ChaCha20, ct-swap (Section 6.4) | `cloq/timing/examples/crypto/` |
| TIG (Section 5.3, Appendix B) | `tig/tig/cloq_main.py`, `tig/tig/loops.py`, `tig/tig/cloq.py` |

## Tool reports and hardware measurements

- **aiT** (Table 2): project files (`*.apx`), annotations (`*.ais`) and reports (`*report.txt`) are in each directory of `cloq/timing/examples/arm_wcet_comparison/`.
- **RapiTime** (Table 1): exported timing reports are in each directory of `cloq/timing/examples/x86_wcet_comparison/`.
- **Cortex-M0 board measurements**: `cloq/timing/examples/arm_wcet_comparison/board/`.
- **i5-7300U measurements**: `cloq/timing/examples/x86_wcet_comparison/hw/`.
- **Improvement factors and Fig. 8**: `cloq/timing/examples/arm_wcet_comparison/scripts/`.

## Notes

- The lifted programs (`*_lifted.v`, `RTOSDemo.v`, …) were produced by the lifters in `cloq/riscv_lifter.sh`, `cloq/armv6m_lifter.sh`, and `cloq/timing/amd64/timing_lifter/`. They are part of the trusted base (Section 3.3).
- Some directories also contain proofs that are not part of the paper. `cloq/timing/examples/_CoqProject` lists the files that are built.
