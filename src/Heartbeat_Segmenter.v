/*
 * Copyright (c) 2025 davidbroughsmyth
 * SPDX-License-Identifier: Apache-2.0
 *
 * Heartbeat_Segmenter.v - Window controller state machine
 */

`default_nettype none

module Heartbeat_Segmenter #(
    parameter DATA_WIDTH       = 12,
    parameter R_PEAK_THRESHOLD = 12'd2200,
    parameter SAMPLE_RATE_HZ   = 500,
    parameter EVAL_WINDOW_MS   = 200,
    parameter REFRACTORY_MS    = 300
)(
    input  wire                  clk,
    input  wire                  rst,
    input  wire                  sample_en,
    input  wire [DATA_WIDTH-1:0] data_in,

    output reg                   window_start,
    output reg                   window_end
);

    localparam EVAL_CYCLES = (SAMPLE_RATE_HZ * EVAL_WINDOW_MS) / 1000;
    localparam REFR_CYCLES = (SAMPLE_RATE_HZ * REFRACTORY_MS) / 1000;

    localparam SEARCH     = 2'b00;
    localparam EVALUATE   = 2'b01;
    localparam REFRACTORY = 2'b10;
    reg [1:0] state;

    reg [15:0] cycle_counter;

    always @(posedge clk) begin
        if (rst) begin
            state         <= SEARCH;
            cycle_counter <= 16'd0;
            window_start  <= 1'b0;
            window_end    <= 1'b0;
        end else if (sample_en) begin
            window_start <= 1'b0;
            window_end   <= 1'b0;

            case (state)
                SEARCH: begin
                    if (data_in >= R_PEAK_THRESHOLD) begin
                        window_start  <= 1'b1;
                        cycle_counter <= 16'd0;
                        state         <= EVALUATE;
                    end
                end

                EVALUATE: begin
                    if (cycle_counter >= (EVAL_CYCLES - 1)) begin
                        window_end    <= 1'b1;
                        cycle_counter <= 16'd0;
                        state         <= REFRACTORY;
                    end else begin
                        cycle_counter <= cycle_counter + 1'b1;
                    end
                end

                REFRACTORY: begin
                    if (cycle_counter >= (REFR_CYCLES - EVAL_CYCLES - 1)) begin
                        state <= SEARCH;
                    end else begin
                        cycle_counter <= cycle_counter + 1'b1;
                    end
                end
                default: state <= SEARCH;
            endcase
        end else begin
            window_start <= 1'b0;
            window_end   <= 1'b0;
        end
    end

endmodule
