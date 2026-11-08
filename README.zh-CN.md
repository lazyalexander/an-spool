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

## 发布与检查

[目录身份](catalog.json)记录不可变渲染包。渲染器保留历史 `@an-loom/cad-paint-spool` 0.1.0 身份；
Shuttle 导入的 `@an-spool/cad-material-policy` 独立版本化补全指令、外观 kit 规划与历史材质采纳。
源码或策略修改须产生新的审阅版本，不改写旧发布包。

参见[渲染包复现检查](spools/cad-paint/DISTRIBUTION.md)及[策略构建与测试](packages/cad-material-policy/README.md)。
打包复现、host 执行和真实应用验收分别记录。

## 案例 · 机械动画

### 水墨动画与手绘蒸汽机对比

| 水墨动画 | 手绘版本 · 6 秒 |
| --- | --- |
| ![水墨动画](https://raw.githubusercontent.com/lazyalexander/an-agent/d94f574197d8a7f56d30ca78d9cad8d81039d65d/assets/demos/mechanical-ink.gif) | ![手绘蒸汽机](https://raw.githubusercontent.com/lazyalexander/an-agent/d94f574197d8a7f56d30ca78d9cad8d81039d65d/assets/demos/painted-steam-engine.gif) |

后续动画 spool 负责几何、既定运动、外观指令和领域检查。当前发布目录包含 CAD 绘画包，动画打包待完成。
[教学流程与复现证据](https://github.com/lazyalexander/an-agent/blob/d94f574197d8a7f56d30ca78d9cad8d81039d65d/doc/zh-CN/doc/cases.md)。

### 补充案例 · 四缸发动机

<img src="https://raw.githubusercontent.com/lazyalexander/an-agent/d94f574197d8a7f56d30ca78d9cad8d81039d65d/assets/demos/painted-inline-four.gif" alt="四缸发动机" width="420">

40 个 CAD 零件复用手绘流程，完整周期为 8 秒。两段手绘 GIF 为 720 × 405、12 fps 循环预览。
素材和教学说明引用 an-agent 的固定版本。

## 示例：CAD → Krita

把保存的 CAD 版本变成可按零件分层编辑的透明绘画。CAD 是领域打包的示范案例，不限定目录范围。

![分层 CAD 绘画](https://raw.githubusercontent.com/lazyalexander/an-shuttle/a94485bcb348b28d8ce62cabab321b7739167139/examples/cad-paint/sample/vise.png)

[Spool 源码与契约](spools/cad-paint/README.md) ·
[材质策略](packages/cad-material-policy/README.md) ·
[应用配置与验收](https://github.com/lazyalexander/an-shuttle/blob/main/docs/cad-paint.zh-CN.md)

kit 标记 agent 修改或新增的代码、skill 和文件。未修改副本保留 silk 基线标签。修改历史、当前基线匹配、可信度和保留决定分别记录，路径与旧槽位名称不决定标签。

教学包与三阶段宿主复跑参见[机械动画教学链](examples/mechanical-animation/README.md)，发布身份见[教学发布清单](teaching-releases.json)。
