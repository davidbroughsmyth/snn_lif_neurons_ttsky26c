# Demoboard MicroPython HIL — snn_lif_neurons

Hardware-in-the-loop tests for the Tiny Tapeout **demo PCB** (RP2350) + ASIC
**breakout**, using the [tt-micropython-firmware](https://github.com/TinyTapeout/tt-micropython-firmware)
API.

See [docs/USER_MANUAL.md](../docs/USER_MANUAL.md).

| Package | Enables | Role |
|---|---|---|
| `tt_um_snn_lif_neuron/` | SNN | RP emulates ADC → class / `diag_valid` / alarm |

ADC-alone HIL lives in the companion repo:
[heart_monitor_adc demoboard](https://github.com/davidbroughsmyth/heart_monitor_adc_ttsky26c/tree/main/demoboard).
