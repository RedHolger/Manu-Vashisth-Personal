module fifo #(parameter DEPTH=4, parameter WIDTH=8)(
// SEEDED DEFECT (P21-03): simultaneous read+write miscounts. Correct line is
//   2'b11 implicit in default (hold). This variant adds +1, so back-to-back
//   simultaneous cycles inflate `count` toward a false full.
 input logic clk, reset, wr_en, rd_en,
 input logic [WIDTH-1:0] data_in,
 output logic [WIDTH-1:0] data_out,
 output logic full, empty,
 output logic wr_accepted, rd_accepted);
 localparam PTR_W = (DEPTH < 2) ? 1 : $clog2(DEPTH);
 logic [WIDTH-1:0] mem[0:DEPTH-1];
 logic [PTR_W-1:0] head, tail;
 integer count;
 assign full=(count==DEPTH);
 assign empty=(count==0);
 always_ff @(posedge clk) begin
  if (reset) begin head<=0;tail<=0;count<=0;data_out<=0;wr_accepted<=0;rd_accepted<=0;end
  else begin
   wr_accepted<=wr_en&&!full;rd_accepted<=rd_en&&!empty;
   if(wr_en&&!full) begin mem[tail]<=data_in;tail<=(tail==DEPTH-1)?0:tail+1;end
   if(rd_en&&!empty) begin data_out<=mem[head];head<=(head==DEPTH-1)?0:head+1;end
   case ({(wr_en&&!full),(rd_en&&!empty)})
    2'b10:count<=count+1;
    2'b01:count<=count-1;
    2'b11:count<=count+1; // SEEDED DEFECT: must hold, not +1
    default:count<=count;
   endcase
  end
 end
endmodule
