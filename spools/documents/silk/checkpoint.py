"""Portable private document state; publication and execution authority stay in the host."""
import hashlib
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import document


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(directory):
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('checkpoint must be a regular directory')
    expected = {'checkpoint.json', 'markdown.md', 'result.xlsx'}
    if {path.name for path in directory.iterdir()} != expected:
        raise ValueError('unexpected checkpoint files')
    for name in expected:
        if (directory / name).is_symlink() or not (directory / name).is_file():
            raise ValueError('checkpoint links are refused')
    manifest = json.loads(document.read(directory / 'checkpoint.json', 4096))
    if set(manifest) != {'schema', 'markdown_sha256', 'workbook_sha256'} or manifest['schema'] != 'an-document-project-v1':
        raise ValueError('unsupported document checkpoint')
    markdown = document.read(directory / 'markdown.md', 65536)
    workbook = document.read(directory / 'result.xlsx')
    if sha(markdown) != manifest['markdown_sha256'] or sha(workbook) != manifest['workbook_sha256']:
        raise ValueError('checkpoint input identity changed')
    report = document.verify_workbook(markdown.decode('utf-8'), directory / 'result.xlsx')
    return dict(report, schema='an-document-project-verification-v1', **{key: manifest[key] for key in ('markdown_sha256', 'workbook_sha256')})


def save(markdown, workbook, destination):
    """Freeze exactly the selected domain inputs; never infer host acceptance from a disk."""
    markdown, workbook, destination = Path(markdown), Path(workbook), Path(destination)
    md = document.read(markdown, 65536)
    book = document.read(workbook)
    document.verify_workbook(md.decode('utf-8'), workbook)
    destination.mkdir(mode=0o700)
    for name, data in [('markdown.md', md), ('result.xlsx', book), ('checkpoint.json', json.dumps({
            'schema': 'an-document-project-v1', 'markdown_sha256': sha(md), 'workbook_sha256': sha(book)}, sort_keys=True).encode())]:
        with (destination / name).open('xb') as stream:
            os.chmod(stream.name, 0o600)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    descriptor = os.open(destination, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return verify(destination)


if __name__ == '__main__':
    if len(sys.argv) == 5 and sys.argv[1] == 'save':
        result = save(*sys.argv[2:])
    elif len(sys.argv) == 3 and sys.argv[1] == 'verify':
        result = verify(sys.argv[2])
    else:
        raise SystemExit('usage: checkpoint.py save MARKDOWN WORKBOOK NEW_DIRECTORY | verify DIRECTORY')
    print(json.dumps(result, sort_keys=True))
