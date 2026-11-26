# 企业知识库梳理与GEO知识缺口诊断 Skills

把企业分散的产品资料、证照报告、客户反馈和业务经验，整理为有来源、可核对、能继续补充的知识准备成果。

本仓库提供两套已有成果，共6个Skill：一套覆盖材料准备到入库验收的五步工作流，一套专注高价值GEO场景下的知识缺口诊断。二者可以分别使用，不需要一次运行全部技能。

## 先选你要解决的问题

| 你现在的情况 | 使用哪套 |
|---|---|
| 刚接触客户，需要判断重点收什么、资料在哪里、怎样整理 | 客户知识库梳理五步工作流 |
| 已有材料，要检查格式、内容、证据、矛盾，再访谈补齐 | 客户知识库梳理五步工作流 |
| 已确定一家企业、一个高价值GEO场景和5—10个典型用户问题，需要分析现有资料能否回答 | GEO高价值场景知识缺口诊断 |

## 方案一：客户知识库梳理五步工作流

首批行业模板覆盖制造、门店服务、专业服务。客户侧接收一张汇总准备清单，内部台账由交付方维护。

| Skill | 工作 | 文件入口 |
|---|---|---|
| `kb-client-plan` | 企业画像、行业重点、材料准备清单与来源调查 | [SKILL.md](client-knowledge-workflow/技能/kb-client-plan/SKILL.md) |
| `kb-format-check` | 提交规范、文件可读性、Excel图文混排等结构风险 | [SKILL.md](client-knowledge-workflow/技能/kb-format-check/SKILL.md) |
| `kb-content-audit` | 六类内容、证据、证照、照片、客户反馈与矛盾检查 | [SKILL.md](client-knowledge-workflow/技能/kb-content-audit/SKILL.md) |
| `kb-knowledge-interview` | 找到微信、回访与人员经验，定向访谈、整理FAQ候选 | [SKILL.md](client-knowledge-workflow/技能/kb-knowledge-interview/SKILL.md) |
| `kb-acceptance` | 资料预验收、实际平台解析/问答检查与更新交接 | [SKILL.md](client-knowledge-workflow/技能/kb-acceptance/SKILL.md) |

五步沿用材料、问题、证据、知识和验收编号。收集前先找来源，质检后再围绕缺口访谈。保留原文与证据，待确认内容不自动转为正式知识。

支持按需检查产品与服务、市场与价格、品牌与公司、客户与反馈、竞争与行业、合规与红线。多工作表本身不判不合格；图片、公式、合并或隐藏内容作为待复核风险信号。专利、检测报告和其他证照按类型、对象、状态与用途分别核对，不能只看编号或套统一有效期。

安装提示：

> 请从 https://github.com/dugudexingzhe/enterprise-knowledge-skills/tree/main/client-knowledge-workflow/技能 安装五个知识库梳理Skill，分别保留各自的references、agents和scripts，不要只复制SKILL.md。

也可以仅安装需要的一个技能目录。具体安装位置按当前工具的Skill管理方式选择，已有同名目录先核对。

开始使用：

```text
使用 $kb-client-plan。
公司：【名称】；城市或官网：【如已知】；主营：【业务】。
本次优先用于：【GEO公开内容/内部销售/客服/培训】。
结合已有资料生成有针对性的准备清单，说明为什么需要、怎样提交、哪些可后补。
不清楚的企业事实保留待确认，不要求客户重复填多份表。
```

收到材料后按需调用其余技能；实质检查以能访问的原件和工具为准。资料未提供时，不生成虚假的质检通过结果。

- [客户填写示例](client-knowledge-workflow/共享资源/客户填写示例.md)
- [项目工作册模板](client-knowledge-workflow/共享资源/项目工作册模板.md)
- [三类虚构样本走查](client-knowledge-workflow/试运行样本/三类样本走查结果.md)
- [平台与核验来源](client-knowledge-workflow/共享资源/平台与核验来源.md)

## 方案二：GEO高价值场景知识缺口诊断

输入：**1家企业、1个已确定的高价值GEO场景、5—10个典型用户问题，以及用户授权的一个本地资料文件夹和全部子文件夹。**

先全量清点、分批提取，再由Agent阅读和分析，逐问题输出用户意图、所需知识、来源定位、覆盖状态、补充建议和优先级，并去重汇总共性缺口。状态包括充分、部分、缺失、冲突、无法判断；无法读取不直接判知识缺失。

该Skill只做诊断，不重新选场景、不修改客户原件、不录入知识库、不生成或发布营销内容。

安装提示：

> 请从 https://github.com/dugudexingzhe/enterprise-knowledge-skills/tree/main/geo-knowledge-gap-diagnosis 安装geo-knowledge-gap-diagnosis，保留脚本、模板和参考资料。

开始使用：

```text
使用 $geo-knowledge-gap-diagnosis。
企业：【名称】
已确定的高价值GEO场景：【场景原话】
典型用户问题：【列出5—10个问题，保留原话】
授权读取资料根目录：【实际本地路径，包括全部子目录】
输出目录：【资料树之外的新目录】
只做诊断，保留全部来源、无法读取项和待确认问题。
```

详细命令及复现方法见[使用说明](geo-knowledge-gap-diagnosis/README.md)。

## 环境与验证

技能需要支持读取SKILL.md和本地工具执行的Agent环境。脚本不替代Agent的业务判断，也没有单独运行便自动完成全部语义审核的承诺。

- 五步工作流的辅助预检使用Python 3.10+标准库。
- 场景缺口诊断使用Python 3.10+；PDF/XLSX解析依赖[requirements.txt](geo-knowledge-gap-diagnosis/requirements.txt)。
- 五步工作流原版完成14项自动测试及三类虚构材料作者走查；场景缺口诊断原版完成27项测试，其中26通过、1项符号链接测试因权限跳过。
- 原版Codex显式加载与模拟执行有记录；Claude Code、WorkBuddy以及知识库平台实际导入效果未在本仓库发布前统一验证。共同文件格式不等于所有平台运行通过。
- 图片、音视频、扫描件、复杂Office存在明确读取限制；见各技能规则。保留未完成项，不把技术成功包装成真实客户验收。

本次公开分发版复测记录见[发布检查](docs/发布检查.md)。

## 试用与反馈

欢迎通过Issues反馈触发方式、预期结果、实际表现和脱敏的最小复现样本。不要在公开Issue里提交客户原件、完整聊天、联系方式或账号凭证。

公开仓库只包含技能、脚本、模板和明确虚构的测试材料；原开发环境路径、真实客户材料、运行提取结果和内部协作笔记不在发布范围内。
