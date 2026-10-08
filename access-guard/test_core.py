import unittest
from project import *
class Tests(unittest.TestCase):
 def test_fixed_matrix(self):self.assertEqual(evaluate()['mismatches'],0)
 def test_bug_detected(self):self.assertGreater(evaluate(True)['mismatches'],0)
 def test_admin_cannot_cross_tenant(self):self.assertFalse(policy({'id':'a','tenant':'A','role':'admin','active':True},{'owner':'a','tenant':'B'},'read'))
 def test_unknown_action_denied(self):self.assertFalse(policy({'id':'a','tenant':'A','role':'admin','active':True},{'owner':'a','tenant':'A'},'unknown'))
if __name__=='__main__':unittest.main()
