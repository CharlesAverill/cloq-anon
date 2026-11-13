/*
 * Measure the x86_wcet_comparison functions on this machine's i5-7300U.
 *
 *     ./measure [cpu] [outdir]
 *
 * Runs the exact bytes of each analyzed function (funcs.h, from extract.py) at
 * the same offset within a 4 KiB page as in the analyzed binary, and counts core
 * cycles in user mode with the PMU (perf_event_open + rdpmc). Needs
 * kernel.perf_event_paranoid <= 2.
 *
 * Inputs cover the ranges of the paper's RapiTime table. Input i of each
 * benchmark is a deterministic function of i. Each function is called once,
 * untimed, before its first input (so the first measurement doesn't include
 * the cold page). Each input is then measured until REPS runs were not hit by
 * an interrupt (rebuilding any list the function modifies before each run),
 * and the minimum, median and maximum of those runs are recorded, along with
 * the maximum over all runs and the number of interrupted runs. Cycle counts are
 * net of the counter-reading overhead, so each includes the call and ret. Each
 * result is checked against a C reference.
 *
 * A run counts as interrupted when the TSC, which keeps counting while the
 * kernel runs, advanced by more than 3 x the user-mode cycles + 1500 ticks.
 * Uninterrupted runs stay below 2 x the cycles even at half the TSC rate, while
 * an interrupt costs thousands of ticks.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <linux/perf_event.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <unistd.h>

#include "funcs.h"

#define REPS 11
#define MAX_ATTEMPTS (4 * REPS)
#define INT_MAX_U 0x7FFFFFFFull

typedef struct list_node {
    uint64_t value;
    struct list_node *next;
} list_node;

uint64_t measure_call(void *fn, uint64_t a0, uint64_t a1, uint64_t a2, uint32_t pmc,
                      uint64_t out[2]);
uint64_t measure_empty(void *fn, uint64_t a0, uint64_t a1, uint64_t a2, uint32_t pmc,
                       uint64_t out[2]);

/* ---------------- counter ---------------- */

static uint32_t pmc_index;
static uint64_t pmc_mask;
static uint64_t base;   /* median of the empty measurement */

static void setup_counter(void)
{
    struct perf_event_attr pe;
    memset(&pe, 0, sizeof pe);
    pe.type = PERF_TYPE_HARDWARE;
    pe.size = sizeof pe;
    pe.config = PERF_COUNT_HW_CPU_CYCLES;
    pe.exclude_kernel = 1;
    pe.exclude_hv = 1;
    pe.pinned = 1;
    int fd = syscall(SYS_perf_event_open, &pe, 0, -1, -1, 0);
    if (fd < 0) {
        fprintf(stderr, "perf_event_open: %s (kernel.perf_event_paranoid must be <= 2)\n",
                strerror(errno));
        exit(1);
    }
    struct perf_event_mmap_page *pc = mmap(NULL, 4096, PROT_READ, MAP_SHARED, fd, 0);
    if (pc == MAP_FAILED || !pc->cap_user_rdpmc || !pc->index) {
        fprintf(stderr, "rdpmc not available to user space\n");
        exit(1);
    }
    pmc_index = pc->index - 1;
    pmc_mask = (pc->pmc_width >= 64) ? ~0ull : ((1ull << pc->pmc_width) - 1);
}

static int cmp_u64(const void *a, const void *b)
{
    uint64_t x = *(const uint64_t *)a, y = *(const uint64_t *)b;
    return (x > y) - (x < y);
}

static void calibrate(void)
{
    enum { N = 20001 };
    static uint64_t d[N];
    uint64_t out[2];
    for (int k = 0; k < N; k++)
        d[k] = measure_empty(NULL, 0, 0, 0, pmc_index, out) & pmc_mask;
    qsort(d, N, sizeof d[0], cmp_u64);
    base = d[N / 2];
    fprintf(stderr, "counter overhead: min %lu, median %lu, max %lu cycles\n",
            d[0], d[N / 2], d[N - 1]);
}

/* ---------------- loading the analyzed code ---------------- */

static void *load(const unsigned char *code, size_t len, size_t pageoff)
{
    unsigned char *page = mmap(NULL, 8192, PROT_READ | PROT_WRITE,
                               MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (page == MAP_FAILED) { perror("mmap"); exit(1); }
    memset(page, 0xcc, 8192);   /* int3 around the function */
    memcpy(page + pageoff, code, len);
    if (mprotect(page, 8192, PROT_READ | PROT_EXEC)) { perror("mprotect"); exit(1); }
    return page + pageoff;
}
static int warm_next;   /* do one untimed run before the next measurement */
#define LOAD(name) (warm_next = 1, load(code_##name, sizeof code_##name, PAGEOFF_##name))

/* ---------------- measuring ---------------- */

struct result { uint64_t ret, cmin, cmed, cmax, allmax, interrupted; };

static int interrupted(uint64_t cycles, uint64_t tsc) { return tsc > 3 * cycles + 1500; }

static struct result measure(void *fn, uint64_t a0, uint64_t a1, uint64_t a2,
                             void (*setup)(void))
{
    uint64_t c[REPS], out[2] = { 0, 0 }, allmax = 0, nint = 0;
    int clean = 0;
    if (warm_next) {
        if (setup) setup();
        measure_call(fn, a0, a1, a2, pmc_index, out);
        warm_next = 0;
    }
    for (int k = 0; k < MAX_ATTEMPTS && clean < REPS; k++) {
        if (setup) setup();
        uint64_t raw = measure_call(fn, a0, a1, a2, pmc_index, out) & pmc_mask;
        uint64_t d = raw > base ? raw - base : 0;
        if (d > allmax) allmax = d;
        if (interrupted(raw, out[1])) nint++;
        else c[clean++] = d;
    }
    if (clean == 0) { fprintf(stderr, "every run was interrupted\n"); exit(1); }
    qsort(c, clean, sizeof c[0], cmp_u64);
    return (struct result){ out[0], c[0], c[clean / 2], c[clean - 1], allmax, nint };
}

static FILE *open_csv(const char *dir, const char *name)
{
    char path[512];
    snprintf(path, sizeof path, "%s/%s.csv", dir, name);
    FILE *f = fopen(path, "w");
    if (!f) { perror(path); exit(1); }
    fprintf(f, "in0,in1,in2,ret,ok,cmin,cmed,cmax,allmax,interrupted\n");
    return f;
}

static void row(FILE *f, uint64_t a, uint64_t b, uint64_t c, struct result r, int ok)
{
    fprintf(f, "%lu,%lu,%lu,%lu,%d,%lu,%lu,%lu,%lu,%lu\n", a, b, c, r.ret, ok, r.cmin, r.cmed,
            r.cmax, r.allmax, r.interrupted);
}

/* ---------------- deterministic inputs ---------------- */

static uint64_t mix(uint64_t x)
{
    x ^= x >> 30; x *= 0xbf58476d1ce4e5b9ull;
    x ^= x >> 27; x *= 0x94d049bb133111ebull;
    x ^= x >> 31;
    return x;
}
static uint64_t H(uint64_t i, uint64_t salt) { return mix(i * 0x9E3779B97F4A7C15ull ^ mix(salt)); }

#define MAXLEN 1000
static int ints[MAXLEN];
static uint64_t u64s[MAXLEN];
static list_node nodes[MAXLEN + 4];

/* ---------------- benchmarks ---------------- */

static void bench_sum(const char *dir)
{
    void *fn = LOAD(sum);
    FILE *f = open_csv(dir, "sum");
    for (uint64_t n = 0; n <= 1000; n++) {
        int ref = 0;
        for (uint64_t j = 0; j < n; j++) { ints[j] = (int)H(j, 1); ref += ints[j]; }
        struct result r = measure(fn, (uint64_t)ints, n, 0, NULL);
        row(f, n, 0, 0, r, (int)r.ret == ref);
    }
    fclose(f);
}

static void bench_wtb(const char *dir)
{
    void *fn = LOAD(while_true_break);
    FILE *f = open_csv(dir, "while_true_break");
    for (uint64_t n = 0; n <= 1000; n++) {
        uint64_t ref = n;
        while (!(ref + ref >= ref * ref)) ref--;
        struct result r = measure(fn, n, 0, 0, NULL);
        row(f, n, 0, 0, r, r.ret == ref);
    }
    fclose(f);
}

/* i -> len = i/2; key found at a pseudo-random index (i odd, len > 0) or absent */
static void bench_find(const char *dir)
{
    void *fn = LOAD(find);
    FILE *f = open_csv(dir, "find");
    for (uint64_t i = 0; i < 2 * MAXLEN + 2; i++) {
        uint64_t len = i >> 1;
        int found = (i & 1) && len > 0;
        for (uint64_t j = 0; j < len; j++) u64s[j] = (H(j, 31) & ~0x3FFull) | j;
        uint64_t idx = found ? H(i, 33) % len : ~0ull;
        uint64_t key = found ? u64s[idx] : ((H(i, 34) & ~0x3FFull) | 1023);
        struct result r = measure(fn, (uint64_t)u64s, len, key, NULL);
        row(f, len, idx, 0, r, (r.ret & 0xFFFF) == (found ? idx : 0xFFFF));
    }
    fclose(f);
}

static void bench_collatz(const char *dir)
{
    void *fn = LOAD(collatz);
    FILE *f = open_csv(dir, "collatz");
    for (uint64_t i = 0; i < 65536; i++) {
        uint16_t n = (uint16_t)i;
        uint64_t k;
        for (k = 0; k < 55000; k++) {
            n = (n % 2 == 0) ? (uint16_t)(n / 2) : (uint16_t)(3 * n + 1);
            if (n == 1) break;
        }
        struct result r = measure(fn, i, 0, 0, NULL);
        /* inputs that never reach 1 return nothing (undefined behavior) */
        row(f, i, n == 1, 0, r, n != 1 || r.ret == k);
    }
    fclose(f);
}

static uint64_t ll_len;
static list_node *ll_value;

static void build_list(uint64_t len)
{
    for (uint64_t j = 0; j < len; j++)
        nodes[j].next = (j + 1 < len) ? &nodes[j + 1] : NULL;
}

/* len = 0..128, 8 inputs each: key absent, or at a pseudo-random index */
static void bench_find_in_list(const char *dir)
{
    void *fn = LOAD(find_in_list);
    FILE *f = open_csv(dir, "find_in_list");
    for (uint64_t i = 0; i < 129 * 8; i++) {
        uint64_t len = i / 8;
        int found = (i % 8) && len > 0;
        for (uint64_t j = 0; j < len; j++) nodes[j].value = (H(j, 51) & ~0x3FFull) | j;
        build_list(len);
        uint64_t idx = found ? H(i, 52) % len : ~0ull;
        uint64_t key = found ? nodes[idx].value : ((H(i, 53) & ~0x3FFull) | 1023);
        list_node *head = len ? &nodes[0] : NULL;
        struct result r = measure(fn, (uint64_t)head, key, 0, NULL);
        row(f, len, idx, 0, r, r.ret == (uint64_t)(found ? &nodes[idx] : NULL));
    }
    fclose(f);
}

static void setup_iap(void)
{
    build_list(ll_len);
    ll_value->value = 9999;
    ll_value->next = NULL;
}

/* i = 0: l = NULL; i = 1: value = NULL; otherwise len = 1..128, 8 inputs each:
   pos = 0, len - 1, >= len (sometimes huge), or pseudo-random in [1, len - 1] */
static void bench_insert_after_pos(const char *dir)
{
    void *fn = LOAD(insert_after_pos_in_list);
    FILE *f = open_csv(dir, "insert_after_pos_in_list");
    for (uint64_t i = 0; i < 2 + 128 * 8; i++) {
        uint64_t len, pos, kind;
        if (i < 2) {
            kind = i + 1; len = (i == 0) ? 0 : 1; pos = 0;
        } else {
            uint64_t j = i - 2, v = j % 8;
            kind = 0; len = j / 8 + 1;
            if (v == 0)      pos = 0;
            else if (v == 1) pos = len - 1;
            else if (v == 2) pos = (H(i, 62) % 4 == 0) ? ~0ull : len + H(i, 63) % 1000;
            else             pos = len > 1 ? 1 + H(i, 61) % (len - 1) : 1;
        }
        for (uint64_t j = 0; j < len; j++) nodes[j].value = j;
        ll_len = len;
        ll_value = &nodes[MAXLEN + 1];
        list_node *l = (kind == 1) ? NULL : &nodes[0];
        list_node *value = (kind == 2) ? NULL : ll_value;
        struct result r = measure(fn, (uint64_t)l, (uint64_t)value, pos, setup_iap);
        int ok = 1;
        if (kind == 0) {
            uint64_t at = pos < len - 1 ? pos : len - 1;
            list_node *after = (at + 1 < len) ? &nodes[at + 1] : NULL;
            ok = nodes[at].next == ll_value && ll_value->next == after;
        }
        r.ret = 0;
        row(f, len, pos, kind, r, ok);
    }
    fclose(f);
}

static void setup_iis(void)
{
    build_list(ll_len);
    ll_value->next = NULL;
}

/* A head node, k nodes with values 4, 8, .., 4k, and an INT_MAX sentinel.
   i = 0: value is INT_MAX (the skip branch); otherwise k = 0..130, 8 inputs
   each: value 4k + 100 (passes every node) or pseudo-random in [0, 4k + 8). */
static void bench_insert_in_sorted(const char *dir)
{
    void *fn = LOAD(insert_in_sorted_list);
    FILE *f = open_csv(dir, "insert_in_sorted_list");
    for (uint64_t i = 0; i < 1 + 131 * 8; i++) {
        uint64_t k, val;
        if (i == 0) {
            k = 10; val = INT_MAX_U;
        } else {
            uint64_t j = i - 1;
            k = j / 8;
            val = (j % 8 == 0) ? 4 * k + 100 : H(i, 71) % (4 * k + 8);
        }
        nodes[0].value = 0;
        for (uint64_t m = 1; m <= k; m++) nodes[m].value = 4 * m;
        nodes[k + 1].value = INT_MAX_U;
        ll_len = k + 2;
        ll_value = &nodes[MAXLEN + 2];
        ll_value->value = val;
        build_list(ll_len);
        uint64_t d = 0;
        list_node *it = &nodes[0];
        if (val != INT_MAX_U)
            while (it->next->value <= val) { it = it->next; d++; }
        struct result r = measure(fn, (uint64_t)&nodes[0], (uint64_t)ll_value, 0, setup_iis);
        int ok = nodes[d].next == ll_value && ll_value->next == &nodes[d + 1];
        r.ret = 0;
        row(f, k, val, d, r, ok);
    }
    fclose(f);
}

int main(int argc, char **argv)
{
    int cpu = argc > 1 ? atoi(argv[1]) : 3;
    const char *dir = argc > 2 ? argv[2] : "results";
    mkdir(dir, 0755);

    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(cpu, &set);
    if (sched_setaffinity(0, sizeof set, &set)) { perror("sched_setaffinity"); return 1; }

    setup_counter();
    calibrate();

    struct { const char *name; void (*run)(const char *); } benches[] = {
        { "sum", bench_sum }, { "while_true_break", bench_wtb }, { "find", bench_find },
        { "collatz", bench_collatz }, { "find_in_list", bench_find_in_list },
        { "insert_after_pos_in_list", bench_insert_after_pos },
        { "insert_in_sorted_list", bench_insert_in_sorted },
    };
    for (size_t b = 0; b < sizeof benches / sizeof benches[0]; b++) {
        fprintf(stderr, "%s\n", benches[b].name);
        benches[b].run(dir);
    }
    return 0;
}
