"""Create explicitly fictitious, local-only fixtures; never accept a customer path."""
import json
import shutil
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def docx(path, paragraphs):
    # A compact OOXML document with valid content types and package relationship.
    path.parent.mkdir(parents=True, exist_ok=True)
    body = ''.join('<w:p><w:r><w:t>'+escape(p)+'</w:t></w:r></w:p>' for p in paragraphs)
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('[Content_Types].xml', '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        z.writestr('_rels/.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        z.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+body+'</w:body></w:document>')


def pdf(path, text=None):
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = PdfWriter()
    page = writer.add_blank_page(width=595, height=842)
    if text:
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
                                 NameObject('/Subtype'): NameObject('/Type1'),
                                 NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
        stream = DecodedStreamObject()
        stream.set_data(('BT /F1 11 Tf 40 790 Td ('+text+') Tj ET').encode('ascii'))
        page[NameObject('/Contents')] = writer._add_object(stream)
    with path.open('wb') as f:
        writer.write(f)


def create(base):
    base = Path(base)
    if base.exists() and any(base.iterdir()):
        raise ValueError('测试样本目录非空，拒绝覆盖')
    clean = base / '完整与缺口'
    write(clean / '00_样本声明.md', '# 虚构测试资料\n本目录全部企业、产品、金额和案例均为模拟数据，不代表真实客户。\n')
    write(clean / '产品/多层/参数.md', '# 星帆设备（虚构）SF-10\nSF-10适用于20人及以下食品车间。\nSF-10的额定处理量为每小时100公斤。\n')
    write(clean / '产品/安装说明.txt', '本模拟企业为SF-10提供上门安装服务。\n')
    write(clean / '报价/报价A.csv', '型号,范围,金额,单位,税费运费\nSF-10,河南地区2026年11月标准配置,28000,元/台,含税含运费\n')
    write(clean / '报价/报价B.json', '{"型号":"SF-10","范围":"河南地区2026年11月标准配置","金额":32000,"单位":"元/台","税费运费":"含税含运费"}\n')
    docx(clean / '产品/服务条款.docx', ['模拟资料：SF-10售后服务条款', 'SF-10整机质保12个月。'])
    from openpyxl import Workbook
    wb = Workbook()
    sheet = wb.active
    sheet.title = '参数'
    sheet.append(['型号', '额定功率', '单位'])
    sheet.append(['SF-10', 3, 'kW'])
    wb.save(clean / '产品/参数.xlsx')
    wb.close()
    pdf(clean / '案例/模拟测试.pdf', 'FICTITIOUS. SF-10 test lot A: throughput 100 kg per hour; no measured annual energy data.')
    # Real PPTX package, no media; use the installed optional test-only generator.
    try:
        from pptx import Presentation
        deck = Presentation()
        slide = deck.slides.add_slide(deck.slide_layouts[1])
        slide.shapes.title.text = '虚构样本：SF-10采购评估'
        slide.placeholders[1].text = '设备额定功率不等于客户实际年耗电量。'
        deck.save(clean / '产品/评估说明.pptx')
    except ImportError:
        # Fixture generation still covers the supported OOXML text-part parser.
        with zipfile.ZipFile(clean / '产品/评估说明.pptx', 'w') as z:
            z.writestr('ppt/slides/slide1.xml', '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:p><a:r><a:t>设备额定功率不等于客户实际年耗电量。</a:t></a:r></a:p></p:sld>')
    write(clean / '.隐藏资料/说明.txt', '虚构资料完整清点需包含隐藏目录。\n')
    duplicate = clean / '副本/参数副本.md'
    duplicate.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(clean / '产品/多层/参数.md', duplicate)
    request = {'enterprise': '星帆设备有限公司（完全虚构测试企业）',
               'scenario': '20人食品车间采购SF-10前，通过AI搜索了解适配性、总成本和服务（场景已确定）',
               'questions': [
                   {'id': 'Q1', 'text': 'SF-10适合20人食品车间吗，每小时能处理多少？'},
                   {'id': 'Q2', 'text': '河南地区2026年11月采购一台SF-10标准配置，含税含运费多少钱？'},
                   {'id': 'Q3', 'text': 'SF-10是否上门安装，签约后几天可以完成安装？'},
                   {'id': 'Q4', 'text': 'SF-10实际一年耗电多少，年度维护费用多少？'},
                   {'id': 'Q5', 'text': '评估SF-10年度持有成本时，有哪些实际年耗电和维护费依据？'},
                   {'id': 'Q6', 'text': 'SF-10整机质保多长时间？'}]}
    write(base / '示例任务.json', json.dumps(request, ensure_ascii=False, indent=2)+'\n')
    broken = base / '不可读与重复'
    shutil.copytree(clean, broken)
    write(broken / '异常/损坏.docx', 'this is not a docx zip')
    write(broken / '异常/损坏.pdf', '%PDF-1.7\nbroken')
    write(broken / '异常/旧版.doc', 'unsupported legacy office format')
    write(broken / '异常/空白.txt', '')
    (broken / '异常/图片.png').write_bytes(b'\x89PNG\r\n\x1a\nnot-a-real-image')
    (broken / '异常/视频.mp4').write_bytes(b'not-a-real-video')
    (broken / '异常/无效编码.txt').write_bytes(b'\xff')
    pdf(broken / '异常/无正文页.pdf')
    # Includes a formula in an actual workbook, ensuring partial reads are surfaced.
    wb = Workbook()
    wb.active['A1'] = '=1+1'
    wb.save(broken / '异常/公式.xlsx')
    wb.close()
    return clean, broken, base / '示例任务.json'


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('用法: python tests/make_fixtures.py <新的模拟资料目录>')
    print('\n'.join(str(p) for p in create(Path(sys.argv[1]))))
