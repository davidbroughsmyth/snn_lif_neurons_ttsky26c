# SPDX-FileCopyrightText: © 2025 davidbroughsmyth
# SPDX-License-Identifier: Apache-2.0
"""HIL package for tt_um_snn_lif_neuron — RP2350 emulates ADC; import run()."""

from . import tt_um_snn_lif_neuron as _mod


def run():
    return _mod.main()
