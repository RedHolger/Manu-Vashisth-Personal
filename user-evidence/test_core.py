import unittest
from project import summarize
class Tests(unittest.TestCase):
 def row(self):return {'participant':'p1','task':'t1','success':True,'seconds':10,'observation':'fixture','codes':['a'],'synthetic':True}
 def test_summary(self):self.assertEqual(summarize([self.row()])['tasks']['t1']['completed'],1)
 def test_duplicate(self):
  with self.assertRaises(ValueError):summarize([self.row(),self.row()])
if __name__=='__main__':unittest.main()
