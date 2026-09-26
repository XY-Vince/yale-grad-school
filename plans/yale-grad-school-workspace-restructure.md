# (Yale) Grad School Workspace Hub — 重构实施记录 (Implementation Record)

**Date**: 2026-09-25  
**Target Repository**: `yale-grad-school` (formerly `GradQuest`)  
**Branch**: `codex/rebrand-yale-grad-school` (isolated worktree)  
**Status**: Phase 0 ~ Phase 3 已完成 (Implementation Complete)

---

## 1. 架构定位与两级体系

仓库已正式确立为 **(Yale) Grad School Workspace Hub**，统筹耶鲁博士学业事务、学术里程碑、自主研究智能体（Agent）工具链与科研模拟游戏：

```
yale-grad-school/                  <-- (Yale) Grad School Hub
├── README.md                      <-- Hub 概述：耶鲁博士主页、子模块索引、保密与合规规则
├── AGENTS.md                      <-- 根指令：Hub 路由、FERPA/隐私边界、各子项目权威源
├── plans/                         <-- 跟踪重构实施方案与历史记录
│   └── yale-grad-school-workspace-restructure.md
├── docs/                          <-- GradQuest @ Yale 游戏子模块 (PhD Simulator)
│   ├── index.html                 <-- 游戏核心单文件（标题更新为 'GradQuest @ Yale'，保存 key 保持不变）
│   ├── README.md                  <-- 对齐 V2.59.2 纯前端架构现实
│   ├── CONTRIBUTING.md            <-- 明确单文件纯前端贡献规范
│   └── AGENTS.md                  <-- 游戏子项目工程与机制指南
├── .agents/                       <-- 研究与工程智能体基础设施
│   ├── rules/                     <-- 工程规范、措辞要求与行为守则
│   ├── skills/                    <-- 自主研究技能（如 verify-public-person-profile）
│   └── workflows/                 <-- 研发与运行工作流
├── tests/                         <-- 浏览器集成测试与单元回归测试集
└── data/                          <-- 历史/实验性规则与辅助数据（非运行时核心）
```

### 确认的命名规范
- **顶层工作区与仓库名**：`(Yale) Grad School`
- **仓库 Slug 与目录标识符**：`yale-grad-school`
- **交互式模拟游戏子项目**：`GradQuest @ Yale`（副标题：`PhD Life Simulator`）
- **保持不变的内部标识符**：
  - 本地存档存储键继续使用 `gradquest_save`，避免引入不必要的 key 迁移分支，并由回归测试验证。
  - Python 内部类名（如 `GradQuestPlaytester` 等）保持不变。
  - 历史报告与归档目录（`archive/`、`test reports/`、历史 CHANGELOG）保留历史事实，不作全局篡改。

---

## 2. 公开与保密边界 (FERPA & Academic Privacy)

在根目录 `README.md` 与根 `AGENTS.md` 中严格规定：
1. **学生隐私与教育记录合规 (FERPA)**：严禁向本仓库提交任何涉及学生个人可识别信息（PII）、课程作业成绩、学生沟通邮件或教学考核记录。
2. **敏感科研与个人记录**：严禁提交未公开的实验室敏感原始数据、私密导师通讯、个人学位审计敏感记录或各类 API 令牌/凭证。
3. **物理隔离**：真正的私密文件必须保存在独立的私有仓库或学校受保护存储设备中，绝不能仅依靠 `.gitignore`。

---

## 3. 子项目权威源划分 (Source of Truth)

- **全局 Hub 权威**：根目录 `AGENTS.md` 统筹工作区全局路由、隐私合规与跨模块协作。
- **游戏运行时权威**：`docs/index.html` 是游戏运行逻辑与状态转移的唯一权威源；`data/` 定位为历史/实验性规则与测试辅助数据。
- **Agent 技能权威**：各独立研究技能由对应目录下的 `.agents/skills/*/SKILL.md` 独立定义。

---

## 4. 实施记录与执行结果

### Phase 0: 安全加固与分支隔离 (已完成)
- [x] **Phase 0A 凭据脱敏**：清除了 `git remote origin` 中的明文 GitHub PAT，远程地址变更为无凭据 HTTPS 地址 `https://github.com/XY-Vince/GradQuest.git`。
- [x] **Phase 0B 分支工作区隔离**：利用 `git worktree add -b codex/rebrand-yale-grad-school .worktrees/rebrand-yale-grad-school main` 创建独立工作树，完全保留了主工作树 `feat/v5-alpha-integration` 分支上 7 个与改名无关的未提交改动。

### Phase 1: 游戏 UI 展现与存档稳定性 (已完成)
- [x] 更新 `docs/index.html`：
  - 页面 `<title>` 变更为 `🎓 GradQuest @ Yale - PhD Life Simulator`
  - 顶部大标题 `<h1>` 变更为 `🎓 GradQuest @ Yale`
  - 初始欢迎弹窗变更为 `Welcome to GradQuest @ Yale!`
  - 玩法说明弹窗变更为 `📖 How to Play GradQuest @ Yale`
  - **存档 Key**：内部严格保留 `localStorage['gradquest_save']`。
- [x] 新增浏览器回归测试于 `tests/browser_tests.js`：
  - Test 13: `brandDisplayReflectsYaleGradSchool` 验证页面标题与界面中品牌显示准确无误。
  - Test 14: `saveLoadContinuityPreservesStorageKey` 验证游戏保存与读取继续直接作用于 `gradquest_save` 键。
- [x] 更新 `docs/README.md` 与 `docs/CONTRIBUTING.md`：
  - 纠正历史陈旧说明，将基线锁定为 V2.59.2，清晰阐释静态单文件架构，移除所谓 Python 后端的不实描述。

### Phase 2: Hub 根目录治理与分层文档 (已完成)
- [x] 新建根目录 `README.md`：定义 (Yale) Grad School Hub 两级体系与子项目索引，公示 FERPA 保密边界。
- [x] 重构根目录 `AGENTS.md`：建立 Hub 路由、FERPA/隐私边界、子项目权威源与工程措辞守则。
- [x] 修订 `docs/AGENTS.md`：明确标注其作为 `GradQuest @ Yale` 子项目局部规则指南的定位。

### Phase 3: 自动化质量门禁 (已完成)
- [x] 语法与补丁质量校验：
  - `node --check tests/browser_tests.js` 检查通过。
  - `git diff --check` 修复行尾空白后完全通过。
- [x] 提交入库：提交至分支 `codex/rebrand-yale-grad-school`（Commit SHA: `fe2de30`）。

---

## 5. 后续操作指南 (Phase 4: 远端重命名与目录切换)

本阶段修改已在独立分支 `codex/rebrand-yale-grad-school` 上安全提交。待将本分支合并至 `main` 后，由用户执行以下终态变更：

1. **合并分支**：
   ```bash
   git merge codex/rebrand-yale-grad-school
   ```
2. **GitHub 仓库改名**：
   在 GitHub 仓库设置中将 `GradQuest` 改名为 `yale-grad-school`。
3. **更新本地 Git Remote**：
   ```bash
   git remote set-url origin https://github.com/XY-Vince/yale-grad-school.git
   ```
4. **清理临时 Worktree 并重命名本地物理目录**：
   ```bash
   git worktree remove .worktrees/rebrand-yale-grad-school
   cd /Users/xiang-yu/Desktop
   mv GradQuest yale-grad-school
   ```
5. **Pages 链接过渡说明**：
   GitHub 官方不会对 Pages 项目路径做自动跳转。仓库改名后，Pages 真实访问地址将成为 `https://xy-vince.github.io/yale-grad-school/`，旧地址外链需按需更新。
