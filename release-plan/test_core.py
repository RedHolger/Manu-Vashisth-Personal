import unittest
from project import plan
class Tests(unittest.TestCase):
 def t(self,i,dep,h):return {'id':i,'depends':dep,'hours':h,'owner':'me','done':True,'evidence':['fixture']}
 def test_diamond(self):
  r=plan([self.t('a',[],2),self.t('b',['a'],3),self.t('c',['a'],5),self.t('d',['b','c'],1)]);self.assertEqual(r['critical_path'],['a','c','d']);self.assertEqual(r['estimated_hours'],8)
 def test_cycle(self):
  with self.assertRaises(ValueError):plan([self.t('a',['b'],1),self.t('b',['a'],1)])
 def test_not_ready_without_evidence(self):
  t=self.t('a',[],1);t['evidence']=[];self.assertFalse(plan([t])['ready']['a'])
if __name__=='__main__':unittest.main()
