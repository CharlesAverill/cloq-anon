"""Compare cycle counts measured on the i5-7300U with Cloq's proved bounds.

    python3 compare.py [results]

The bounds are the i5-7300U closed forms proved in the Goals at the end of each
*_proofs.v (cycle_count <= bound). find_in_list has no x86-64 proof; its bound
is the formula in the paper's RapiTime table. collatz uses collatz_max.py, a
copy of collatz_proofs.v (precondition 1 <= n).

Measurements include the call and ret around each function, so they slightly
overstate its time; a bound that holds for them holds for the function alone.
cmin/cmed/cmax are over the runs no interrupt hit (see main.c); allmax is over
every run, interrupted or not.
"""
import csv
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

spec = importlib.util.spec_from_file_location('x86_collatz', HERE.parent / 'collatz/collatz_max.py')
x86_collatz = importlib.util.module_from_spec(spec)
spec.loader.exec_module(x86_collatz)

NOT_FOUND = 2**64 - 1
INT_MAX = 2**31 - 1


def sum_bound(n, *_):
    return 38 if n == 0 else 50 + 18 * n


def wtb_bound(n, *_):
    return 52 if n <= 2 else 56 + (n - 2) * 26


def find_bound(length, idx, _):
    if length == 0:
        return 39
    return 65 + 28 * idx if idx != NOT_FOUND else 50 + 28 * length


def collatz_bound(n, *_):
    return x86_collatz.cycles(n) if n >= 1 else None   # outside the precondition


def find_in_list_bound(length, idx, _):
    # From the RapiTime table, not a proof: 94 + 99 min(idx, len)
    return 94 + 99 * (length if idx == NOT_FOUND else min(idx, length))


def insert_after_pos_bound(length, pos, kind):
    if kind == 1:                       # l == NULL
        return 37
    t = 22
    if kind == 2:                       # value == NULL
        return t + 26
    if pos == 0:
        return t + 59
    m = min(pos, length) - 1
    return t + (79 + 30 * m if pos < length else 60 + 30 * m)


def insert_in_sorted_bound(_k, val, d):
    return 54 if val == INT_MAX else 49 + (1 + d) * 23


BENCHES = {
    'sum': (sum_bound, 'size'),
    'while_true_break': (wtb_bound, 'n'),
    'find': (find_bound, 'len, idx (or not found)'),
    'collatz': (collatz_bound, 'n'),
    'find_in_list': (find_in_list_bound, 'len, idx (or not found)  [bound from Table 1, no proof]'),
    'insert_after_pos_in_list': (insert_after_pos_bound, 'len, pos, kind (0 normal, 1 l=NULL, 2 value=NULL)'),
    'insert_in_sorted_list': (insert_in_sorted_bound, 'k, value, nodes passed over'),
}


def load(path):
    with open(path) as f:
        return [{k: int(v) for k, v in r.items()} for r in csv.DictReader(f)]


def summarize(results_dir):
    results_dir = Path(results_dir)
    lines, total, total_ok = [], 0, 0
    total_all_ok, total_int = [0], [0]
    for name, (bound, params) in BENCHES.items():
        path = results_dir / f'{name}.csv'
        if not path.exists():
            continue
        rows = load(path)
        checked = [(r, bound(r['in0'], r['in1'], r['in2'])) for r in rows]
        checked = [(r, b) for r, b in checked if b is not None]
        bad_result = sum(1 for r in rows if not r['ok'])
        over_max = [(r, b) for r, b in checked if r['cmax'] > b]
        over_med = [(r, b) for r, b in checked if r['cmed'] > b]
        over_all = [(r, b) for r, b in checked if r['allmax'] > b]
        ratios = [r['cmax'] / b for r, b in checked]
        n = len(checked)
        total += n
        total_ok += n - len(over_max)
        total_all_ok[0] += n - len(over_all)
        total_int[0] += sum(r['interrupted'] for r in rows)
        lines.append(f'== {name}  ({len(rows)} inputs; in = {params})')
        lines.append(f'   functional result correct      : {len(rows) - bad_result}/{len(rows)}')
        if n != len(rows):
            lines.append(f'   outside the proof precondition : {len(rows) - n} (not compared)')
        lines.append(f'   slowest run <= bound           : {n - len(over_max)}/{n}'
                     f'   (all runs, incl. interrupted: {n - len(over_all)}/{n})')
        lines.append(f'   median run <= bound            : {n - len(over_med)}/{n}')
        lines.append(f'   slowest run / bound            : min {min(ratios):.3f}, '
                     f'mean {sum(ratios) / n:.3f}, max {max(ratios):.3f}')
        lines.append(f'   interrupted runs (discarded)   : {sum(r["interrupted"] for r in rows)}')
        for r, b in sorted(over_max, key=lambda rb: rb[0]['cmax'] - rb[1], reverse=True)[:5]:
            lines.append(f'     over: in=({r["in0"]}, {r["in1"]}, {r["in2"]}) '
                         f'min/med/max {r["cmin"]}/{r["cmed"]}/{r["cmax"]} > bound {b}')
        lines.append('')
    lines.append(f'TOTAL: {total_ok}/{total} inputs within the bound in every uninterrupted run; '
                 f'{total_all_ok[0]}/{total} counting interrupted runs too '
                 f'({total_int[0]} interrupted runs discarded)')
    text = '\n'.join(lines)
    (results_dir / 'summary.txt').write_text(text + '\n')
    return text


if __name__ == '__main__':
    print(summarize(sys.argv[1] if len(sys.argv) > 1 else HERE / 'results'))
