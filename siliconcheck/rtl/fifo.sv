// Parameterized synchronous FIFO with occupancy counter.
// DEPTH must be a power of 2; synchronous read (dout updates after rd_en).
module fifo #(
    parameter int DATA_WIDTH = 32,
    parameter int DEPTH = 16
) (
    input  logic                   clk,
    input  logic                   rst_n,
    input  logic                   wr_en,
    input  logic                   rd_en,
    input  logic [DATA_WIDTH-1:0]  din,
    output logic [DATA_WIDTH-1:0]  dout,
    output logic                   full,
    output logic                   empty,
    output logic [$clog2(DEPTH):0] count
);
    localparam int AW = $clog2(DEPTH);
    logic [DATA_WIDTH-1:0] mem [0:DEPTH-1];
    logic [AW-1:0] wptr, rptr;
    logic [AW:0]   occ;

    assign full  = (occ == DEPTH);
    assign empty = (occ == 0);
    assign count = occ;

    wire do_write = wr_en && !full;
    wire do_read  = rd_en && !empty;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wptr <= '0;
            rptr <= '0;
            occ  <= '0;
            dout <= '0;
        end else begin
            if (do_write) begin
                mem[wptr] <= din;
                wptr <= (wptr == DEPTH-1) ? '0 : wptr + 1'b1;
            end
            if (do_read) begin
                dout <= mem[rptr];
                rptr <= (rptr == DEPTH-1) ? '0 : rptr + 1'b1;
            end
            case ({do_write, do_read})
                2'b10:   occ <= occ + 1'b1;
                2'b01:   occ <= occ - 1'b1;
                default: occ <= occ;
            endcase
        end
    end

    // Assertion: occupancy conservation. Out-of-window wr/rd are IGNORED by
    // design (do_write/do_read gating) and covered by the cocotb
    // overflow/underflow tests — so no $error on wr_en&&full here.
    // synopsys translate_off
    always @(posedge clk) begin
        if (rst_n) begin
            assert (occ <= DEPTH) else $error("occupancy overflow");
        end
    end
    // synopsys translate_on
endmodule
