![](../../workflows/gds/badge.svg) ![](../../workflows/docs/badge.svg) ![](../../workflows/test/badge.svg) ![](../../workflows/fpga/badge.svg)

# snn_lif_neurons (Tiny Tapeout)

Spiking neural network heart-beat classifier for Tiny Tapeout (ttsky26c).

- [Project documentation](docs/info.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Component datasheet](docs/DATASHEET.md) (databook style)
- [User manual](docs/USER_MANUAL.md) (demoboard + HIL)
- [Companion ADC manual](https://github.com/davidbroughsmyth/heart_monitor_adc_ttsky26c/blob/main/docs/USER_MANUAL.md)

## What it does

Classifies synthetic ECG-like morphology after an R-peak using five banded LIF neurons (Normal / Supra / Ventricular / Fusion / Unknown). An alarm asserts only after **three consecutive** anomaly beats.

## Pin summary

| Pins | Function |
|---|---|
| `ui_in[7:0]` | ADC `[7:0]` |
| `uio_in[3:0]` | ADC `[11:8]` |
| `uio_in[4]` | `sample_en` |
| `uo_out[2:0]` | heart class |
| `uo_out[3]` | `diagnostic_valid` |
| `uo_out[4]` | `alarm_strobe` |

## Local test

```sh
cd test
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
make -B
```

Includes synthetic class/alarm checks plus a MIT-BIH CSV stream smoke test
(`test/data/mitbih_100_excerpt.csv`).

## What is Tiny Tapeout?

Tiny Tapeout makes it easier and cheaper to get digital designs manufactured on a real chip. Learn more at https://tinytapeout.com.

## Resources

- [FAQ](https://tinytapeout.com/faq/)
- [Digital design lessons](https://tinytapeout.com/digital_design/)
- [Build your design locally](https://www.tinytapeout.com/guides/local-hardening/)
- [Submit to a shuttle](https://app.tinytapeout.com/)
