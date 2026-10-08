# FleetDoctor — diagnostics that admit what they can't see

Host health checks (disk, memory, DNS, process, load, quota) where a blind
check reports UNKNOWN — never healthy. A confined fault lab (temp dirs only;
`/`, home and outside refused) seeds quota exhaustion, killed services, DNS
failure and CPU pressure with verified setup and reaping cleanup, then scores
localization (4/4, zero false alarms) into hedged reports that name evidence
and next steps, never a proven root cause. Pure Python, stdlib only.

## Run it

```sh
python3 -B -m unittest discover -p 'test_*.py'   # 19 tests
```

Faults are process- and directory-level (no containers/VMs here) with a
documented emergency stop (`cleanup()`). No spare hardware exists, so no
hardware work was performed or claimed — process labs are not server repair.

## Limits

Single host; OS-dependent memory/pressure semantics. Localization is
check-firing, not diagnosis. Container/VM and physical-machine validation
need runtimes and hardware not present here.
