# DeviceTelemetry build: sim with ASan+UBSan, harness tests, demo.
CXX ?= g++
CXXFLAGS ?= -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer

all: build/sim

build/sim: src/sim.cpp
	mkdir -p build
	$(CXX) $(CXXFLAGS) src/sim.cpp -o build/sim

test: build/sim
	$(abspath ../../../.venv-builds/bin/python) -m unittest discover -s tests -v

demo: build/sim
	./build/sim clean 7 | $(abspath ../../../.venv-builds/bin/python) src/harness.py > results/demo_clean.json
	./build/sim corrupt 7 | $(abspath ../../../.venv-builds/bin/python) src/harness.py > results/demo_corrupt.json

clean:
	rm -rf build results/demo_*.json
