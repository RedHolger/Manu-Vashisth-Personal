"""Read-only harness: parse frames, check CRC/seq/range, enforce state machine."""
import json
import sys

SYNC = (0xA5, 0x5A)
TYPES = {0x01: "data", 0x02: "status", 0x03: "reset-ack"}
LIMIT = 4000  # |value| centi-units


def crc16(data: bytes) -> int:
    c = 0xFFFF
    for b in data:
        c ^= b << 8
        for _ in range(8):
            c = ((c << 1) ^ 0x1021) & 0xFFFF if c & 0x8000 else (c << 1) & 0xFFFF
    return c


def parse_frame(line: str, lineno: int) -> dict:
    raw = bytes.fromhex(line.strip())
    if len(raw) != 12:
        return {"ok": False, "error": "bad-length", "lineno": lineno}
    if (raw[0], raw[1]) != SYNC:
        return {"ok": False, "error": "bad-sync", "lineno": lineno}
    body, got = raw[:10], int.from_bytes(raw[10:], "big")
    if crc16(body) != got:
        return {"ok": False, "error": "bad-crc", "lineno": lineno}
    value = int.from_bytes(body[4:6], "big", signed=True)
    return {"ok": True, "seq": body[2], "type": body[3], "value": value, "lineno": lineno}


class Monitor:
    def __init__(self) -> None:
        self.state = "IDLE"
        self.last_seq: int | None = None
        self.events: list[dict] = []

    def _ev(self, kind: str, detail: str) -> None:
        self.events.append({"type": kind, "detail": detail})

    def feed(self, fr: dict) -> None:
        if not fr["ok"]:
            self.state = "FAULT"
            self._ev("CORRUPT_FRAME", f"line {fr['lineno']}: {fr['error']}")
            return
        if self.last_seq is not None:
            if fr["seq"] == self.last_seq:
                self._ev("DUPLICATE_SEQ", f"seq {fr['seq']}")
            else:
                d = (fr["seq"] - self.last_seq) % 256
                if d == 1:
                    pass  # in order
                elif d >= 128:
                    self._ev("SEQ_REGRESSION", f"{self.last_seq}->{fr['seq']} (reordered?)")
                else:
                    self._ev("SEQ_GAP", f"{self.last_seq}->{fr['seq']} (dropped?)")
        self.last_seq = fr["seq"]
        if abs(fr["value"]) > LIMIT:
            self.state = "FAULT"
            self._ev("OUT_OF_RANGE", f"seq {fr['seq']}: {fr['value']}")
            return
        if self.state == "IDLE" and fr["type"] == 0x01:
            self.state = "STREAMING"
        if fr["type"] == 0x03 and self.state == "FAULT":
            self.state = "IDLE"
            self._ev("RESET_OK", "reset-ack accepted")

    def summary(self) -> dict:
        kinds = sorted({e["type"] for e in self.events})
        return {"final_state": self.state, "event_kinds": kinds, "events": self.events}


def run(lines: list[str]) -> dict:
    mon = Monitor()
    for i, line in enumerate(lines):
        if line.strip():
            mon.feed(parse_frame(line, i + 1))
    return mon.summary()


if __name__ == "__main__":
    print(json.dumps(run(sys.stdin.read().splitlines()), indent=2))
