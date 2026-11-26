#!/usr/bin/env python3
"""Read-only, standard-library material preflight; no semantic or platform verdicts."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import struct
import sys
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
import zipfile

VERSION = '1.0.0'
OLE = bytes.fromhex('D0CF11E0A1B11AE1')
OFFICE = {'.docx': 'word/document.xml', '.xlsx': 'xl/workbook.xml',
          '.pptx': 'ppt/presentation.xml'}
TEXT = {'.txt', '.md', '.csv', '.json', '.html', '.htm'}
IMAGES = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.tif', '.tiff'}
EXECUTABLE = {'.exe', '.dll', '.bat', '.cmd', '.ps1', '.js', '.vbs', '.msi', '.py', '.sh'}
MAX_XML = 20 * 1024 * 1024
MAX_ARCHIVE = 64 * 1024 * 1024
MAX_ENTRIES = 10000
MAX_FILES = 5000
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
REL_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'


def inside(path, parent):
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def note(record, code, message):
    record['风险信号'].append({'代码': code, '说明': message})


def xml_part(archive, name):
    info = archive.getinfo(name)
    if info.file_size > MAX_XML:
        raise ValueError('XML结构超过单项检查上限')
    return ET.fromstring(archive.read(name))


def xlsx_structure(archive, record):
    workbook = xml_part(archive, 'xl/workbook.xml')
    relationships = xml_part(archive, 'xl/_rels/workbook.xml.rels')
    targets = {r.attrib.get('Id'): r.attrib.get('Target', '') for r in relationships
               if r.attrib.get('TargetMode') != 'External'}
    sheets = []
    for sheet in workbook.findall('s:sheets/s:sheet', NS):
        item = {'工作表': sheet.attrib.get('name', ''),
                '可见性': sheet.attrib.get('state', 'visible')}
        target = targets.get(sheet.attrib.get('{%s}id' % REL_NS), '')
        parts = []
        for part in PurePosixPath(target.lstrip('/') if target.startswith('/') else 'xl/' + target).parts:
            if part == '..':
                if not parts:
                    raise ValueError('工作表路径越界')
                parts.pop()
            elif part != '.':
                parts.append(part)
        sheet_path = '/'.join(parts)
        if not target or not sheet_path.startswith('xl/'):
            raise ValueError('缺少有效工作表关系')
        root = xml_part(archive, sheet_path)
        rows = root.findall('s:sheetData/s:row', NS)
        formulas = [f.text or '' for f in root.findall('.//s:f', NS)]
        cells = root.findall('.//s:c', NS)
        item.update({'记录行数': len(rows),
                     '隐藏行数': sum(r.attrib.get('hidden') in ('1', 'true') for r in rows),
                     '隐藏列段数': sum(c.attrib.get('hidden') in ('1', 'true')
                                      for c in root.findall('s:cols/s:col', NS)),
                     '合并区域数': len(root.findall('s:mergeCells/s:mergeCell', NS)),
                     '公式数': len(formulas),
                     '图片公式数': sum(bool(re.search(r'(?:^|[^A-Z0-9_])(?:_XLFN\.)?(?:DISPIMG|IMAGE)\s*\(', f, re.I))
                                       for f in formulas),
                     '错误单元格数': sum(c.attrib.get('t') == 'e' for c in cells),
                     '绘图引用数': len(root.findall('s:drawing', NS))})
        sheets.append(item)
    names = archive.namelist()
    record['结构'] = {'工作表数': len(sheets), '工作表': sheets,
                      '媒体文件数': sum(n.startswith('xl/media/') and not n.endswith('/') for n in names),
                      '外部链接部件数': sum(n.startswith('xl/externalLinks/externalLink') and n.endswith('.xml') for n in names)}
    if record['结构']['媒体文件数'] or any(s['图片公式数'] or s['绘图引用数'] for s in sheets):
        note(record, 'EXCEL_MEDIA', '存在图片/媒体线索；需实际查看图片提取及图文关联，不能据此认定图片已丢失')
    if any(s['合并区域数'] for s in sheets):
        note(record, 'EXCEL_MERGED', '存在合并区域；检查字段、单位与对象关系')
    if any(s['可见性'] != 'visible' or s['隐藏行数'] or s['隐藏列段数'] for s in sheets):
        note(record, 'EXCEL_HIDDEN', '存在隐藏内容；需确定解析范围及是否允许入库')
    if any(s['错误单元格数'] for s in sheets):
        note(record, 'EXCEL_ERROR', '存在错误单元格；检查是否影响关键事实')
    if any(s['公式数'] for s in sheets):
        note(record, 'EXCEL_FORMULA', '存在公式；本工具不重算，需核对缓存值与实际数值')
    if record['结构']['外部链接部件数']:
        note(record, 'EXCEL_EXTERNAL', '存在外部链接部件；本工具不访问，需核对依赖和数据完整性')
    note(record, 'EXCEL_HEADERS_UNCHECKED', '未判断表头、字段含义和一行一个对象，需内容检查及平台解析复核')


def office_structure(path, suffix, record):
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if len(entries) > MAX_ENTRIES or sum(i.file_size for i in entries) > MAX_ARCHIVE:
            record['检查状态'] = '部分预检'
            note(record, 'ARCHIVE_LIMIT', '压缩包结构超过检查上限，已跳过内部解析；不代表材料不合格')
            return
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('压缩包含同名部件，读取含义不唯一')
        if OFFICE[suffix] not in names:
            record['检查状态'] = '部分预检'
            note(record, 'OFFICE_SIGNATURE', '缺少该Office格式必需部件，需确认实际类型或文件完整性')
            return
        if any(n.lower().endswith('vbaproject.bin') for n in names):
            note(record, 'OFFICE_MACRO', '存在宏部件；本工具未执行，需提供不依赖宏的可读内容')
        if suffix == '.xlsx':
            xlsx_structure(archive, record)
        else:
            xml_part(archive, OFFICE[suffix])
            prefix = 'word/' if suffix == '.docx' else 'ppt/'
            record['结构'] = {'媒体文件数': sum(n.startswith(prefix + 'media/') and not n.endswith('/') for n in names)}
            note(record, 'OFFICE_CONTENT_UNCHECKED', '仅核对容器结构，未检查正文、页序、表格或媒体可读性')


def image_header(data, suffix, record):
    width = height = None
    valid = False
    if suffix == '.png':
        valid = data.startswith(b'\x89PNG\r\n\x1a\n')
        if valid and len(data) >= 24 and data[12:16] == b'IHDR':
            width, height = struct.unpack('>II', data[16:24])
    elif suffix in ('.jpg', '.jpeg'):
        valid = data.startswith(b'\xff\xd8\xff')
    elif suffix == '.gif':
        valid = data.startswith((b'GIF87a', b'GIF89a'))
        if valid and len(data) >= 10:
            width, height = struct.unpack('<HH', data[6:10])
    elif suffix == '.bmp':
        valid = data.startswith(b'BM')
        if valid and len(data) >= 26:
            width, height = struct.unpack('<ii', data[18:26])
            width, height = abs(width), abs(height)
    elif suffix == '.webp':
        valid = data.startswith(b'RIFF') and data[8:12] == b'WEBP'
    else:
        valid = data.startswith((b'II*\x00', b'MM\x00*', b'II+\x00', b'MM\x00+'))
    record['文件头与扩展名'] = '基本对应' if valid else '疑似不对应或文件头不完整'
    if width is not None:
        record['结构'] = {'宽': width, '高': height}
    if not valid:
        record['检查状态'] = '部分预检'
        note(record, 'IMAGE_SIGNATURE', '文件头不匹配，需实际解码或由客户提供原件')
    note(record, 'IMAGE_VISUAL_UNCHECKED', '未进行完整图像解码、清晰度、裁切、文字、真实性或场景适用性检查')


def inspect(path, relative, max_bytes):
    record = {'文件': relative, '检查状态': '技术预检完成', '风险信号': [], '仍需': ['内容质检', '实际平台解析验证']}
    if path.is_symlink():
        record['检查状态'] = '未检查'
        note(record, 'SYMLINK_SKIPPED', '符号链接未跟随')
        return record
    try:
        size = path.stat().st_size
        record['大小字节'] = size
        if size > max_bytes:
            record['检查状态'] = '未检查'
            note(record, 'FILE_LIMIT', '文件超过本次检查上限；可另行检查，不代表不合格')
            return record
        hasher = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                hasher.update(chunk)
        record['SHA256'] = hasher.hexdigest()
        with path.open('rb') as stream:
            data = stream.read(65536)
        suffix = path.suffix.lower()
        record['扩展名'] = suffix
        if not size:
            record['检查状态'] = '部分预检'
            note(record, 'EMPTY_FILE', '空文件，未取得可读内容')
        elif suffix in EXECUTABLE:
            record['检查状态'] = '未检查'
            note(record, 'EXECUTABLE_NOT_RUN', '可执行内容不是默认知识材料，本工具未执行')
        elif suffix in OFFICE:
            if data.startswith(OLE):
                record['检查状态'] = '部分预检'
                note(record, 'OFFICE_OLE_OR_ENCRYPTED', '可能是加密Office或其他二进制格式，请确认并提供可读副本')
            elif data.startswith(b'PK'):
                office_structure(path, suffix, record)
            else:
                record['检查状态'] = '部分预检'
                note(record, 'OFFICE_SIGNATURE', '文件头与Office容器不符，需确认类型或完整性')
        elif suffix in ('.doc', '.xls', '.ppt'):
            record['检查状态'] = '部分预检'
            note(record, 'LEGACY_OFFICE', '旧版二进制Office需相应工具读取；本工具未解析正文')
            if not data.startswith(OLE):
                note(record, 'LEGACY_TYPE_UNCERTAIN', '可能是HTML/XML等兼容格式，需确认实际文件类型')
        elif suffix == '.pdf':
            record['文件头与扩展名'] = '基本对应' if b'%PDF-' in data[:1024] else '疑似不对应'
            if b'%PDF-' not in data[:1024]:
                record['检查状态'] = '部分预检'
                note(record, 'PDF_SIGNATURE', '未找到PDF文件头，需确认类型')
            note(record, 'PDF_CONTENT_UNCHECKED', '未检查加密、完整页数、扫描文字或证据内容；需PDF/视觉工具读取')
        elif suffix in IMAGES:
            image_header(data, suffix, record)
        elif suffix in TEXT:
            try:
                text = path.read_text(encoding='utf-8-sig')
                record['结构'] = {'字符数': len(text), '编码': 'UTF-8'}
                if suffix == '.json':
                    json.loads(text)
            except (UnicodeError, json.JSONDecodeError, RecursionError):
                record['检查状态'] = '部分预检'
                note(record, 'TEXT_ENCODING_OR_JSON', 'UTF-8读取或JSON结构验证失败，需确认编码/格式，未判定业务内容')
            note(record, 'TEXT_SEMANTICS_UNCHECKED', '未审核语义、表格字段、HTML外部资源或聊天上下文')
        else:
            record['检查状态'] = '未检查'
            note(record, 'TYPE_UNSUPPORTED', '此类型未自动解析；按现有工具人工检查，不自动执行或上传')
    except (OSError, ValueError, ET.ParseError, zipfile.BadZipFile, KeyError, RuntimeError, NotImplementedError) as exc:
        record['检查状态'] = '部分预检'
        note(record, 'READ_FAILED', '读取/结构解析未完成：' + type(exc).__name__)
    return record


def scan(source, max_bytes=100 * 1024 * 1024):
    source = Path(source).absolute()
    if source.is_symlink() or not source.exists():
        raise ValueError('输入必须是存在的普通文件或目录，不能是符号链接')
    source = source.resolve()
    records = []
    omitted = []
    if source.is_file():
        candidates = [(source, source.name)]
    else:
        candidates = []
        def walk_error(error):
            omitted.append({'目录': str(error.filename), '原因': '目录无法读取'})
        for root, dirs, files in os.walk(source, followlinks=False, onerror=walk_error):
            dirs.sort()
            for name in list(dirs):
                child = Path(root) / name
                if child.is_symlink():
                    omitted.append({'目录': str(child.relative_to(source)), '原因': '符号链接未跟随'})
                    dirs.remove(name)
            for name in sorted(files):
                path = Path(root) / name
                if len(candidates) < MAX_FILES:
                    candidates.append((path, str(path.relative_to(source))))
                else:
                    omitted.append({'目录': str(path.relative_to(source)), '原因': '超过文件数量检查上限'})
    for i, (path, relative) in enumerate(candidates, 1):
        record = inspect(path, relative, max_bytes)
        record['扫描临时编号'] = 'F%04d' % i
        records.append(record)
    hashes = {}
    for record in records:
        if 'SHA256' in record:
            hashes.setdefault(record['SHA256'], []).append(record['文件'])
    duplicates = [files for files in hashes.values() if len(files) > 1]
    return {'工具版本': VERSION, '生成时间UTC': datetime.now(timezone.utc).isoformat(),
            '输入': str(source), '结论范围': '本地技术预检；非内容质检、真实性核验或平台验收',
            '文件数': len(records), '未覆盖': omitted, '完全相同字节组': duplicates, '文件': records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--max-file-mb', type=int, default=100)
    args = parser.parse_args()
    source = Path(args.input).absolute()
    output = Path(args.output).resolve()
    if args.max_file_mb <= 0:
        parser.error('max-file-mb必须大于0')
    if source.is_symlink() or (source.is_dir() and inside(output, source.resolve())) or output == source.resolve():
        parser.error('输出必须位于输入材料之外，且输入不能是符号链接')
    if output.exists():
        parser.error('输出文件已存在，请指定新文件名，避免覆盖已有记录')
    try:
        report = scan(source, args.max_file_mb * 1024 * 1024)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    except (OSError, ValueError) as exc:
        print('预检未完成：' + str(exc), file=sys.stderr)
        return 2
    print(json.dumps({'文件数': report['文件数'], '未覆盖数': len(report['未覆盖']),
                      '报告': str(output), '范围': report['结论范围']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
