---
name: webnovel-role
description: 创建或修改角色卡信息，支持角色设定管理、出场章节检查与一致性修正。
allowed-tools: Read Write Edit Grep Bash Task AskUserQuestion
---

# Role Management Skill

## 目标

- 支持命令格式：`/webnovel-role 角色A 角色信息描述`
- 若角色不存在，添加角色卡并写入设定
- 若角色已存在，修改已有角色卡
- 查看角色的出场章节
- 检查所有出场章节中角色出场内容是否符合新设定
- 若有不符合新设定的，需要修改那些不符合设定的章节内容

## Project Root Guard（必须先确认）

- Claude Code 的"工作区根目录"不一定等于"书项目根目录"。常见结构：工作区为 `D:\wk\xiaoshuo`，书项目为 `D:\wk\xiaoshuo\凡人资本论`。
- 必须先解析真实书项目根（必须包含 `.webnovel/state.json`），后续所有读写路径都以该目录为准。
- **禁止**在插件目录 `${CLAUDE_PLUGIN_ROOT}/` 下读取或写入项目文件

环境设置（bash 命令执行前）：
```bash
export WORKSPACE_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"

if [ -z "${CLAUDE_PLUGIN_ROOT}" ] || [ ! -d "${CLAUDE_PLUGIN_ROOT}/skills/webnovel-role" ]; then
  echo "ERROR: 未设置 CLAUDE_PLUGIN_ROOT 或缺少目录: ${CLAUDE_PLUGIN_ROOT}/skills/webnovel-role" >&2
  exit 1
fi
export SKILL_ROOT="${CLAUDE_PLUGIN_ROOT}/skills/webnovel-role"

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
角色管理进度：
- [ ] Step 1: 解析命令参数（角色名 + 角色描述）
- [ ] Step 2: 加载项目数据（state.json）
- [ ] Step 3: 检查角色是否存在
- [ ] Step 4: 添加或更新角色信息
- [ ] Step 5: 获取角色出场章节
- [ ] Step 6: 检查出场内容是否符合新设定
- [ ] Step 7: 修正不符合设定的章节内容
```

---

## Step 1: 解析命令参数

从用户输入中提取：
- **角色名**：命令的第一个参数
- **角色描述**：命令的剩余部分（角色信息描述）

格式示例：
```
/webnovel-role 角色A 角色信息描述
/webnovel-role 李明 主角的好友，表面温柔但实际腹黑，是主角小时候的玩伴
/webnovel-role 女主角 聪明伶俐的古灵精怪少女，与主角不打不相识
```

---

## Step 2: 加载项目数据

```bash
cat "$PROJECT_ROOT/.webnovel/state.json"
```

---

## Step 3: 检查角色是否存在

使用以下命令查询角色是否已存在：

```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" status -- --focus entity
```

或直接使用 Grep 搜索：

```bash
grep -r "角色名" "$PROJECT_ROOT/.webnovel/" 2>/dev/null
grep -r "角色名" "$PROJECT_ROOT/设定集/" 2>/dev/null
```

### 判定逻辑

| 情况 | 后续操作 |
|------|---------|
| 角色不存在 | 创建新角色卡 |
| 角色已存在 | 更新角色信息 |

---

## Step 4: 添加或更新角色信息

### 4.1 角色不存在：创建新角色

使用以下命令添加新角色：

```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" entity add 角色名 --type 角色 --tier 次要 --desc "角色描述"
```

或使用 state_manager 直接操作：

```bash
python -c "
import sys
sys.path.insert(0, '${SCRIPTS_DIR}')
from data_modules.state_manager import StateManager, EntityState
sm = StateManager()
entity = EntityState(
    id='角色名',
    name='角色名',
    type='角色',
    tier='次要',
    desc='角色描述',
    attributes={'description': '角色描述'}
)
sm.add_entity(entity)
"
```

### 4.2 角色已存在：更新角色信息

使用以下命令更新角色：

```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" entity update 角色名 --description "新角色描述"
```

或直接读取现有角色信息并更新：

```bash
# 读取当前角色信息
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" query entity 角色名
```

### 角色卡格式

更新或创建的角色信息应包含：
```json
{
  "id": "角色名",
  "name": "角色名",
  "type": "角色",
  "tier": "核心|重要|次要|装饰",
  "aliases": ["别名1", "别名2"],
  "attributes": {
    "description": "角色描述",
    "personality": "性格特点",
    "background": "背景故事",
    "relationships": {}
  },
  "first_appearance": 1,
  "last_appearance": 10
}
```

---

## Step 5: 获取角色出场章节

从索引数据库或 state.json 获取角色出场章节：

```bash
# 查看角色出场信息
python -c "
import sys
import json
sys.path.insert(0, '${SCRIPTS_DIR}')
from data_modules.state_manager import StateManager
sm = StateManager()
entity = sm.get_entity('角色名', '角色')
if entity:
    print('首次出场:', entity.get('first_appearance', '未知'))
    print('最后出场:', entity.get('last_appearance', '未知'))
    # 获取完整出场记录
    print(json.dumps(entity, indent=2, ensure_ascii=False))
"
```

获取角色出现的所有章节：

```bash
# 查询角色出现的所有章节
python -c "
import sys
import json
sys.path.insert(0, '${SCRIPTS_DIR}')
from data_modules.index_manager import IndexManager
config_path = '${PROJECT_ROOT}/.webnovel/config.json'
im = IndexManager(config_path)
appearances = im.get_entity_appearances('角色名', '角色')
print(json.dumps(appearances, indent=2, ensure_ascii=False))
"
```

---

## Step 6: 检查出场内容是否符合新设定

对于每个出场章节：

1. 读取章节内容
2. 查找角色出场段落
3. 分析出场内容是否与新设定一致
4. 标记不一致的章节

### 章节内容检查

```bash
# 列出所有章节文件
ls "$PROJECT_ROOT/正文/"
```

对于每个出场章节：
- 读取章节内容
- 查找角色名和别名出现的段落
- 分析该段落描述是否符合新设定

### 检查要点

根据新设定检查以下内容：
- **性格特点**：出场行为是否与性格设定一致
- **背景故事**：提及的背景信息是否正确
- **关系描述**：与其他角色的关系是否符合设定
- **实力等级**：实力描述是否与当前等级一致

### 输出检查结果

```
## 角色出场检查报告：{角色名}

### 新设定
{新设定的描述}

### 出场章节分析

| 章节 | 出场内容 | 是否符合 | 备注 |
|-----|---------|---------|------|
| 第3章 | 角色出场描述 | ✅ 符合 | |
| 第5章 | 角色出场描述 | ❌ 不符合 | 性格描述与新设定冲突 |
| 第10章 | 角色出场描述 | ⚠️ 部分符合 | 实力等级需要更新 |
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
李明笑道："你这笨蛋，连这么简单的题目都不会。"
```

**新设定**：李明性格腹黑，表面温柔但实际阴险

**修改后**（符合新设定）：
```
李明心中冷笑，脸上却温和地笑道："你这笨蛋，连这么简单的题目都不会。"（内心OS：真是愚蠢的人类）
```

### 修改原则

- **保留角色出场事实**：角色的出场不能被删除
- **调整描述方式**：通过词语替换、添加内心os等方式调整
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
用户输入：/webnovel-role 李明 主角的好友，表面温柔但实际腹黑，是主角小时候的玩伴

1. 解析参数：
   - 角色名：李明
   - 角色描述：主角的好友，表面温柔但实际腹黑，是主角小时候的玩伴

2. 检查角色是否存在：
   - 角色已存在

3. 更新角色信息：
   - 更新 description: "主角的好友，表面温柔但实际腹黑，是主角小时候的玩伴"

4. 获取出场章节：
   - 第3章、第5章、第10章、第15章

5. 检查出场内容：
   - 第3章：✅ 符合
   - 第5章：❌ 不符合（性格描述过于直白）
   - 第10章：✅ 符合
   - 第15章：⚠️ 需要调整（添加腹黑内心os）

6. 修正不符合的章节：
   - 向用户展示修改方案
   - 确认后执行修改
```

---

## 输出格式

### 成功输出

```markdown
# 角色管理完成：{角色名}

## 操作类型
{添加新角色 / 更新角色信息}

## 角色信息
- **角色名**: {角色名}
- **层级**: {核心/重要/次要/装饰}
- **首次出场**: 第{数字}章
- **最后出场**: 第{数字}章

## 角色设定
{角色描述}

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
2. 角色名是否有效
3. 是否有权限修改文件
```
