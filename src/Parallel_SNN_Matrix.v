/*
 * Copyright (c) 2025 davidbroughsmyth
 * SPDX-License-Identifier: Apache-2.0
 *
 * Parallel_SNN_Matrix.v - Class-specialized banded rate coding
 * Default NUM_NEURONS=5 (one neuron per AAMI class) for Tiny Tapeout area.
 */

`default_nettype none

module Parallel_SNN_Matrix #(
    parameter NUM_NEURONS = 5,
    parameter BIT_WIDTH   = 16,
    parameter THRESHOLD   = 16'h0800,
    parameter LEAK        = 16'h0000
)(
    input  wire                   clk,
    input  wire                   rst,
    input  wire                   clear,
    input  wire                   tick_en,

    input  wire                   spike_up_gentle,
    input  wire                   spike_down_gentle,
    input  wire                   spike_up_steep,
    input  wire                   spike_down_steep,
    input  wire                   spike_flip,

    output wire [NUM_NEURONS-1:0] out_spikes,
    output wire [(NUM_NEURONS*BIT_WIDTH)-1:0] matrix_v_mem
);

    wire steep_up_cont   = spike_up_steep   & ~spike_flip;
    wire steep_down_cont = spike_down_steep & ~spike_flip;

    wire [BIT_WIDTH-1:0] weights_exc [0:NUM_NEURONS-1];
    wire [BIT_WIDTH-1:0] weights_inh [0:NUM_NEURONS-1];
    wire [BIT_WIDTH-1:0] leak_val    [0:NUM_NEURONS-1];
    wire [NUM_NEURONS-1:0] map_spike_up;
    wire [NUM_NEURONS-1:0] map_spike_down;

    genvar i;
    generate
        for (i = 0; i < NUM_NEURONS; i = i + 1) begin : config_loop

            case (i % 5)
                0: begin
                    assign map_spike_up[i]   = spike_up_gentle;
                    assign map_spike_down[i] = spike_down_gentle | spike_up_steep | spike_down_steep | spike_flip;
                    assign weights_exc[i]    = 16'h0300;
                    assign weights_inh[i]    = 16'h0400;
                    assign leak_val[i]       = 16'h0010;
                end
                1: begin
                    assign map_spike_up[i]   = spike_down_gentle;
                    assign map_spike_down[i] = spike_up_gentle | spike_up_steep | spike_down_steep | spike_flip;
                    assign weights_exc[i]    = 16'h0300;
                    assign weights_inh[i]    = 16'h0400;
                    assign leak_val[i]       = 16'h0010;
                end
                2: begin
                    assign map_spike_up[i]   = steep_up_cont;
                    assign map_spike_down[i] = steep_down_cont | spike_up_gentle | spike_down_gentle | spike_flip;
                    assign weights_exc[i]    = 16'h0600;
                    assign weights_inh[i]    = 16'h0400;
                    assign leak_val[i]       = 16'h0080;
                end
                3: begin
                    assign map_spike_up[i]   = steep_down_cont;
                    assign map_spike_down[i] = steep_up_cont | spike_up_gentle | spike_down_gentle | spike_flip;
                    assign weights_exc[i]    = 16'h0600;
                    assign weights_inh[i]    = 16'h0400;
                    assign leak_val[i]       = 16'h0080;
                end
                4: begin
                    assign map_spike_up[i]   = spike_flip;
                    assign map_spike_down[i] = (spike_up_gentle | spike_down_gentle |
                                               steep_up_cont | steep_down_cont) & ~spike_flip;
                    assign weights_exc[i]    = 16'h0500;
                    assign weights_inh[i]    = 16'h0200;
                    assign leak_val[i]       = 16'h0040;
                end
            endcase

            Heart_Monitor_Neuron #(
                .BIT_WIDTH(BIT_WIDTH), .THRESHOLD(THRESHOLD)
            ) neuron_inst (
                .clk(clk), .rst(rst), .clear(clear), .tick_en(tick_en),
                .spike_up(map_spike_up[i]),
                .spike_down(map_spike_down[i]),
                .w_excitatory(weights_exc[i]),
                .w_inhibitory(weights_inh[i]),
                .leak_in(leak_val[i]),
                .anomaly_alert(out_spikes[i]),
                .v_mem(matrix_v_mem[(i*BIT_WIDTH) +: BIT_WIDTH])
            );
        end
    endgenerate
endmodule
