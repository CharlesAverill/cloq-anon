# Compiles the Cloq development and every timing proof in the paper.
# Build from the repository root:
#   docker build -f cloq/Dockerfile -t cloq .
FROM rocq/rocq-prover:9.1.1

ARG JOBS=2
WORKDIR /artifact/cloq
COPY --chown=rocq:rocq cloq/ /artifact/cloq/

# 1. Picinae core: IL semantics, symbolic interpreter, ISA models
RUN make -j"${JOBS}"
# 2. Cloq timing modules and cpu timing models (NEORV32, Cortex-M0, i5-7300U)
RUN make -C timing -j"${JOBS}"
# 3. All timing proofs (FreeRTOS, crypto, algorithms, WCET comparisons)
RUN make -C timing/examples -j"${JOBS}"

CMD ["bash"]
