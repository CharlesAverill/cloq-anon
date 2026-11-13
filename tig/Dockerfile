# Regenerates the TIG timing proofs and checks them in Rocq.
# Build the Cloq image first, then build from the repository root:
#   docker build -f cloq/Dockerfile -t cloq .
#   docker build -f tig/Dockerfile -t cloq-tig .
#   docker run --rm -v "$PWD/results:/artifact/results" cloq-tig
ARG CLOQ_IMAGE=cloq

FROM eclipse-temurin:21-jdk AS jdk

# TIG's environment. It uses the same base image as cloq/Dockerfile, so that
# the Rocq that checks TIG's proofs is the one that compiled the development.
FROM rocq/rocq-prover:9.1.1 AS tig-env
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-venv python3-dev build-essential cmake git \
        binutils-riscv64-unknown-elf wget unzip ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# TIG reads RISC-V operands from objdump; binutils' riscv64 build handles rv32
RUN mkdir -p /opt/riscv/bin \
    && ln -s /usr/bin/riscv64-unknown-elf-objdump /opt/riscv/bin/riscv32-unknown-elf-objdump

# Ghidra 11.4.2 (basic-block extraction) on JDK 21
COPY --from=jdk /opt/java/openjdk /opt/java/openjdk
ENV JAVA_HOME=/opt/java/openjdk PATH=/opt/java/openjdk/bin:$PATH
ARG GHIDRA_URL=https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_11.4.2_build/ghidra_11.4.2_PUBLIC_20250826.zip
RUN wget -q -O /tmp/ghidra.zip "$GHIDRA_URL" \
    && unzip -q /tmp/ghidra.zip -d /opt && mv /opt/ghidra_11.4.2_PUBLIC /opt/ghidra \
    && rm /tmp/ghidra.zip && rm -rf /opt/ghidra/docs
ENV GHIDRA_HOME=/opt/ghidra

RUN mkdir -p /artifact/results && chown -R rocq:rocq /artifact
USER rocq
WORKDIR /artifact/tig
COPY --chown=rocq:rocq tig/requirements.txt /artifact/tig/requirements.txt
COPY --chown=rocq:rocq tig/vendor/ /artifact/tig/vendor/
# TIG was evaluated on CPython 3.12 in a uv-managed venv; Debian 12 ships 3.11
RUN python3 -m venv /tmp/uvenv && /tmp/uvenv/bin/pip install --no-cache-dir uv==0.10.11 \
    && /tmp/uvenv/bin/uv venv --python 3.12 .venv \
    && /tmp/uvenv/bin/uv pip install --python .venv/bin/python -r requirements.txt \
    && rm -rf /tmp/uvenv
COPY --chown=rocq:rocq tig/ /artifact/tig/

# The compiled Cloq development, whose proofs TIG's output is checked against
FROM ${CLOQ_IMAGE} AS cloq-built
FROM tig-env
COPY --from=cloq-built --chown=rocq:rocq /artifact/cloq /artifact/cloq

CMD ["/artifact/tig/run_artifact.sh"]
