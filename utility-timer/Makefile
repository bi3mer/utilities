.PHONY: all clean run

all:
	dune build
	mkdir -p bin
	cp _build/default/bin/main.exe bin/utility-timer

run:
	dune exec utility-timer -- $(filter-out run,$(MAKECMDGOALS))

%:
	@:

clean:
	dune clean
	rm -rf bin