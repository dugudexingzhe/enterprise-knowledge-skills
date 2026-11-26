"""Fixed test oracle for validator tests, NOT an automated semantic diagnosis engine."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import geo_gap as g


def assessment(run, incomplete=False):
    m = g.read_json(Path(run) / 'manifest.json')
    corpus = list(g.chunks(run, m))
    def evidence(text):
        c = next(c for c in corpus if text in c['text'])
        return {'chunk_id': c['id'], 'quote': text}
    def req(rid, key, knowledge, criteria, status, rationale, recommendation, refs=(), priority='P1', terms=()):
        return {'id': rid, 'key': key, 'knowledge': knowledge, 'criteria': criteria,
                'status': status, 'rationale': rationale, 'recommendation': recommendation,
                'evidence': list(refs), 'priority': priority, 'search_terms': list(terms)}
    def energy():
        return req('R1', 'SF-10|实际工况|年耗电', '实际年耗电量与工况',
                   '需要实测年耗电、运行时长和工况；额定功率不能替代', '部分',
                   '只有额定功率及不得等同年耗电的说明，缺实际年耗电记录。',
                   '请技术/客户成功提供SF-10实际工况、运行时长、年耗电实测记录及测量方法。',
                   [evidence('3'), evidence('设备额定功率不等于客户实际年耗电量。')])
    def maintenance():
        return req('R2', 'SF-10|年度|维护费', '年度维护费用', '需年度金额、包含项目和适用工况',
                   '无法判断' if incomplete else '缺失',
                   '可读资料未发现维护费记录；有未读资料，不能确认缺失。' if incomplete else '全量可读资料未发现年度维护费依据。',
                   '请售后提供年度维护费、耗材/人工明细、计价条件和对应原始记录。',
                   terms=['年度维护费用', '保养费', '耗材', '维修预算'])
    quote_a = next(c['text'] for c in corpus if '28000' in c['text'])
    quote_b = next(c['text'] for c in corpus if '32000' in c['text'])
    q = [
        {'id': 'Q1', 'intent': '判断车间适配与产能。', 'requirements': [
            req('R1', 'SF-10|20人食品车间|适配', '适用车间', '须明确20人食品车间适用', '充分',
                '资料有对应适用范围。', '本项无需补充，保留来源。', [evidence('SF-10适用于20人及以下食品车间。')]),
            req('R2', 'SF-10|额定|产能', '额定处理量', '需型号、数值及单位', '充分', '资料给出型号和额定处理量。',
                '本项无需补充，保留来源。', [evidence('SF-10的额定处理量为每小时100公斤。')])]},
        {'id': 'Q2', 'intent': '确认同口径采购预算。', 'requirements': [
            req('R1', 'SF-10|河南2026-11标准含税含运|报价', '同口径含税含运报价', '型号、地区、有效期、配置、税运和金额一致',
                '冲突', '同范围标准配置报价分别为28000和32000元/台，未确定哪份有效。',
                '请销售负责人确认有效报价及适用条件，提供签核价目表；保留两份原文。',
                [evidence(quote_a), evidence(quote_b)], priority='P0')]},
        {'id': 'Q3', 'intent': '判断是否提供安装以及交付等待时间。', 'requirements': [
            req('R1', 'SF-10|安装|服务', '安装服务', '需明确上门安装', '充分', '资料明确提供上门安装。',
                '本项无需补充，保留来源。', [evidence('本模拟企业为SF-10提供上门安装服务。')]),
            req('R2', 'SF-10|签约后|安装周期', '签约至安装完成的周期', '需起算条件及天数',
                '无法判断' if incomplete else '缺失', '可读资料未发现安装周期，未读资料仍待核查。' if incomplete else '全量资料没有安装完成时限。',
                '请交付负责人补充签约/付款/现场条件的起算要求、安装天数及例外。', terms=['安装周期', '交付天数', '完成安装'])]},
        {'id': 'Q4', 'intent': '评估年度运行和维护成本。', 'requirements': [energy(), maintenance()]},
        {'id': 'Q5', 'intent': '核对年度持有成本的可验证依据。', 'requirements': [energy(), maintenance()]},
        {'id': 'Q6', 'intent': '判断整机质保时长。', 'requirements': [
            req('R1', 'SF-10|整机|质保期', '整机质保时长', '需型号、整机范围及月数', '充分', '售后条款明确整机质保12个月。',
                '本项无需补充，保留来源。', [evidence('SF-10整机质保12个月。')])]},
    ]
    return {'request_sha256': m['request_sha256'], 'reviewed_chunks': [c['id'] for c in corpus],
            'questions': q, 'confirmations': ['请企业确认两份同条件报价的有效版本和适用条件，不以文件新旧自动裁决。']}
