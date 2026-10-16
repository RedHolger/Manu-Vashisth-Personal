# DeviceTelemetry

A C++ sensor-frame generator and a Python monitor for testing what happens when a stream contains damaged or missing data. The generator can emit clean frames or introduce seeded corruption, drops, reordering and out-of-range readings.

The monitor checks CRC16, sequence numbers and value ranges. It latches a fault and handles reset acknowledgements instead of treating the next good frame as proof of recovery.

## Build and test

Requirements: a C++17 compiler with AddressSanitizer/UBSan, Make and Python 3. From this directory:

```bash
make all
python3 -m unittest discover -s tests -v
mkdir -p results
./build/sim clean 7 | python3 src/harness.py > results/demo_clean.json
./build/sim corrupt 7 | python3 src/harness.py > results/demo_corrupt.json
```

`make test` and `make demo` are also available in the original workspace, but their Python path points at its shared `.venv-builds`. The commands above avoid that dependency.

The 12-byte frame format is documented in [SPEC.md](SPEC.md). This is a software simulator; it has not been used to validate a physical sensor or medical device. [EVIDENCE.md](EVIDENCE.md) records the saved sanitizer and harness runs.
