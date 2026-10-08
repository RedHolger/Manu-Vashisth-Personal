import unittest
from project import *
class Tests(unittest.TestCase):
 def rows(self):return [{'id':str(i),'at':f'2026-01-01T00:00:0{i}Z','user':'u','ip':'192.0.2.1','kind':'failure' if i<3 else 'success'} for i in range(4)]
 def test_order_independent(self):self.assertEqual(analyze(self.rows())['findings'],analyze(self.rows()[::-1])['findings'])
 def test_benign_short_retry(self):self.assertEqual(analyze(self.rows()[2:])['findings'],[])
 def test_dedup(self):self.assertEqual(len(analyze(self.rows()+self.rows())['findings']),1)
if __name__=='__main__':unittest.main()
