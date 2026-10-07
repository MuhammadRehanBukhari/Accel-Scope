// AccelScope parallel 4x4 matrix-vector accelerator.
//
// Four rows are processed simultaneously.
// Each row has one signed multiplier and one 18-bit accumulator.
//
// Packing and control protocol match accelscope_seq.
// All four outputs become valid together on completion.

module accelscope_parallel (
    input  wire         clk,
    input  wire         rst,
    input  wire         start,
    input  wire [127:0] weights,
    input  wire [31:0]  x_vec,

    output reg          busy,
    output reg          done,
    output wire [71:0]  y
);

    reg [127:0] weights_reg;
    reg [31:0] vector_reg;
    reg [1:0] column_index;

    wire signed [7:0] vector_value;

    assign vector_value =
        $signed(vector_reg[column_index * 8 +: 8]);

    // Shared controller and captured inputs.
    always @(posedge clk) begin
        if (rst) begin
            weights_reg <= 128'd0;
            vector_reg <= 32'd0;
            column_index <= 2'd0;
            busy <= 1'b0;
            done <= 1'b0;
        end else begin
            done <= 1'b0;

            if (!busy) begin
                if (start) begin
                    weights_reg <= weights;
                    vector_reg <= x_vec;
                    column_index <= 2'd0;
                    busy <= 1'b1;
                end
            end else begin
                if (column_index == 2'd3) begin
                    column_index <= 2'd0;
                    busy <= 1'b0;
                    done <= 1'b1;
                end else begin
                    column_index <= column_index + 2'd1;
                end
            end
        end
    end

    // Generate four separate calculation units.
    genvar row;
    generate
        for (row = 0; row < 4; row = row + 1) begin : row_units
            localparam [1:0] ROW_ID = row;

            wire [3:0] weight_index;
            wire signed [7:0] weight_value;
            wire signed [15:0] product;
            wire signed [17:0] extended_product;
            wire signed [17:0] next_sum;

            reg signed [17:0] accumulator;
            reg signed [17:0] result;

            assign weight_index = {ROW_ID, column_index};

            assign weight_value =
                $signed(weights_reg[weight_index * 8 +: 8]);

            assign product = weight_value * vector_value;
            assign extended_product = {{2{product[15]}}, product};
            assign next_sum = accumulator + extended_product;

            assign y[row * 18 +: 18] = result;

            always @(posedge clk) begin
                if (rst) begin
                    accumulator <= 18'sd0;
                    result <= 18'sd0;
                end else if (!busy && start) begin
                    accumulator <= 18'sd0;
                    result <= 18'sd0;
                end else if (busy) begin
                    if (column_index == 2'd3) begin
                        result <= next_sum;
                        accumulator <= 18'sd0;
                    end else begin
                        accumulator <= next_sum;
                    end
                end
            end
        end
    endgenerate

endmodule
