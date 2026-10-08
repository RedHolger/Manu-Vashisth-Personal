import tempfile,unittest
from pathlib import Path
from project import *
class Tests(unittest.TestCase):
 def setUp(self):self.t=tempfile.TemporaryDirectory();self.p=Path(self.t.name)/'db';self.i=Importer(self.p);self.rows=[{'id':str(x),'customer':'a','amount':'1.25'} for x in range(5)]
 def tearDown(self):self.i.close();self.t.cleanup()
 def test_rollback_and_resume(self):
  s=Source(self.rows)
  with self.assertRaises(RuntimeError):self.i.step('a',s,'a',True)
  self.assertIsNone(self.i.report('a')['checkpoint'])
  self.i.step('a',s,'a');self.i.close();self.i=Importer(self.p)
  while self.i.step('a',s,'a'):pass
  self.assertEqual(self.i.report('a')['valid_unique_orders'],5);self.assertFalse(self.i.step('a',s,'a'))
 def test_transient_does_not_advance(self):
  s=Source(self.rows);s.fail_once.add('0')
  with self.assertRaises(TransientError):self.i.step('a',s,'a')
  self.assertIsNone(self.i.report('a')['checkpoint'])
 def test_snapshot_and_missing_page(self):
  s=Source(self.rows);self.i.step('a',s,'a');s.snapshot='changed'
  with self.assertRaises(IntegrityError):self.i.step('a',s,'a')
 def test_duplicate_and_quarantine(self):
  s=Source([self.rows[0],self.rows[0],{'id':'bad'}],3)
  self.i.step('a',s,'a');r=self.i.report('a');self.assertEqual(r['valid_unique_orders'],1);self.assertEqual(len(r['quarantine']),1)
 def test_manifest_mismatch_rolls_back_final_page(self):
  class Corrupt(Source):
   def fetch(self,cursor):
    p=super().fetch(cursor);p['rows']=[dict(r,amount='99.00') for r in p['rows']];return p
  with self.assertRaises(IntegrityError):self.i.step('a',Corrupt(self.rows,5),'a')
  self.assertIsNone(self.i.report('a')['checkpoint'])
 def test_missing_page(self):
  class Skip(Source):
   def fetch(self,cursor):
    p=super().fetch(cursor);p['start']+=2;return p
  with self.assertRaises(IntegrityError):self.i.step('a',Skip(self.rows),'a')
 def test_amount(self):
  for value in ['NaN','Infinity','-1','1.001']:
   with self.assertRaises(ValueError):normalize({'id':'x','customer':'a','amount':value},'a')
if __name__=='__main__':unittest.main()
