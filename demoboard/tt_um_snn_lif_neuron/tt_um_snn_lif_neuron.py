# SPDX-FileCopyrightText: © 2025 davidbroughsmyth
# SPDX-License-Identifier: Apache-2.0
"""
Hardware-in-the-loop tests for tt_um_snn_lif_neuron (canonical copy in
snn_lif_neurons_ttsky26c/demoboard).

SNN alone / combined HIL: enable the SNN; RP2350 synthesizes ADC samples +
sample_en (as if heart_monitor_adc were wired in). Patterned after
TinyTapeout/tt-micropython-firmware examples.
"""

import gc

from ttboard.demoboard import DemoBoard
from ttboard.mode import RPMode
from microcotb.clock import Clock
from microcotb.triggers import RisingEdge, ClockCycles
import microcotb as cocotb

gc.collect()
cocotb.set_runner_scope(__name__)

PROJECT = "tt_um_snn_lif_neuron"

# SNN treats all uio as inputs — Pico drives ADC bus + sample_en
UIO_OE_PICO = 0xFF

R_PEAK = 2200
BASELINE = 150
EVAL_SAMPLES = 100


def drive_adc(dut, code: int, sample_en: int = 1):
    code &= 0xFFF
    dut.ui_in.value = code & 0xFF
    # uio[3:0]=adc[11:8], uio[4]=sample_en, [7:5]=0
    dut.uio_in.value = ((code >> 8) & 0xF) | ((sample_en & 1) << 4)


async def pulse_sample(dut, code: int, clocks_high: int = 4, clocks_gap: int = 2):
    drive_adc(dut, code, 1)
    await ClockCycles(dut.clk, clocks_high)
    drive_adc(dut, code, 0)
    await ClockCycles(dut.clk, clocks_gap)


async def reset_dut(dut):
    cocotb.start_soon(Clock(dut.clk, 2, units="us").start())
    dut.ena.value = 1
    dut.uio_oe_pico.value = UIO_OE_PICO
    drive_adc(dut, BASELINE, 0)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)


def read_class_valid_alarm(dut):
    uo = int(dut.uo_out.value)
    return uo & 0x7, (uo >> 3) & 1, (uo >> 4) & 1


async def beat_gentle_rise(dut):
    """Baseline, R-peak, then gentle rising morphology (~Δ15–40)."""
    for _ in range(5):
        await pulse_sample(dut, BASELINE)
    await pulse_sample(dut, R_PEAK)
    level = R_PEAK
    for _ in range(EVAL_SAMPLES):
        level = min(4095, level + 20)  # steepness in gentle band relative to encoder
        # Use smaller steps for gentle: delta 20 is between 15 and 50
        await pulse_sample(dut, level)


async def beat_steep_rise(dut):
    for _ in range(5):
        await pulse_sample(dut, BASELINE)
    await pulse_sample(dut, R_PEAK)
    level = R_PEAK
    for _ in range(EVAL_SAMPLES):
        level = min(4095, level + 60)  # >= STEEP_THRESHOLD 50
        await pulse_sample(dut, level)


@cocotb.test()
async def test_gentle_rise_class0(dut):
    """RP-as-ADC: gentle rise after R-peak → class 0 + diag_valid."""
    dut._log.info("SNN HIL: gentle rise → class 0")
    await reset_dut(dut)
    await beat_gentle_rise(dut)

    # allow voter / window end
    got_valid = False
    cls = None
    for _ in range(500):
        await RisingEdge(dut.clk)
        c, v, _a = read_class_valid_alarm(dut)
        if v:
            got_valid = True
            cls = c
            break

    assert got_valid, "diag_valid did not pulse"
    dut._log.info("class=%d", cls)
    assert cls == 0, f"expected class 0, got {cls}"


@cocotb.test()
async def test_alarm_after_three_steep(dut):
    """Three steep-rise (ventricular) beats assert alarm; Normal clears."""
    dut._log.info("SNN HIL: alarm persistence")
    await reset_dut(dut)

    for i in range(3):
        await beat_steep_rise(dut)
        # drain until diag_valid
        for _ in range(800):
            await RisingEdge(dut.clk)
            c, v, a = read_class_valid_alarm(dut)
            if v:
                dut._log.info("beat %d class=%d alarm=%d", i + 1, c, a)
                break

    # After 3rd anomaly, alarm should be set (may still be high)
    _c, _v, alarm = read_class_valid_alarm(dut)
    # one more poll window
    for _ in range(50):
        await RisingEdge(dut.clk)
        _c, _v, alarm = read_class_valid_alarm(dut)
        if alarm:
            break
    assert alarm == 1, "alarm should assert after 3 anomalies"

    # Clear with gentle/normal beat
    await beat_gentle_rise(dut)
    for _ in range(800):
        await RisingEdge(dut.clk)
        c, v, a = read_class_valid_alarm(dut)
        if v and c == 0:
            assert a == 0, "alarm should clear on Normal"
            break


def _enable_project(tt: DemoBoard):
    if tt.shuttle.has(PROJECT):
        getattr(tt.shuttle, PROJECT).enable()
        return
    found = tt.shuttle.find("snn_lif")
    if not found:
        found = tt.shuttle.find("snn")
    if not found:
        raise RuntimeError(f"{PROJECT} not on this shuttle — try shuttle.find()")
    found[0].enable()


def main():
    import ttboard.cocotb.dut
    from microcotb.time.value import TimeValue

    class DUT(ttboard.cocotb.dut.DUT):
        def __init__(self):
            super().__init__("snn_lif")
            self.tt = DemoBoard.get()
            self.add_slice_attribute("heart_class", self.tt.uo_out, 2, 0)
            self.add_bit_attribute("diag_valid", self.tt.uo_out, 3)
            self.add_bit_attribute("alarm", self.tt.uo_out, 4)

    tt = DemoBoard.get()
    if tt.mode != RPMode.ASIC_RP_CONTROL:
        tt.mode = RPMode.ASIC_RP_CONTROL

    _enable_project(tt)
    tt.uio_oe_pico.value = UIO_OE_PICO
    TimeValue.ReBaseStringUnits = True

    runner = cocotb.get_runner(__name__)
    dut = DUT()
    dut._log.info("enabled %s — RP emulates ADC", PROJECT)
    runner.test(dut)
    return runner


if __name__ == "__main__":
    main()
