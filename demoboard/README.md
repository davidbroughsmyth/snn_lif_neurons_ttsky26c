# Demoboard MicroPython HIL — snn_lif_neurons

Hardware-in-the-loop tests for the Tiny Tapeout **demo PCB** (RP2350) + ASIC
**breakout**, using the [tt-micropython-firmware](https://github.com/TinyTapeout/tt-micropython-firmware)
API.

See [docs/USER_MANUAL.md](../docs/USER_MANUAL.md).

| Package / file | Enables | Role |
|---|---|---|
| `tt_um_snn_lif_neuron/` | SNN | RP emulates ADC → class / `diag_valid` / alarm |
| `external_adc_bridge_example.py` | SNN | Template: SPI ADC → pack bus + `sample_en` (edit pins) |

ADC-alone HIL lives in the fabrication companion repo:
[heart_monitor_adc_art demoboard](https://github.com/davidbroughsmyth/heart_monitor_adc_art_ttsky26c/tree/main/demoboard).

External ADC setup: [docs/USER_MANUAL.md](../docs/USER_MANUAL.md) §4.
