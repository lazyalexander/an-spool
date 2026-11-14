import contextlib
import json
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch
from test_document import body,MARKDOWN,ROWS,pdf_bytes

ROOT=Path(__file__).resolve().parents[1]

@contextlib.contextmanager
def workspace(root,environment):
    previous=Path.cwd()
    try:
        os.chdir(root)
        with patch.dict(os.environ,environment,clear=True):yield
    finally:os.chdir(previous)


class NativeAcceptance(unittest.TestCase):
    def test_markdown_rechecks_source_and_separately_supplied_answers(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source.pdf';source.write_bytes(pdf_bytes('Currency not specified','?'))
            proposal=root/'proposal.md';proposal.write_text(MARKDOWN)
            answers=root/'answers.json';answers.write_text(json.dumps({'currency':'EUR','quantity:0':12}))
            with workspace(root,{'AN_SPOOL_INPUT':str(proposal),'AN_SPOOL_AUX_0':str(source),'AN_SPOOL_AUX_1':str(answers)}):
                runpy.run_path(str(ROOT/'acceptance/markdown.py'))
            self.assertEqual((root/'markdown.md').read_text(),MARKDOWN)
            self.assertTrue(json.loads((root/'verification.json').read_text())['passed'])
    def test_changed_markdown_never_produces_an_accepted_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source.pdf';source.write_bytes(pdf_bytes())
            proposal=root/'proposal.md';proposal.write_text(MARKDOWN.replace('12','13'))
            answers=root/'answers.json';answers.write_text('{}')
            with workspace(root,{'AN_SPOOL_INPUT':str(proposal),'AN_SPOOL_AUX_0':str(source),'AN_SPOOL_AUX_1':str(answers)}):
                with self.assertRaises(ValueError):runpy.run_path(str(ROOT/'acceptance/markdown.py'))
            self.assertFalse((root/'verification.json').exists())
    def test_workbook_is_verified_against_accepted_markdown(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);markdown=root/'accepted.md';markdown.write_text(MARKDOWN)
            candidate=root/'candidate.xlsx';body.write_workbook(MARKDOWN,{'source_sha256':body.digest(MARKDOWN.encode()),'rows':ROWS},candidate)
            with workspace(root,{'AN_SPOOL_INPUT':str(candidate),'AN_SPOOL_AUX_0':str(markdown)}):
                runpy.run_path(str(ROOT/'acceptance/workbook.py'))
            self.assertEqual((root/'result.xlsx').read_bytes(),candidate.read_bytes())
            self.assertEqual(json.loads((root/'verification.json').read_text())['total_eur'],'38.50')
