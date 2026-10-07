// AccelScope sequential 4x4 matrix-vector accelerator.
//
// Input values: signed 8-bit integers.
// Products: signed 16-bit integers.
// Accumulators and outputs: signed 18-bit integers.
//
// Packing:
//   weights[8*(4*row + column) +: 8] = W[row][column]
//   x_vec[8*column +: 8]           = x[column]
//   y[18*row +: 18]                 = output[row]
//
// Protocol:
//   rst is an active-high synchronous reset.
//   start is accepted only when busy is low.
//   Inputs are captured on the accepted start edge.
//   Processing begins on the following clock edge.
//   done pulses for one cycle with all outputs valid.
//   Outputs remain available until reset or the next accepted start.

module accelscope_seq (
    input  wire         clk,
    input  wire         rst,
    input  wire         start,
    input  wire [127:0] weights,
    input  wire [31:0]  x_vec,

    output reg          busy,
    output reg          done,
    output reg  [71:0]  y
);

    reg [127:0] weights_reg;
    reg [31:0]  vector_reg;

    reg [1:0] row_index;
    reg [1:0] column_index;

    reg signed [17:0] accumulator;

    wire [3:0] weight_index;

    wire signed [7:0]  weight_value;
    wire signed [7:0]  vector_value;
    wire signed [15:0] product;
    wire signed [17:0] extended_product;
    wire signed [17:0] next_sum;

    // Concatenating the two indices gives 4*row + column.
    assign weight_index = {row_index, column_index};

    // Select the current signed input values.
    assign weight_value =
        $signed(weights_reg[weight_index * 8 +: 8]);

    assign vector_value =
        $signed(vector_reg[column_index * 8 +: 8]);

    // One multiplier, reused throughout the calculation.
    assign product = weight_value * vector_value;

    // Preserve the product's sign when widening from 16 to 18 bits.
    assign extended_product = {{2{product[15]}}, product};

    // One accumulator adder, also reused.
    assign next_sum = accumulator + extended_product;

    always @(posedge clk) begin
        if (rst) begin
            weights_reg <= 128'd0;
            vector_reg  <= 32'd0;
            row_index   <= 2'd0;
            column_index <= 2'd0;
            accumulator <= 18'sd0;
            busy <= 1'b0;
            done <= 1'b0;
            y <= 72'd0;
        end else begin
            // Completion is a one-cycle pulse.
            done <= 1'b0;

            if (!busy) begin
                if (start) begin
                    weights_reg <= weights;
                    vector_reg  <= x_vec;

                    row_index    <= 2'd0;
                    column_index <= 2'd0;
                    accumulator  <= 18'sd0;

                    y <= 72'd0;
                    busy <= 1'b1;
                end
            end else begin
                if (column_index == 2'd3) begin
                    // Include the fourth product in the stored result.
                    case (row_index)
                        2'd0: y[17:0]  <= next_sum;
                        2'd1: y[35:18] <= next_sum;
                        2'd2: y[53:36] <= next_sum;
                        2'd3: y[71:54] <= next_sum;
                    endcase

                    accumulator  <= 18'sd0;
                    column_index <= 2'd0;

                    if (row_index == 2'd3) begin
                        busy <= 1'b0;
                        done <= 1'b1;
                    end else begin
                        row_index <= row_index + 2'd1;
                    end
                end else begin
                    accumulator <= next_sum;
                    column_index <= column_index + 2'd1;
                end
            end
        end
    end

endmodule
