# SPDX-FileCopyrightText: © 2025 davidbroughsmyth
# SPDX-License-Identifier: Apache-2.0

"""cocotb tests for the Tiny Tapeout SNN heart-monitor wrapper."""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles


ALARM_N = 3


def set_adc(dut, value: int, sample_en: int = 0):
    """Drive 12-bit ADC on ui_in + uio_in[3:0], sample_en on uio_in[4]."""
    value &= 0xFFF
    dut.ui_in.value = value & 0xFF
    dut.uio_in.value = ((sample_en & 1) << 4) | ((value >> 8) & 0xF)


def read_outputs(dut):
    uo = int(dut.uo_out.value)
    return {
        "class": uo & 0x7,
        "valid": (uo >> 3) & 1,
        "alarm": (uo >> 4) & 1,
    }


async def pulse_sample(dut, value: int, idle_cycles: int = 4):
    """
    Present ADC value and pulse sample_en for one clock.
    Returns outputs if diagnostic_valid is observed during the following cycles
    (valid is a 1-cycle pulse two clocks after window_end).
    """
    set_adc(dut, value, sample_en=0)
    await RisingEdge(dut.clk)
    set_adc(dut, value, sample_en=1)
    await RisingEdge(dut.clk)
    set_adc(dut, value, sample_en=0)

    captured = None
    for _ in range(max(idle_cycles, 3)):
        await RisingEdge(dut.clk)
        out = read_outputs(dut)
        if out["valid"]:
            # Alarm FSM updates on the next posedge after diagnostic_valid
            await RisingEdge(dut.clk)
            captured = read_outputs(dut)
            # finish remaining idle if any
            break
    return captured


async def send_beat(dut, class_id: int):
    """Drive one synthetic beat; return settled {class, valid, alarm}."""
    got = await pulse_sample(dut, 2500)

    def values():
        if class_id == 0:
            for k in range(1, 101):
                yield min(2500 + k * 25, 4095)
        elif class_id == 1:
            for k in range(1, 101):
                yield max(2500 - k * 25, 0)
        elif class_id == 2:
            for k in range(1, 101):
                yield min(2500 + k * 80, 4095)
        elif class_id == 3:
            for k in range(1, 101):
                yield max(2500 - k * 80, 0)
        else:
            for k in range(100):
                yield 3000 if (k % 2) == 0 else 2000

    for val in values():
        cap = await pulse_sample(dut, val)
        if cap is not None:
            got = cap
            break

    # Baseline / refractory cover
    for _ in range(120):
        cap = await pulse_sample(dut, 150)
        if cap is not None:
            got = cap
        if got is not None and _ >= 60:
            break

    if got is None:
        raise TimeoutError(f"No diagnostic_valid for class {class_id}")
    return got


async def reset_dut(dut):
    clock = Clock(dut.clk, 20, unit="ns")  # 50 MHz
    cocotb.start_soon(clock.start())

    dut.ena.value = 1
    set_adc(dut, 150, sample_en=0)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)


@cocotb.test()
async def test_classify_gentle_rise(dut):
    """Class 0 (Normal) from a gentle rising slope after R-peak."""
    await reset_dut(dut)
    out = await send_beat(dut, 0)
    dut._log.info("gentle rise -> %s", out)
    assert out["class"] == 0, f"expected class 0, got {out}"


@cocotb.test()
async def test_classify_steep_rise(dut):
    """Class 2 (Ventricular) from a steep rising slope."""
    await reset_dut(dut)
    out = await send_beat(dut, 2)
    dut._log.info("steep rise -> %s", out)
    assert out["class"] == 2, f"expected class 2, got {out}"


@cocotb.test()
async def test_classify_zigzag(dut):
    """Class 4 (Unknown) from alternating steep edges."""
    await reset_dut(dut)
    out = await send_beat(dut, 4)
    dut._log.info("zigzag -> %s", out)
    assert out["class"] == 4, f"expected class 4, got {out}"


@cocotb.test()
async def test_alarm_persistence(dut):
    """Alarm asserts only after ALARM_PERSIST_MAX consecutive anomalies."""
    await reset_dut(dut)

    out = await send_beat(dut, 0)
    assert out["class"] == 0
    assert out["alarm"] == 0

    for n in range(1, ALARM_N):
        out = await send_beat(dut, 2)
        dut._log.info("anomaly %d/%d -> %s", n, ALARM_N, out)
        assert out["class"] == 2
        assert out["alarm"] == 0, f"alarm early on beat {n}"

    out = await send_beat(dut, 2)
    dut._log.info("anomaly %d/%d -> %s", ALARM_N, ALARM_N, out)
    assert out["class"] == 2
    assert out["alarm"] == 1, "alarm should assert on 3rd consecutive anomaly"

    out = await send_beat(dut, 0)
    assert out["class"] == 0
    assert out["alarm"] == 0, "Normal should clear alarm"
