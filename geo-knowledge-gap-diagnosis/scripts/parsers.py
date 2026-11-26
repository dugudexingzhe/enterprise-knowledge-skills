"""Read-only extractors. A segment is (locator, original extracted text)."""
import csv
import io
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

TEXT = {'.md', '.txt', '.rst', '.log', '.json', '.jsonl', '.yaml', '.yml',
        '.xml', '.html', '.htm', '.csv', '.tsv'}
SUPPORTED = TEXT | {'.pdf', '.docx', '.xlsx', '.pptx'}
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'


def decode(raw):
    # No replacement characters: an undecodable file is a recorded failure.
    encodings = ['utf-8-sig']
    if raw.startswith((b'\xff\xfe', b'\xfe\xff')):
        encodings.insert(0, 'utf-16')
    encodings.append('gb18030')
    for encoding in encodings:
        try:
            value = raw.decode(encoding)
            if '\x00' in value:
                raise ValueError('文本包含 NUL，不能可靠按文本读取')
            return value
        except UnicodeDecodeError:
            continue
    raise ValueError('编码不可识别；未使用替代字符掩盖损坏')


def parse(path):
    """Return segments, warnings. Warnings force partial, never silent loss."""
    path = Path(path)
    suffix = path.suffix.lower()
    segments, warnings = [], []
    if suffix in TEXT:
        value = decode(path.read_bytes())
        # Keep exact source lines, including HTML tags, no guessed rendered text.
        if suffix in {'.csv', '.tsv'}:
            reader = csv.reader(io.StringIO(value), delimiter='\t' if suffix == '.tsv' else ',')
            for row_number, row in enumerate(reader, 1):
                if any(row):
                    segments.append((f'记录 {row_number}（截至物理行 {reader.line_num}）',
                                     ' | '.join(row)))
        else:
            segments = [(f'行 {n}', line) for n, line in enumerate(value.splitlines(), 1)
                        if line.strip()]
    elif suffix == '.docx':
        with zipfile.ZipFile(path) as archive:
            root = ET.fromstring(archive.read('word/document.xml'))
            body = root.find(f'{W}body')
            if body is None:
                raise ValueError('Word 主文档无 body')
            paragraph, table = 0, 0
            for node in body:
                if node.tag == f'{W}p':
                    paragraph += 1
                    text = ''.join(n.text or '' for n in node.iter(f'{W}t'))
                    if text.strip():
                        segments.append((f'正文段落 {paragraph}', text))
                elif node.tag == f'{W}tbl':
                    table += 1
                    for row_num, row in enumerate(node.findall(f'{W}tr'), 1):
                        for col_num, cell in enumerate(row.findall(f'{W}tc'), 1):
                            text = '\n'.join(''.join(n.text or '' for n in p.iter(f'{W}t'))
                                             for p in cell.findall(f'{W}p'))
                            if text.strip():
                                segments.append((f'表 {table} 行 {row_num} 列 {col_num}', text))
            # Read supplementary text parts as well; no fabricated Word page numbers.
            for name in sorted(archive.namelist()):
                if re.fullmatch(r'word/(header\d+|footer\d+|footnotes|endnotes|comments)\.xml', name):
                    part = ET.fromstring(archive.read(name))
                    for n, p in enumerate(part.iter(f'{W}p'), 1):
                        text = ''.join(x.text or '' for x in p.iter(f'{W}t'))
                        if text.strip():
                            segments.append((f'{name} 段落 {n}', text))
            if any(n.startswith(('word/media/', 'word/embeddings/')) for n in archive.namelist()):
                warnings.append('含嵌入图片或对象，未进行 OCR 或对象解析')
            if root.find(f'.//{W}del') is not None or root.find(f'.//{W}ins') is not None:
                warnings.append('含修订标记，须人工核对接受/删除状态')
            if root.find(f'.//{W}altChunk') is not None:
                warnings.append('含 altChunk 内容，未展开')
            if root.find(f'.//{W}txbxContent') is not None:
                warnings.append('含文本框，正文段落提取未完整覆盖其内容')
            if any(len(list(t.iter(f'{W}tbl'))) > 1 for t in root.iter(f'{W}tbl')):
                warnings.append('含嵌套表格，未完整覆盖内层表格')
            if any(n.startswith(('word/charts/', 'word/diagrams/')) for n in archive.namelist()):
                warnings.append('含图表或SmartArt，未解析其视觉/结构内容')
    elif suffix == '.xlsx':
        from openpyxl import load_workbook
        book = load_workbook(path, read_only=True, data_only=False, keep_links=False)
        try:
            for sheet in book.worksheets:
                # Some producers write incorrect dimensions; enumerate actual cells.
                sheet.reset_dimensions()
                for row in sheet.iter_rows():
                    for cell in row:
                        if cell.value is None:
                            continue
                        if cell.data_type == 'f':
                            warnings.append(f'{sheet.title}!{cell.coordinate} 是公式；未计算或采用缓存结果')
                        segments.append((f'工作表 {sheet.title}!{cell.coordinate}', str(cell.value)))
        finally:
            book.close()
        with zipfile.ZipFile(path) as archive:
            if any(n.startswith(('xl/media/', 'xl/embeddings/', 'xl/charts/')) for n in archive.namelist()):
                warnings.append('含图片、图表或嵌入对象，未解析其视觉内容')
    elif suffix == '.pptx':
        with zipfile.ZipFile(path) as archive:
            names = [n for n in archive.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml', n)]
            for name in sorted(names, key=lambda n: int(re.search(r'slide(\d+)\.xml', n).group(1))):
                number = re.search(r'slide(\d+)\.xml', name).group(1)
                root = ET.fromstring(archive.read(name))
                for index, p in enumerate(root.iter(f'{A}p'), 1):
                    text = ''.join(n.text or '' for n in p.iter(f'{A}t'))
                    if text.strip():
                        segments.append((f'幻灯片 {number} 文本段 {index}', text))
            for name in sorted(archive.namelist()):
                if re.fullmatch(r'ppt/notesSlides/notesSlide\d+\.xml', name):
                    root = ET.fromstring(archive.read(name))
                    for index, p in enumerate(root.iter(f'{A}p'), 1):
                        text = ''.join(n.text or '' for n in p.iter(f'{A}t'))
                        if text.strip():
                            segments.append((f'{name} 备注段 {index}', text))
            if any(n.startswith(('ppt/media/', 'ppt/embeddings/', 'ppt/charts/')) for n in archive.namelist()):
                warnings.append('含图片、图表或嵌入对象，未解析其视觉内容')
    elif suffix == '.pdf':
        from pypdf import PdfReader
        reader = PdfReader(path, strict=True)
        if reader.is_encrypted:
            raise ValueError('加密 PDF 不自动解密；请另提供获授权的可读副本')
        for number, page in enumerate(reader.pages, 1):
            try:
                value = page.extract_text() or ''
                if value.strip():
                    segments.append((f'页 {number}', value))
                else:
                    warnings.append(f'页 {number} 无可提取文本；可能为空白页或扫描页，待核对')
                if page.images:
                    warnings.append(f'页 {number} 含图片，未 OCR')
            except Exception as exc:
                warnings.append(f'页 {number} 解析失败：{type(exc).__name__}: {exc}')
    else:
        raise ValueError(f'不支持格式 {suffix or "无扩展名"}')
    return segments, sorted(set(warnings))
