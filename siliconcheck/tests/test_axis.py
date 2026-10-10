"""AXI-Stream adapter tests: ordered flow with backpressure, overflow blocking.

Race-free discipline: at each FallingEdge, sample DUT outputs then drive inputs
(5ns setup before the rise the DUT samples). Handshake bookkeeping uses the
PRE-edge values both sides agreed on, so every counted transfer really happened.
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
    dut.s_valid.value = 0
    dut.s_data.value = 0
    dut.m_ready.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)


@cocotb.test()
async def test_stream_order_with_backpressure(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)
    rng = random.Random(1234)
    n_words = 4 * DEPTH + 3
    tx = [rng.getrandbits(DW) & MASK for _ in range(n_words)]
    rx = []
    ti = 0
    while len(rx) < n_words:
        await FallingEdge(dut.clk)
        s_ready = int(dut.s_ready.value)
        m_valid = int(dut.m_valid.value)
        m_ready = 1 if rng.random() < 0.7 else 0
        accept = (ti < n_words) and bool(s_ready)
        pop = bool(m_valid) and bool(m_ready)
        if accept:
            dut.s_valid.value = 1
            dut.s_data.value = tx[ti]
        else:
            dut.s_valid.value = 0
        dut.m_ready.value = m_ready
        await RisingEdge(dut.clk)  # both handshakes (if asserted) land here
        await ReadOnly()
        m_d = int(dut.m_data.value)
        if accept:
            ti += 1
        if pop:
            rx.append(m_d)
    assert rx == tx, "stream order corrupted under backpressure"


@cocotb.test()
async def test_overflow_blocks_ingress(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)
    for i in range(DEPTH + 6):
        await FallingEdge(dut.clk)
        dut.s_valid.value = 1
        dut.s_data.value = i & MASK
        dut.m_ready.value = 0  # never drain
        await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.s_valid.value = 0
    assert int(dut.s_ready.value) == 0, "s_ready must drop when full"
    assert int(dut.count.value) == DEPTH, "overflow words must be rejected"
    for i in range(DEPTH):
        await FallingEdge(dut.clk)
        dut.m_ready.value = 1
        await RisingEdge(dut.clk)  # pop lands here
        await ReadOnly()
        got = int(dut.m_data.value)
        assert got == (i & MASK), f"word {i} corrupted (got {got})"
    await FallingEdge(dut.clk)
    dut.m_ready.value = 0
    assert int(dut.empty.value) == 1
