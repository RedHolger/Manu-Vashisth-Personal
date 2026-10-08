// Trace-driven differential testbench (P21-02). Reads stimulus, logs results.
//
// `trace.txt`: one `wr rd data reset` decimal tuple per line (data 0-255).
// `result.log`: one `cycle wa ra data_out full empty` tuple per line.
// A one-cycle reset pulse aligns the DUT before the trace; the Python model
// starts empty, so both sides agree before cycle 0. `trace.vcd` records the
// wave for the run.
module tb_diff;
 logic clk=0, reset=0, wr_en=0, rd_en=0;
 logic [7:0] data_in=0, data_out;
 logic full, empty, wa, ra;
 integer trace_fd, result_fd, cycle;
 integer wr, rd, data, rst;
 fifo dut(clk,reset,wr_en,rd_en,data_in,data_out,full,empty,wa,ra);
 always #5 clk=~clk;
 initial begin
  $dumpfile("trace.vcd");$dumpvars(0,tb_diff);
  trace_fd=$fopen("trace.txt","r");
  result_fd=$fopen("result.log","w");
  if(!trace_fd)$fatal(1,"no trace.txt");
  if(!result_fd)$fatal(1,"cannot open result.log");
  reset=1;@(negedge clk);reset=0;
  cycle=0;
  while(!$feof(trace_fd)) begin
   if($fscanf(trace_fd,"%d %d %d %d",wr,rd,data,rst)!=4) break;
   wr_en=wr;rd_en=rd;data_in=data[7:0];reset=rst;
   @(posedge clk);@(negedge clk);
   $fdisplay(result_fd,"%0d %0d %0d %0d %0d %0d",cycle,wa,ra,data_out,full,empty);
   cycle=cycle+1;
  end
  $fclose(trace_fd);$fclose(result_fd);
  $display("DIFF cycles=%0d",cycle);
  $finish;
 end
endmodule
