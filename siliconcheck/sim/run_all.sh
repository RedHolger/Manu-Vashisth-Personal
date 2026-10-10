#!/bin/bash
# Regression: both DUTs x DEPTH/DATA_WIDTH configs. Writes results/regression.json.
# Fails (exit 1) if any config fails.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
export PATH="/opt/homebrew/bin:/Users/manuvashistha/Developer/MANU_INTERNSHIP_OPPURTUNITIES/.venv-builds/bin:$PATH"
cd "$HERE"
VENV=/Users/manuvashistha/Developer/MANU_INTERNSHIP_OPPURTUNITIES/.venv-builds/bin/python
overall=0
json_rows=""
for cfg in "4 8" "16 32" "64 32"; do
  set -- $cfg; DEPTH=$1; DW=$2
  for tm in "fifo test_fifo" "axis_adapter test_axis"; do
    set -- $tm; TOP=$1; MOD=$2
    echo "=== TOP=$TOP MOD=$MOD DEPTH=$DEPTH DW=$DW ==="
    if make TOP=$TOP TESTMOD=$MOD DEPTH=$DEPTH DW=$DW > /tmp/sim_${TOP}_${DEPTH}.log 2>&1; then
      st="pass"
    else
      st="fail"; overall=1
    fi
    echo "$st (log /tmp/sim_${TOP}_${DEPTH}.log)"
    json_rows="$json_rows{\"top\":\"$TOP\",\"depth\":$DEPTH,\"dw\":$DW,\"status\":\"$st\"},"
  done
done
$VENV -c "
import json
rows = json.loads('[' + '''$json_rows'''.rstrip(',') + ']')
open('../results/regression.json','w').write(json.dumps(rows, indent=2))
print(json.dumps(rows, indent=2))
"
exit $overall
