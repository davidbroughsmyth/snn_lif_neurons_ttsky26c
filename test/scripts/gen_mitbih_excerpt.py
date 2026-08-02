#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2025 davidbroughsmyth
# SPDX-License-Identifier: Apache-2.0
"""Regenerate MIT-BIH record-100 CSV excerpt for cocotb streaming tests."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import wfdb

SECONDS = 15
FS = 360
OUT_DIR = Path(__file__).resolve().parent.parent / "data"


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    sampto = FS * SECONDS
    rec = wfdb.rdrecord("100", pn_dir="mitdb", sampto=sampto)
    ann = wfdb.rdann("100", "atr", pn_dir="mitdb", sampto=sampto)

    sig = rec.p_signal[:, 0].astype(float)
    lo = np.percentile(sig, 5)
    hi = np.percentile(sig, 99.5)
    a = (3200 - 400) / max(hi - lo, 1e-6)
    b = 400 - a * lo
    adc = np.clip(np.rint(a * sig + b), 0, 4095).astype(int)

    csv_path = OUT_DIR / "mitbih_100_excerpt.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sample_index", "adc_raw"])
        for i, v in enumerate(adc):
            w.writerow([i, int(v)])

    beat_map = {
        "N": 0, "L": 0, "R": 0, "e": 0, "j": 0,
        "A": 1, "a": 1, "J": 1, "S": 1,
        "V": 2, "E": 2,
        "F": 3,
        "/": 4, "f": 4, "Q": 4,
    }
    ann_path = OUT_DIR / "mitbih_100_ann.csv"
    with ann_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sample_index", "symbol", "aami_class"])
        for sample, sym in zip(ann.sample, ann.symbol):
            if sample >= len(adc):
                continue
            if sym in beat_map:
                w.writerow([int(sample), sym, beat_map[sym]])

    print(f"adc = {a:.6f} * mV + {b:.6f}")
    print(f"wrote {csv_path} ({len(adc)} samples), peaks>=2200: {(adc >= 2200).sum()}")
    print(f"wrote {ann_path}")


if __name__ == "__main__":
    main()
