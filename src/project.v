/*
 * Copyright (c) 2025 davidbroughsmyth
 * SPDX-License-Identifier: Apache-2.0
 *
 * Tiny Tapeout wrapper for the SNN heart-monitor classifier.
 *
 * Pin map:
 *   ui_in[7:0]     = adc_data_in[7:0]
 *   uio_in[3:0]    = adc_data_in[11:8]
 *   uio_in[4]      = sample_en
 *   uo_out[2:0]    = heart_class_out
 *   uo_out[3]      = diagnostic_valid
 *   uo_out[4]      = alarm_strobe
 */

`default_nettype none

module tt_um_snn_lif_neuron (
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input  wire       ena,
    input  wire       clk,
    input  wire       rst_n
);

    wire        rst = ~rst_n;
    wire        sample_en = uio_in[4];
    wire [11:0] adc_data_in = {uio_in[3:0], ui_in};

    wire [2:0] heart_class_out;
    wire       diagnostic_valid;
    wire       alarm_strobe;

    SNN_Heart_Monitor_Top #(
        .NUM_NEURONS(5),
        .ALARM_PERSIST_MAX(3),
        .WIN_MARGIN(16'd8)
    ) core (
        .clk(clk),
        .rst(rst),
        .sample_en(sample_en),
        .adc_data_in(adc_data_in),
        .heart_class_out(heart_class_out),
        .diagnostic_valid(diagnostic_valid),
        .alarm_strobe(alarm_strobe)
    );

    assign uo_out  = {3'b000, alarm_strobe, diagnostic_valid, heart_class_out};
    assign uio_out = 8'b0;
    assign uio_oe  = 8'b0;

    wire _unused = &{ena, uio_in[7:5], 1'b0};

endmodule
