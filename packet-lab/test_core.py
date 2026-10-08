import unittest
from project import *
class Tests(unittest.TestCase):
 def test_missing_unknown(self):self.assertTrue(all(x['status']=='UNKNOWN' for x in diagnose({})))
 def test_byte_aggregation(self):
  r={'src':'192.0.2.1','dst':'192.0.2.2','protocol':'TCP','bytes':40};self.assertEqual(flows([r,r])[0]['bytes'],80)
 def test_invalid_address(self):
  with self.assertRaises(ValueError):flows([{'src':'bad','dst':'192.0.2.1','protocol':'TCP','bytes':1}])
if __name__=='__main__':unittest.main()
