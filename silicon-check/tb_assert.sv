// Invariant assertions for the FIFO (P21-03). Replays `trace.txt` and
// $fatal on the first violated structural invariant; prints PASS_ASSERTIONS
// on a clean run. White-box probe `dut.count` targets the DEPTH=4 config.
//
// Checked every cycle (after the edge settles):
//   A1  full  == (count == 4)          A2  empty == (count == 0)
//   A3  0 <= count <= 4                A4  wa == (wr_en && !full_pre)
//   A5  ra == (rd_en && !empty_pre)    A6  data_out == expected queue head
// A6 is a testbench scoreboard (expected FIFO queue); it catches
// data-integrity fallout that self-consistent flags cannot see.
module tb_assert;
 localparam DEPTH=4;
 logic clk=0, reset=0, wr_en=0, rd_en=0;
 logic [7:0] data_in=0, data_out;
 logic full, empty, wa, ra;
 logic full_pre, empty_pre;
 logic [7:0] queue[$];
 logic [7:0] expected;
 integer trace_fd, cycle;
 integer wr, rd, data, rst;
 fifo dut(clk,reset,wr_en,rd_en,data_in,data_out,full,empty,wa,ra);
 always #5 clk=~clk;
 initial begin
  trace_fd=$fopen("trace.txt","r");
  if(!trace_fd)$fatal(1,"no trace.txt");
  reset=1;@(negedge clk);reset=0;
  cycle=0;
  while(!$feof(trace_fd)) begin
   if($fscanf(trace_fd,"%d %d %d %d",wr,rd,data,rst)!=4) break;
   wr_en=wr;rd_en=rd;data_in=data[7:0];reset=rst;
   full_pre=full;empty_pre=empty;
   @(posedge clk);@(negedge clk);
   if(full!==(dut.count==DEPTH))$fatal(1,"A1 full/count at cycle %0d",cycle);
   if(empty!==(dut.count==0))$fatal(1,"A2 empty/count at cycle %0d",cycle);
   if(!(dut.count>=0&&dut.count<=DEPTH))$fatal(1,"A3 count bounds %0d at %0d",dut.count,cycle);
   if(wa!==(wr_en&&!full_pre))$fatal(1,"A4 wr_accept at cycle %0d",cycle);
   if(ra!==(rd_en&&!empty_pre))$fatal(1,"A5 rd_accept at cycle %0d",cycle);
   if(rst) queue.delete();
   else begin
    if(wr_en&&!full_pre) queue.push_back(data_in);
    if(rd_en&&!empty_pre) begin
     expected=queue.pop_front();
     if(data_out!==expected)$fatal(1,"A6 data order at cycle %0d",cycle);
    end
   end
   cycle=cycle+1;
  end
  $fclose(trace_fd);
  $display("PASS_ASSERTIONS cycles=%0d",cycle);
  $finish;
 end
endmodule
