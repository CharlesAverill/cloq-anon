# Improvement factors for the paper's WCET tables:
#   [mean_n WCP/o(n)] / [mean_n f(n)/o(n)],  n = 0..m
# f(n): Cloq's largest prediction at size n; o(n): longest observed time at size n.
#
# aiT table (Cortex-M0): the board measured o(n) = f(n) on every input (see
# ../board/results/flash/summary.txt; checked below), and we take o(n) = f(n)
# for the unmeasured sizes, so the factor is (1/m) sum WCP/f(n), computed in
# closed form below over aiT's full input ranges.
# WCP: aiT reports; f: closed forms checked by check_closed_forms.py; m: from the .ais loop bounds.
import math
from collatz_max import cyc
def psi(x):  # digamma, asymptotic (x large)
    return math.log(x)-1/(2*x)-1/(12*x*x)+1/(120*x**4)
def lin_sum(a,b,lo,hi):  # sum_{n=lo}^{hi} 1/(a+b n), exact head + digamma tail
    K=min(hi,lo+10**6); s=sum(1/(a+b*n) for n in range(lo,K+1))
    if hi>K: s+=(psi(a/b+hi+1)-psi(a/b+K+1))/b
    return s
def fac(wcp, terms, m):  # terms: list of (value f at single n) or (a,b,lo,hi)
    tot=0
    for t in terms:
        tot += wcp/t[0] if len(t)==1 else wcp*lin_sum(*t)
    return tot/m
M31=2**31-1
print('sum   ', round(fac(15032385539, [(11,),(7,7,1,M31)], M31)))
print('wtb   ', round(fac(8981, [(10,),(10,),(10,),(-10,8,3,999)], 999)))
print('arr   ', round(fac(983077, [(29,14,0,65535)], 65535)))  # len is uint16_t; +4/elt partial matches (worst case)
print('ins   ', round(fac(21474836499, [(29,),(30,10,1,M31)], M31)))
print('sorted', round(fac(18448, [(26,9,0,2047)], 2047)))
print('find_in_list', round(fac(20496, [(11,10,0,2047)], 2047)))  # key at idx n (find_in_list_proof.v)
print('collatz', round(sum(990042/cyc(n) for n in range(1,65536))/65535))


# --- RapiTime table (i5-7300U): o(n) from ../../x86_wcet_comparison/hw/results
import csv, importlib.util
from collections import defaultdict
from pathlib import Path
EX = Path(__file__).resolve().parents[2]
def _mod(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
def _rows(path):
    with open(path) as f:
        return [{k: int(v) for k, v in r.items()} for r in csv.DictReader(f)]
def measured_factor(path, bound, wcp, col, size, keep=lambda r: True):
    o, f = defaultdict(int), defaultdict(int)
    for r in _rows(path):
        b = bound(r['in0'], r['in1'], r['in2'])
        if b is None or not keep(r):
            continue
        n = size(r); o[n] = max(o[n], r[col]); f[n] = max(f[n], b)
    tool = sum(wcp / o[n] for n in o) / len(o)
    cloq = sum(f[n] / o[n] for n in o) / len(o)
    return tool / cloq, cloq
LEN = lambda r: r['in0']
PASSED = lambda r: r['in2']
NOT_SKIP = lambda r: r['in1'] != 2**31 - 1    # value == INT_MAX takes the skip branch (no size)

board = _mod(EX / 'arm_wcet_comparison/board/compare.py', 'board')
for name, (model, _, _) in board.BENCHES.items():
    p = EX / 'arm_wcet_comparison/board/results/flash' / f'{name}.csv'
    if p.exists():
        assert all(r['cmax'] == model(r['in0'], r['in1'], r['in2']) for r in _rows(p)), name
print('board: o(n) == f(n) on every measured input')

hw = _mod(EX / 'x86_wcet_comparison/hw/compare.py', 'hw')
R = EX / 'x86_wcet_comparison/hw/results'
print('RapiTime (factor, mean Cloq/observed):')
for label, csvname, bound, wcp, size, keep in [
        ('sum', 'sum', hw.sum_bound, 436933677, LEN, None),
        ('wtb', 'while_true_break', hw.wtb_bound, 87811117, LEN, None),
        ('arr', 'find', hw.find_bound, 65244002, LEN, None),
        ('find_in_list', 'find_in_list', hw.find_in_list_bound, 10824648, LEN, None),
        ('ins', 'insert_after_pos_in_list', hw.insert_after_pos_bound, 1446238, LEN, None),
        ('sorted', 'insert_in_sorted_list', hw.insert_in_sorted_bound, 250768, PASSED, NOT_SKIP)]:
    fac_, cloq = measured_factor(R / f'{csvname}.csv', bound, wcp, 'cmed', size, keep or (lambda r: True))
    print(f'  {label:12s} {round(fac_):7d}   {cloq:.1f}')
