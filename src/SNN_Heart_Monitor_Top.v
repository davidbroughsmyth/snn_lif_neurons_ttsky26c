/*
 * Copyright (c) 2025 davidbroughsmyth
 * SPDX-License-Identifier: Apache-2.0
 *
 * SNN_Heart_Monitor_Top.v - Heart-monitor SNN core (Tiny Tapeout sized)
 */

`default_nettype none

module SNN_Heart_Monitor_Top #(
    parameter DATA_WIDTH        = 12,
    parameter BIT_WIDTH         = 16,
    parameter NUM_NEURONS       = 5,
    parameter R_PEAK_THRESHOLD  = 12'd2200,
    parameter DELTA_THRESHOLD   = 12'd15,
    parameter STEEP_THRESHOLD   = 12'd50,
    parameter SAMPLE_RATE_HZ    = 500,
    parameter EVAL_WINDOW_MS    = 200,
    parameter REFRACTORY_MS     = 300,
    parameter ALARM_PERSIST_MAX = 3,
    parameter WIN_MARGIN        = 16'd8
)(
    input  wire                  clk,
    input  wire                  rst,
    input  wire                  sample_en,
    input  wire [DATA_WIDTH-1:0] adc_data_in,

    output wire [2:0]            heart_class_out,
    output wire                  diagnostic_valid,
    output reg                   alarm_strobe
);

    wire spike_up, spike_down;
    wire spike_up_gentle, spike_down_gentle;
    wire spike_up_steep, spike_down_steep;
    wire spike_flip;
    wire window_start, window_end;
    wire [NUM_NEURONS-1:0] parallel_spikes;
    // wire [(NUM_NEURONS*BIT_WIDTH)-1:0] matrix_v_mem;

    reg neuron_tick;
    always @(posedge clk) begin
        if (rst) neuron_tick <= 1'b0;
        else     neuron_tick <= sample_en;
    end

    Heartbeat_Segmenter #(
        .DATA_WIDTH(DATA_WIDTH), .R_PEAK_THRESHOLD(R_PEAK_THRESHOLD),
        .SAMPLE_RATE_HZ(SAMPLE_RATE_HZ), .EVAL_WINDOW_MS(EVAL_WINDOW_MS),
        .REFRACTORY_MS(REFRACTORY_MS)
    ) segmenter_inst (
        .clk(clk), .rst(rst), .sample_en(sample_en), .data_in(adc_data_in),
        .window_start(window_start), .window_end(window_end)
    );

    Delta_Encoder #(
        .DATA_WIDTH(DATA_WIDTH),
        .DELTA_THRESHOLD(DELTA_THRESHOLD),
        .STEEP_THRESHOLD(STEEP_THRESHOLD)
    ) encoder_inst (
        .clk(clk), .rst(rst), .sample_en(sample_en), .window_start(window_start),
        .data_in(adc_data_in),
        .spike_up(spike_up), .spike_down(spike_down),
        .spike_up_gentle(spike_up_gentle), .spike_down_gentle(spike_down_gentle),
        .spike_up_steep(spike_up_steep), .spike_down_steep(spike_down_steep),
        .spike_flip(spike_flip)
    );

    Parallel_SNN_Matrix #(
        .NUM_NEURONS(NUM_NEURONS), .BIT_WIDTH(BIT_WIDTH),
        .THRESHOLD(16'h0800)
    ) processing_matrix_inst (
        .clk(clk), .rst(rst),
        .clear(window_start),
        .tick_en(neuron_tick),
        .spike_up_gentle(spike_up_gentle),
        .spike_down_gentle(spike_down_gentle),
        .spike_up_steep(spike_up_steep),
        .spike_down_steep(spike_down_steep),
        .spike_flip(spike_flip),
        .out_spikes(parallel_spikes),
        .matrix_v_mem(matrix_v_mem)
    );

    MultiClass_SNN_Voter #(
        .PARALLEL_NEURONS(NUM_NEURONS), .BIT_WIDTH(BIT_WIDTH), .WIN_MARGIN(WIN_MARGIN)
    ) voting_engine_inst (
        .clk(clk), .rst(rst), .window_start(window_start), .window_end(window_end),
        .input_spikes(parallel_spikes), .assigned_class(heart_class_out),
        .valid_out(diagnostic_valid)
    );

    reg [7:0] consecutive_anomaly_counter;
    always @(posedge clk) begin
        if (rst) begin
            consecutive_anomaly_counter <= 8'd0;
            alarm_strobe                <= 1'b0;
        end else if (diagnostic_valid) begin
            if (heart_class_out == 3'd1 || heart_class_out == 3'd2 || heart_class_out == 3'd4) begin
                if (consecutive_anomaly_counter < ALARM_PERSIST_MAX) begin
                    consecutive_anomaly_counter <= consecutive_anomaly_counter + 1'b1;
                end
                if ((consecutive_anomaly_counter + 1'b1) >= ALARM_PERSIST_MAX) begin
                    alarm_strobe <= 1'b1;
                end
            end else begin
                consecutive_anomaly_counter <= 8'd0;
                alarm_strobe                <= 1'b0;
            end
        end
    end

    wire _unused = &{spike_up, spike_down, matrix_v_mem, 1'b0};

endmodule
