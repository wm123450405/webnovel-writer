---
name: webnovel-review
description: Reviews chapter quality with checker agents and generates reports. Use when the user asks for a chapter review or runs /webnovel-review.
allowed-tools: Read Grep Write Edit Bash Task AskUserQuestion
---

# Quality Review Skill

## Project Root Guard（必须先确认）

- Claude Code 的“工作区根目录”不一定等于“书项目根目录”。常见结构：工作区为 `D:\wk\xiaoshuo`，书项目为 `D:\wk\xiaoshuo\凡人资本论`。
- 必须先解析真实书项目根（必须包含 `.webnovel/state.json`），后续所有读写路径都以该目录为准。

环境设置（bash 命令执行前）：
```bash
export WORKSPACE_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"

if [ -z "${CLAUDE_PLUGIN_ROOT}" ] || [ ! -d "${CLAUDE_PLUGIN_ROOT}/skills/webnovel-review" ]; then
  echo "ERROR: 未设置 CLAUDE_PLUGIN_ROOT 或缺少目录: ${CLAUDE_PLUGIN_ROOT}/skills/webnovel-review" >&2
  exit 1
fi
export SKILL_ROOT="${CLAUDE_PLUGIN_ROOT}/skills/webnovel-review"

if [ -z "${CLAUDE_PLUGIN_ROOT}" ] || [ ! -d "${CLAUDE_PLUGIN_ROOT}/scripts" ]; then
  echo "ERROR: 未设置 CLAUDE_PLUGIN_ROOT 或缺少目录: ${CLAUDE_PLUGIN_ROOT}/scripts" >&2
  exit 1
fi
export SCRIPTS_DIR="${CLAUDE_PLUGIN_ROOT}/scripts"

export PROJECT_ROOT="$(python "${SCRIPTS_DIR}/webnovel.py" --project-root "${WORKSPACE_ROOT}" where)"
```

## 0.5 工作流断点（best-effort，不得阻断主流程）

> 目标：让 `/webnovel-resume` 能基于真实断点恢复。即使 workflow_manager 出错，也**只记录警告**，审查继续。

推荐（bash）：
```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" workflow start-task --command webnovel-review --chapter {end} || true
```

Step 映射（必须与 `workflow_manager.py get_pending_steps("webnovel-review")` 对齐）：
- Step 1：加载参考
- Step 2：加载项目状态
- Step 3：并行调用检查员
- Step 4：生成审查报告
- Step 5：保存审查指标到 index.db
- Step 6：写回审查记录到 state.json
- Step 7：处理关键问题（AskUserQuestion）
- Step 8：生成章节摘要（每个章节都要生成）
- Step 9：标记章节审查状态（检测修改过的章节）
- Step 10：收尾（完成任务）

Step 记录模板（bash，失败不阻断）：
```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" workflow start-step --step-id "Step 1" --step-name "加载参考" || true
python "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" workflow complete-step --step-id "Step 1" --artifacts '{"ok":true}' || true
```

## Review depth

- **Core (default)**: consistency / continuity / ooc / reader-pull / duplicate-description
- **Full (关键章/用户要求)**: core + high-point + pacing

> **注意**: `duplicate-description-checker` 是 Core 默认检查器，用于检测外貌、动作、内心独白等描写的重复问题

## Step 1: 加载参考（按需）

## References（按步骤导航）

- Step 1（必读，硬约束）：[core-constraints.md](../../references/shared/core-constraints.md)
- Step 1（可选，Full 或节奏/爽点相关问题）：[cool-points-guide.md](../../references/shared/cool-points-guide.md)
- Step 1（可选，Full 或节奏/爽点相关问题）：[strand-weave-pattern.md](../../references/shared/strand-weave-pattern.md)
- Step 1（可选，仅在返工建议需要时）：[common-mistakes.md](references/common-mistakes.md)
- Step 1（可选，仅在返工建议需要时）：[pacing-control.md](references/pacing-control.md)
- Step 1（可选，仅在描写重复检查需要时）：[duplicate-description-checker.md](references/duplicate-description-checker.md)

## Reference Loading Levels (strict, lazy)

- L0: 先确定审查深度（Core / Full），再加载参考。
- L1: 只加载 References 区的“必读”条目。
- L2: 仅在问题定位需要时加载 References 区的“可选”条目。

**必读**:
```bash
cat "${SKILL_ROOT}/../../references/shared/core-constraints.md"
```

**建议（Full 或需要时）**:
```bash
cat "${SKILL_ROOT}/../../references/shared/cool-points-guide.md"
cat "${SKILL_ROOT}/../../references/shared/strand-weave-pattern.md"
```

**可选**:
```bash
cat "${SKILL_ROOT}/references/common-mistakes.md"
cat "${SKILL_ROOT}/references/pacing-control.md"
```

## Step 2: 加载项目状态（若存在）

```bash
cat "$PROJECT_ROOT/.webnovel/state.json"
```

> 注意：地图约束和道具约束已整合到 `core-constraints.md` 中，加载参考文件时已包含。

## Step 3: 并行调用检查员（Task）

**调用约束**:
- 必须通过 `Task` 工具调用审查 subagent，禁止主流程直接内联审查结论。
- 各 subagent 结果全部返回后再生成总评与优先级。

**Core**:
- `consistency-checker`
- `continuity-checker`
- `ooc-checker`
- `reader-pull-checker`
- `map-consistency-checker`
- `power-consistency-checker`
- `duplicate-description-checker`

**Full 追加**:
- `high-point-checker`
- `pacing-checker`

## Step 4: 生成审查报告

保存到：`审查报告/第{start}-{end}章审查报告.md`

**报告结构（精简版）**:
```markdown
# 第 {start}-{end} 章质量审查报告

## 综合评分
- 爽点密度 / 设定一致性 / 节奏控制 / 人物塑造 / 连贯性 / 追读力
- 总评与等级

## 修改优先级
- 🔴 高优先级（必须修改）
- 🟠 中优先级（建议修改）
- 🟡 低优先级（可选优化）

## 改进建议
- 可执行的修复建议
```

**审查指标 JSON（用于趋势统计）**:
```json
{
  "start_chapter": {start},
  "end_chapter": {end},
  "overall_score": 48,
  "dimension_scores": {
    "爽点密度": 8,
    "设定一致性": 7,
    "节奏控制": 7,
    "人物塑造": 8,
    "连贯性": 9,
    "追读力": 9
  },
  "severity_counts": {"critical": 1, "high": 2, "medium": 3, "low": 1},
  "critical_issues": ["设定自相矛盾"],
  "report_file": "审查报告/第{start}-{end}章审查报告.md",
  "notes": ""
}
```

注意：此处只生成审查指标 JSON；落库见 Step 5。

## Step 5: 保存审查指标到 index.db（必做）

```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" index save-review-metrics --data '@review_metrics.json'
```

## Step 6: 写回审查记录到 state.json（必做）

将审查报告记录写回 `state.json.review_checkpoints`，用于后续追踪与回溯（依赖 `update_state.py --add-review`）：
```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" update-state -- --add-review "{start}-{end}" "审查报告/第{start}-{end}章审查报告.md"
```

## Step 7: 处理关键问题

如发现 critical 问题（`severity_counts.critical > 0` 或 `critical_issues` 非空），**必须使用 AskUserQuestion** 询问用户：
- A) 立即修复（推荐）
- B) 仅保存报告，稍后处理

若用户选择 A：
- 输出“返工清单”（逐条 critical 问题 → 定位 → 最小修复动作 → 注意事项）
- 如用户明确授权可直接修改正文文件，则用 `Edit` 对对应章节文件做最小修复，并建议重新运行一次 `/webnovel-review` 验证

若用户选择 B：
- 不做正文修改，仅保留审查报告与指标记录，结束本次审查

## Step 8: 生成章节摘要（每个章节都要生成）

**重要**：当一次性审查多个章节时，必须为**每个章节**都生成摘要文件。

```bash
# 为每个章节生成摘要
mkdir -p "${PROJECT_ROOT}/.webnovel/summaries"

for chapter in $(seq {start} {end}); do
    chapter_padded=$(printf "%04d" $chapter)
    summary_file="${PROJECT_ROOT}/.webnovel/summaries/ch${chapter_padded}.md"

    # 生成章节摘要（包含本章要点、人物出场、伏笔等）
    cat > "$summary_file" << 'EOF'
---
chapter: {chapter_num}
type: summary
reviewed_at: {timestamp}
---

# 第 {chapter_num} 章摘要

## 本章要点
- ...

## 主要人物出场
- ...

## 伏笔记录
- ...

## 设定引用
- ...
EOF
    echo "已生成: $summary_file"
done
```

## Step 9: 标记章节审查状态

### 9.1 标记已审查的章节

```bash
# 更新审查记录，标记每个章节的审查状态
python "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" update-state -- --mark-reviewed "{start}-{end}"
```

### 9.2 检测并标记修改过的章节

在审查开始前，检查是否有章节被修改过：

```bash
# 检查章节文件的修改时间
for chapter in $(seq {start} {end}); do
    chapter_padded=$(printf "%04d" $chapter)

    # 查找章节文件
    chapter_file=$(find "${PROJECT_ROOT}/正文" -name "第${chapter}章.md" -o -name "第${chapter}章-*.md" 2>/dev/null | head -1)

    if [ -n "$chapter_file" ]; then
        # 获取文件的修改时间
        file_mtime=$(stat -c %Y "$chapter_file" 2>/dev/null || stat -f %m "$chapter_file" 2>/dev/null)

        # 检查上次审查时间
        last_review=$(python "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" get-chapter-meta --chapter $chapter 2>/dev/null | grep -o '"last_review":[0-9]*' | cut -d: -f2)

        if [ -n "$last_review" ] && [ "$file_mtime" -gt "$last_review" ]; then
            echo "章节 $chapter 已被修改，标记为需要重新审查"
            python "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" update-state -- --mark-needs-review $chapter
        fi
    fi
done
```

### 9.3 审查后更新章节状态

```bash
# 更新审查后的章节状态
python "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" update-state -- --update-chapter-meta {start}-{end}
```

## Step 10: 收尾（完成任务）

```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" workflow start-step --step-id "Step 10" --step-name "收尾" || true
python "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" workflow complete-step --step-id "Step 10" --artifacts '{"ok":true}' || true
python "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" workflow complete-task --artifacts '{"ok":true}' || true
```

## 【修改检测机制】

### 修改检测原理

当章节文件被修改后，需要自动标记该章节为"需要重新审查"状态：

1. **修改检测触发时机**：
   - 手动修改章节文件后
   - 通过 Edit 工具修改正文后
   - 章节文件时间戳发生变化时

2. **标记方式**：
   - 在 `state.json` 的 `chapter_meta` 中设置 `needs_review: true`
   - 同时记录 `modified_at` 时间戳

3. **审查优先级**：
   - 标记为 `needs_review: true` 的章节优先审查
   - 审查完成后自动设置为 `needs_review: false`

### 修改检测命令

```bash
# 检测单个章节是否需要重新审查
python "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" check-chapter-modified --chapter {num}

# 标记章节需要重新审查
python "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" mark-chapter-modified --chapter {num}

# 获取所有需要重新审查的章节
python "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" list-chapters-needs-review
```

### 修改后自动标记流程

在完成任何章节修改后（通过 Edit 工具），自动执行：

```bash
# 自动标记修改的章节
chapter_num={章节号}
python "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" mark-chapter-modified --chapter $chapter_num

echo "章节 $chapter_num 已标记为需要重新审查，下次审查时将重点检查"
```
