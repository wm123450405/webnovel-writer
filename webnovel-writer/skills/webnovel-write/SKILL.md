---
name: webnovel-write
description: Writes webnovel chapters (default 2000-2500 words). Use when the user asks to write a chapter or runs /webnovel-write. Runs context, drafting, review, polish, and data extraction.
allowed-tools: Read Write Edit Grep Bash Task
---

# Chapter Writing (Structured Workflow)

## 目标

- 以稳定流程产出可发布章节：优先使用 `正文/第{NNNN}章-{title_safe}.md`，无标题时回退 `正文/第{NNNN}章.md`。
- 默认章节字数目标：2000-2500（用户或大纲明确覆盖时从其约定）。
- 保证审查、润色、数据回写完整闭环，避免“写完即丢上下文”。
- 输出直接可被后续章节消费的结构化数据：`review_metrics`、`summaries`、`chapter_meta`。

## 执行原则

1. 先校验输入完整性，再进入写作流程；缺关键输入时立即阻断。
2. 审查与数据回写是硬步骤，`--fast`/`--minimal` 只允许降级可选环节。
3. 参考资料严格按步骤按需加载，不一次性灌入全部文档。
4. Step 2B 与 Step 4 职责分离：2B 只做风格转译，4 只做问题修复与质控。
5. 任一步失败优先做最小回滚，不重跑全流程。

## 模式定义

- `/webnovel-write`：Step 1 → 2A → 2B → 3 → 4 → 5 → 6
- `/webnovel-write --fast`：Step 1 → 2A → 3 → 4 → 5 → 6（跳过 2B）
- `/webnovel-write --minimal`：Step 1 → 2A → 3（仅3个基础审查）→ 4 → 5 → 6

最小产物（所有模式）：
- `正文/第{NNNN}章-{title_safe}.md` 或 `正文/第{NNNN}章.md`
- `index.db.review_metrics` 新纪录（含 `overall_score`）
- `.webnovel/summaries/ch{NNNN}.md`
- `.webnovel/state.json` 的进度与 `chapter_meta` 更新

### 流程硬约束（禁止事项）

- **禁止并步**：不得将两个 Step 合并为一个动作执行（如同时做 2A 和 3）。
- **禁止跳步**：不得跳过未被模式定义标记为可跳过的 Step。
- **禁止临时改名**：不得将 Step 的输出产物改写为非标准文件名或格式。
- **禁止自创模式**：`--fast` / `--minimal` 只允许按上方定义裁剪步骤，不允许自创混合模式、"半步"或"简化版"。
- **禁止自审替代**：Step 3 审查必须由 Task 子代理执行，主流程不得内联伪造审查结论。
- **禁止源码探测**：脚本调用方式以本文档与 data-agent 文档中的命令示例为准，命令失败时查日志定位问题，不去翻源码学习调用方式。

## 引用加载等级（strict, lazy）

- L0：未进入对应步骤前，不加载任何参考文件。
- L1：每步仅加载该步“必读”文件。
- L2：仅在触发条件满足时加载“条件必读/可选”文件。

路径约定：
- `references/...` 相对当前 skill 目录。
- `../../references/...` 指向全局共享参考。

## References（逐文件引用清单）

### 根目录

- `references/step-3-review-gate.md`
  - 用途：Step 3 审查调用模板、汇总格式、落库 JSON 规范。
  - 触发：Step 3 必读。
- `references/step-5-debt-switch.md`
  - 用途：Step 5 债务利息开关规则（默认关闭）。
  - 触发：Step 5 必读。
- `../../references/shared/core-constraints.md`
  - 用途：Step 2A 写作硬约束（大纲即法律 / 设定即物理 / 发明需识别）。
  - 触发：Step 2A 必读。
- `references/polish-guide.md`
  - 用途：Step 4 问题修复、Anti-AI 与 No-Poison 规则。
  - 触发：Step 4 必读。
- `references/writing/typesetting.md`
  - 用途：Step 4 移动端阅读排版与发布前速查。
  - 触发：Step 4 必读。
- `references/style-adapter.md`
  - 用途：Step 2B 风格转译规则，不改剧情事实。
  - 触发：Step 2B 执行时必读（`--fast`/`--minimal` 跳过）。
- `references/style-variants.md`
  - 用途：Step 1（内置 Contract）开头/钩子/节奏变体与重复风险控制。
  - 触发：Step 1 当需要做差异化设计时加载。
- `../../references/reading-power-taxonomy.md`
  - 用途：Step 1（内置 Contract）钩子、爽点、微兑现 taxonomy。
  - 触发：Step 1 当需要追读力设计时加载。
- `../../references/genre-profiles.md`
  - 用途：Step 1（内置 Contract）按题材配置节奏阈值与钩子偏好。
  - 触发：Step 1 当 `state.project.genre` 已知时加载。
- `references/writing/genre-hook-payoff-library.md`
  - 用途：电竞/直播文/克苏鲁的钩子与微兑现快速库。
  - 触发：Step 1 题材命中 `esports/livestream/cosmic-horror` 时必读。

### writing（问题定向加读）

- `references/writing/combat-scenes.md`
  - 触发：战斗章或审查命中“战斗可读性/镜头混乱”。
- `references/writing/dialogue-writing.md`
  - 触发：审查命中 OOC、对话说明书化、对白辨识差。
- `references/writing/emotion-psychology.md`
  - 触发：情绪转折生硬、动机断层、共情弱。
- `references/writing/scene-description.md`
  - 触发：场景空泛、空间方位不清、切场突兀。
- `references/writing/desire-description.md`
  - 触发：主角目标弱、欲望驱动力不足。

## 工具策略（按需）

- `Read/Grep`：读取 `state.json`、大纲、章节正文与参考文件。
- `Bash`：运行 `extract_chapter_context.py`、`index_manager`、`workflow_manager`。
- `Task`：调用 `context-agent`、审查 subagent、`data-agent` 并行执行。

## 交互流程

### Step 0：预检与上下文最小加载

必须做：
- 解析真实书项目根（book project_root）：必须包含 `.webnovel/state.json`。
- 校验核心输入：`大纲/总纲.md`、`${CLAUDE_PLUGIN_ROOT}/scripts/extract_chapter_context.py` 存在。
- 规范化变量：
  - `WORKSPACE_ROOT`：Claude Code 打开的工作区根目录（可能是书项目的父目录，例如 `D:\wk\xiaoshuo`）
  - `PROJECT_ROOT`：真实书项目根目录（必须包含 `.webnovel/state.json`，例如 `D:\wk\xiaoshuo\凡人资本论`）
  - `SKILL_ROOT`：skill 所在目录（固定 `${CLAUDE_PLUGIN_ROOT}/skills/webnovel-write`）
  - `SCRIPTS_DIR`：脚本目录（固定 `${CLAUDE_PLUGIN_ROOT}/scripts`）
  - `chapter_num`：当前章号（整数）
  - `chapter_padded`：四位章号（如 `0007`）

环境设置（bash 命令执行前）：
```bash
export WORKSPACE_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
export SCRIPTS_DIR="${CLAUDE_PLUGIN_ROOT:?CLAUDE_PLUGIN_ROOT is required}/scripts"
export SKILL_ROOT="${CLAUDE_PLUGIN_ROOT:?CLAUDE_PLUGIN_ROOT is required}/skills/webnovel-write"

python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${WORKSPACE_ROOT}" preflight
export PROJECT_ROOT="$(python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${WORKSPACE_ROOT}" where)"
```

**硬门槛**：`preflight` 必须成功。它统一校验 `CLAUDE_PLUGIN_ROOT` 派生出的 `SKILL_ROOT` / `SCRIPTS_DIR`、`webnovel.py`、`extract_chapter_context.py` 和解析出的 `PROJECT_ROOT`。任一失败都立即阻断。

输出：
- “已就绪输入”与“缺失输入”清单；缺失则阻断并提示先补齐。

### Step 0.5：工作流断点记录（best-effort，不阻断）

```bash
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" workflow start-task --command webnovel-write --chapter {chapter_num} || true
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" workflow start-step --step-id "Step 1" --step-name "Context Agent" || true
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" workflow complete-step --step-id "Step 1" --artifacts '{"ok":true}' || true
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" workflow complete-task --artifacts '{"ok":true}' || true
```

要求：
- `--step-id` 仅允许：`Step 1` / `Step 2A` / `Step 2B` / `Step 3` / `Step 4` / `Step 5` / `Step 6`。
- 任何记录失败只记警告，不阻断写作。
- 每个 Step 执行结束后，同样需要 `complete-step`（失败不阻断）。

### Step 1：Context Agent（内置 Context Contract，生成直写执行包）

使用 Task 调用 `context-agent`，参数：
- `chapter`
- `project_root`
- `storage_path=.webnovel/`
- `state_file=.webnovel/state.json`

硬要求：
- 若 `state` 或大纲不可用，立即阻断并返回缺失项。
- 输出必须同时包含：
  - 7 板块任务书（目标/冲突/承接/角色/场景约束/伏笔/追读力）；
  - Context Contract 全字段（目标/阻力/代价/本章变化/未闭合问题/开头类型/情绪节奏/信息密度/过渡章判定/追读力设计）；
  - Step 2A 可直接消费的”写作执行包”（章节节拍、不可变事实清单、禁止事项、终检清单）。
- **【新增】用户提供的章节梗概处理**：
  - 若用户提供了当前章节的故事梗概，将其作为写作参考
  - 将梗概保存到：`${PROJECT_ROOT}/.webnovel/tmp/chapter_${chapter}_synopsis.md`
  - 梗概内容将用于后续 Step 5.5 的大纲检查与调整
- **【新增】角色首次出场描写指导**：
  - 本章出场角色列表（含是否是首次出场）
  - 首次出场角色：必须重点描写，包括外貌、气质、声音等特点
  - 非首次出场角色：根据出场方式决定描写重点
- **【新增】角色动态称呼指导**：
  - 本章各角色的当前关系阶段（陌生人/初识/熟人/亲近/亲密/敌对/尊敬）
  - 各角色对应的称呼列表（按视角角色划分）
  - 本章是否涉及关系变化（如刚认识、关系破裂、关系亲密等）
  - 称呼变化触发点提示：
    - 如果首次出场是”仅闻其声”，本次出场可以重点描写外貌
    - 如果首次出场是远距离印象，本次出场可以重点描写近距离细节
    - 如果已有完整描写，本次出场可以侧重表情、动作、心理等
- **【新增】道具出场指导**：
  - 本章出场道具列表（含是否是首次出现、首次使用）
  - 首次出现道具：必须重点描写外观
  - 首次使用道具：必须重点描写功效
  - 已使用过道具：根据使用场景决定描写重点
- 合同与任务书出现冲突时，以”大纲与设定约束更严格者”为准。

获取角色首次出场信息的命令：
```bash
# 获取本章出场角色及其首次出场章节
python -X utf8 “${SCRIPTS_DIR}/webnovel.py” --project-root “${PROJECT_ROOT}” status -- --focus entity | grep -A 5 “首次出场”
```

获取道具出场信息的命令：
```bash
# 获取本章出场道具及首次出场信息
python -X utf8 “${SCRIPTS_DIR}/webnovel.py” --project-root “${PROJECT_ROOT}” index entity-appearances --type 物品
```

输出：
- 单一”创作执行包”（任务书 + Context Contract + 直写提示词），供 Step 2A 直接消费，不再拆分独立 Step 1.5。

### Step 2A：正文起草

执行前必须加载：
```bash
cat "${SKILL_ROOT}/../../references/shared/core-constraints.md"
```

硬要求：
- 只输出纯正文到章节正文文件；若详细大纲已有章节名，优先使用 `正文/第{chapter_padded}章-{title_safe}.md`，否则回退为 `正文/第{chapter_padded}章.md`。
- 默认按 2000-2500 字执行；若大纲为关键战斗章/高潮章/卷末章或用户明确指定，则按大纲/用户优先。
- 禁止占位符正文（如 `[TODO]`、`[待补充]`）。
- 保留承接关系：若上章有明确钩子，本章必须回应（可部分兑现）。

**【新增】角色首次出场描写规则**：
- 首次出场角色必须重点描写：
  - 外貌特征：身高、衣着、面容特点
  - 气质印象：给主角/读者的第一感觉
  - 标志性特征：声音、动作、口头禅等
- 非首次出场角色的描写策略：
  - **渐进式揭露**：根据角色在本章的出场方式决定描写深度
  - **首次仅闻其声**：本次出场重点描写外貌
  - **首次远距离印象**：本次出场可描写近距离细节
  - **已有完整印象**：本次出场侧重表情、动作、心理活动
- 禁止重复描写：已完整描写的角色不应重复描写相同特征

**【新增】角色动态称呼规则**：
- **称呼原则**：基于当前叙事视角（主角视角或主要角色视角）动态调整对其他角色的称呼
- **称呼发展阶段**：
  | 阶段 | 条件 | 称呼示例 | 英文对应 |
  |------|------|---------|---------|
  | 陌生人 | 未知姓名 | 公子、姑娘、这位阁下 | stranger |
  | 初识 | 仅知姓氏 | 林公子、王姑娘、李少侠 | first_name + honorific |
  | 熟人 | 知道全名 | 林少侠、李小姐、张兄 | full_name |
  | 亲近 | 关系友好 | 兄弟、姐妹、张兄、李兄 | close_friend |
  | 亲密 | 关系密切 | 昵称、小林、小李、心肝 | nickname |
  | 敌对 | 关系恶劣 | 那人、那个姓林的、刺客 | antagonist |
  | 尊敬 | 辈分/实力高 | 前辈、掌门、长老、宗师 | elder |

- **称呼切换规则**：
  - 视角切换时保持一致：如从主角视角切换到女主视角，各自使用符合自己关系的称呼
  - 关系变化时称呼随之变化：关系亲近后从"林公子"变为"林兄"
  - 对同一角色的称呼在同一章内应保持稳定
  - 旁白叙述使用视角拥有者的称呼习惯
- **特殊称呼场景**：
  - 内心独白：可使用更亲密或更客观的称呼
  - 对话中：直接使用对方名字或习惯称呼
  - 第三方叙述：根据叙述者与角色的关系选择称呼
  - 回忆/闪回：可使用过去的称呼

**【新增】道具首次出现与首次使用描写规则**：
- **首次出现（首次描写道具外观）**：
  - 外观特征：形态、颜色、光泽、尺寸、材质感
  - 独特标记：纹理、符文、特殊印记
  - 气质感觉：给主角/读者的第一感受（如璀璨夺目、朴实无华、阴森诡异）
  - 命名来源：名字的由来或含义（如有）
- **首次使用（首次描写道具功效）**：
  - 功效描述：具体效果和作用
  - 使用感受：使用时的感觉（视觉、听觉、触觉）
  - 限制与代价：使用限制、副作用、反噬
  - 对比参照：与同类道具的对比（如"比寻常疗伤丹效果强十倍"）
- **非首次出现/使用的描写策略**：
  - 已熟悉道具：可简写，重点放在当前使用场景的效果
  - 进化/升级道具：重点描写变化之处
  - 特殊场景：突出道具在当前情境下的特殊表现
- 禁止重复描写：已完整描写的道具不应重复描写相同特征

获取道具关系信息的命令：
```bash
# 获取道具数据
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" state get-entities --type 物品
```

中文思维写作约束（硬规则）：
```bash
# 获取角色关系数据
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" state get-relationships
```

中文思维写作约束（硬规则）：
- **禁止"先英后中"**：不得先用英文工程化骨架（如 ABCDE 分段、Summary/Conclusion 框架）组织内容，再翻译成中文。
- **中文叙事单元优先**：以"动作、反应、代价、情绪、场景、关系位移"为基本叙事单元，不使用英文结构标签驱动正文生成。
- **禁止英文结论话术**：正文、审查说明、润色说明、变更摘要、最终报告中不得出现 Overall / PASS / FAIL / Summary / Conclusion 等英文结论标题。
- **英文仅限机器标识**：CLI flag（`--fast`）、checker id（`consistency-checker`）、DB 字段名（`anti_ai_force_check`）、JSON 键名等不可改的接口名保持英文，其余一律使用简体中文。

输出：
- 章节草稿（可进入 Step 2B 或 Step 3）。

### Step 2B：风格适配（`--fast` / `--minimal` 跳过）

执行前加载：
```bash
cat "${SKILL_ROOT}/references/style-adapter.md"
```

硬要求：
- 只做表达层转译，不改剧情事实、事件顺序、角色行为结果、设定规则。
- 对“模板腔、说明腔、机械腔”做定向改写，为 Step 4 留出问题修复空间。

输出：
- 风格化正文（覆盖原章节文件）。

### Step 3：审查（auto 路由，必须由 Task 子代理执行）

执行前加载：
```bash
cat "${SKILL_ROOT}/references/step-3-review-gate.md"
```

调用约束：
- 必须用 `Task` 调用审查 subagent，禁止主流程伪造审查结论。
- 可并行发起审查，统一汇总 `issues/severity/overall_score`。
- 默认使用 `auto` 路由：根据“本章执行合同 + 正文信号 + 大纲标签”动态选择审查器。

核心审查器（始终执行）：
- `consistency-checker`
- `continuity-checker`
- `ooc-checker`

条件审查器（`auto` 命中时执行）：
- `reader-pull-checker`
- `high-point-checker`
- `pacing-checker`

模式说明：
- 标准/`--fast`：核心 3 个 + auto 命中的条件审查器
- `--minimal`：只跑核心 3 个（忽略条件审查器）

审查指标落库（必做）：
```bash
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" index save-review-metrics --data "@${PROJECT_ROOT}/.webnovel/tmp/review_metrics.json"
```

review_metrics 字段约束（当前工作流约定只传以下字段）：
```json
{
  "start_chapter": 100,
  "end_chapter": 100,
  "overall_score": 85.0,
  "dimension_scores": {"爽点密度": 8.5, "设定一致性": 8.0, "节奏控制": 7.8, "人物塑造": 8.2, "连贯性": 9.0, "追读力": 8.7},
  "severity_counts": {"critical": 0, "high": 1, "medium": 2, "low": 0},
  "critical_issues": ["问题描述"],
  "report_file": "审查报告/第100-100章审查报告.md",
  "notes": "单个字符串；selected_checkers / timeline_gate / anti_ai_force_check 等扩展信息压成单行文本写入此字段"
}
```
- `notes` 在当前执行契约中必须是单个字符串，不得传入对象或数组。
- 当前工作流不额外传入其它顶层字段；脚本侧未在此处做新增硬校验。

硬要求：
- `--minimal` 也必须产出 `overall_score`。
- 未落库 `review_metrics` 不得进入 Step 5。

### Step 4：润色（问题修复优先）

执行前必须加载：
```bash
cat "${SKILL_ROOT}/references/polish-guide.md"
cat "${SKILL_ROOT}/references/writing/typesetting.md"
```

执行顺序：
1. 修复 `critical`（必须）
2. 修复 `high`（不能修复则记录 deviation）
3. 处理 `medium/low`（按收益择优）
4. 执行 Anti-AI 与 No-Poison 全文终检（必须输出 `anti_ai_force_check: pass/fail`）

输出：
- 润色后正文（覆盖章节文件）
- 变更摘要（至少含：修复项、保留项、deviation、`anti_ai_force_check`）

### Step 5：Data Agent（状态与索引回写）

使用 Task 调用 `data-agent`，参数：
- `chapter`
- `chapter_file` 必须传入实际章节文件路径；若详细大纲已有章节名，优先传 `正文/第{chapter_padded}章-{title_safe}.md`，否则传 `正文/第{chapter_padded}章.md`
- `review_score=Step 3 overall_score`
- `project_root`
- `storage_path=.webnovel/`
- `state_file=.webnovel/state.json`

Data Agent 默认子步骤（全部执行）：
- A. 加载上下文
- B. AI 实体提取
- C. 实体消歧
- D. 写入 state/index
- E. 写入章节摘要
- F. AI 场景切片
- G. RAG 向量索引（`rag index-chapter --scenes ...`）
- H. 风格样本评估（`style extract --scenes ...`，仅 `review_score >= 80` 时）
- I. 债务利息（默认跳过）

**【新增】角色卡出场记录更新（J. 更新角色卡）**：
在 Data Agent 执行完实体提取后，必须更新设定集中的角色卡出场记录：

```bash
# J. 更新角色卡出场记录
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" update-character-card --chapter ${chapter_num}
```

更新逻辑：
1. 从 `index.db` 获取本章出场的所有角色列表
2. 对每个出场角色：
   - 读取对应的角色卡文件（`设定集/主角卡.md`、`设定集/女主卡.md` 或 `设定集/角色库/主要角色/*.md` 等）
   - 更新"出场记录"部分：
     - 首次出场章节：若角色首次出场，更新此字段
     - 最后出场章节：更新为当前章节
     - 出场章节列表：添加当前章节
     - 本章出场摘要：提取本章中角色出场的内容摘要
3. 如果角色卡文件不存在或格式不匹配，跳过该角色的更新

**【新增】道具卡出场记录更新（K. 更新道具卡）**：
在角色卡更新之后，必须更新设定集中的道具卡出场记录：

```bash
# K. 更新道具卡出场记录
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" update-item-card --chapter ${chapter_num}
```

更新逻辑：
1. 从 `index.db` 获取本章出场的所有物品/道具列表
2. 对每个出场道具：
   - 读取对应的道具卡文件（`设定集/物品库/*.md`）
   - 更新"出场记录"部分：
     - 首次出场章节：若道具首次出场，更新此字段
     - 最后出场章节：更新为当前章节
     - 出场章节列表：添加当前章节
     - 本章出场摘要：提取本章中道具出场的内容摘要
3. 如果道具卡文件不存在或格式不匹配，跳过该道具的更新

`--scenes` 来源优先级（G/H 步骤共用）：
1. 优先从 `index.db` 的 scenes 记录获取（Step F 写入的结果）
2. 其次按 `start_line` / `end_line` 从正文切片构造
3. 最后允许单场景退化（整章作为一个 scene）

Step 5 失败隔离规则：
- 若 G/H 失败原因是 `--scenes` 缺失、scene 为空、scene JSON 格式错误：只补跑 G/H 子步骤，不回滚或重跑 Step 1-4。
- 若 A-E 失败（state/index/summary 写入失败）：仅重跑 Step 5，不回滚已通过的 Step 1-4。
- 禁止因 RAG/style 子步骤失败而重跑整个写作链。

执行后检查（最小白名单）：
- `.webnovel/state.json`
- `.webnovel/index.db`
- `.webnovel/summaries/ch{chapter_padded}.md`
- `.webnovel/observability/data_agent_timing.jsonl`（观测日志）

性能要求：
- 读取 timing 日志最近一条；
- 当 `TOTAL > 30000ms` 时，输出最慢 2-3 个环节与原因说明。

观测日志说明：
- `call_trace.jsonl`：外层流程调用链（agent 启动、排队、环境探测等系统开销）。
- `data_agent_timing.jsonl`：Data Agent 内部各子步骤耗时。
- 当外层总耗时远大于内层 timing 之和时，默认先归因为 agent 启动与环境探测开销，不误判为正文或数据处理慢。

债务利息：
- 默认关闭，仅在用户明确要求或开启追踪时执行（见 `step-5-debt-switch.md`）。

### Step 5.5：章节完成后大纲检查与调整（条件执行）

**触发条件**：当用户提供了当前章节的故事梗概时执行

**执行时机**：在 Step 5（Data Agent）完成后，Step 6（Git 备份）之前

**检查流程**：

1. **加载原始大纲数据**：
   ```bash
   # 获取本章的原始大纲规划
   cat "${PROJECT_ROOT}/大纲/卷纲.md" || echo "无卷纲"
   cat "${PROJECT_ROOT}/大纲/总纲.md" || echo "无总纲"

   # 获取本章详细大纲
   cat "${PROJECT_ROOT}/大纲/章纲/第${chapter_padded}章.md" || echo "无章纲"
   ```

2. **对比用户梗概与原大纲**：
   - 用户提供的故事梗概存储在：`${PROJECT_ROOT}/.webnovel/tmp/chapter_${chapter_padded}_synopsis.md`
   - 对比内容差异点：
     - 情节走向是否一致
     - 角色出场是否匹配
     - 伏笔埋设是否变化
     - 情感线/实力线变化

3. **偏差分析**：
   ```
   偏差类型：
   - 情节偏移：实际写的与原大纲有较大出入
   - 角色变更：新增/删减角色出场
   - 伏笔变化：提前兑现/延后/取消伏笔
   - 支线增删：新增或删除了支线剧情
   ```

4. **后续章节影响评估**：
   ```bash
   # 检查后续章节是否受影响
   python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" outline check-impact --chapter ${chapter_num} --deviation-type "情节偏移"
   ```

5. **大纲调整建议**：
   如果偏差超过阈值，生成调整建议：
   - 需要调整的章节列表
   - 调整内容说明
   - 调整优先级

**偏差阈值**：
- 轻微偏差（<20%）：仅记录，不强制调整
- 中度偏差（20%-50%）：建议调整后续1-3章
- 严重偏差（>50%）：必须调整后续章节

**调整原则**：
- 优先保证故事逻辑连贯性
- 保持已写章节不变
- 调整应最小化，只修改必要的后续章节
- 调整后需用户确认

**输出格式**：
```markdown
## 章节完成后大纲检查报告

### 本章信息
- 章节号：第{chapter_num}章
- 标题：{title}
- 用户梗概：{synopsis_summary}

### 偏差分析
- 偏差类型：{类型}
- 偏差程度：{轻微/中度/严重}
- 偏差内容：
  1. {具体偏差点1}
  2. {具体偏差点2}

### 后续章节影响
- 受影响章节：{列表}
- 影响说明：{说明}

### 调整建议
- 建议调整：{是/否}
- 调整内容：
  - 第{章}章：{调整说明}
  - 第{章}章：{调整说明}

### 用户确认
- [ ] 确认调整
- [ ] 暂不调整
- [ ] 手动调整
```

**注意**：
- 此步骤为条件执行，只有用户提供章节梗概时才运行
- 若用户未提供梗概，此步骤自动跳过
- 调整建议需要用户确认后才能执行

### Step 6：Git 备份（可失败但需说明）

```bash
git add .
git -c i18n.commitEncoding=UTF-8 commit -m "第{chapter_num}章: {title}"
```

规则：
- 提交时机：验证、回写、清理全部完成后最后执行。
- 提交信息默认中文，格式：`第{chapter_num}章: {title}`。
- 若 commit 失败，必须给出失败原因与未提交文件范围。

## 充分性闸门（必须通过）

未满足以下条件前，不得结束流程：

1. 章节正文文件存在且非空：`正文/第{chapter_padded}章-{title_safe}.md` 或 `正文/第{chapter_padded}章.md`
2. Step 3 已产出 `overall_score` 且 `review_metrics` 成功落库
3. Step 4 已处理全部 `critical`，`high` 未修项有 deviation 记录
4. Step 4 的 `anti_ai_force_check=pass`（基于全文检查；fail 时不得进入 Step 5）
5. Step 5 已回写 `state.json`、`index.db`、`summaries/ch{chapter_padded}.md`
6. **【新增】若用户提供了章节梗概**：Step 5.5 大纲检查已完成（或用户确认跳过/暂不调整）
7. 若开启性能观测，已读取最新 timing 记录并输出结论

## 验证与交付

执行检查：

```bash
test -f "${PROJECT_ROOT}/.webnovel/state.json"
test -f "${PROJECT_ROOT}/正文/第${chapter_padded}章.md"
test -f "${PROJECT_ROOT}/.webnovel/summaries/ch${chapter_padded}.md"
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" index get-recent-review-metrics --limit 1
tail -n 1 "${PROJECT_ROOT}/.webnovel/observability/data_agent_timing.jsonl" || true
```

成功标准：
- 章节文件、摘要文件、状态文件齐全且内容可读。
- 审查分数可追溯，`overall_score` 与 Step 5 输入一致。
- 润色后未破坏大纲与设定约束。

## 失败处理（最小回滚）

触发条件：
- 章节文件缺失或空文件；
- 审查结果未落库；
- Data Agent 关键产物缺失；
- 润色引入设定冲突。

恢复流程：
1. 仅重跑失败步骤，不回滚已通过步骤。
2. 常见最小修复：
   - 审查缺失：只重跑 Step 3 并落库；
   - 润色失真：恢复 Step 2A 输出并重做 Step 4；
   - 摘要/状态缺失：只重跑 Step 5；
3. 重新执行“验证与交付”全部检查，通过后结束。
