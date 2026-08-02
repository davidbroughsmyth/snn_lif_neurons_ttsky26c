# MIT-BIH test data

Excerpt from the [MIT-BIH Arrhythmia Database](https://physionet.org/content/mitdb/1.0.0/)
(PhysioNet; Goldberger et al., Moody & Mark).

## Files

| File | Description |
|---|---|
| `mitbih_100_excerpt.csv` | ~15 s of record **100**, MLII lead, already scaled to 12-bit `adc_raw` |
| `mitbih_100_ann.csv` | Beat annotations in the same window (`symbol`, AAMI class) |

## How the excerpt was made

```text
Source: PhysioNet mitdb/100, first 15 seconds @ 360 Hz, channel MLII
Physical signal range used for mapping: 5th percentile → ADC 400,
                                        99.5th percentile → ADC 3200
adc_raw = clip(round(a * mV + b), 0, 4095)
```

Approximate scale for this excerpt (see generator log when regenerating):

```text
adc ≈ 2196.08 * mV + 1366.27
```

R-peaks in the scaled signal exceed the RTL `R_PEAK_THRESHOLD` of **2200**.

## Sample-rate note

MIT-BIH is **360 Hz**. The SNN segmenter parameters are expressed for **500 Hz**
(`EVAL_WINDOW_MS` / `REFRACTORY_MS`). The cocotb stream test treats each CSV row as
one `sample_en` pulse, so evaluation windows are correct in *samples* but not exact
wall-clock milliseconds. That is intentional for this demo.

## Regenerating

From `test/` with the project venv:

```sh
pip install wfdb numpy
python3 scripts/gen_mitbih_excerpt.py   # if present
```

Or re-run the one-shot download used to create these files via `wfdb.rdrecord("100", pn_dir="mitdb", ...)`.

## License / citation

Please cite PhysioNet / MIT-BIH when redistributing. This repo vendors only a short
excerpt for offline CI; full records remain on PhysioNet.
