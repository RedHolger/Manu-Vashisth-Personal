// Directed RTL FIFO test with VCD waveform (P21-01).
//
// Same stimulus as the kit `tb.sv` (fill to full, overflow refused, drain in
// order, underflow refused) plus `$dumpfile`/`$dumpvars` so the waveform is
// recorded. The kit `tb.sv` itself is never modified.
module tb_wave;
 logic clk=0,reset=1,wr_en=0,rd_en=0;logic[7:0]data_in=0,data_out;
 logic full,empty,wa,ra;integer i;
 fifo dut(clk,reset,wr_en,rd_en,data_in,data_out,full,empty,wa,ra);
 always #5 clk=~clk;
 initial begin
  $dumpfile("directed.vcd");$dumpvars(0,tb_wave);
  @(negedge clk);reset=0;
  for(i=0;i<4;i=i+1)begin wr_en=1;data_in=i;@(negedge clk);end
  if(!full)$fatal(1,"not full");
  data_in=99;@(negedge clk);if(wa)$fatal(1,"overflow accepted");
  wr_en=0;rd_en=1;
  for(i=0;i<4;i=i+1)begin @(negedge clk);if(!ra||data_out!==i)$fatal(1,"bad FIFO order");end
  if(!empty)$fatal(1,"not empty");
  @(negedge clk);if(ra)$fatal(1,"underflow accepted");
  $display("PASS directed RTL FIFO test");$finish;
 end
endmodule
