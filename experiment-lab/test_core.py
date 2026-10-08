import unittest
from project import *
class Tests(unittest.TestCase):
 def test_constant_null(self):
  r=[{'user':str(i),'arm':'A' if i<5 else 'B','outcome':1} for i in range(10)];a=analyze(r,permutations=99);self.assertEqual(a['effect_B_minus_A'],0);self.assertEqual(a['randomization_p'],1)
 def test_duplicate_rejected(self):
  r=simulate();r[1]['user']=r[0]['user']
  with self.assertRaises(ValueError):analyze(r)
 def test_seed_reproducible(self):self.assertEqual(analyze(simulate(),permutations=99),analyze(simulate(),permutations=99))
 def test_missing_arm(self):
  r=simulate();[x.update(arm='A') for x in r]
  with self.assertRaises(ValueError):analyze(r)
if __name__=='__main__':unittest.main()
