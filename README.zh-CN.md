# an-spool

[English](README.md) · 简体中文

集中维护已验收的领域 spool：源码、知识、技能、指令、领域测试与固定版本发布包。
运行实例由 an-agent 托管。

## 分工

- **an-spool**：领域行为和业务验收规则。
- **an-loom**：开发准备、校验与打包。
- **an-agent**：任务权限、调度、外部 harness 监督、生命周期和产物保管。
- **an-shuttle**：应用连接、交互与产物交付。

本仓库不增加运行器、调度器或模型循环。发布基线为 **silk**；获准修改或新增的运行内容标为 **kit**。
指令保持受保护，标签不授予权限。凭据、模型事件、机器配置和用户产物不进入本仓库。

## 示例：CAD → Krita

把保存的 CAD 版本变成可按零件分层编辑的透明绘画。CAD 是领域打包的示范案例，不限定目录范围。

![分层 CAD 绘画](https://raw.githubusercontent.com/lazyalexander/an-shuttle/a94485bcb348b28d8ce62cabab321b7739167139/examples/cad-paint/sample/vise.png)

[Spool 源码与契约](spools/cad-paint/README.md) ·
[材质策略](packages/cad-material-policy/README.md) ·
[应用配置与验收](https://github.com/lazyalexander/an-shuttle/blob/main/docs/cad-paint.zh-CN.md)

## 发布与检查

[目录身份](catalog.json)记录不可变渲染包。渲染器保留历史 `@an-loom/cad-paint-spool` 0.1.0 身份；
Shuttle 导入的 `@an-spool/cad-material-policy` 独立版本化补全指令、外观 kit 规划与历史材质采纳。
源码或策略修改须产生新的审阅版本，不改写旧发布包。

参见[渲染包复现检查](spools/cad-paint/DISTRIBUTION.md)及[策略构建与测试](packages/cad-material-policy/README.md)。
打包复现、host 执行和真实应用验收分别记录。
