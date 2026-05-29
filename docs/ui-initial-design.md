# Novel-Assistant UI 初步设计

## 1. 产品定位

Novel-Assistant 的 UI 不应做成普通聊天页，也不应先做营销落地页。第一版应直接进入可用的创作工作台，让用户打开后就能管理小说、生成蓝图、查看人物关系、生产章节、审阅质检结果。

产品形态：

```text
小说创作工作台
```

核心用户：

```text
网文作者
AI 辅助创作者
小说工作室策划
需要批量生成和管理长篇内容的内容团队
```

第一版 UI 目标：

```text
让用户看得见生成流程
让用户改得动小说蓝图
让用户查得到人物关系
让用户审得了章节质量
让用户知道系统为什么这样写
```

## 2. 设计原则

### 2.1 工作台优先

首屏直接展示项目状态、当前创作任务、章节进度和图谱摘要。不做大面积宣传页，不做空泛 hero。

### 2.2 内容密度适中

小说项目有大量信息：人物、关系、伏笔、章节、质检。界面需要可扫描，但不能把所有内容同时塞满。采用左中右三栏结构，信息按优先级折叠。

### 2.3 图谱不是装饰

人物关系图、伏笔图、章节事件图都必须服务创作决策。图谱节点点击后应能影响右侧详情和后续生成上下文。

### 2.4 每一步可追踪

LangGraph 执行流需要可视化：用户应能看到当前处于需求分析、蓝图生成、写图谱、章节生成、质检、修订还是回写阶段。

### 2.5 生成结果可编辑

蓝图、人物设定、章节计划、章节正文、质检建议都应可编辑或重新生成。用户不应该只能被动接受 AI 输出。

## 3. 信息架构

推荐第一版页面结构：

```text
App Shell
├── Sidebar 项目导航
│   ├── 小说项目列表
│   ├── 当前小说章节
│   ├── 图谱视图入口
│   └── 设置
├── Main Workspace 主工作区
│   ├── Dashboard 总览
│   ├── Blueprint 小说蓝图
│   ├── Characters 人物与势力
│   ├── Outline 大纲与章节计划
│   ├── Chapter Editor 章节写作与审阅
│   └── Quality Review 质检与修订
└── Inspector 右侧检查器
    ├── 当前图谱上下文
    ├── 节点详情
    ├── 伏笔状态
    ├── 质检问题
    └── 执行日志
```

## 4. 第一版核心页面

### 4.1 Dashboard 项目总览

目的：让用户进入项目后立即知道当前小说写到哪里、系统状态如何、下一步该做什么。

内容：

```text
当前小说标题
题材 / 状态 / 目标章节数 / 已生成章节数
当前阶段：蓝图确认 / 章节生成 / 等待审阅 / 图谱回写完成
最近章节
当前活跃伏笔数量
主要人物数量
质检通过率
下一步操作按钮
```

主要操作：

```text
继续生成下一章
查看小说蓝图
查看人物关系
审阅最新章节
打开执行日志
```

布局建议：

```text
顶部：项目标题 + 状态 + 主操作
中部：章节进度 / 质检摘要 / 图谱摘要
底部：最近事件 / 最近质检问题
```

### 4.2 Blueprint 小说蓝图页

目的：编辑和确认小说方向。

内容：

```text
核心卖点
故事简介
世界观概述
主线冲突
主角成长线
阶段路线
结局方向
风格要求
禁忌内容
```

主要操作：

```text
重新生成蓝图
局部修改
确认蓝图
生成大纲
写入图谱
```

交互建议：

```text
每个蓝图段落可以单独重写。
修改后显示“待同步到图谱”的状态。
确认后才进入章节计划生成。
```

### 4.3 Characters 人物与势力页

目的：管理人物、势力、关系和人物状态。

内容：

```text
人物列表
人物详情
人物目标 / 动机 / 弱点 / 成长线
当前状态
所属势力
关系列表
关系图谱
```

主要操作：

```text
新增人物
修改人物状态
新增关系
变更关系状态
查看该人物参与的事件
查看该人物相关伏笔
```

图谱要求：

```text
节点类型用颜色区分，但必须同时有文字标签。
点击节点后右侧 Inspector 展示详情。
人物关系图必须提供列表视图作为无障碍替代。
```

### 4.4 Outline 大纲与章节计划页

目的：管理长线剧情和每章目标。

内容：

```text
卷级大纲
阶段目标
章节列表
每章目标
每章出场人物
每章必须推进事件
每章伏笔动作
每章禁止事项
```

主要操作：

```text
生成章节计划
调整章节顺序
锁定关键章节
查看章节关联图谱
开始生成该章
```

布局建议：

```text
左侧：章节列表
中间：当前章节计划
右侧：关联人物 / 伏笔 / 世界规则
```

### 4.5 Chapter Editor 章节编辑页

目的：生成、编辑和审阅章节正文。

内容：

```text
章节计划
图谱上下文摘要
章节正文编辑器
生成状态
质检入口
修订记录
```

主要操作：

```text
生成草稿
重新生成
局部重写
质检章节
应用修订
确认终稿
回写图谱
```

编辑器要求：

```text
正文区优先可读性，宽度控制在舒适阅读范围。
质检问题可以定位到相关段落。
右侧显示“本章使用的上下文”，避免用户不知道 AI 为什么这样写。
```

### 4.6 Quality Review 质检页

目的：让用户知道章节哪里有问题，以及系统准备怎么修。

内容：

```text
总分
是否通过
阻断问题
维度得分
问题证据
修改建议
修订模式
修订前后对比
```

质检维度：

```text
人设一致性
世界观一致性
人物关系一致性
事件因果
伏笔推进
大纲对齐
节奏
重复表达
AI 味
敏感内容
```

主要操作：

```text
自动修订
只修复选中问题
忽略低风险问题
查看证据
确认终稿
```

## 5. 图谱视图设计

第一版支持三种图谱：

### 5.1 人物关系图

节点：

```text
Character
Faction
Location
```

关系：

```text
ALLY_OF
ENEMY_OF
RELATED_TO
BELONGS_TO
LOCATED_AT
```

交互：

```text
点击人物 -> Inspector 显示人物详情
点击关系 -> 显示关系说明、强度、起始章节、当前状态
筛选：主角相关 / 反派相关 / 指定势力 / 活跃关系
```

### 5.2 伏笔追踪图

节点：

```text
Hook
Chapter
Event
```

关系：

```text
PLANTED_IN
ADVANCED_IN
RESOLVED_IN
```

交互：

```text
按状态筛选：open / planted / advancing / resolved
按重要性筛选：low / medium / high / critical
点击伏笔 -> 查看埋设、推进、回收记录
```

### 5.3 章节时间线图

节点：

```text
Chapter
Event
Character
Hook
```

关系：

```text
CONTAINS_EVENT
INVOLVES
ADVANCES_HOOK
RESOLVES_HOOK
```

交互：

```text
按章节查看事件链
按人物查看出场轨迹
按伏笔查看推进轨迹
```

图谱可访问性要求：

```text
网络图不能作为唯一表达。
必须同时提供列表视图：
节点 A -> 关系 -> 节点 B -> 来源章节 -> 状态。
```

## 6. 执行流可视化

在页面底部或右侧提供 LangGraph 执行状态。

状态节点：

```text
需求分析
蓝图生成
人物生成
世界观生成
图谱写入
大纲生成
章节计划
上下文检索
正文生成
质检
修订
事实抽取
图谱回写
完成
```

状态样式：

```text
未开始：muted
进行中：primary + progress
成功：success
等待人工确认：accent
失败：destructive
跳过：muted outline
```

用户应能点击某个执行节点查看：

```text
输入摘要
输出摘要
耗时
错误信息
重试次数
关联产物
```

## 7. 视觉系统建议

设计方向：安静、专业、创作工具感、数据可扫描。

不建议：

```text
大面积营销 hero
装饰性渐变球
过度玻璃拟态
满屏卡片嵌套
全部使用单一紫蓝色
过度米色/奶油色主题
```

推荐色彩：

```text
Background: #F7F8FA
Surface: #FFFFFF
Surface Alt: #F1F5F9
Foreground: #111827
Muted Text: #64748B
Primary: #2563EB
Secondary: #0F766E
Accent: #D97706
Success: #16A34A
Warning: #D97706
Danger: #DC2626
Border: #E5E7EB
Focus Ring: #2563EB
```

说明：

```text
Primary 用于主操作和当前流程。
Secondary 用于图谱与关系。
Accent 用于人工确认和待处理状态。
Danger 只用于阻断问题和 destructive 操作。
```

字体建议：

```text
UI 字体：Inter / system-ui
代码和结构化数据：JetBrains Mono / Fira Code
正文编辑器：Noto Serif SC 或系统宋体类字体
```

字号层级：

```text
页面标题：24-28px
区块标题：16-18px
正文 UI：14-16px
辅助说明：12-13px
章节正文：17-18px，line-height 1.7
```

## 8. 组件清单

第一版组件：

```text
AppShell
Sidebar
ProjectSwitcher
StatusBadge
WorkflowStepper
BlueprintEditor
CharacterList
CharacterInspector
GraphCanvas
GraphFallbackTable
OutlineTree
ChapterPlanPanel
ChapterEditor
QualityScorePanel
QualityIssueList
RevisionDiffViewer
RunLogPanel
ConfirmDialog
Toast
```

图标建议使用 Lucide：

```text
BookOpen
Users
Network
GitBranch
FileText
CheckCircle
AlertTriangle
RefreshCw
Play
Pause
Settings
Search
Eye
Edit
Save
Download
```

## 9. 第一版页面流

### 9.1 新建小说

```text
输入创意
-> 系统生成需求解析
-> 用户确认或补充
-> 生成蓝图
-> 生成角色与世界观
-> 图谱预览
-> 用户确认
-> 生成大纲
```

### 9.2 生成章节

```text
选择下一章
-> 查看章节计划
-> 查看图谱上下文
-> 点击生成草稿
-> 查看正文
-> 运行质检
-> 应用修订
-> 确认终稿
-> 回写图谱
```

### 9.3 查看图谱

```text
打开人物关系图
-> 点击人物
-> 查看状态和关系
-> 查看相关章节和事件
-> 必要时编辑人物状态
-> 保存并影响后续生成
```

## 10. 第一版 UI 不做的内容

暂不做：

```text
多用户登录
支付订阅
公开作品市场
复杂权限系统
移动端完整适配
封面生成
EPUB 高级排版
多模型配置中心
大型数据分析看板
```

## 11. 推荐实现路线

后端 MVP 跑通后，按以下顺序做 UI：

```text
1. FastAPI 包装后端能力
2. Vite + React + TypeScript 项目
3. AppShell + Sidebar + Dashboard
4. Blueprint Editor
5. Chapter Editor + Quality Review
6. GraphCanvas + Fallback Table
7. WorkflowStepper + RunLogPanel
```

第一版 UI 只需要服务一件事：

```text
让用户能完整操作一章生成闭环。
```

## 12. 验收标准

UI 第一版通过标准：

```text
用户能创建小说项目。
用户能查看和确认小说蓝图。
用户能查看人物关系图。
用户能生成第一章。
用户能看到质检结果。
用户能应用修订。
用户能看到图谱回写后的变化。
所有关键操作都有 loading / success / error 状态。
网络图有列表替代视图。
375px 宽度无横向滚动。
键盘可访问核心按钮和表单。
```
