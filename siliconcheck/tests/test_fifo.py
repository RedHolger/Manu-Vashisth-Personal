"""FIFO tests: reset, ordering, full/empty, wraparound, simultaneous R+W.

Race-free discipline: drive inputs right after a FallingEdge await (writable
phase, 5ns setup before the rise the DUT samples); sample outputs in ReadOnly
after the RisingEdge. No driving in ReadOnly; no same-timestep drive/edge races.
"""
import os
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, ReadOnly, RisingEdge

DEPTH = int(os.environ.get("CFG_DEPTH", "16"))
DW = int(os.environ.get("CFG_DW", "32"))
MASK = (1 << DW) - 1


async def reset(dut):
    dut.rst_n.value = 0
    dut.wr_en.value = 0
    dut.rd_en.value = 0
    dut.din.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)


async def write_word(dut, val):
    await FallingEdge(dut.clk)
    dut.din.value = val & MASK
    dut.wr_en.value = 1
    dut.rd_en.value = 0
    await RisingEdge(dut.clk)  # transfer lands here
    await FallingEdge(dut.clk)
    dut.wr_en.value = 0


async def read_word(dut):
    await FallingEdge(dut.clk)
    dut.wr_en.value = 0
    dut.rd_en.value = 1
    await RisingEdge(dut.clk)  # pop lands here; dout updates
    await ReadOnly()
    got = int(dut.dout.value)
    await FallingEdge(dut.clk)
    dut.rd_en.value = 0
    return got


async def sample_flags(dut):
    await ReadOnly()
    return (int(dut.full.value), int(dut.empty.value), int(dut.count.value))


@cocotb.test()
async def test_reset(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)
    full, empty, count = await sample_flags(dut)
    await FallingEdge(dut.clk)
    assert (full, empty, count) == (0, 1, 0)


@cocotb.test()
async def test_ordered_fill_drain(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)
    rng = random.Random(42)
    data = [rng.getrandbits(DW) for _ in range(DEPTH)]
    for w in data:
        await write_word(dut, w)
    full, _, count = await sample_flags(dut)
    await FallingEdge(dut.clk)
    assert full == 1, "full must assert at DEPTH"
    assert count == DEPTH
    for want in data:
        assert await read_word(dut) == (want & MASK)
    _, empty, _ = await sample_flags(dut)
    await FallingEdge(dut.clk)
    assert empty == 1


@cocotb.test()
async def test_overflow_ignored(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)
    for i in range(DEPTH):
        await write_word(dut, 0xA000 + i)
    for _ in range(4):  # extra writes must be ignored, not corrupt
        await write_word(dut, 0xDEAD)
    _, _, count = await sample_flags(dut)
    await FallingEdge(dut.clk)
    assert count == DEPTH
    for i in range(DEPTH):
        assert await read_word(dut) == ((0xA000 + i) & MASK)


@cocotb.test()
async def test_empty_read_ignored(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)
    await read_word(dut)
    _, empty, count = await sample_flags(dut)
    await FallingEdge(dut.clk)
    assert (empty, count) == (1, 0)


@cocotb.test()
async def test_wraparound_and_simultaneous(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)
    rng = random.Random(7)
    shadow = []
    occ = 0
    for step in range(6 * DEPTH + 5):
        do_wr = (occ < DEPTH) and (occ == 0 or rng.random() < 0.6)
        do_rd = (occ > 0) and (not do_wr or rng.random() < 0.5)
        w = rng.getrandbits(DW)
        await FallingEdge(dut.clk)
        dut.din.value = w & MASK
        dut.wr_en.value = 1 if do_wr else 0
        dut.rd_en.value = 1 if do_rd else 0
        await RisingEdge(dut.clk)
        await ReadOnly()
        got = int(dut.dout.value)
        cnt = int(dut.count.value)
        if do_wr:
            shadow.append(w & MASK)
            occ += 1
        if do_rd:
            assert got == shadow.pop(0), f"order break at step {step}"
            occ -= 1
        assert cnt == occ, f"count mismatch at step {step} (dut {cnt})"
    while shadow:
        assert await read_word(dut) == shadow.pop(0)
