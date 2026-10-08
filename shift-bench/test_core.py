import unittest
from project import *
class Tests(unittest.TestCase):
 def test_extreme_logits(self):self.assertAlmostEqual(sum(softmax([1000,-1000])),1)
 def test_group_leakage(self):
  with self.assertRaises(ValueError):validate_splits([{'id':'a','group':'p'}],[],[{'id':'b','group':'p'}])
 def test_temperature_changes_confidence_not_prediction(self):
  r=[{'logits':[3,1],'label':0}];self.assertEqual(metrics(r,1)['accuracy'],metrics(r,5)['accuracy']);self.assertNotEqual(metrics(r,1)['nll'],metrics(r,5)['nll'])
if __name__=='__main__':unittest.main()
