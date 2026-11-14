import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from zipfile import ZipFile, ZIP_DEFLATED
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'silk'))
import document as body

MARKDOWN = '| Item | Quantity | Unit price (EUR) |\n| --- | --- | --- |\n| Bolt | 12 | 0.50 |\n| Plate | 3 | 8.00 |\n| Bearing | 2 | 4.25 |\n'
ROWS = [{'item':'Bolt','quantity':12,'unit_price':'0.50'},
        {'item':'Plate','quantity':3,'unit_price':'8.00'},
        {'item':'Bearing','quantity':2,'unit_price':'4.25'}]


def pdf_bytes(currency='Currency EUR',quantity='12'):
    lines=['Workshop supplies',currency,'Item Quantity Unit price',f'Bolt {quantity} 0.50','Plate 3 8.00','Bearing 2 4.25']
    content='BT /F1 12 Tf 40 780 Td '+' '.join(('0 -20 Td ' if i else '')+'('+line+') Tj' for i,line in enumerate(lines))+' ET'
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',f'<< /Length {len(content)} >>\nstream\n{content}\nendstream'.encode()]
    result=bytearray(b'%PDF-1.4\n'); offsets=[0]
    for i, value in enumerate(objects,1):
        offsets.append(len(result));result.extend(f'{i} 0 obj\n'.encode()+value+b'\nendobj\n')
    xref=len(result);result.extend(f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode())
    for offset in offsets[1:]:result.extend(f'{offset:010d} 00000 n \n'.encode())
    result.extend(f'trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
    return bytes(result)


class Documents(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.proposal={'source_sha256':body.digest(MARKDOWN.encode()),'rows':ROWS}
    def tearDown(self):self.temp.cleanup()
    def workbook(self):
        path=self.root/'result.xlsx';body.write_workbook(MARKDOWN,self.proposal,path);return path
    def test_pdf_markdown_workbook_preserve_all_facts(self):
        pdf=self.root/'source.pdf';pdf.write_bytes(pdf_bytes())
        source=body.extract_pdf(pdf);self.assertEqual(source['rows'],ROWS)
        self.assertEqual(body.validate_markdown(source,MARKDOWN),MARKDOWN.encode())
        report=body.verify_workbook(MARKDOWN,self.workbook())
        self.assertEqual(report['total_eur'],'38.50');self.assertEqual(report['rows'],3)
    def test_ambiguous_source_and_changed_markdown_refuse(self):
        pdf=self.root/'source.pdf';pdf.write_bytes(pdf_bytes('Currency not specified'))
        uncertain=body.extract_pdf(pdf)
        self.assertEqual(uncertain['requires_clarification'],['currency'])
        with self.assertRaises(ValueError):body.validate_markdown(uncertain,MARKDOWN)
        self.assertEqual(body.validate_markdown(uncertain,MARKDOWN,{'currency':'EUR'}),MARKDOWN.encode())
        with self.assertRaises(ValueError):body.validate_markdown(uncertain,MARKDOWN,{'currency':'USD'})
        source={'schema':'an-document-source-v1','currency':'EUR','rows':ROWS}
        with self.assertRaises(ValueError):body.validate_markdown(source,MARKDOWN.replace('12','13'))
    def test_workbook_rejects_foreign_source_and_rows(self):
        for proposal in [dict(self.proposal,source_sha256='a'*64),dict(self.proposal,rows=ROWS[:-1])]:
            with self.assertRaises(ValueError):body.write_workbook(MARKDOWN,proposal,self.root/'bad.xlsx')
        for value in [True,-1,1.25,1000001]:
            with self.assertRaises(ValueError):body.rows([dict(ROWS[0],quantity=value)])
        for value in ['NaN','Infinity','1e2','0.001',-1]:
            with self.assertRaises(ValueError):body.price(value)
    def test_amount_and_provenance_tampering_are_rejected(self):
        original=self.workbook()
        with ZipFile(original) as archive: files={name:archive.read(name) for name in archive.namelist()}
        for name,old,new in [('xl/worksheets/sheet1.xml',b'<v>38.5</v>',b'<v>99</v>'),
                             ('xl/sharedStrings.xml',self.proposal['source_sha256'].encode(),b'a'*64)]:
            changed=dict(files);self.assertIn(old,changed[name]);changed[name]=changed[name].replace(old,new)
            path=self.root/'tampered.xlsx'
            with ZipFile(path,'w',ZIP_DEFLATED) as archive:
                for item,data in changed.items():archive.writestr(item,data)
            with self.assertRaises(ValueError):body.verify_workbook(MARKDOWN,path)
    def test_item_strings_cannot_become_formulas(self):
        md=MARKDOWN.replace('Bolt','=SUM(A1:A2)');proposal={'source_sha256':body.digest(md.encode()),'rows':[dict(ROWS[0],item='=SUM(A1:A2)'),*ROWS[1:]]}
        path=self.root/'literal.xlsx';body.write_workbook(md,proposal,path)
        self.assertTrue(body.verify_workbook(md,path)['passed'])
    def test_existing_product_is_not_overwritten(self):
        path=self.workbook();before=hashlib.sha256(path.read_bytes()).hexdigest()
        with self.assertRaises(FileExistsError):body.write_workbook(MARKDOWN,self.proposal,path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),before)



class ClarificationAndFormulaBoundaries(unittest.TestCase):
    def test_user_input_can_fill_only_missing_source_facts(self):
        with tempfile.TemporaryDirectory() as directory:
            pdf=Path(directory)/'source.pdf';pdf.write_bytes(pdf_bytes('Currency not specified','?'))
            source=body.extract_pdf(pdf)
            self.assertEqual(source['requires_clarification'],['currency','quantity:0'])
            self.assertEqual(body.validate_markdown(source,MARKDOWN,{'currency':'EUR','quantity:0':12}),MARKDOWN.encode())
            with self.assertRaises(ValueError):body.validate_markdown(source,MARKDOWN,{'currency':'EUR','quantity:0':13})
            with self.assertRaises(ValueError):body.validate_markdown(source,MARKDOWN,{'currency':'EUR','quantity:0':12,'quantity:1':99})
    def test_narrative_or_header_formula_cannot_change_verified_facts(self):
        source={'schema':'an-document-source-v1','currency':'EUR','rows':ROWS}
        with self.assertRaises(ValueError):body.validate_markdown(source,'Total EUR 999\n'+MARKDOWN)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'good.xlsx';proposal={'source_sha256':body.digest(MARKDOWN.encode()),'rows':ROWS}
            body.write_workbook(MARKDOWN,proposal,path)
            with ZipFile(path) as archive:files={name:archive.read(name) for name in archive.namelist()}
            name='xl/worksheets/sheet1.xml';original=b'<c r="A1" t="s"><v>0</v></c>'
            self.assertIn(original,files[name]);files[name]=files[name].replace(original,b'<c r="A1" t="s"><f>1+1</f><v>0</v></c>')
            bad=Path(directory)/'bad.xlsx'
            with ZipFile(bad,'w',ZIP_DEFLATED) as archive:
                for name,data in files.items():archive.writestr(name,data)
            with self.assertRaises(ValueError):body.verify_workbook(MARKDOWN,bad)

if __name__=='__main__':unittest.main()
