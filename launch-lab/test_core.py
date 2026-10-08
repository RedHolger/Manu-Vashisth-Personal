import unittest
from project import *
class Tests(unittest.TestCase):
 def test_empty_unknown(self):self.assertIsNone(funnel([])['activation_per_visitor'])
 def test_test_accounts_excluded(self):self.assertEqual(funnel([{'id':'1','user':'test','type':'visit','test_account':True}])['visitors'],0)
 def test_missing_evidence(self):
  with self.assertRaises(ValueError):prioritize([{'id':'x','evidence':['missing']}],set())
if __name__=='__main__':unittest.main()
