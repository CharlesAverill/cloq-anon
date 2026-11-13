# Builds every file listed in _CoqProject.
all: Makefile.coq
	+$(MAKE) -f Makefile.coq all

Makefile.coq: _CoqProject
	rocq makefile -f _CoqProject -o Makefile.coq

clean: Makefile.coq
	+$(MAKE) -f Makefile.coq clean
	rm -f Makefile.coq Makefile.coq.conf

.PHONY: all clean

# The ChaCha20 proof is excluded from `all` because it takes 10-20 minutes.
chacha20: all
	rocq compile -R ../../ Picinae crypto/chacha20/chacha20_proof.v

.PHONY: chacha20
