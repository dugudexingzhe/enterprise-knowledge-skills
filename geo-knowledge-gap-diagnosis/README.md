# GEO高价值场景知识缺口诊断 V1.0

输入一家公司、一个已确定场景、5—10个问题和一个授权的本地资料目录。递归清点全部子目录、分批读取，并在Agent分析后生成可溯源的综合知识缺口报告。正式行为边界以[SKILL.md](SKILL.md)为准。

本公开分发目录保留原有技能、脚本、模板、参考和虚构测试样本；原开发机器生成的manifest、提取文本、诊断运行结果和日志未公开，避免传播本地路径。可在自己的临时目录复现，未改写原开发包。

## 执行

根据[任务输入模板](assets/任务输入模板.json)准备输入。Python 3.10+，PDF/XLSX依赖见[requirements.txt](requirements.txt)。

```text
python scripts/geo_gap.py scan --source "授权资料根目录" --request "任务.json" --out "资料树外的新运行目录" --batch-size 25
python scripts/geo_gap.py review-packs --run "运行目录"
```

随后让Agent逐包阅读全部资料，按照[判断规则](references/判断与数据结构.md)与[分析模板](assets/诊断分析模板.json)填写分析，最后执行：

```text
python scripts/geo_gap.py finalize --run "运行目录" --assessment "分析.json"
```

scan不会自动产生语义判断；仅有文件清单不能当作完成诊断。失败或不支持的文件登记并保留，不能悄悄跳过或一律判知识缺失。输出包括诊断报告、结果JSON、文件清单、未完整读取清单与扫描异常。

## 虚构样本与测试

```text
python tests/make_fixtures.py "新的模拟资料目录"
python tests/run_tests.py --out "新的测试结果目录"
```

自动测试创建独立临时样本。诊断意图、充分性、冲突口径和共性缺口仍需Agent/人工审阅，固定测试决策不能作为模型准确率。

原版验证范围及未验证项见[平台验证](references/平台验证.md)；格式能力见[格式与异常](references/格式与异常.md)。本次公开分发复测见[发布检查](../docs/发布检查.md)。真实客户资料与跨平台运行尚需分别测试。
