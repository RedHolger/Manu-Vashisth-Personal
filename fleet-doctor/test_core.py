import unittest
from project import *
class Tests(unittest.TestCase):
 def test_thresholds(self):self.assertEqual(classify_free(100,4),'FAIL');self.assertEqual(classify_free(100,10),'WARN');self.assertEqual(classify_free(100,50),'PASS')
 def test_unknown(self):self.assertEqual(classify_free(0,0),'UNKNOWN');self.assertEqual(command(['/definitely-not-present-program'])['status'],'UNKNOWN')
if __name__=='__main__':unittest.main()
