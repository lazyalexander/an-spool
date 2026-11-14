#!/usr/bin/env python3
"""Assemble both native acceptance releases using Loom; never execute a workload."""
import argparse
import json
from pathlib import Path
import subprocess


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--loom',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parent
    output=args.output.resolve();output.mkdir(mode=0o700)
    for name in ('markdown','workbook'):
        source=output/(name+'-source');(source/'silk').mkdir(parents=True)
        (source/'tests').mkdir()
        (source/'tests/test_document.py').write_bytes((root/'tests/test_document.py').read_bytes())
        (source/'silk/document.py').write_bytes((root/'silk/document.py').read_bytes())
        (source/'silk/main.py').write_bytes((root/'acceptance'/ (name+'.py')).read_bytes())
        (source/'loom.toml').write_text('schema_version = 1\nname = "documents-'+name+'"\nversion = "0.2.0"\ndescription = "Source-bound document acceptance"\ninclude = ["loom.toml", "native-spool.toml", "silk", "tests"]\n')
        dependencies=['pypdf-7.1.0'] if name=='markdown' else []
        result='markdown.md' if name=='markdown' else 'result.xlsx'
        (source/'native-spool.toml').write_text('schema = "an-native-spool-v1"\nruntime = "macos-native-python-v1"\nentry = "silk/main.py"\nsilk = ["silk/main.py", "silk/document.py"]\nkit = []\neditable = []\ninputs = ["proposal"]\noutputs = '+json.dumps([result,'verification.json'])+'\nbinary_outputs = '+json.dumps([] if name=='markdown' else [result])+'\ncapabilities = ["read-input", "write-declared-outputs"]\ndependencies = '+json.dumps(dependencies)+'\nacceptance = ["python3 -B -m unittest discover -s tests -v"]\n\n[events]\nconsumes = []\nproduces = ["artifact.accepted"]\n')
        packed=json.loads(subprocess.check_output([str(args.loom.resolve()),'pack',str(source)],text=True))
        subprocess.run([str(args.loom.resolve()),'verify',packed['archive']],check=True,stdout=subprocess.DEVNULL)
        subprocess.run([str(args.loom.resolve()),'export-native-spool-v3',packed['archive'],str(output/name)],check=True,stdout=subprocess.DEVNULL)
    print(json.dumps({'markdown':str(output/'markdown'),'workbook':str(output/'workbook'),'execution_authorized':False}))


if __name__=='__main__':main()
