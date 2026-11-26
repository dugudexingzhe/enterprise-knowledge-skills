"""Meaningful, isolated tests of read-only preflight and installer behavior."""
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / '技能' / 'kb-format-check' / 'scripts' / 'preflight.py'
spec = importlib.util.spec_from_file_location('kb_preflight', PREFLIGHT)
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)
build_spec = importlib.util.spec_from_file_location('kb_build', ROOT / 'scripts' / '构建与安装.py')
builder = importlib.util.module_from_spec(build_spec)
build_spec.loader.exec_module(builder)
S = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
P = 'http://schemas.openxmlformats.org/package/2006/relationships'
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=')


def workbook(path, mixed=False):
    sheets = []
    rels = []
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        for n in range(1, 11):
            state = ' state="hidden"' if mixed and n == 10 else ''
            sheets.append('<sheet name="产品%d" sheetId="%d" r:id="rId%d"%s/>' % (n, n, n, state))
            rels.append('<Relationship Id="rId%d" Type="%s/worksheet" Target="worksheets/sheet%d.xml"/>' % (n, R, n))
            extra = '<mergeCells count="1"><mergeCell ref="A1:B1"/></mergeCells><drawing r:id="rIdImage"/>' if mixed and n == 1 else ''
            data = '<row r="1"><c r="A1" t="inlineStr"><is><t>型号</t></is></c><c r="B1" t="inlineStr"><is><t>价格</t></is></c></row><row r="2"><c r="A2" t="inlineStr"><is><t>F-%d</t></is></c><c r="B2"><v>3000</v></c></row>' % n
            if mixed and n == 1:
                data += '<row r="3" hidden="1"><c r="C3"><f>_xlfn.DISPIMG("ID_DEMO",1)</f><v>0</v></c><c r="D3" t="e"><v>#REF!</v></c></row>'
            z.writestr('xl/worksheets/sheet%d.xml' % n,
                       '<worksheet xmlns="%s" xmlns:r="%s"><sheetData>%s</sheetData>%s</worksheet>' % (S, R, data, extra))
        z.writestr('xl/workbook.xml', '<workbook xmlns="%s" xmlns:r="%s"><sheets>%s</sheets></workbook>' % (S, R, ''.join(sheets)))
        z.writestr('xl/_rels/workbook.xml.rels', '<Relationships xmlns="%s">%s</Relationships>' % (P, ''.join(rels)))
        if mixed:
            z.writestr('xl/media/image1.png', PNG)
            z.writestr('xl/externalLinks/externalLink1.xml', '<externalLink/>')


def codes(record):
    return {n['代码'] for n in record['风险信号']}


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.materials = self.root / '客户资料'
        self.materials.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def test_ten_structured_sheets_are_not_media_failure(self):
        path = self.materials / '结构化十表.xlsx'
        workbook(path)
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        report = preflight.scan(self.materials)
        row = report['文件'][0]
        self.assertEqual(row['结构']['工作表数'], 10)
        self.assertNotIn('EXCEL_MEDIA', codes(row))
        self.assertNotIn('READ_FAILED', codes(row))
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), before)

    def test_mixed_workbook_signals_preserve_uncertainty(self):
        workbook(self.materials / '图文十表.xlsx', mixed=True)
        row = preflight.scan(self.materials)['文件'][0]
        self.assertTrue({'EXCEL_MEDIA', 'EXCEL_MERGED', 'EXCEL_HIDDEN', 'EXCEL_ERROR', 'EXCEL_FORMULA', 'EXCEL_EXTERNAL'} <= codes(row))
        self.assertEqual(row['结构']['工作表'][0]['图片公式数'], 1)
        self.assertEqual(row['结构']['工作表数'], 10)

    def test_duplicates_are_bytes_not_filename(self):
        (self.materials / 'A.md').write_text('相同正文', encoding='utf-8')
        (self.materials / 'B.md').write_text('相同正文', encoding='utf-8')
        report = preflight.scan(self.materials)
        self.assertEqual(len(report['完全相同字节组']), 1)
        self.assertEqual(len(report['完全相同字节组'][0]), 2)

    def test_wrong_office_type_is_not_accepted(self):
        (self.materials / '伪扩展名.xlsx').write_text('不是Excel', encoding='utf-8')
        row = preflight.scan(self.materials)['文件'][0]
        self.assertIn('OFFICE_SIGNATURE', codes(row))
        self.assertEqual(row['检查状态'], '部分预检')

    def test_empty_and_non_utf8_do_not_crash(self):
        (self.materials / '空.txt').touch()
        (self.materials / '旧编码.txt').write_bytes('中文'.encode('gbk'))
        report = preflight.scan(self.materials)
        all_codes = set().union(*(codes(r) for r in report['文件']))
        self.assertTrue({'EMPTY_FILE', 'TEXT_ENCODING_OR_JSON'} <= all_codes)

    def test_file_limit_reports_unchecked(self):
        (self.materials / '大文件.txt').write_bytes(b'12345')
        row = preflight.scan(self.materials, max_bytes=4)['文件'][0]
        self.assertEqual(row['检查状态'], '未检查')
        self.assertIn('FILE_LIMIT', codes(row))

    def test_archive_limit_is_partial(self):
        path = self.materials / '超限.xlsx'
        with zipfile.ZipFile(path, 'w') as z:
            for i in range(preflight.MAX_ENTRIES + 1):
                z.writestr('part/%d' % i, b'')
        row = preflight.scan(self.materials)['文件'][0]
        self.assertIn('ARCHIVE_LIMIT', codes(row))

    def test_ole_container_is_not_claimed_corrupt(self):
        (self.materials / '可能加密.docx').write_bytes(preflight.OLE + b'not-real-document')
        row = preflight.scan(self.materials)['文件'][0]
        self.assertIn('OFFICE_OLE_OR_ENCRYPTED', codes(row))
        self.assertNotIn('OFFICE_SIGNATURE', codes(row))

    def test_image_header_is_not_visual_verdict(self):
        (self.materials / '图片.png').write_bytes(PNG)
        row = preflight.scan(self.materials)['文件'][0]
        self.assertEqual(row['结构'], {'宽': 1, '高': 1})
        self.assertIn('IMAGE_VISUAL_UNCHECKED', codes(row))

    def test_executable_never_runs(self):
        marker = self.root / '不应存在.txt'
        (self.materials / '不能执行.py').write_text('from pathlib import Path; Path(%r).touch()' % str(marker), encoding='utf-8')
        row = preflight.scan(self.materials)['文件'][0]
        self.assertIn('EXECUTABLE_NOT_RUN', codes(row))
        self.assertFalse(marker.exists())

    def test_output_inside_input_is_rejected(self):
        completed = subprocess.run([sys.executable, '-X', 'utf8', str(PREFLIGHT), '--input', str(self.materials), '--output', str(self.materials / '报告.json')], capture_output=True)
        self.assertNotEqual(completed.returncode, 0)
        self.assertFalse((self.materials / '报告.json').exists())

    def test_output_preserved_and_success_is_scoped(self):
        (self.materials / '资料.md').write_text('示例正文', encoding='utf-8')
        output = self.root / '输出' / '结果.json'
        args = [sys.executable, '-X', 'utf8', str(PREFLIGHT), '--input', str(self.materials), '--output', str(output)]
        self.assertEqual(subprocess.run(args, capture_output=True).returncode, 0)
        original = output.read_bytes()
        report = json.loads(original)
        self.assertIn('非内容质检', report['结论范围'])
        self.assertNotEqual(subprocess.run(args, capture_output=True).returncode, 0)
        self.assertEqual(output.read_bytes(), original)

    def test_install_precheck_does_not_partially_install(self):
        target = self.root / '安装目录'
        conflict = target / 'kb-content-audit'
        conflict.mkdir(parents=True)
        (conflict / '原有文件.txt').write_text('保留', encoding='utf-8')
        with self.assertRaises(ValueError):
            builder.install(target)
        self.assertFalse((target / 'kb-client-plan').exists())
        self.assertEqual((conflict / '原有文件.txt').read_text(encoding='utf-8'), '保留')

    def test_install_source_overlap_rejected(self):
        with self.assertRaises(ValueError):
            builder.install(ROOT / '技能' / 'kb-client-plan')


if __name__ == '__main__':
    unittest.main(verbosity=2)
