"""Reopening a private image must still revalidate its selected domain inputs."""
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'silk'))
import checkpoint
import document

MD = '| Item | Quantity | Unit price (EUR) |\n| --- | --- | --- |\n| Bolt | 12 | 0.50 |\n'


class Checkpoint(unittest.TestCase):
    def test_roundtrip_rechecks_workbook_and_preserves_original_on_replay(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            md, book, project = root / 'input.md', root / 'input.xlsx', root / 'project'
            md.write_text(MD)
            document.write_workbook(MD, {'source_sha256': document.digest(MD.encode()), 'rows': document.parse_markdown(MD)}, book)
            saved = checkpoint.save(md, book, project)
            self.assertTrue(saved['passed'])
            self.assertEqual(checkpoint.verify(project), saved)
            restored = checkpoint.resume(project, saved['markdown_sha256'], saved['workbook_sha256'])
            self.assertTrue(restored['selected_inputs_match'])
            self.assertTrue(restored['host_acceptance_required'])
            for expected_md, expected_book in [('0' * 64, saved['workbook_sha256']), (saved['markdown_sha256'], '0' * 64), ('invalid', saved['workbook_sha256'])]:
                with self.assertRaises(ValueError):
                    checkpoint.resume(project, expected_md, expected_book)
            with self.assertRaises(FileExistsError):
                checkpoint.save(md, book, project)
            (project / 'markdown.md').write_text(MD.replace('12', '13'))
            with self.assertRaises(ValueError):
                checkpoint.verify(project)
            self.assertEqual(md.read_text(), MD)

    def test_extra_files_and_links_are_not_domain_state(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'unlisted').write_text('private unrelated material')
            with self.assertRaises(ValueError):
                checkpoint.verify(root)


if __name__ == '__main__':
    unittest.main()
