# 有界文档链

[English](README.md) · 简体中文

v1 支持文本 PDF 的 EUR 物料报价：标题、Currency EUR、Item Quantity Unit price，随后
每行一个物料、数量和单价。币种或数量缺失时，只能通过获准的用户补充输入填写。其他币种、OCR 及通用表格编辑不在本契约范围。合计上限为 EUR 10,000,000,000.00，以保证工作簿缓存金额的精确性。领域代码不依赖
模型提供方或运行时管理接口。

可移植程序提取 PDF 文本、对照来源验证 Markdown 提案、对照已验收 Markdown 检查结构化行、
生成 XLSX，并独立验证单元格、公式、缓存合计和来源摘要。客体提取和生成所需的固定
pypdf/XlsxWriter wheel 由操作员离线准备。原生 spool 入口仅用 Python 标准库，对照操作员
选定的已验收 Markdown（AN_SPOOL_AUX_0）检查 XLSX 候选，输出 result.xlsx 和 verification.json。
依赖归档、镜像、配置、凭据、原始会话和生成文档均保留在私有目录。

使用选定依赖目录运行领域测试，再执行 Loom check/pack/verify 和 export-native-spool-v3。
静态打包不授予执行权限；真实模型与 VM 文档链单独验收，不能由打包检查推断宿主终止、模型
行为或产物保管。依赖遵守各自许可证；requirements.lock.json 记录获取身份，不是安全审计。
