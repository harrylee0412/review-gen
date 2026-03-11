# review-gen

`review-gen` 是一套面向管理学、战略、创业与创新研究的长期文献综述工具包。它把“检索文献、构建综述语料、收集原文、PDF 转 Markdown、分块检索、规划综述框架、批准计划、生成写作提示词、控制写作规范”串成一条稳定的多 agent 工作流。

## 平台模式

这次版本已经改成平台无关的使用方式。核心脚本不再依赖固定的 Windows 路径，使用时只需要替换三个占位符：

- `<workflow-python>`：能运行这些脚本的 Python 解释器
- `<review-gen-home>`：`review-gen` 包所在目录
- `<review-workspace>`：某个具体综述项目的工作区目录

也就是说，同一套脚本逻辑可以在 Windows PowerShell、macOS 终端、Linux shell 中使用，区别只在于你实际填入的路径不同。

## 工具包包含什么

本工具包包含四个 skills：

- `openalex-ajg-insights`
  负责文献检索、原始结果留存、语料库合并去重、全文清单生成、PDF 转 Markdown、Markdown 分块与检索。
- `management-review-planner`
  负责在正式写作前进入计划模式，生成并持续打磨综述框架。
- `management-review-writer`
  负责把已整理好的文献证据和已批准的框架转成正式综述正文。
- `review-orchestrator`
  负责判断当前项目所处阶段、决定下一步该调用哪个 subagent、并在用户明确口头同意后自动批准或重新打开计划。

## 规划逻辑怎么改了

planner 不再默认假设只有一个 `focal concept`。现在的逻辑是：

1. 根据用户给出的主题拆解出需要处理的构念、概念、机制和关系
2. 先确定这些内容分别需要怎样定义和界定边界
3. 再生成章节级框架
4. 最后进一步生成段落级蓝图

所以无论是单概念、双概念关系、中介机制、调节逻辑，planner 都不会先套死某一种模板，而是先基于主题和文献给用户一个可打磨的框架。

## 计划打磨与存档机制

这是这次升级的重点。

现在每次 planner 生成或重写 `review_plan.md` 时，都会同时在 `07_plan/history/` 下创建一个带时间戳的架构存档点，方便查看每一轮框架迭代。批准 plan 或重新打开 plan 时，orchestrator 也会再额外留一个带时间戳的状态存档。

也就是说，后续你可以同时拥有：

- 当前正在执行的活跃版 `review_plan.md`
- 每一次打磨留下的历史版 `07_plan/history/*.md`

这样就能清楚追踪框架是如何变化的。

## 当前推荐工作流

1. 用 `openalex-ajg-insights` 构建语料库
2. 用 `management-review-planner` 生成第一版 `review_plan.md`
3. 和用户打磨章节与段落蓝图
4. 每轮修改自动生成时间戳架构存档
5. 用户口头确认后，由 `review-orchestrator` 自动批准计划
6. 再用 `management-review-writer` 按已批准框架执行正文写作

## 目录结构

```text
review-gen/
├── README_zh.md
└── skills/
    ├── openalex-ajg-insights/
    ├── management-review-planner/
    ├── management-review-writer/
    └── review-orchestrator/
```

## 建议的使用顺序

建议先用 `openalex-ajg-insights` 完成检索、筛选和全文准备，再由 `review-orchestrator` 判断是否进入 planner 或 writer。长期使用时，优先让 orchestrator 负责路由和批准控制。
