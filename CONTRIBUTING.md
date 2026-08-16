# 贡献指南

感谢你对 health-report-trend-analysis 的关注。

## 如何贡献

1. **报告问题**：提交 Issue，附上报告格式样例（脱敏后）与报错日志
2. **补充指标字典**：新医院/新报告的指标名未收录时，在 `scripts/indicator_dict.py` 的 `NAME_MAP` 补一行映射；需权威解读则补 `INDICATOR_META` 条目（引用默沙东诊疗手册/丁香医生/中国指南）
3. **增强 OCR**：改进扫描件/照片提取准确率（参考 `references/OCR方法学.md`）

## 隐私红线（强制）

- **禁止**在 SKILL.md、scripts、references 中提交任何真实个人健康数据、身份信息（姓名/证件号/电话/地址）、体检编号、医院实名
- 解析口径/参考范围等示例数据必须**脱敏**（用"某医院""某指标"等泛化表述）
- 数据驱动优先：任何个体数值都应运行时从数据文件生成，而非硬编码在代码中

## 提交规范

- 新增脚本须支持 `WORK_DIR` / `REPORT_DIR` / `DATA_DIR` 环境变量（不硬编码绝对路径）
- 语法检查：`python -m py_compile scripts/*.py`
- 隐私扫描：提交前 grep 个人路径/身份信息/健康数值，确保零命中

## 许可证

贡献默认遵循项目 MIT License。
