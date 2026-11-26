# 客户知识库梳理五步工作流

本目录包含五个可独立安装的Skill、共享规则与模板、虚构样本和辅助脚本。入口见[仓库使用说明](../README.md)。

目录：`技能/`为自包含技能，`共享资源/`为维护源，`试运行样本/`为虚构桌面走查，`scripts/`为构建与测试。维护时修改共享资源后运行`python scripts/构建与安装.py`，会同步各技能的参考副本并生成压缩包；只有指定`--install-dir`才执行安装。不同内容的同名技能会停止，避免自动覆盖。

自动预检：

```text
python 技能/kb-format-check/scripts/preflight.py --input "客户资料目录" --output "资料树外的新报告.json"
```

这是本地技术预检，不代替内容、视觉、证据核验或平台实测。

复现自动测试：

```text
python -X utf8 scripts/test_preflight.py
```
