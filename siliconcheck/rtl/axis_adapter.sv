// AXI-Stream word adapter over fifo: s_ready = ~full, m_valid = ~empty.
// Stream words only; no TLAST/TKEEP framing (out of scope, see SPEC).
module axis_adapter #(
    parameter int DATA_WIDTH = 32,
    parameter int DEPTH = 16
) (
    input  logic                   clk,
    input  logic                   rst_n,
    // slave (ingress)
    input  logic                   s_valid,
    output logic                   s_ready,
    input  logic [DATA_WIDTH-1:0]  s_data,
    // master (egress)
    output logic                   m_valid,
    input  logic                   m_ready,
    output logic [DATA_WIDTH-1:0]  m_data,
    // status
    output logic                   full,
    output logic                   empty,
    output logic [$clog2(DEPTH):0] count
);
    logic wr_en, rd_en;
    logic [DATA_WIDTH-1:0] dout;

    assign s_ready = ~full;
    assign m_valid = ~empty;
    assign m_data  = dout;
    assign wr_en   = s_valid & s_ready;
    assign rd_en   = m_valid & m_ready;

    fifo #(
        .DATA_WIDTH(DATA_WIDTH),
        .DEPTH(DEPTH)
    ) u_fifo (
        .clk(clk), .rst_n(rst_n),
        .wr_en(wr_en), .rd_en(rd_en),
        .din(s_data), .dout(dout),
        .full(full), .empty(empty), .count(count)
    );
endmodule
