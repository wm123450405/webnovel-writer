---
name: webnovel-item
description: 创建或修改道具信息，支持道具设定管理、出场章节检查与一致性修正。
allowed-tools: Read Write Edit Grep Bash Task AskUserQuestion
---

# Item Management Skill

## 目标

- 支持命令格式：`/webnovel-item 道具名 道具信息描述`
- 支持导入外部文件：`/webnovel-item --file <文件路径> [--file <文件路径2> ...]`
- 若道具不存在，添加道具卡并写入设定
- 若道具已存在，修改已有道具信息
- 查看道具的出场章节
- 检查所有出场章节中道具出场内容是否符合新设定
- 若有不符合新设定的，需要修改那些不符合设定的章节内容
- 支持外部文件解析，检测冲突并由用户确认处理方式

## 道具类型说明

道具按类型分类存储在不同的子目录下：

| 类型 | 说明 | 示例 | 存储目录 |
|------|------|------|---------|
| 丹药 | 修炼/疗伤/突破等丹药 | 筑基丹、破境丹、养魂丹 | 设定集/道具库/丹药/ |
| 法宝 | 储物/攻防/辅助法宝 | 储物戒指、青锋剑、护盾 | 设定集/道具库/法宝/ |
| 符箓 | 符咒、灵符、阵符 | 护身符、传讯符、爆炸符 | 设定集/道具库/符箓/ |
| 兵器 | 武器、盔甲、盾牌 | 长剑、长枪、战甲 | 设定集/道具库/兵器/ |
| 防具 | 防护类装备 | 护腕、护心镜、战靴 | 设定集/道具库/防具/ |
| 材料 | 天材地宝、炼器材料 | 玄铁、灵草、妖丹 | 设定集/道具库/材料/ |
| 灵宠 | 宠物、坐骑、灵兽 | 灵狐、飞鹰、麒麟 | 设定集/道具库/灵宠/ |
| 阵法 | 阵盘、阵旗、阵图 | 困仙阵、传送阵 | 设定集/道具库/阵法/ |
| 信物 | 身份凭证、任务信物 | 掌门令、地图残片 | 设定集/道具库/信物/ |
| 日常 | 日常生活用品 | 银两、衣物、食物 | 设定集/道具库/日常/ |
| 其他 | 无法归类的道具 | 特殊物品 | 设定集/道具库/其他/ |

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
- [ ] Step 1: 解析命令参数（支持 --file 导入外部文件）
- [ ] Step 1.5: 解析外部文件（支持 Markdown/Word/图片/视频）
- [ ] Step 2: 加载项目数据（state.json）
- [ ] Step 3: 检查道具是否存在
- [ ] Step 3.5: 检测冲突（当道具已存在时）
- [ ] Step 3.6: 用户确认冲突处理方式
- [ ] Step 4: 添加或更新道具信息
- [ ] Step 5: 获取道具出场章节
- [ ] Step 6: 检查出场内容是否符合新设定
- [ ] Step 7: 修正不符合设定的章节内容
```

---

## Step 1: 解析命令参数

从用户输入中提取：
- **道具名**：命令的第一个参数（当不使用 --file 时）
- **道具描述**：命令的剩余部分（道具信息描述）
- **--file 参数**：支持导入一个或多个外部文件

### 格式示例

#### 直接输入模式
```
/webnovel-item 道具名 道具信息描述
/webnovel-item 玄元丹 主角在秘境中获得的疗伤圣药，可瞬间恢复严重伤势，副作用是会虚弱三天
/webnovel-item 青锋剑 主角的随身佩剑，下品法器，削铁如泥，是主角家族传承之物
/webnovel-item 储物戒指 内含十丈空间的储物法宝，可存放活物，价值连城
```

#### 文件导入模式
```
/webnovel-item --file <文件路径1> [--file <文件路径2> ...]
/webnovel-item --file 道具设定.md
/webnovel-item --file 道具设定.docx
/webnovel-item --file 道具图.png --file 道具视频.mp4
/webnovel-item --file 道具1.md --file 道具2.docx
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
name: 道具名
tier: 重要
type: 物品
aliases:
  - 别名1
  - 别名2
attributes:
  category: 法宝
  rarity: 上品
  abilities:
    - 能力1
    - 能力2
---

# 道具名

道具描述内容...
```

**JSON 格式**：
```json
{
  "道具名": {
    "name": "道具名",
    "type": "物品",
    "tier": "重要",
    "aliases": ["别名1", "别名2"],
    "attributes": {
      "description": "道具描述",
      "category": "法宝",
      "rarity": "上品",
      "abilities": ["能力1", "能力2"],
      "owner": "持有者",
      "history": "历史背景"
    }
  }
}
```

---

### 多文件处理流程

当使用多个 --file 参数时：

1. **依次解析每个文件**：按顺序读取并解析外部文件
2. **提取道具信息**：从每个文件中提取道具名和属性
3. **合并道具数据**：将多个文件中的道具信息合并
4. **冲突检测**：检测同一道具的重复定义

```bash
# 示例：处理多个文件
/webnovel-item --file 道具设定1.md --file 道具设定2.json
```

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

### 文件解析函数

```python
import os
import json
from pathlib import Path

# 支持的文件格式
SUPPORTED_EXTENSIONS = {
    '.md': 'markdown',
    '.json': 'json',
    '.docx': 'word',
    '.jpg': 'image',
    '.jpeg': 'image',
    '.png': 'image',
    '.mp4': 'video',
    '.avi': 'video',
    '.mkv': 'video',
}

def parse_external_file(file_path: str) -> dict:
    """解析外部文件，支持多种格式"""
    ext = Path(file_path).suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"不支持的文件格式: {ext}")

    file_type = SUPPORTED_EXTENSIONS[ext]

    if file_type == 'json':
        with open(file_path, encoding='utf-8') as f:
            return json.load(f)
    elif file_type == 'markdown':
        return parse_markdown_content(file_path)
    elif file_type == 'word':
        return parse_word_document(file_path)
    elif file_type == 'image':
        return {'body': '', 'media_type': 'image', 'path': file_path}
    elif file_type == 'video':
        return {'body': '', 'media_type': 'video', 'path': file_path}

def parse_markdown_content(file_path: str) -> dict:
    """解析 Markdown 文件，提取 YAML frontmatter 和正文"""
    with open(file_path, encoding='utf-8') as f:
        content = f.read()
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            import yaml
            frontmatter = yaml.safe_load(parts[1])
            body = parts[2].strip()
            return {'frontmatter': frontmatter, 'body': body}
    return {'body': content}

def parse_word_document(file_path: str) -> dict:
    """解析 Word 文档"""
    try:
        import docx
        doc = docx.Document(file_path)
        text = '\n'.join([p.text for p in doc.paragraphs])
        return {'body': text}
    except ImportError:
        return {'error': '请安装 python-docx: pip install python-docx'}
```

### 图片/视频文件处理

当检测到图片或视频文件时，提示用户：

```
⚠️ 检测到媒体文件：{文件路径}

图片/视频文件需要您提供文字描述，请选择：
1. 手动输入道具描述
2. 尝试 OCR 提取文字（仅图片）
3. 跳过此文件
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
| 道具已存在 | 更新道具信息（进入冲突检测） |

---

## Step 3.5: 检测冲突

当从外部文件导入道具信息，且道具已存在时，需要检测新旧设定之间的冲突。

### 冲突检测函数

```python
def detect_conflicts(old_entity: dict, new_entity: dict) -> list:
    """检测冲突项，返回冲突列表"""
    conflicts = []

    # 比较 attributes
    old_attrs = old_entity.get('attributes', {})
    new_attrs = new_entity.get('attributes', {})

    for key in set(old_attrs.keys()) | set(new_attrs.keys()):
        old_val = old_attrs.get(key)
        new_val = new_attrs.get(key)
        if old_val != new_val:
            conflicts.append({
                'field': f'attributes.{key}',
                'old_value': old_val,
                'new_value': new_val
            })

    # 检查 tier 和 category 冲突
    for field in ['tier', 'category', 'rarity']:
        if old_entity.get(field) != new_entity.get(field):
            conflicts.append({
                'field': field,
                'old_value': old_entity.get(field),
                'new_value': new_entity.get(field)
            })

    return conflicts
```

### 冲突类型

| 冲突类型 | 说明 | 处理方式 |
|---------|------|---------|
| **核心属性冲突** | tier、category、rarity 等核心属性冲突 | 必须用户确认 |
| **次要属性冲突** | description、abilities 等非核心属性 | 展示差异，用户选择 |
| **别名冲突** | 道具别名不一致 | 合并新旧别名 |

---

## Step 3.6: 用户确认冲突处理

当检测到冲突时，需要向用户展示冲突并确认处理方式。

### 用户确认交互

```markdown
## 检测到冲突：{道具名}

### 已有设定
- **层级**: {old_tier}
- **类别**: {old_category}
- **稀有度**: {old_rarity}
- **描述**: {old_description}

### 新导入信息
- **层级**: {new_tier}
- **类别**: {new_category}
- **稀有度**: {new_rarity}
- **描述**: {new_description}

### 冲突详情
| 字段 | 旧值 | 新值 |
|-----|------|------|
| tier | 重要 | 核心 |
| category | 法宝 | 丹药 |
| rarity | 上品 | 极品 |

### 请选择处理方式
- [ ] **使用新值**：完全使用导入的信息替换旧设定
- [ ] **保留旧值**：保留已有设定，忽略导入的冲突信息
- [ ] **合并**：保留两者，创建一个包含所有信息的综合版本
```

### 处理优先级

- **命令行参数** > **文件参数** > **已有设定**
- 当同时存在命令行参数和文件参数时，以命令行参数为准

---

## Step 4: 添加或更新道具信息

### 4.1 创建道具库目录结构

```bash
# 创建道具库目录
mkdir -p "$PROJECT_ROOT/设定集/道具库"
mkdir -p "$PROJECT_ROOT/设定集/道具库/丹药"
mkdir -p "$PROJECT_ROOT/设定集/道具库/法宝"
mkdir -p "$PROJECT_ROOT/设定集/道具库/符箓"
mkdir -p "$PROJECT_ROOT/设定集/道具库/兵器"
mkdir -p "$PROJECT_ROOT/设定集/道具库/防具"
mkdir -p "$PROJECT_ROOT/设定集/道具库/材料"
mkdir -p "$PROJECT_ROOT/设定集/道具库/灵宠"
mkdir -p "$PROJECT_ROOT/设定集/道具库/阵法"
mkdir -p "$PROJECT_ROOT/设定集/道具库/信物"
mkdir -p "$PROJECT_ROOT/设定集/道具库/日常"
mkdir -p "$PROJECT_ROOT/设定集/道具库/其他"
```

### 4.2 保存道具文件

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

#### 保存道具文件到分类目录

```bash
# 根据道具类别选择保存路径
ITEM_NAME="道具名"
ITEM_CATEGORY="法宝"  # 从道具描述中提取或由用户指定

case "$ITEM_CATEGORY" in
  "丹药")
    SAVE_DIR="$PROJECT_ROOT/设定集/道具库/丹药"
    ;;
  "法宝")
    SAVE_DIR="$PROJECT_ROOT/设定集/道具库/法宝"
    ;;
  "符箓")
    SAVE_DIR="$PROJECT_ROOT/设定集/道具库/符箓"
    ;;
  "兵器")
    SAVE_DIR="$PROJECT_ROOT/设定集/道具库/兵器"
    ;;
  "防具")
    SAVE_DIR="$PROJECT_ROOT/设定集/道具库/防具"
    ;;
  "材料")
    SAVE_DIR="$PROJECT_ROOT/设定集/道具库/材料"
    ;;
  "灵宠")
    SAVE_DIR="$PROJECT_ROOT/设定集/道具库/灵宠"
    ;;
  "阵法")
    SAVE_DIR="$PROJECT_ROOT/设定集/道具库/阵法"
    ;;
  "信物")
    SAVE_DIR="$PROJECT_ROOT/设定集/道具库/信物"
    ;;
  "日常")
    SAVE_DIR="$PROJECT_ROOT/设定集/道具库/日常"
    ;;
  *)
    SAVE_DIR="$PROJECT_ROOT/设定集/道具库/其他"
    ;;
esac

# 保存道具文件
SAVE_PATH="${SAVE_DIR}/${ITEM_NAME}.md"
cat > "$SAVE_PATH" << 'EOF'
---
name: {道具名}
category: {道具类别}
tier: 重要
rarity: 上品
---

# {道具名}

## 概述

{道具描述}

## 基本信息

| 属性 | 内容 |
|------|------|
| 类别 | {道具类别} |
| 层级 | 核心/重要/次要 |
| 稀有度 | 凡品/下品/中品/上品/极品/仙品/神品 |
| 持有者 | {持有者} |

## 能力效果

{道具能力描述}

## 获得方式

{道具获得方式描述}

## 历史背景

{道具历史背景}

## 出场章节

- 首次出场：第{数字}章
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
    "category": "丹药|法宝|符箓|兵器|防具|材料|灵宠|阵法|信物|日常|其他",
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
