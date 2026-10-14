"""Bibliography regeneration must preserve compound surnames and suffixes."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReferenceGenerationTests(unittest.TestCase):
    def test_generated_bibliography_preserves_parsed_names(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            references = project / 'artifact' / 'references'
            references.mkdir(parents=True)
            (project / 'paper').mkdir()
            for name in ('build_references.py', 'resolved-references.json'):
                shutil.copy2(ROOT / 'references' / name, references / name)
            result = subprocess.run([sys.executable, '-B', str(references / 'build_references.py')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            generated = (references / 'references.bib').read_text(encoding='utf-8')
            self.assertEqual(generated, (ROOT / 'references' / 'references.bib').read_text(encoding='utf-8'))
            self.assertEqual(generated, (project / 'paper' / 'references.bib').read_text(encoding='utf-8'))
            self.assertIn('Chue Hong, Neil P.', generated)
            self.assertIn('Ford, Jr., L. R.', generated)
            self.assertNotIn('and Neil P. Chue Hong and', generated)


if __name__ == '__main__':
    unittest.main()
