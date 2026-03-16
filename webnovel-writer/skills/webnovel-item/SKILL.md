---
name: webnovel-item
description: 创建或修改道具信息，支持道具设定管理、出场章节检查与一致性修正。
allowed-tools: Read Write Edit Grep Bash Task AskUserQuestion
---

# Item Management Skill

## 目标

- 支持命令格式：`/webnovel-item 道具名 道具信息描述`
- 若道具不存在，添加道具卡并写入设定
- 若道具已存在，修改已有道具信息
- 查看道具的出场章节
- 检查所有出场章节中道具出场内容是否符合新设定
- 若有不符合新设定的，需要修改那些不符合设定的章节内容

## Project Root Guard（必须先确认）

- Claude Code 的"工作区根目录"不一定等于"书项目根目录"。常见结构：工作区为 `D:\wk\xiaoshuo`，书项目为 `D:\wk\xiaoshuo\凡人资本论`。
- 必须先解析真实书项目根（必须包含 `.webnovel/state.json`），后续所有读写路径都以该目录为准。
- **禁止**在插件目录 `${CLAUDE_PLUGIN_ROOT}/` 下读取或写入项目文件

环境设置（bash 命令执行前）：
```bash
export WORKSPACE_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"

if [ -z "${CLAUDE_PLUGIN_ROOT}" ] || [ ! -d "${CLAUDE_PLUGIN_ROOT}/skills/webnovel-item" ]; then
  echo "ERROR: 未设置 CLAUDE_PLUGIN_ROOT 或缺少目录: ${CLAUDE_PLUGIN_ROOT}/skills/webnovel-item" >&2
  exit 1
fi
export SKILL_ROOT="${CLAUDE_PLUGIN_ROOT}/skills/webnovel-item"

if [ -z "${CLAUDE_PLUGIN_ROOT}" ] || [ ! -d "${CLAUDE_PLUGIN_ROOT}/scripts" ]; then
  echo "ERROR: 未设置 CLAUDE_PLUGIN_ROOT 或缺少目录: ${CLAUDE_PLUGIN_ROOT}/scripts" >&2
  exit 1
fi
export SCRIPTS_DIR="${CLAUDE_PLUGIN_ROOT}/scripts"

export PROJECT_ROOT="$(python "${SCRIPTS_DIR}/webnovel.py" --project-root "${WORKSPACE_ROOT}" where)"
```

## Workflow Checklist

Copy and track progress:

```
道具管理进度：
- [ ] Step 1: 解析命令参数（道具名 + 道具描述）
- [ ] Step 2: 加载项目数据（state.json）
- [ ] Step 3: 检查道具是否存在
- [ ] Step 4: 添加或更新道具信息
- [ ] Step 5: 获取道具出场章节
- [ ] Step 6: 检查出场内容是否符合新设定
- [ ] Step 7: 修正不符合设定的章节内容
```

---

## Step 1: 解析命令参数

从用户输入中提取：
- **道具名**：命令的第一个参数
- **道具描述**：命令的剩余部分（道具信息描述）

格式示例：
```
/webnovel-item 道具名 道具信息描述
/webnovel-item 玄元丹 主角在秘境中获得的疗伤圣药，可瞬间恢复严重伤势，副作用是会虚弱三天
/webnovel-item 青锋剑 主角的随身佩剑，下品法器，削铁如泥，是主角家族传承之物
/webnovel-item 储物戒指 内含十丈空间的储物法宝，可存放活物，价值连城
```

---

## Step 2: 加载项目数据

```bash
cat "$PROJECT_ROOT/.webnovel/state.json"
```

---

## Step 3: 检查道具是否存在

使用以下命令查询道具是否已存在：

```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" status -- --focus entity
```

或直接使用 Grep 搜索：

```bash
grep -r "道具名" "$PROJECT_ROOT/.webnovel/" 2>/dev/null
grep -r "道具名" "$PROJECT_ROOT/设定集/" 2>/dev/null
```

### 判定逻辑

| 情况 | 后续操作 |
|------|---------|
| 道具不存在 | 创建新道具卡 |
| 道具已存在 | 更新道具信息 |

---

## Step 4: 添加或更新道具信息

### 4.1 道具不存在：创建新道具

使用以下命令添加新道具：

```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" entity add 道具名 --type 物品 --tier 次要 --desc "道具描述"
```

或使用 state_manager 直接操作：

```bash
python -c "
import sys
sys.path.insert(0, '${SCRIPTS_DIR}')
from data_modules.state_manager import StateManager, EntityState
sm = StateManager()
entity = EntityState(
    id='道具名',
    name='道具名',
    type='物品',
    tier='次要',
    desc='道具描述',
    attributes={'description': '道具描述', 'category': '法宝'}
)
sm.add_entity(entity)
"
```

### 4.2 道具已存在：更新道具信息

使用以下命令更新道具：

```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" entity update 道具名 --description "新道具描述"
```

或直接读取现有道具信息并更新：

```bash
# 读取当前道具信息
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" query entity 道具名
```

### 道具卡格式

更新或创建的道具信息应包含：
```json
{
  "id": "道具名",
  "name": "道具名",
  "type": "物品",
  "tier": "核心|重要|次要|装饰",
  "aliases": ["别名1", "别名2"],
  "attributes": {
    "description": "道具描述",
    "category": "丹药|武器|防具|信物|法宝|灵宠|材料|阵法",
    "rarity": "凡品|下品|中品|上品|极品|仙品|神品",
    "abilities": [],
    "owner": "",
    "history": ""
  },
  "first_appearance": 1,
  "last_appearance": 10
}
```

---

## Step 5: 获取道具出场章节

从索引数据库或 state.json 获取道具出场章节：

```bash
# 查看道具出场信息
python -c "
import sys
import json
sys.path.insert(0, '${SCRIPTS_DIR}')
from data_modules.state_manager import StateManager
sm = StateManager()
entity = sm.get_entity('道具名', '物品')
if entity:
    print('首次出场:', entity.get('first_appearance', '未知'))
    print('最后出场:', entity.get('last_appearance', '未知'))
    print(json.dumps(entity, indent=2, ensure_ascii=False))
"
```

获取道具出现的所有章节：

```bash
# 查询道具出现的所有章节
python -c "
import sys
import json
sys.path.insert(0, '${SCRIPTS_DIR}')
from data_modules.index_manager import IndexManager
config_path = '${PROJECT_ROOT}/.webnovel/config.json'
im = IndexManager(config_path)
appearances = im.get_entity_appearances('道具名', '物品')
print(json.dumps(appearances, indent=2, ensure_ascii=False))
"
```

---

## Step 6: 检查出场内容是否符合新设定

对于每个出场章节：

1. 读取章节内容
2. 查找道具出场段落
3. 分析出场内容是否与新设定一致
4. 标记不一致的章节

### 章节内容检查

```bash
# 列出所有章节文件
ls "$PROJECT_ROOT/正文/"
```

对于每个出场章节：
- 读取章节内容
- 查找道具名和别名出现的段落
- 分析该段落描述是否符合新设定

### 检查要点

根据新设定检查以下内容：
- **能力效果**：道具表现的能力是否与设定一致
- **稀有度**：道具出现的场景是否合理
- **持有者**：道具的归属是否正确
- **形态变化**：道具的形态描述是否一致

### 输出检查结果

```
## 道具出场检查报告：{道具名}

### 新设定
{新设定的描述}

### 出场章节分析

| 章节 | 出场内容 | 是否符合 | 备注 |
|-----|---------|---------|------|
| 第3章 | 道具出场描述 | ✅ 符合 | |
| 第5章 | 道具出场描述 | ❌ 不符合 | 能力描述与新设定冲突 |
| 第10章 | 道具出场描述 | ⚠️ 部分符合 | 稀有度需要更新 |
```

---

## Step 7: 修正不符合设定的章节内容

对于不符合设定的章节，需要修改章节内容使其符合新设定。

### 修改流程

1. **读取原章节内容**
2. **定位需要修改的段落**
3. **修改内容使其符合新设定**
4. **保持上下文一致性**

### 修改示例

**原内容**（不符合新设定）：
```
玄元丹只是一枚普通的疗伤药，效果有限。
```

**新设定**：玄元丹是疗伤圣药，可瞬间恢复严重伤势

**修改后**（符合新设定）：
```
玄元丹不愧为疗伤圣药，只见光华流转，主角身上的重伤以肉眼可见的速度恢复。
```

### 修改原则

- **保留道具出场事实**：道具的出现不能被删除
- **调整描述方式**：通过词语替换、能力描述调整等方式
- **保持情节合理**：修改不能破坏情节逻辑
- **标记修改位置**：在修改处添加注释（可选）

### 用户确认

修改前应向用户展示修改方案并确认：

```markdown
## 修改建议：第{章节}章

### 原内容
{原文}

### 修改后
{修改后内容}

### 修改理由
{为什么这样修改}

是否确认修改？
- [ ] 确认修改
- [ ] 取消
- [ ] 手动调整
```

---

## 完整执行流程示例

```
用户输入：/webnovel-item 玄元丹 主角在秘境中获得的疗伤圣药，可瞬间恢复严重伤势，副作用是会虚弱三天

1. 解析参数：
   - 道具名：玄元丹
   - 道具描述：主角在秘境中获得的疗伤圣药，可瞬间恢复严重伤势，副作用是会虚弱三天

2. 检查道具是否存在：
   - 道具已存在

3. 更新道具信息：
   - 更新 description: "主角在秘境中获得的疗伤圣药，可瞬间恢复严重伤势，副作用是会虚弱三天"

4. 获取出场章节：
   - 第3章、第5章、第10章、第15章

5. 检查出场内容：
   - 第3章：✅ 符合
   - 第5章：❌ 不符合（描述为普通疗伤药）
   - 第10章：✅ 符合
   - 第15章：⚠️ 需要调整（缺少副作用描述）

6. 修正不符合的章节：
   - 向用户展示修改方案
   - 确认后执行修改
```

---

## 输出格式

### 成功输出

```markdown
# 道具管理完成：{道具名}

## 操作类型
{添加新道具 / 更新道具信息}

## 道具信息
- **道具名**: {道具名}
- **类别**: {丹药/武器/防具/信物/法宝/灵宠/材料/阵法}
- **稀有度**: {凡品/下品/中品/上品/极品/仙品/神品}
- **首次出场**: 第{数字}章
- **最后出场**: 第{数字}章

## 道具设定
{道具描述}

## 出场章节检查
- 共出场 {数字} 章
- 符合新设定：{数字} 章
- 需要修改：{数字} 章

## 修改的章节
{修改的章节列表}
```

### 错误输出

```markdown
# 错误

{错误原因}

请检查：
1. 项目根目录是否正确
2. 道具名是否有效
3. 是否有权限修改文件
```
