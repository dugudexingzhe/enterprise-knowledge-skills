#!/usr/bin/env python3
"""Build five self-contained skills and a portable archive; optional non-overwriting install."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
COMMON = '通用规则与交接.md'
BOOK = '项目工作册模板.md'
SOURCES = '平台与核验来源.md'
EXAMPLE = '客户填写示例.md'
SKILLS = {
    'kb-client-plan': ('企业画像与材料规划', '根据企业主营与使用场景，生成客户准备清单、行业重点和资料寻找路径',
                       [COMMON, BOOK, EXAMPLE, '三类行业与收集清单.md']),
    'kb-format-check': ('提交规范与格式预检', '提供知识库材料整理示例，检查文件可读性、表格结构和图文解析风险',
                        [COMMON, BOOK, EXAMPLE, SOURCES, '提交规范与格式检查.md']),
    'kb-content-audit': ('内容与证据质检', '检查六类业务资料、证照报告、照片与客户记录，生成有依据的补件单',
                         [COMMON, BOOK, SOURCES, '六类内容质检.md', '证据与证照核验.md']),
    'kb-knowledge-interview': ('隐性知识挖掘与访谈', '寻找微信回访等分散经验，围绕质检缺口访谈并整理带来源的FAQ候选',
                               [COMMON, BOOK, EXAMPLE, SOURCES, '隐性知识与访谈.md']),
    'kb-acceptance': ('入库验收与更新交接', '通过真实业务问题检查知识解析、回答与引用，区分预验收和平台实测',
                      [COMMON, BOOK, SOURCES, '入库验收与更新.md']),
}


def hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files_in(root):
    return sorted(p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts)


def manifest(root):
    return {p.relative_to(root).as_posix(): hash_file(p) for p in files_in(root)}


def validate_links(skill):
    for path in skill.rglob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            if '://' in target or target.startswith('#'):
                continue
            resolved = (path.parent / target.split('#')[0]).resolve()
            if not resolved.is_relative_to(skill.resolve()) or not resolved.exists():
                raise ValueError('引用缺失或越出技能目录：%s -> %s' % (path, target))


def build():
    for name, (display, description, references) in SKILLS.items():
        skill = ROOT / '技能' / name
        if not (skill / 'SKILL.md').is_file():
            raise ValueError('技能入口缺失：' + name)
        (skill / 'references').mkdir(exist_ok=True)
        for filename in references:
            shutil.copyfile(ROOT / '共享资源' / filename, skill / 'references' / filename)
        (skill / 'agents').mkdir(exist_ok=True)
        assert 25 <= len(description) <= 64
        prompt = '使用 $%s，结合已有资料和本次用途完成%s，明确未核实范围。' % (name, display)
        content = 'interface:\n  display_name: %s\n  short_description: %s\n  default_prompt: %s\n' % tuple(
            json.dumps(s, ensure_ascii=False) for s in (display, description, prompt))
        (skill / 'agents' / 'openai.yaml').write_text(content, encoding='utf-8', newline='\n')
        validate_links(skill)
    return len(SKILLS)


def install(destination):
    destination = destination.expanduser().resolve()
    for name in SKILLS:
        source = (ROOT / '技能' / name).resolve()
        target = destination / name
        if target.is_relative_to(source) or source.is_relative_to(target):
            raise ValueError('安装目标与技能源重叠，请选择独立的技能目录')
    # Check every existing destination before making any changes.
    for name in SKILLS:
        target = destination / name
        if target.is_symlink() or (target.exists() and (not target.is_dir() or manifest(target) != manifest(ROOT / '技能' / name))):
            raise ValueError('同名技能内容不同，未覆盖：' + str(target))
    installed = []
    for name in SKILLS:
        target = destination / name
        if not target.exists():
            shutil.copytree(ROOT / '技能' / name, target, ignore=shutil.ignore_patterns('__pycache__'))
        if manifest(target) != manifest(ROOT / '技能' / name):
            raise ValueError('安装后校验失败：' + name)
        installed.append(str(target))
    return installed


def archive():
    entries = manifest(ROOT)
    entries.pop('文件校验清单.json', None)
    (ROOT / '文件校验清单.json').write_text(json.dumps(entries, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    output = ROOT.parent / (ROOT.name + '.zip')
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as result:
        for path in files_in(ROOT):
            result.write(path, ROOT.name + '/' + path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(output) as result:
        if result.testzip() is not None:
            raise ValueError('压缩包完整性检查失败')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install-dir', type=Path)
    args = parser.parse_args()
    count = build()
    installed = install(args.install_dir) if args.install_dir else []
    output = archive()
    print(json.dumps({'技能数': count, '压缩包': str(output), '已安装并校验': installed}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as exc:
        print('构建/安装未完成：' + str(exc), file=sys.stderr)
        sys.exit(2)
