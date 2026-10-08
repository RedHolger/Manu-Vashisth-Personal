import unittest
from project import *
def e(i,kind,date,ingest=None):return {'id':i,'user':'u','type':kind,'at':date,'ingested_at':ingest or date}
class Tests(unittest.TestCase):
 def test_censoring(self):
  r=cohorts([e('1','signup','2026-01-01T00:00:00Z')],'2026-01-05T00:00:00Z');self.assertIsNone(next(iter(r['cohorts'].values()))['week1_retention'])
 def test_duplicate_and_late_arrival(self):
  a=e('1','signup','2026-01-01T00:00:00Z');b=e('2','active','2026-01-09T00:00:00Z','2026-02-01T00:00:00Z')
  r=cohorts([a,a,b],'2026-01-20T00:00:00Z');self.assertEqual(next(iter(r['cohorts'].values()))['week1_retention'],0)
 def test_conflict(self):
  a=e('1','signup','2026-01-01T00:00:00Z');b=dict(a,type='active')
  with self.assertRaises(ValueError):cohorts([a,b],'2026-01-20T00:00:00Z')
if __name__=='__main__':unittest.main()
