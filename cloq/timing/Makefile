# Builds every file listed in _CoqProject.
all: Makefile.coq
	+$(MAKE) -f Makefile.coq all

Makefile.coq: _CoqProject
	rocq makefile -f _CoqProject -o Makefile.coq

clean: Makefile.coq
	+$(MAKE) -f Makefile.coq clean
	rm -f Makefile.coq Makefile.coq.conf

.PHONY: all clean
