"""Bounded EUR line-item documents. No provider, host control or network access."""
import hashlib
import json
import os
from decimal import Decimal
from pathlib import Path
import re
import sys
from xml.etree import ElementTree as ET
from zipfile import ZipFile

MAX_BYTES = 4 * 1024 * 1024
HEADERS = ['Item', 'Quantity', 'Unit price (EUR)']
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def read(path, limit=MAX_BYTES):
    with Path(path).open('rb') as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError('document size limit')
    return data


def digest(data):
    return hashlib.sha256(data).hexdigest()


def price(value):
    if isinstance(value, bool) or not re.fullmatch(r'[0-9]{1,9}(?:\.[0-9]{1,2})?', str(value)):
        raise ValueError('price requires nonnegative decimal cents')
    return Decimal(str(value)).quantize(Decimal('.01'))


def rows(value):
    if not isinstance(value, list) or not 1 <= len(value) <= 200:
        raise ValueError('row count limit')
    result = []
    for row in value:
        if not isinstance(row, dict) or set(row) != {'item', 'quantity', 'unit_price'}:
            raise ValueError('unexpected row fields')
        name, quantity = row['item'], row['quantity']
        if not isinstance(name, str) or not name.strip() or len(name) > 128 or any(ord(c) < 32 for c in name):
            raise ValueError('invalid item')
        if type(quantity) is not int or not 1 <= quantity <= 1000000:
            raise ValueError('quantity requires a positive bounded integer')
        result.append({'item': name, 'quantity': quantity, 'unit_price': str(price(row['unit_price']))})
    if sum(row['quantity'] * price(row['unit_price']) for row in result) > Decimal('10000000000.00'):
        raise ValueError('quote total exceeds exact workbook bound')
    return result


def parse_markdown(text):
    if not isinstance(text, str) or len(text.encode()) > 65536:
        raise ValueError('Markdown size limit')
    lines = [line.strip() for line in text.splitlines() if line.strip().startswith('|')]
    if len(lines) < 3 or [v.strip() for v in lines[0].strip('|').split('|')] != HEADERS:
        raise ValueError('required EUR table header missing')
    separators = [v.strip() for v in lines[1].strip('|').split('|')]
    if len(separators) != 3 or any(not re.fullmatch(r':?-{3,}:?', v) for v in separators):
        raise ValueError('invalid Markdown table separator')
    parsed = []
    for line in lines[2:]:
        fields = [v.strip() for v in line.strip('|').split('|')]
        if len(fields) != 3 or not re.fullmatch(r'[0-9]+', fields[1]):
            raise ValueError('invalid Markdown row')
        parsed.append({'item': fields[0], 'quantity': int(fields[1]), 'unit_price': fields[2]})
    return rows(parsed)


def extract_pdf(path):
    from pypdf import PdfReader
    from io import BytesIO
    data = read(path)
    pdf = PdfReader(BytesIO(data), strict=True)
    if pdf.is_encrypted or not 1 <= len(pdf.pages) <= 32:
        raise ValueError('unsupported encrypted PDF or page count')
    text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
    if len(text.encode()) > 65536:
        raise ValueError('bounded EUR source required; ask for clarification')
    lines = text.splitlines()
    if len(lines) < 4 or lines[1] not in ('Currency EUR', 'Currency not specified') or lines[2] != 'Item Quantity Unit price':
        raise ValueError('unsupported source header; ask for clarification')
    source_rows = []
    for line in lines[3:]:
        if not line.strip():
            continue
        match = re.fullmatch(r'(.+?) ([0-9]+|\?) ([0-9]+(?:\.[0-9]{1,2})?)', line.strip())
        if not match:
            raise ValueError('unsupported source row; ask for clarification')
        source_rows.append({'item': match[1], 'quantity': None if match[2] == '?' else int(match[2]), 'unit_price': str(price(match[3]))})
    questions = ([] if lines[1] == 'Currency EUR' else ['currency'])
    questions += [f'quantity:{i}' for i,row in enumerate(source_rows) if row['quantity'] is None]
    if not questions:
        source_rows = rows(source_rows)
    return {'schema': 'an-document-source-v1', 'pdf_sha256': digest(data), 'title': lines[0], 'text': text,
            'currency': 'EUR' if lines[1] == 'Currency EUR' else None, 'rows': source_rows,
            'requires_clarification': questions}


def validate_markdown(source, markdown, clarifications=None):
    if source.get('schema') != 'an-document-source-v1':
        raise ValueError('unsupported source contract')
    allowed_notes={'', 'Currency: EUR', '# '+source.get('title','Workshop supplies')}
    if any(line.strip() not in allowed_notes for line in markdown.splitlines() if not line.strip().startswith('|')):
        raise ValueError('unsupported Markdown narrative')
    answers = clarifications or {}
    questions = source.get('requires_clarification', [])
    if set(answers) != set(questions):
        raise ValueError('missing or unrelated clarification')
    if source.get('currency') != 'EUR' and answers.get('currency') != 'EUR':
        raise ValueError('explicit EUR clarification required')
    expected = [dict(row) for row in source['rows']]
    for key in questions:
        if key.startswith('quantity:'):
            expected[int(key.split(':')[1])]['quantity'] = answers[key]
    if parse_markdown(markdown) != rows(expected):
        raise ValueError('Markdown changed source facts')
    return markdown.encode('utf-8')


def write_workbook(markdown, proposal, destination):
    import datetime
    import xlsxwriter
    expected = parse_markdown(markdown)
    if set(proposal) != {'source_sha256', 'rows'} or proposal['source_sha256'] != digest(markdown.encode()):
        raise ValueError('proposal is not bound to accepted Markdown')
    if rows(proposal['rows']) != expected:
        raise ValueError('structured rows changed accepted Markdown')
    destination = Path(destination)
    # Never overwrite an earlier product, even after an unknown result.
    with destination.open('xb') as output:
        with xlsxwriter.Workbook(output, {'in_memory': True, 'strings_to_formulas': False,
                                         'strings_to_urls': False}) as book:
            book.set_properties({'created': datetime.datetime(2000, 1, 1)})
            sheet = book.add_worksheet('Supplies')
            sheet.write_row(0, 0, HEADERS + ['Amount (EUR)'])
            total = Decimal('0.00')
            for i, row in enumerate(expected, 1):
                amount = row['quantity'] * price(row['unit_price'])
                total += amount
                sheet.write_string(i, 0, row['item'])
                sheet.write_number(i, 1, row['quantity'])
                sheet.write_number(i, 2, float(price(row['unit_price'])))
                sheet.write_formula(i, 3, f'=B{i+1}*C{i+1}', None, float(amount))
            end = len(expected) + 1
            sheet.write_string(end, 0, 'Total (EUR)')
            sheet.write_formula(end, 3, f'=SUM(D2:D{end})', None, float(total))
            sheet.write_string(end + 2, 0, 'Markdown SHA256 ' + proposal['source_sha256'])
            sheet.set_column('A:A', 30)
            sheet.set_column('B:D', 22)
    verify_workbook(markdown, destination)


def verify_workbook(markdown, path):
    expected = parse_markdown(markdown)
    data = read(path)
    from io import BytesIO
    with ZipFile(BytesIO(data)) as archive:
        entries = archive.infolist()
        names = [e.filename for e in entries]
        if len(entries) > 128 or len(names) != len(set(names)) or sum(e.file_size for e in entries) > 8 * MAX_BYTES:
            raise ValueError('workbook archive limit')
        for name in names:
            if name.startswith('/') or '..' in Path(name).parts or 'vba' in name.lower() or 'externallink' in name.lower():
                raise ValueError('unsupported workbook content')
            if name.endswith('.rels'):
                tree = ET.fromstring(archive.read(name))
                if any(e.attrib.get('TargetMode') == 'External' for e in tree):
                    raise ValueError('external workbook relationship')
        workbook = ET.fromstring(archive.read('xl/workbook.xml'))
        sheets = workbook.findall('s:sheets/s:sheet', NS)
        if len(sheets) != 1 or sheets[0].get('name') != 'Supplies':
            raise ValueError('unexpected workbook sheets')
        strings = [''.join(e.itertext()) for e in ET.fromstring(archive.read('xl/sharedStrings.xml')).findall('s:si', NS)]
        sheet = ET.fromstring(archive.read('xl/worksheets/sheet1.xml'))
        cells = {}
        for cell in sheet.findall('.//s:sheetData/s:row/s:c', NS):
            ref = cell.attrib['r']
            if ref in cells:
                raise ValueError('duplicate cell')
            cells[ref] = cell
        def value(ref):
            cell = cells[ref]
            v = cell.findtext('s:v', namespaces=NS)
            return strings[int(v)] if cell.get('t') == 's' else v
        def formula(ref, expected_formula, expected_value):
            if cells[ref].findtext('s:f', namespaces=NS) != expected_formula or Decimal(value(ref)) != expected_value:
                raise ValueError('workbook formula or cached amount mismatch')
        allowed = {f'{column}1' for column in 'ABCD'}
        if [value(f'{c}1') for c in 'ABCD'] != HEADERS + ['Amount (EUR)']:
            raise ValueError('workbook header mismatch')
        total = Decimal('0.00')
        for index, row in enumerate(expected, 2):
            allowed.update(f'{c}{index}' for c in 'ABCD')
            if value(f'A{index}') != row['item'] or Decimal(value(f'B{index}')) != row['quantity'] or Decimal(value(f'C{index}')) != price(row['unit_price']):
                raise ValueError('workbook row mismatch')
            if any(cells[f'{c}{index}'].find('s:f', NS) is not None for c in 'ABC'):
                raise ValueError('unexpected source cell formula')
            amount = row['quantity'] * price(row['unit_price']); total += amount
            formula(f'D{index}', f'B{index}*C{index}', amount)
        end = len(expected) + 2
        allowed.update([f'A{end}', f'D{end}', f'A{end+2}'])
        formula(f'D{end}', f'SUM(D2:D{end-1})', total)
        if value(f'A{end}') != 'Total (EUR)' or value(f'A{end+2}') != 'Markdown SHA256 ' + digest(markdown.encode()):
            raise ValueError('workbook provenance mismatch')
        formula_cells={f'D{i}' for i in range(2,end+1)}
        for ref,cell in cells.items():
            if cell.find('s:f',NS) is not None and ref not in formula_cells:
                raise ValueError('unexpected workbook formula')
            if ref[0] in 'BCD' and ref not in {'B1','C1','D1'} and cell.get('t') not in (None,'n'):
                raise ValueError('workbook number has a nonnumeric cell type')
        if set(cells) != allowed:
            raise ValueError('unexpected workbook cells')
    return {'schema': 'an-document-verification-v1', 'passed': True, 'rows': len(expected),
            'total_eur': str(total), 'sha256': digest(data), 'bytes': len(data),
            'source_sha256': digest(markdown.encode())}


def main():
    if 'AN_SPOOL_INPUT' in os.environ:
        markdown = read(os.environ['AN_SPOOL_AUX_0'], 65536).decode()
        candidate = Path(os.environ['AN_SPOOL_INPUT'])
        report = verify_workbook(markdown, candidate)
        Path('result.xlsx').write_bytes(read(candidate))
        Path('verification.json').write_text(json.dumps(report, sort_keys=True))
        return
    action, *args = sys.argv[1:]
    if action.startswith('job-'):
        request = json.loads(read(args[0], 131072))
        output = Path(args[1])
        if not 1 <= len(request['inputs']) <= (2 if action == 'job-markdown' else 1):
            raise ValueError('one authorized document input required')
        source = request['inputs'][0]
        if action == 'job-extract':
            product = output / 'source.json'
            with product.open('xb') as stream:
                stream.write(json.dumps(extract_pdf(source), sort_keys=True).encode())
            names = ['source.json']
        elif action == 'job-markdown':
            data = request['data']
            if set(data) != {'markdown'}:
                raise ValueError('Markdown proposal required')
            with (output / 'markdown.md').open('xb') as stream:
                stream.write(validate_markdown(extract_pdf(source), data['markdown'],
                    json.loads(read(request['inputs'][1], 65536)) if len(request['inputs']) == 2 else None))
            names = ['markdown.md']
        elif action == 'job-workbook':
            markdown = read(source, 65536).decode()
            write_workbook(markdown, request['data'], output / 'result.xlsx')
            report = verify_workbook(markdown, output / 'result.xlsx')
            with (output / 'verification.json').open('xb') as stream:
                stream.write(json.dumps(report, sort_keys=True).encode())
            names = ['result.xlsx', 'verification.json']
        else:
            raise ValueError('unsupported fixed document action')
        manifest = {name: {'sha256': digest(read(output / name)), 'bytes': (output / name).stat().st_size} for name in names}
        with (output / 'manifest.json').open('xb') as stream:
            stream.write(json.dumps(manifest, sort_keys=True).encode())
        return
    if action == 'extract':
        source = extract_pdf(args[0]); data = json.dumps(source, sort_keys=True).encode()
        with Path(args[1]).open('xb') as output: output.write(data)
    elif action == 'markdown':
        request = json.loads(read(args[0], 131072))
        with Path(args[1]).open('xb') as output:
            output.write(validate_markdown(request['source'], request['markdown']))
    elif action == 'workbook':
        write_workbook(read(args[0], 65536).decode(), json.loads(read(args[1], 65536)), args[2])
    elif action == 'verify':
        report = verify_workbook(read(args[0], 65536).decode(), args[1])
        with Path(args[2]).open('xb') as output: output.write(json.dumps(report, sort_keys=True).encode())
    else:
        raise ValueError('unsupported document action')


if __name__ == '__main__':
    main()
