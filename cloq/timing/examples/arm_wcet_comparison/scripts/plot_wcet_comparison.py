"""Plot the WCET tools' single-number bounds against Cloq's timing formulas.

    python3 plot_wcet_comparison.py [output.png]

One panel per program in the paper's WCET comparison tables. Each panel shows
aiT's and RapiTime's WCET predictions (WCP) as horizontal lines over the
shorter of the two input ranges the tools' annotations admit, and the range of Cloq's predictions over
inputs of each size as a shaded region, for the Cortex-M0 (compared with aiT)
and the i5-7300U (compared with RapiTime). Both axes are logarithmic, so the
plots start at n = 1.

The formulas are those in the tables (aiT: Table 2, from the Cortex-M0 proofs;
RapiTime: Table 1); collatz uses the per-input models in the collatz_max.py
scripts, which copy collatz_proofs.v.
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt

HERE = Path(__file__).resolve().parent
EXAMPLES = HERE.parents[1]
DEFAULT_OUT = (Path.home() / 'Desktop/projects/latex/cloq/experiment_results'
               / 'wcet_comparison.png')


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


m0_collatz = load(EXAMPLES / 'arm_wcet_comparison/scripts/collatz_max.py', 'm0_collatz').cyc
x86_collatz = load(EXAMPLES / 'x86_wcet_comparison/collatz/collatz_max.py', 'x86_collatz').cycles

M31 = 2**31 - 1

# Each program: x-axis label, and per tool (WCP, n_max, f_min(n), f_max(n)),
# where f_min/f_max bound Cloq's predictions over inputs of size n.
#
# The aiT WCPs are for RapiTime's input ranges (the *_rapitime_bounds.ais
# annotations). Until those analyses are rerun, they are extrapolated from the
# existing aiT reports: the cost outside the loop, the first iteration, and the
# per-iteration cost, with the loop bound reduced. collatz's range is the same
# for both tools (all 16-bit inputs), so its aiT WCP is aiT's actual result.
PROGRAMS = [
    ('sum', 'Array Length', {
        'ait': (7010, 1000, lambda n: 7 + 7 * n, lambda n: 7 + 7 * n),
        'rt': (436933677, 1000, lambda n: 50 + 18 * n, lambda n: 50 + 18 * n),
    }),
    ('while_true_break', 'Input n', {
        'ait': (8990, 1000, lambda n: np.where(n <= 2, 10, 8 * n - 10),
                lambda n: np.where(n <= 2, 10, 8 * n - 10)),
        'rt': (87811117, 1000, lambda n: np.where(n <= 2, 52, 4 + 26 * n),
               lambda n: np.where(n <= 2, 52, 4 + 26 * n)),
    }),
    ('arraysearch', 'Array Length', {
        # key at index 0 .. not found with every element a partial match
        'ait': (15052, 1000, lambda n: 29 + 0 * n, lambda n: 21 + 14 * n),
        'rt': (65244002, 1000, lambda n: 65 + 0 * n, lambda n: 50 + 28 * n),
    }),
    ('list_find', 'List Length', {
        # key at the head .. key absent
        'ait': (1296, 128, lambda n: 11 + 0 * n, lambda n: 3 + 10 * n),
        'rt': (10824648, 128, lambda n: 94 + 0 * n, lambda n: 94 + 99 * n),
    }),
    ('list_insert_at_n', 'List Length', {
        # insert at the head .. insert at the end
        'ait': (1309, 128, lambda n: np.minimum(29, 17 + 10 * n), lambda n: 20 + 10 * n),
        'rt': (1446238, 128, lambda n: np.minimum(71, 52 + 30 * n), lambda n: 52 + 30 * n),
    }),
    ('sorted_list_insert', 'Nodes Passed', {
        'ait': (1195, 130, lambda n: 26 + 9 * n, lambda n: 26 + 9 * n),
        'rt': (250768, 130, lambda n: 72 + 23 * n, lambda n: 72 + 23 * n),
    }),
]

STYLE = {
    'ait': dict(line='tab:blue', region='#9ecae1', wcp='aiT WCP (Cortex-M0)',
                cloq='Cloq (Cortex-M0)'),
    'rt': dict(line='tab:red', region='#fcae91', wcp='RapiTime WCP (i5-7300U)',
               cloq='Cloq (i5-7300U)'),
}


def draw_tool(ax, tool, wcp, n_max, f_min, f_max):
    st = STYLE[tool]
    n = np.unique(np.round(np.geomspace(1, n_max, 400)))
    lo, hi = f_min(n), f_max(n)
    ax.fill_between(n, lo, hi, color=st['region'], alpha=0.5, label=st['cloq'], lw=0)
    # outline, so that regions with lo == hi still show as a line
    ax.plot(n, lo, color=st['region'], lw=2)
    ax.plot(n, hi, color=st['region'], lw=2)
    ax.hlines(wcp, 1, n_max, color=st['line'], lw=2, label=st['wcp'])


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    plt.rcParams.update({'font.size': 12})
    fig, axes = plt.subplots(2, 4, figsize=(14, 6.4))
    axes = axes.flatten()

    for ax, (title, xlabel, tools) in zip(axes, PROGRAMS):
        # plot both tools over the shorter of their two admitted input ranges
        n_max = min(tools[t][1] for t in tools)
        for tool in ('ait', 'rt'):
            wcp, _, f_min, f_max = tools[tool]
            draw_tool(ax, tool, wcp, n_max, f_min, f_max)
        ax.set_xscale('log')
        ax.set_yscale('log')
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel('Cycle Count')
        ax.grid(True, which='major')

    # collatz: Cloq's prediction is exact per input value; RapiTime fails
    ax = axes[len(PROGRAMS)]
    n = np.arange(1, 2**16)
    ax.scatter(n, [x86_collatz(int(k)) for k in n], s=1, color=STYLE['rt']['region'],
               rasterized=True)
    ax.scatter(n, [m0_collatz(int(k)) for k in n], s=1, color=STYLE['ait']['region'],
               rasterized=True)
    ax.hlines(990042, 1, 2**16 - 1, color=STYLE['ait']['line'], lw=2)
    ax.set_xticks([0, 2**15, 2**16])
    ax.set_xticklabels(['0', '$2^{15}$', '$2^{16}$'])
    ax.text(0.97, 0.62, 'RapiTime: no result', transform=ax.transAxes, va='center',
            ha='right', color=STYLE['rt']['line'])
    ax.set_yscale('log')
    ax.set_title('collatz')
    ax.set_xlabel('Input n')
    ax.set_ylabel('Cycle Count')
    ax.grid(True, which='major')

    # shared legend in the cell after collatz; the last cell stays empty
    legend_ax = axes[len(PROGRAMS) + 1]
    legend_ax.axis('off')
    for spare in axes[len(PROGRAMS) + 2:]:
        spare.axis('off')
    handles, labels = axes[0].get_legend_handles_labels()
    order = [labels.index(l) for l in (STYLE['ait']['wcp'], STYLE['ait']['cloq'],
                                       STYLE['rt']['wcp'], STYLE['rt']['cloq'])]
    legend_ax.legend([handles[i] for i in order], [labels[i] for i in order],
                     loc='center', fontsize=13, frameon=False)

    fig.tight_layout()
    fig.savefig(out, dpi=150)
    print(f'wrote {out}')


if __name__ == '__main__':
    main()
