import unittest
from project import FIFO
class Tests(unittest.TestCase):
 def test_order_overflow_underflow(self):
  q=FIFO(2);q.step(True,value=1);q.step(True,value=2);self.assertFalse(q.step(True,value=3)['write_accepted']);self.assertEqual(q.step(read=True)['read_value'],1);self.assertEqual(q.step(read=True)['read_value'],2);self.assertFalse(q.step(read=True)['read_accepted'])
 def test_full_simultaneous(self):
  q=FIFO(1);q.step(True,value=1);r=q.step(True,True,2);self.assertFalse(r['write_accepted']);self.assertEqual(r['read_value'],1)
 def test_reset(self):
  q=FIFO();q.step(True,value=4);self.assertEqual(q.step(reset=True)['count'],0)
if __name__=='__main__':unittest.main()
