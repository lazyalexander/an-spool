# 文档链 v1

[English](contract.md) · 简体中文

保持一个主会话，读取获准的源文本并保留全部行。Markdown 管道表仅包含 Item、Quantity、
Unit price (EUR) 三列。数量为正整数，单价为非负 EUR 十进制且最多两位小数；必须明确币种
为 EUR。来源 requires_clarification 非空时，必须通过获准的补充输入取得用户回答。事实缺失时询问，不补造数据，也不把合计当作数据行。表格外只允许可选的来源标题和 Currency: EUR。Markdown 在宿主验收前仅为提案。

下一轮通过宿主产物引用读取已验收 Markdown，提出包含 source_sha256 和 rows 的 JSON。
每行仅包含 item、quantity 和 unit_price。source_sha256 来自已验收 Markdown 字节，
不得从路径推断身份。程序计算金额和合计，宿主验证工作簿后交付。不启用模型子 agent。
