"""Verify workbook content against the original accepted Markdown snapshot."""
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent))
import document

markdown=document.read(os.environ['AN_SPOOL_AUX_0'],65536).decode('utf-8')
candidate=Path(os.environ['AN_SPOOL_INPUT'])
report=document.verify_workbook(markdown,candidate)
with Path('result.xlsx').open('xb') as output:output.write(document.read(candidate))
with Path('verification.json').open('x') as output:json.dump(report,output,sort_keys=True)
