import unittest
from project import *
class Tests(unittest.TestCase):
 def test_clearance(self):
  p=parameters();self.assertEqual(p['outer_width']-2*p['wall'],p['width']+2*p['clearance'])
 def test_invalid(self):
  with self.assertRaises(ValueError):parameters(wall=-1)
 def test_generation(self):self.assertIn('difference()',scad(parameters()))
if __name__=='__main__':unittest.main()
