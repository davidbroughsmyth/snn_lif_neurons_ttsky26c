# SPDX-FileCopyrightText: © 2025 davidbroughsmyth
# SPDX-License-Identifier: Apache-2.0

"""Stream a vendored MIT-BIH ECG CSV excerpt into the TT-wrapped SNN core."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

import cocotb
from cocotb.triggers import RisingEdge

from test import pulse_sample, reset_dut

DATA_DIR = Path(__file__).resolve().parent / "data"
ECG_CSV = DATA_DIR / "mitbih_100_excerpt.csv"
ANN_CSV = DATA_DIR / "mitbih_100_ann.csv"

# Segmenter eval window is 100 samples after R-peak; valid is observed near peak+100.
EVAL_LAG = 100
ANN_MATCH_RADIUS = 80
MIN_BEATS = 5


def load_ecg_csv(path: Path) -> list[int]:
    samples: list[int] = []
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            samples.append(int(row["adc_raw"]) & 0xFFF)
    return samples


def load_ann_csv(path: Path) -> list[tuple[int, str, int]]:
    anns: list[tuple[int, str, int]] = []
    if not path.exists():
        return anns
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            anns.append((int(row["sample_index"]), row["symbol"], int(row["aami_class"])))
    return anns


def nearest_annotation(peak_idx: int, anns: list[tuple[int, str, int]]):
    best = None
    best_dist = None
    for sample, sym, aami in anns:
        dist = abs(sample - peak_idx)
        if dist <= ANN_MATCH_RADIUS and (best_dist is None or dist < best_dist):
            best = (sample, sym, aami)
            best_dist = dist
    return best


@cocotb.test()
async def test_mitbih_csv_stream(dut):
    """Stream MIT-BIH record-100 excerpt; require R-peak detections (smoke)."""
    assert ECG_CSV.exists(), f"missing {ECG_CSV}"
    samples = load_ecg_csv(ECG_CSV)
    anns = load_ann_csv(ANN_CSV)
    assert len(samples) > 1000, "excerpt too short"

    await reset_dut(dut)

    detections: list[dict] = []
    for idx, adc in enumerate(samples):
        cap = await pulse_sample(dut, adc, idle_cycles=3)
        if cap is not None:
            # Valid fires ~EVAL_LAG samples after the R-peak that opened the window.
            peak_idx = max(idx - EVAL_LAG, 0)
            det = {
                "stream_idx": idx,
                "peak_idx": peak_idx,
                "class": cap["class"],
                "alarm": cap["alarm"],
            }
            match = nearest_annotation(peak_idx, anns)
            if match is not None:
                det["ann_sample"] = match[0]
                det["ann_symbol"] = match[1]
                det["ann_aami"] = match[2]
                det["agree"] = int(match[2] == cap["class"])
            detections.append(det)
            dut._log.info(
                "beat#%d stream=%d peak~%d class=%d alarm=%d ann=%s",
                len(detections),
                idx,
                peak_idx,
                cap["class"],
                cap["alarm"],
                match,
            )

    hist = Counter(d["class"] for d in detections)
    dut._log.info("MIT-BIH detections=%d histogram=%s", len(detections), dict(sorted(hist.items())))

    matched = [d for d in detections if "agree" in d]
    if matched:
        agrees = sum(d["agree"] for d in matched)
        pct = 100.0 * agrees / len(matched)
        dut._log.info(
            "annotation agreement (informational): %d/%d = %.1f%%",
            agrees,
            len(matched),
            pct,
        )
    else:
        dut._log.info("no annotation matches within ±%d samples", ANN_MATCH_RADIUS)

    assert len(detections) >= MIN_BEATS, (
        f"expected at least {MIN_BEATS} diag_valid beats, got {len(detections)}"
    )
