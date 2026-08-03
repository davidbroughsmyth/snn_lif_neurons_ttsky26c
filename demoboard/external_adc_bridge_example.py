# SPDX-FileCopyrightText: © 2025 davidbroughsmyth
# SPDX-License-Identifier: Apache-2.0
"""
External ADC → SNN bridge example for the Tiny Tapeout demoboard (RP2350).

Fill in SPI (or parallel) read for your chip (ADS7886 / MCP3201 / …), then pack
each 12-bit sample onto the SNN consumer bus and pulse sample_en.

See docs/USER_MANUAL.md §4.
"""

import time

from machine import Pin, SPI  # type: ignore
from ttboard.demoboard import DemoBoard
from ttboard.mode import RPMode

PROJECT = "tt_um_snn_lif_neuron"
UIO_OE_PICO = 0xFF

# --- User: assign free RP GPIOs for your ADC (NOT ui/uo/uio project pins) ---
SPI_SCK = 10
SPI_MOSI = 11
SPI_MISO = 12
SPI_CS = 13


def pack_snn_bus(tt, code: int, sample_en: int = 0):
    code &= 0xFFF
    tt.ui_in.value = code & 0xFF
    tt.uio_in.value = ((code >> 8) & 0xF) | ((sample_en & 1) << 4)


def pulse_sample(tt, code: int, high_ms: float = 0.05, gap_ms: float = 0.05):
    """Assert sample_en briefly while adc code is stable on the bus."""
    pack_snn_bus(tt, code, 1)
    time.sleep_ms(max(1, int(high_ms)))
    pack_snn_bus(tt, code, 0)
    time.sleep_ms(max(1, int(gap_ms)))


def read_external_adc_spi(spi, cs) -> int:
    """
    Placeholder — replace with your ADC protocol.

    Example sketch for a 12-bit SPI SAR (timing/bit order are part-specific):
      cs(0)
      raw = spi.read(2)
      cs(1)
      return ((raw[0] << 8) | raw[1]) & 0xFFF
    """
    cs(0)
    raw = spi.read(2)
    cs(1)
    # Many ADCs left-justify 12 bits in 16 — adjust masks to your datasheet
    return ((raw[0] << 4) | (raw[1] >> 4)) & 0xFFF


def enable_snn(tt: DemoBoard):
    if tt.shuttle.has(PROJECT):
        getattr(tt.shuttle, PROJECT).enable()
    else:
        found = tt.shuttle.find("snn")
        if not found:
            raise RuntimeError("SNN project not on this shuttle")
        found[0].enable()


def main():
    tt = DemoBoard.get()
    tt.mode = RPMode.ASIC_RP_CONTROL
    enable_snn(tt)
    tt.uio_oe_pico.value = UIO_OE_PICO
    tt.reset_project(True)
    tt.reset_project(False)
    tt.clock_project_PWM(1_000_000)

    # SPI on free GPIOs — edit pin numbers above
    cs = Pin(SPI_CS, Pin.OUT, value=1)
    spi = SPI(
        1,
        baudrate=1_000_000,
        polarity=0,
        phase=0,
        sck=Pin(SPI_SCK),
        mosi=Pin(SPI_MOSI),
        miso=Pin(SPI_MISO),
    )

    print("External ADC bridge running — Ctrl-C to stop")
    print("Scale input so R-peaks >= 2200 for segmenter")

    while True:
        code = read_external_adc_spi(spi, cs)
        pulse_sample(tt, code)
        uo = int(tt.uo_out.value)
        if (uo >> 3) & 1:
            cls = uo & 7
            alarm = (uo >> 4) & 1
            print("diag_valid class=%d alarm=%d code=%d" % (cls, alarm, code))


if __name__ == "__main__":
    main()
