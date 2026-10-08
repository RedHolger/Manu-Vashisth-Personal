"""P11-04: the threat model keeps its honesty guarantees (and the guard bites)."""
import unittest

import threat_model
from threat_model import audit_threat_model


class ThreatModelTests(unittest.TestCase):
    def test_audit_passes_on_the_real_document(self):
        result = audit_threat_model('THREAT_MODEL.md')
        self.assertTrue(result['all_ok'], result['checks'])
        self.assertGreaterEqual(result['disclaimer_count'], 2)
        self.assertGreaterEqual(result['residual_items'], 3)

    def test_removed_disclaimer_fails(self):
        import tempfile
        from pathlib import Path
        text = Path('THREAT_MODEL.md').read_text(encoding='utf-8')
        stripped = text.replace(threat_model.DISCLAIMER, 'CENSORED')
        with tempfile.NamedTemporaryFile('w', suffix='.md',
                                         delete=False) as handle:
            handle.write(stripped)
            path = handle.name
        try:
            result = audit_threat_model(path)
            self.assertFalse(result['all_ok'])
            self.assertFalse(result['checks']['disclaimer_present_twice'])
        finally:
            Path(path).unlink()

    def test_inserted_universal_claim_fails(self):
        import tempfile
        from pathlib import Path
        text = Path('THREAT_MODEL.md').read_text(encoding='utf-8')
        poisoned = text + '\nOur service is provably secure.\n'
        with tempfile.NamedTemporaryFile('w', suffix='.md',
                                         delete=False) as handle:
            handle.write(poisoned)
            path = handle.name
        try:
            result = audit_threat_model(path)
            self.assertFalse(result['all_ok'])
            self.assertFalse(
                result['checks']['no_universal_security_claim'])
        finally:
            Path(path).unlink()

    def test_removed_section_fails(self):
        import tempfile
        from pathlib import Path
        text = Path('THREAT_MODEL.md').read_text(encoding='utf-8')
        cut = text.replace('## Residual risks', '## Leftovers')
        with tempfile.NamedTemporaryFile('w', suffix='.md',
                                         delete=False) as handle:
            handle.write(cut)
            path = handle.name
        try:
            result = audit_threat_model(path)
            self.assertFalse(result['all_ok'])
            self.assertFalse(result['checks']['required_sections_present'])
        finally:
            Path(path).unlink()


if __name__ == '__main__':
    unittest.main()
