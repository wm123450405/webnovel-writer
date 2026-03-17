---
name: webnovel-power
description: 创建或修改功法/法术/阵法/秘术/技巧等能力设定，支持能力设定管理、出场章节检查与一致性修正。
allowed-tools: Read Write Edit Grep Bash Task AskUserQuestion
---

# Power Management Skill

## 目标

- 支持命令格式：`/webnovel-power 功法名 功法信息描述`
- 支持导入外部文件：`/webnovel-power --file <文件路径> [--file <文件路径2> ...]`
- 若功法不存在，添加功法卡并写入设定
- 若功法已存在，修改已有功法信息
- 查看功法的出场章节
- 检查所有出场章节中功法出场内容是否符合新设定
- 若有不符合新设定的，需要修改那些不符合设定的章节内容
- 支持外部文件解析，检测冲突并由用户确认处理方式

## 能力类型说明

| 类型 | 说明 | 示例 |
|------|------|------|
| 功法 | 主修心法、修炼体系 | 《先天混元功》《九转玄功》 |
| 法术 | 攻击/防御/辅助技能 | 天雷掌、御剑术、隐身术 |
| 阵法 | 组合阵法、禁制 | 困仙阵、护山大阵 |
| 秘术 | 禁术、爆发技、秘传 | 燃血大法、天魔解体 |
| 技巧 | 实战技巧、秘技 | 分光剑影、追星逐月 |
| 神通 | 特殊天赋能力 | 千里眼、顺风耳 |
| 异火 | 天地异火 | 琉璃净火、幽冥鬼火 |
| 炼丹 | 炼丹术、丹道传承 | 《神农百草经》《九转丹道》 |

## Project Root Guard（必须先确认）

- Claude Code 的"工作区根目录"不一定等于"书项目根目录"。常见结构：工作区为 `D:\wk\xiaoshuo`，书项目为 `D:\wk\xiaoshuo\凡人资本论`。
- 必须先解析真实书项目根（必须包含 `.webnovel/state.json`），后续所有读写路径都以该目录为准。
- **禁止**在插件目录 `${CLAUDE_PLUGIN_ROOT}/` 下读取或写入项目文件

环境设置（bash 命令执行前）：
```bash
export WORKSPACE_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"

if [ -z "${CLAUDE_PLUGIN_ROOT}" ] || [ ! -d "${CLAUDE_PLUGIN_ROOT}/skills/webnovel-power" ]; then
  echo "ERROR: 未设置 CLAUDE_PLUGIN_ROOT 或缺少目录: ${CLAUDE_PLUGIN_ROOT}/skills/webnovel-power" >&2
  exit 1
fi
export SKILL_ROOT="${CLAUDE_PLUGIN_ROOT}/skills/webnovel-power"

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
功法管理进度：
- [ ] Step 1: 解析命令参数（支持 --file 导入外部文件）
- [ ] Step 1.5: 解析外部文件（支持 Markdown/Word/图片/视频）
- [ ] Step 2: 加载项目数据（state.json）
- [ ] Step 3: 检查功法是否存在
- [ ] Step 3.5: 检测冲突（当功法已存在时）
- [ ] Step 3.6: 用户确认冲突处理方式
- [ ] Step 4: 添加或更新功法信息
- [ ] Step 5: 获取功法出场章节
- [ ] Step 6: 检查出场内容是否符合新设定
- [ ] Step 7: 修正不符合设定的章节内容
```

---

## Step 1: 解析命令参数

从用户输入中提取：
- **功法名**：命令的第一个参数（当不使用 --file 时）
- **功法描述**：命令的剩余部分（功法信息描述）
- **--file 参数**：支持导入一个或多个外部文件

### 格式示例

#### 直接输入模式
```
/webnovel-power 功法名 功法信息描述
/webnovel-power 天雷掌 主角在秘境中获得的雷系攻击法术，可召唤天雷攻击敌人，威力巨大但消耗极大
/webnovel-power 先天混元功 顶级修炼功法，修炼至大成可突破境界瓶颈，附带护体神光
```

#### 文件导入模式
```
/webnovel-power --file <文件路径1> [--file <文件路径2> ...]
/webnovel-power --file 功法设定.md
/webnovel-power --file 功法设定.docx
/webnovel-power --file 功法图.png --file 功法视频.mp4
/webnovel-power --file 功法1.md --file 功法2.docx
```

---

### 外部文件支持格式

#### 支持的文件类型
| 文件类型 | 扩展名 | 处理方式 |
|---------|-------|---------|
| Markdown | .md | 解析 YAML frontmatter 或正文内容 |
| Word 文档 | .docx | 使用 python-docx 提取文本 |
| 图片 | .jpg, .jpeg, .png | 提示用户 OCR 提取文字或手动描述 |
| 视频 | .mp4, .avi, .mkv | 提示用户提取字幕或手动描述 |

#### 文件内容格式

**Markdown 格式（推荐）**：
```markdown
---
name: 功法名
power_type: 功法
tier: 重要
element: 雷
 cultivation_level: 筑基
---

# 功法名

功法描述内容...
```

**JSON 格式**：
```json
{
  "功法名": {
    "name": "功法名",
    "power_type": "功法",
    "tier": "重要",
    "element": "雷",
    "cultivation_level": "筑基",
    "attributes": {
      "description": "功法描述",
      "abilities": ["能力1", "能力2"],
      "consumption": "消耗描述",
      "cooldown": "冷却时间"
    }
  }
}
```

---

### 多文件处理流程

当使用多个 --file 参数时：

1. **依次解析每个文件**：按顺序读取并解析外部文件
2. **提取功法信息**：从每个文件中提取功法名和属性
3. **合并功法数据**：将多个文件中的功法信息合并
4. **冲突检测**：检测同一功法的重复定义

---

## Step 1.5: 解析外部文件

当使用 --file 参数时，需要解析外部文件内容。

### ⚠️ 安全约束：只读取指定文件

**严格禁止**：
- ❌ 禁止使用 find/grep 等命令扫描目录下的其他文件
- ❌ 禁止读取用户未指定的文件
- ❌ 禁止自动遍历目录读取文件
- ❌ 禁止使用通配符（如 *.md）批量读取

**必须遵守**：
- ✅ 只读取用户通过 --file 参数明确指定的文件
- ✅ 读取文件前验证文件路径是否与参数完全匹配

---

## Step 2: 加载项目数据

```bash
cat "$PROJECT_ROOT/.webnovel/state.json"
```

---

## Step 3: 检查功法是否存在

使用以下命令查询功法是否已存在：

```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" status -- --focus entity
```

或直接使用 Grep 搜索：

```bash
grep -r "功法名" "$PROJECT_ROOT/.webnovel/" 2>/dev/null
grep -r "功法名" "$PROJECT_ROOT/设定集/" 2>/dev/null
```

### 判定逻辑

| 情况 | 后续操作 |
|------|---------|
| 功法不存在 | 创建新功法卡 |
| 功法已存在 | 更新功法信息（进入冲突检测） |

---

## Step 3.5: 检测冲突

当从外部文件导入功法信息，且功法已存在时，需要检测新旧设定之间的冲突。

### 冲突类型

| 冲突类型 | 说明 | 处理方式 |
|---------|------|---------|
| **核心属性冲突** | power_type、tier、cultivation_level 等核心属性冲突 | 必须用户确认 |
| **次要属性冲突** | description、abilities 等非核心属性 | 展示差异，用户选择 |
| **别名冲突** | 功法别名不一致 | 合并新旧别名 |

---

## Step 3.6: 用户确认冲突处理

当检测到冲突时，需要向用户展示冲突并确认处理方式。

### 用户确认交互

```markdown
## 检测到冲突：{功法名}

### 已有设定
- **类型**: {old_power_type}
- **层级**: {old_tier}
- **境界要求**: {old_cultivation_level}
- **描述**: {old_description}

### 新导入信息
- **类型**: {new_power_type}
- **层级**: {new_tier}
- **境界要求**: {new_cultivation_level}
- **描述**: {new_description}

### 请选择处理方式
- [ ] **使用新值**：完全使用导入的信息替换旧设定
- [ ] **保留旧值**：保留已有设定，忽略导入的冲突信息
- [ ] **合并**：保留两者，创建一个包含所有信息的综合版本
```

### 处理优先级

- **命令行参数** > **文件参数** > **已有设定**
- 当同时存在命令行参数和文件参数时，以命令行参数为准

---

## Step 4: 添加或更新功法信息

### 4.1 功法不存在：创建新功法

#### 检查/创建功法库目录

```bash
# 创建功法库目录
mkdir -p "$PROJECT_ROOT/设定集/功法库"
mkdir -p "$PROJECT_ROOT/设定集/功法库/功法"
mkdir -p "$PROJECT_ROOT/设定集/功法库/法术"
mkdir -p "$PROJECT_ROOT/设定集/功法库/阵法"
mkdir -p "$PROJECT_ROOT/设定集/功法库/秘术"
mkdir -p "$PROJECT_ROOT/设定集/功法库/技巧"
mkdir -p "$PROJECT_ROOT/设定集/功法库/神通"
mkdir -p "$PROJECT_ROOT/设定集/功法库/异火"
mkdir -p "$PROJECT_ROOT/设定集/功法库/炼丹"
```

#### 功法卡模板

```markdown
---
name: {功法名}
power_type: {功法/法术/阵法/秘术/技巧/神通/异火/炼丹}
tier: 核心|重要|次要|装饰
element: {属性/元素}
cultivation_level: {境界要求}
sub_type: {子类型}
---

# {功法名}

## 概述

{功法的整体描述}

## 基本信息

| 属性 | 内容 |
|------|------|
| 类型 | {功法/法术/阵法/秘术/技巧/神通/异火/炼丹} |
| 层级 | {核心/重要/次要/装饰} |
| 属性 | {雷/火/水/木/金/土/冰/风/光/暗/无} |
| 境界要求 | {练气/筑基/金丹/元婴/化神/炼虚/大乘} |
| 修炼难度 | {简单/中等/困难/极难} |

## 能力效果

### 主能力

{主能力的详细描述}

### 辅助能力

{辅助能力的描述}

### 特殊效果

{特殊效果的描述}

## 消耗与限制

| 消耗类型 | 消耗量 |
|---------|-------|
| 法力消耗 | {数值} |
| 气血消耗 | {数值} |
| 冷却时间 | {时间} |
| 使用限制 | {限制条件} |

## 修炼条件

### 资质要求

{资质要求描述}

### 前置功法

{前置功法要求}

### 资源需求

{修炼资源需求}

## 进阶路线

### 第一层/初期

{修炼内容}

### 第二层/中期

{修炼内容}

### 第三层/大成

{修炼内容}

## 历史背景

{功法创立的背景故事}

## 相关人物

| 人物 | 关系 | 描述 |
|------|------|------|
| 人物名 | 创始人/传承者 | 描述 |

## 出场章节

- 首次出场：第{数字}章
```

#### 保存功法文件

```bash
# 根据能力类型选择保存路径
case "$POWER_TYPE" in
  "功法")
    SAVE_DIR="$PROJECT_ROOT/设定集/功法库/功法"
    ;;
  "法术")
    SAVE_DIR="$PROJECT_ROOT/设定集/功法库/法术"
    ;;
  "阵法")
    SAVE_DIR="$PROJECT_ROOT/设定集/功法库/阵法"
    ;;
  "秘术")
    SAVE_DIR="$PROJECT_ROOT/设定集/功法库/秘术"
    ;;
  "技巧")
    SAVE_DIR="$PROJECT_ROOT/设定集/功法库/技巧"
    ;;
  "神通")
    SAVE_DIR="$PROJECT_ROOT/设定集/功法库/神通"
    ;;
  "异火")
    SAVE_DIR="$PROJECT_ROOT/设定集/功法库/异火"
    ;;
  "炼丹")
    SAVE_DIR="$PROJECT_ROOT/设定集/功法库/炼丹"
    ;;
  *)
    SAVE_DIR="$PROJECT_ROOT/设定集/功法库"
    ;;
esac

# 保存文件
SAVE_PATH="${SAVE_DIR}/${POWER_NAME}.md"
cat > "$SAVE_PATH" << 'EOF'
{功法内容}
EOF
```

### 4.3 注册到 index.db（必须）

创建或更新功法后，必须注册到 index.db：

```bash
# 注册功法到 index.db
python -c "
import sys
sys.path.insert(0, '${SCRIPTS_DIR}')
from data_modules.index_manager import IndexManager

im = IndexManager('${PROJECT_ROOT}/.webnovel/config.json')
im.upsert_entity({
    'id': '功法名',
    'type': '招式',
    'name': '功法名',
    'power_type': '功法',
    'tier': '次要',
    'desc': '功法描述',
    'element': '雷',
    'cultivation_level': '筑基'
}, update_metadata=True)
print('功法已注册到 index.db')
"
```

### 4.2 功法已存在：更新功法信息

使用以下命令更新功法：

```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" entity update 功法名 --description "新功法描述"
```

### 功法卡格式

更新或创建的功法信息应包含：
```json
{
  "id": "功法名",
  "name": "功法名",
  "type": "招式",
  "power_type": "功法/法术/阵法/秘术/技巧/神通/异火/炼丹",
  "tier": "核心|重要|次要|装饰",
  "element": "属性",
  "cultivation_level": "境界要求",
  "aliases": ["别名1", "别名2"],
  "attributes": {
    "description": "功法描述",
    "abilities": ["能力1", "能力2"],
    "consumption": "消耗描述",
    "cooldown": "冷却时间",
    "difficulty": "修炼难度",
    "history": "历史背景"
  },
  "first_appearance": 1,
  "last_appearance": 10
}
```

---

## Step 5: 获取功法出场章节

从索引数据库或 state.json 获取功法出场章节：

```bash
# 查看功法出场信息
python -c "
import sys
import json
sys.path.insert(0, '${SCRIPTS_DIR}')
from data_modules.state_manager import StateManager
sm = StateManager()
entity = sm.get_entity('功法名', '招式')
if entity:
    print('首次出场:', entity.get('first_appearance', '未知'))
    print('最后出场:', entity.get('last_appearance', '未知'))
    print(json.dumps(entity, indent=2, ensure_ascii=False))
"
```

---

## Step 6: 检查出场内容是否符合新设定

对于每个出场章节：

1. 读取章节内容
2. 查找功法出场段落
3. 分析出场内容是否与新设定一致
4. 标记不一致的章节

### 检查要点

根据新设定检查以下内容：
- **能力效果**：功法展现的能力是否与设定一致
- **消耗描述**：法力/气血消耗是否与设定一致
- **境界匹配**：使用时的境界描述是否正确
- **名称/别名**：是否使用正确名称

### 输出检查结果

```
## 功法出场检查报告：{功法名}

### 新设定
{新设定的描述}

### 出场章节分析

| 章节 | 出场内容 | 是否符合 | 备注 |
|-----|---------|---------|------|
| 第3章 | 功法出场描述 | ✅ 符合 |
| 第5章 | 功法出场描述 | ❌ 不符合 | 能力描述与新设定冲突 |
| 第10章 | 功法出场描述 | ⚠️ 部分符合 | 消耗描述需要更新 |
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
天雷掌只是普通的雷系法术，威力有限。
```

**新设定**：天雷掌是雷系顶级攻击法术，可召唤天雷

**修改后**（符合新设定）：
```
天雷掌不愧为雷系顶级法术，只见天空骤然变色，一道水桶粗的天雷倾泻而下，威力惊人。
```

### 修改原则

- **保留功法出场事实**：功法的出现不能被删除
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
用户输入：/webnovel-power 天雷掌 主角在秘境中获得的雷系攻击法术，可召唤天雷攻击敌人，威力巨大但消耗极大

1. 解析参数：
   - 功法名：天雷掌
   - 功法描述：主角在秘境中获得的雷系攻击法术，可召唤天雷攻击敌人，威力巨大但消耗极大

2. 检查功法是否存在：
   - 功法不存在

3. 创建功法信息：
   - 创建功法卡
   - 保存到设定集/功法库/法术/天雷掌.md

4. 注册到 state.json：
   - 添加实体记录
```

---

## 输出格式

### 成功输出

```markdown
# 功法管理完成：{功法名}

## 操作类型
{添加新功法 / 更新功法信息}

## 功法信息
- **功法名**: {功法名}
- **类型**: {功法/法术/阵法/秘术/技巧/神通/异火/丹药}
- **层级**: {核心/重要/次要/装饰}
- **属性**: {雷/火/水/木/金/土/冰/风/光/暗/无}
- **境界要求**: {练气/筑基/金丹/元婴/化神/炼虚/大乘}
- **首次出场**: 第{数字}章

## 功法设定
{功法描述}

## 出场章节检查
- 共出场 {数字} 章
- 符合新设定：{数字} 章
- 需要修改：{数字} 章

## 保存位置
- 路径：`设定集/功法库/{类型}/{功法名}.md`
```

### 错误输出

```markdown
# 错误

{错误原因}

请检查：
1. 项目根目录是否正确
2. 功法名是否有效
3. 是否有权限创建文件
```

---

## 快捷命令参考

| 命令 | 说明 |
|------|------|
| `/webnovel-power 功法名` | 查询功法信息 |
| `/webnovel-power 功法名 描述` | 创建新功法 |
| `/webnovel-power --file 功法.md` | 从文件导入功法 |
| `/webnovel-power --list` | 列出所有功法 |
| `/webnovel-power --type 法术` | 按类型列出功法 |
