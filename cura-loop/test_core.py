import unittest,random
from project import *
class Tests(unittest.TestCase):
 def test_equal_budget_unique_ids(self):
  for m in ['random','uncertainty','diversity']:
   h=run(m,budget=12)['history'];self.assertEqual(len({x['selected_id'] for x in h}),12);self.assertEqual(h[-1]['labels_acquired'],12)
 def test_shared_initial_pool(self):self.assertEqual([x['selected_id'] for x in run('random')['history'][:5]],[x['selected_id'] for x in run('uncertainty')['history'][:5]])
 def test_selector_no_label_input(self):self.assertEqual(select([{'id':'a','x':[0,0]}],[],'uncertainty',random.Random(1)),0)
if __name__=='__main__':unittest.main()
