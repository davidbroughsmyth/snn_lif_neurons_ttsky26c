/*
 * Copyright (c) 2025 davidbroughsmyth
 * SPDX-License-Identifier: Apache-2.0
 *
 * Delta_Encoder.v - Banded slope encoder (gentle vs steep) + direction flips
 */

`default_nettype none

module Delta_Encoder #(
    parameter DATA_WIDTH       = 12,
    parameter DELTA_THRESHOLD  = 12'd15,
    parameter STEEP_THRESHOLD  = 12'd50
)(
    input  wire                  clk,
    input  wire                  rst,
    input  wire                  sample_en,
    input  wire                  window_start,
    input  wire [DATA_WIDTH-1:0] data_in,

    output reg                   spike_up,
    output reg                   spike_down,
    output reg                   spike_up_gentle,
    output reg                   spike_down_gentle,
    output reg                   spike_up_steep,
    output reg                   spike_down_steep,
    output reg                   spike_flip
);

    reg [DATA_WIDTH-1:0] prev_data;
    reg                  have_dir;
    reg                  last_dir_down;

    reg                  rising;
    reg                  falling;
    reg [DATA_WIDTH-1:0] abs_delta;
    reg                  is_steep;
    reg                  this_down;
    reg                  is_flip;

    always @(posedge clk) begin
        if (rst) begin
            prev_data          <= {DATA_WIDTH{1'b0}};
            have_dir           <= 1'b0;
            last_dir_down      <= 1'b0;
            spike_up           <= 1'b0;
            spike_down         <= 1'b0;
            spike_up_gentle    <= 1'b0;
            spike_down_gentle  <= 1'b0;
            spike_up_steep     <= 1'b0;
            spike_down_steep   <= 1'b0;
            spike_flip         <= 1'b0;
        end else begin
            spike_up           <= 1'b0;
            spike_down         <= 1'b0;
            spike_up_gentle    <= 1'b0;
            spike_down_gentle  <= 1'b0;
            spike_up_steep     <= 1'b0;
            spike_down_steep   <= 1'b0;
            spike_flip         <= 1'b0;

            if (window_start)
                have_dir <= 1'b0;

            if (sample_en) begin
                rising  = (data_in > prev_data) &&
                          ((data_in - prev_data) >= DELTA_THRESHOLD);
                falling = (data_in < prev_data) &&
                          ((prev_data - data_in) >= DELTA_THRESHOLD);

                if (rising || falling) begin
                    abs_delta = rising ? (data_in - prev_data) : (prev_data - data_in);
                    is_steep  = (abs_delta >= STEEP_THRESHOLD);
                    this_down = falling;
                    is_flip   = (!window_start) && have_dir && (this_down != last_dir_down);

                    spike_up   <= rising;
                    spike_down <= falling;
                    spike_flip <= is_flip;

                    if (is_steep) begin
                        spike_up_steep   <= rising;
                        spike_down_steep <= falling;
                    end else begin
                        spike_up_gentle   <= rising;
                        spike_down_gentle <= falling;
                    end

                    have_dir      <= 1'b1;
                    last_dir_down <= this_down;
                    prev_data     <= data_in;
                end else begin
                    prev_data <= data_in;
                end
            end
        end
    end

endmodule
