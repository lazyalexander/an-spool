"""Revalidate Markdown against snapshotted source and authorized answers."""
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent))
import document

proposal=document.read(os.environ['AN_SPOOL_INPUT'],65536).decode('utf-8')
source=document.extract_pdf(os.environ['AN_SPOOL_AUX_0'])
answers=json.loads(document.read(os.environ['AN_SPOOL_AUX_1'],65536))
verified=document.validate_markdown(source,proposal,answers)
with Path('markdown.md').open('xb') as output:output.write(verified)
report={'schema':'an-document-verification-v1','passed':True,'pdf_sha256':source['pdf_sha256'],
        'sha256':document.digest(verified),'bytes':len(verified)}
with Path('verification.json').open('x') as output:json.dump(report,output,sort_keys=True)
