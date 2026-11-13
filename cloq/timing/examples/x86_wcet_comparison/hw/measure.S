/*
 * uint64_t measure_call (void *fn, uint64_t a0, uint64_t a1, uint64_t a2,
 *                        uint32_t pmc, uint64_t out[2]);
 * uint64_t measure_empty(void *fn, uint64_t a0, uint64_t a1, uint64_t a2,
 *                        uint32_t pmc, uint64_t out[2]);
 *
 * Read the user-mode core-cycle counter (rdpmc), call fn(a0, a1, a2), read it
 * again, and return the difference (not yet masked to the counter width).
 * out[0] gets fn's result and out[1] the TSC ticks over the same window: the
 * TSC keeps counting while the kernel runs, so a large TSC delta relative to
 * the user-mode cycles shows that an interrupt hit the run. lfence keeps the
 * reads from being reordered with the code between them. measure_empty is the
 * same sequence without the call; subtracting it leaves the cycles for the
 * call instruction, the function, and its ret.
 */
    .text

.macro MEASURE with_call
    push    %rbx
    push    %rbp
    push    %r12
    push    %r13
    push    %r14
    push    %r15
    push    %r9
    sub     $16, %rsp           /* TSC start; rsp is 16-byte aligned for the call */
    mov     %rdi, %r12
    mov     %rsi, %r13
    mov     %rdx, %r14
    mov     %rcx, %r15
    mov     %r8d, %ebp

    lfence
    rdtsc
    shl     $32, %rdx
    or      %rdx, %rax
    mov     %rax, (%rsp)        /* TSC start */
    lfence
    mov     %ebp, %ecx
    rdpmc
    shl     $32, %rdx
    or      %rdx, %rax
    mov     %rax, %rbx          /* start */
    mov     %r13, %rdi
    mov     %r14, %rsi
    mov     %r15, %rdx
    lfence
.if \with_call
    call    *%r12
.endif
    lfence
    mov     %rax, %r13          /* fn's result */
    mov     %ebp, %ecx
    rdpmc
    lfence
    shl     $32, %rdx
    or      %rdx, %rax
    sub     %rbx, %rax
    mov     %rax, %rbx          /* cycles: end - start */
    rdtsc
    lfence
    shl     $32, %rdx
    or      %rdx, %rax
    sub     (%rsp), %rax        /* TSC ticks */
    add     $16, %rsp
    pop     %r9
    mov     %r13, (%r9)
    mov     %rax, 8(%r9)
    mov     %rbx, %rax
    pop     %r15
    pop     %r14
    pop     %r13
    pop     %r12
    pop     %rbp
    pop     %rbx
    ret
.endm

    .globl measure_call
    .type measure_call, @function
    .p2align 6
measure_call:
    MEASURE 1
    .size measure_call, . - measure_call

    .globl measure_empty
    .type measure_empty, @function
    .p2align 6
measure_empty:
    MEASURE 0
    .size measure_empty, . - measure_empty

    .section .note.GNU-stack, "", @progbits
