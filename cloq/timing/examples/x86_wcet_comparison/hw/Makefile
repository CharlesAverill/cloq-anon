# Measures the analyzed x86-64 functions on this machine's i5-7300U.
#   make            build ./measure
#   make run        measure into results/ (needs kernel.perf_event_paranoid <= 2)
#   make compare    compare results/ with the proofs' bounds

CFLAGS = -O2 -Wall -Wextra

measure: main.c measure.S funcs.h
	$(CC) $(CFLAGS) -o $@ main.c measure.S

funcs.h: extract.py
	python3 extract.py > $@

run: measure
	./measure 3 results

compare:
	python3 compare.py results

clean:
	rm -f measure

.PHONY: run compare clean
