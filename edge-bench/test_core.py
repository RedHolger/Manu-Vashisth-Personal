import unittest
from project import *
class Tests(unittest.TestCase):
 def test_flat(self):self.assertEqual(edges([[5]*4 for _ in range(4)]),[[0,0],[0,0]])
 def test_vertical_edge(self):self.assertGreater(edges([[0,0,255]]*3)[0][0],0)
 def test_invalid(self):
  with self.assertRaises(ValueError):edges([[1]])
if __name__=='__main__':unittest.main()
