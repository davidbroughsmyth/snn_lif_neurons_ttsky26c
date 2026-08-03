# User Manual — snn_lif_neurons on Tiny Tapeout demoboard

How to **use and test** `tt_um_snn_lif_neuron` alone, and how to exercise it
**together with** the companion ADC `tt_um_davidbroughsmyth_ecg_sar12` using the
RP2350 on the Tiny Tapeout demo PCB.

| Doc | Link |
|---|---|
| Architecture | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Component datasheet | [DATASHEET.md](DATASHEET.md) |
| MicroPython HIL scripts | [`../demoboard/`](../demoboard/) |
| Companion ADC manual | [ADC USER_MANUAL](https://github.com/davidbroughsmyth/heart_monitor_adc_ttsky26c/blob/main/docs/USER_MANUAL.md) |
| Two-tile wiring | [ADC INTEGRATION](https://github.com/davidbroughsmyth/heart_monitor_adc_ttsky26c/blob/main/docs/INTEGRATION.md) |

Firmware / board references:

- [tt-demo-pcb](https://github.com/TinyTapeout/tt-demo-pcb) (RP2350 demoboard)
- [breakout-pcb](https://github.com/TinyTapeout/breakout-pcb) (ASIC carrier)
- [tt-micropython-firmware](https://github.com/TinyTapeout/tt-micropython-firmware) (DemoBoard SDK + examples)

---

## 1. Hardware stack

```mermaid
flowchart TB
  host[Host_PC_USB] --> rp[RP2350_on_tt_demo_pcb]
  rp -->|ui_uo_uio_clk_rst| mux[Project_mux]
  mux --> asic[ASIC_on_breakout_pcb]
```

1. ASIC sits on the **breakout**; breakout plugs into the **demoboard**.
2. Install a current **RP2350 UF2** from firmware [releases](https://github.com/TinyTapeout/tt-micropython-firmware/releases) (hold BOOT, copy UF2).
3. Open a serial REPL (`/dev/ttyACM0` or similar).

### Mux limitation (important)

The shuttle **enables one design at a time**. The RP2350 only sees that design’s pins.

| Scenario | Enabled project | What the RP2350 does |
|---|---|---|
| SNN alone / combined HIL | `tt_um_snn_lif_neuron` | Drive ADC-like samples + `sample_en`; read class / `diag_valid` / alarm |
| ADC alone | `tt_um_davidbroughsmyth_ecg_sar12` | Drive digital vin; read ADC bus (see ADC manual) |
| Two-tile silicon | both on chip, external wiring | INTEGRATION wiring; mux still shows one project’s pins to RP |

On the demoboard, **“combined with ADC” HIL** means: enable the **SNN** and have the
RP2350 **emulate** the ADC traffic the SAR tile would produce.

---

## 2. Circuit diagrams

### 2.1 SNN alone (RP synthesizes ADC bus)

```mermaid
flowchart LR
  rp[RP2350] -->|ui_adc_7_0| snn[snn_lif_neuron]
  rp -->|uio_adc_11_8| snn
  rp -->|uio_4_sample_en| snn
  snn -->|uo_class_2_0| rp
  snn -->|uo_3_diag_valid| rp
  snn -->|uo_4_alarm| rp
  rp -->|clk_rst_n| snn
```

**Bidirectional OE:** SNN uses `uio` as inputs. On the Pico:

`tt.uio_oe_pico.value = 0xFF`  
(drive `uio[4:0]` as ADC[11:8] + `sample_en`).

### 2.2 Combined — logical (post-silicon tile wiring)

```mermaid
flowchart LR
  ecg[ECG_front_end] --> adc[ecg_sar12]
  adc -->|uo_uio_sample_en| snn[snn_lif_neuron]
  clk[clk_50MHz] --> adc
  clk --> snn
  snn --> out[class_diag_alarm]
```

| ADC output | SNN input |
|---|---|
| `uo[7:0]` adc[7:0] | `ui_in[7:0]` |
| `uio[3:0]` adc[11:8] | `uio_in[3:0]` |
| `uio[4]` sample_en | `uio_in[4]` |

### 2.3 Combined — demoboard HIL (RP emulates ADC)

```mermaid
flowchart LR
  subgraph rp_role [RP2350_as_ADC]
    gen[baseline_Rpeak_morphology]
  end
  gen -->|adc_bus_sample_en| snn[snn_lif_neuron]
  snn -->|class_diag_alarm| host[REPL_or_HIL_assert]
```

Same pin map as §2.1. Scripts: `demoboard/tt_um_snn_lif_neuron/`.

### 2.4 Optional: verify ADC companion first

```mermaid
flowchart LR
  rp[RP2350] -->|vin_proxy| adc[ecg_sar12]
  adc -->|adc_sample_en| rp
```

Enable the ADC project and run companion HIL from
[heart_monitor_adc demoboard](https://github.com/davidbroughsmyth/heart_monitor_adc_ttsky26c/tree/main/demoboard)
before relying on real silicon ADC→SNN wiring.

---

## 3. Using the SNN alone

### 3.1 Stimulus recipe

| Phase | ADC code | `sample_en` |
|---|---|---|
| Baseline | ~150 | pulse each sample |
| R-peak | ≥ 2200 | pulse |
| Morphology | gentle Δ≈15–49 or steep Δ≥50 | ~100 pulses |
| Readout | — | wait for `uo[3]` `diag_valid`; class on `uo[2:0]` |

| Class | Typical morphology |
|---|---|
| 0 Normal | Gentle rising |
| 1 Supra | Gentle falling |
| 2 Ventricular | Steep rising |
| 3 Fusion | Steep falling |
| 4 Unknown | Zigzag / flips |

Alarm: **3 consecutive** classes in {1, 2, 4}; cleared by 0 or 3.

### 3.2 REPL smoke

```python
from ttboard.demoboard import DemoBoard
from ttboard.mode import RPMode

tt = DemoBoard.get()
tt.mode = RPMode.ASIC_RP_CONTROL
tt.shuttle.tt_um_snn_lif_neuron.enable()
# Fallback: tt.shuttle.find('snn')[0].enable()

tt.uio_oe_pico.value = 0xFF
tt.reset_project(True)
tt.reset_project(False)
tt.clock_project_PWM(1_000_000)
```

Prefer the packaged HIL (drives a full beat):

```python
import examples.tt_um_snn_lif_neuron as snn_hil
snn_hil.run()
```

### 3.3 Desktop RTL (no ASIC)

```sh
cd test
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
make -B
```

Includes synthetic class/alarm tests and MIT-BIH CSV stream smoke
(`test/data/mitbih_100_excerpt.csv`).

---

## 4. Combined with heart_monitor_adc

### 4.1 Demoboard HIL (recommended before silicon)

1. Enable `tt_um_snn_lif_neuron`.
2. Run `demoboard/tt_um_snn_lif_neuron` — RP plays ADC.
3. Expect gentle-rise → class 0; three steep-rise → alarm.

### 4.2 Two-tile silicon

1. Wire ADC digital bus → SNN per INTEGRATION table; share `clk` / `rst_n` / GND.
2. ECG / function-gen → ADC `ua[0]`; `ua[1]` = vref.
3. To observe SNN outputs on the RP, **enable the SNN** in the mux (ADC still runs if clocked on-chip / shared clock — pin visibility is SNN’s).
4. To debug the ADC alone, enable the ADC project and use the ADC user manual.

---

## 5. Installing MicroPython tests

```sh
pip install --user mpremote
mpremote connect list
mpremote fs mkdir :/examples
mpremote fs cp -r demoboard/tt_um_snn_lif_neuron :/examples/
mpremote reset
```

REPL:

```python
import examples.tt_um_snn_lif_neuron as t
t.run()
```

Style matches
[tt_um_factory_test.py](https://github.com/TinyTapeout/tt-micropython-firmware/blob/main/src/examples/tt_um_factory_test/tt_um_factory_test.py):
`@cocotb.test()`, `DemoBoard.get()`, black-box I/O only.

---

## 6. Troubleshooting

| Symptom | Check |
|---|---|
| Project missing | `tt.shuttle.find('snn')` — design must be on the shuttle JSON |
| No `diag_valid` | R-peak ≥ 2200 then ~100 morphology samples with `sample_en` |
| Wrong class | Gentle vs steep Δ (15 / 50); clear window / reset between beats |
| Alarm stuck / never | Need 3× {1,2,4}; 0/3 clear; check `uo[4]` after 3rd `diag_valid` |
| Bus X | `ASIC_RP_CONTROL`; `uio_oe_pico = 0xFF` |

---

## 7. Quick reference

```text
SNN: all consumer uio are inputs
Pico uio_oe_pico = 0xFF

adc[7:0]  -> ui_in[7:0]
adc[11:8] -> uio_in[3:0]
sample_en -> uio_in[4]

uo[2:0] class | uo[3] diag_valid | uo[4] alarm
R_PEAK_THRESHOLD = 2200
```
