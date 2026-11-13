"""Run Ghidra once per binary in an entries file and cache its basic blocks.

run_eval.py caps each TIG process at 3 GB of address space, which is too
little for Ghidra's JVM, so the blocks are extracted beforehand.

    python eval/prefetch_blocks.py ENTRIES.json [ENTRIES.json ...]
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tig.extract_basic_blocks import extract_bb  # noqa: E402

RISCV_OBJDUMP = os.environ.get("RISCV_OBJDUMP", "/opt/riscv/bin/riscv32-unknown-elf-objdump")

seen = set()
for path in sys.argv[1:]:
    for e in json.load(open(path))["proofs"]:
        if e["elf"] in seen:
            continue
        seen.add(e["elf"])
        cache = e["elf"] + ".json"
        if os.path.exists(cache):
            continue
        objdump = RISCV_OBJDUMP if e.get("arch", "riscv") == "riscv" else "none"
        print(f"extracting {e['elf']}", flush=True)
        extract_bb(e["elf"], cache, objdump=objdump)
