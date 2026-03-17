---
name: webnovel-role
description: 创建或修改角色卡信息，支持角色设定管理、出场章节检查与一致性修正。
allowed-tools: Read Write Edit Grep Bash Task AskUserQuestion
---

# Role Management Skill

## 目标

- 支持命令格式：`/webnovel-role 角色A 角色信息描述`
- 支持导入外部文件：`/webnovel-role --file <文件路径> [--file <文件路径2> ...]`
- 若角色不存在，添加角色卡并写入设定
- 若角色已存在，修改已有角色卡
- 查看角色的出场章节
- 检查所有出场章节中角色出场内容是否符合新设定
- 若有不符合新设定的，需要修改那些不符合设定的章节内容
- 支持外部文件解析，检测冲突并由用户确认处理方式

## 角色层级说明

角色按重要程度分为以下层级：

| 层级 | 说明 | 角色卡管理 |
|------|------|-----------|
| **核心** | 主角等主线关键人物 | 完整角色卡（主角卡） |
| **重要** | 主要配角、重要反派 | 完整角色卡 |
| **次要** | 推动特定剧情，有一定描写 | 简化角色卡 |
| **装饰** | 龙套角色，仅推动剧情，无需重点描写 | **轻量级记录**（龙套角色库） |

**龙套角色（装饰）特点**：
- 仅用于推动剧情，不需要详细的性格、动机、关系设定
- 不创建完整角色卡，自动记录到 `设定集/角色库/龙套角色/` 目录
- 章节写作完成后自动检测并记录新出场的龙套角色

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
- [ ] Step 1: 解析命令参数（支持 --file 导入外部文件）
- [ ] Step 1.5: 解析外部文件（支持 Markdown/Word/图片/视频）
- [ ] Step 2: 加载项目数据（state.json）
- [ ] Step 3: 检查角色是否存在
- [ ] Step 3.5: 检测冲突（当角色已存在时）
- [ ] Step 3.6: 用户确认冲突处理方式
- [ ] Step 4: 添加或更新角色信息
- [ ] Step 5: 获取角色出场章节
- [ ] Step 6: 检查出场内容是否符合新设定
- [ ] Step 7: 修正不符合设定的章节内容
```

---

## Step 1: 解析命令参数

从用户输入中提取：
- **角色名**：命令的第一个参数（当不使用 --file 时）
- **角色描述**：命令的剩余部分（角色信息描述）
- **--file 参数**：支持导入一个或多个外部文件

### 格式示例

#### 直接输入模式
```
/webnovel-role 角色A 角色信息描述
/webnovel-role 李明 主角的好友，表面温柔但实际腹黑，是主角小时候的玩伴
/webnovel-role 女主角 聪明伶俐的古灵精怪少女，与主角不打不相识
```

#### 文件导入模式
```
/webnovel-role --file <文件路径1> [--file <文件路径2> ...]
/webnovel-role --file 角色设定.md
/webnovel-role --file 角色设定.docx
/webnovel-role --file 角色图.png --file 角色视频.mp4
/webnovel-role --file 角色1.md --file 角色2.docx --file 角色3.jpg
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
name: 角色名
tier: 重要
aliases:
  - 别名1
  - 别名2
---

# 角色名

角色描述内容...
```

**JSON 格式**：
```json
{
  "角色名": {
    "name": "角色名",
    "tier": "重要",
    "aliases": ["别名1", "别名2"],
    "attributes": {
      "description": "角色描述",
      "personality": "性格特点",
      "background": "背景故事",
      "relationships": {}
    }
  }
}
```

---

### 多文件处理流程

当使用多个 --file 参数时：

1. **依次解析每个文件**：按顺序读取并解析外部文件
2. **提取角色信息**：从每个文件中提取角色名和属性
3. **合并角色数据**：将多个文件中的角色信息合并
4. **冲突检测**：检测同一角色的重复定义

```bash
# 示例：处理多个文件
/webnovel-role --file 角色设定1.md --file 角色设定2.json
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
- ✅ 如果用户指定了多个文件，只处理这些指定文件

**示例**：
```bash
# ✅ 正确：只读取用户指定的文件
/webnovel-role --file 角色设定.md
# 应该只读取 "角色设定.md" 这一个文件

/webnovel-role --file 角色1.md --file 角色2.md
# 应该只读取 "角色1.md" 和 "角色2.md" 这两个文件

# ❌ 错误：禁止的行为
/webnovel-role --file *.md  # 禁止批量读取
/webnovel-role --file ./  # 禁止读取目录
```

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
1. 手动输入角色描述
2. 尝试 OCR 提取文字（仅图片）
3. 跳过此文件
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
| 角色已存在 | 更新角色信息（进入冲突检测） |

---

## Step 3.5: 检测冲突

当从外部文件导入角色信息，且角色已存在时，需要检测新旧设定之间的冲突。

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

    # 检查 tier 冲突
    if old_entity.get('tier') != new_entity.get('tier'):
        conflicts.append({
            'field': 'tier',
            'old_value': old_entity.get('tier'),
            'new_value': new_entity.get('tier')
        })

    return conflicts
```

### 冲突类型

| 冲突类型 | 说明 | 处理方式 |
|---------|------|---------|
| **核心属性冲突** | tier、name 等核心属性冲突 | 必须用户确认 |
| **次要属性冲突** | description、personality 等非核心属性 | 展示差异，用户选择 |
| **别名冲突** | 角色别名不一致 | 合并新旧别名 |

---

## Step 3.6: 用户确认冲突处理

当检测到冲突时，需要向用户展示冲突并确认处理方式。

### 用户确认交互

```markdown
## 检测到冲突：{角色名}

### 已有设定
- **层级**: {old_tier}
- **描述**: {old_description}
- **别名**: {old_aliases}

### 新导入信息
- **层级**: {new_tier}
- **描述**: {new_description}
- **别名**: {new_aliases}

### 冲突详情
| 字段 | 旧值 | 新值 |
|-----|------|------|
| tier | 重要 | 核心 |
| description | 原描述 | 新描述 |

### 请选择处理方式
- [ ] **使用新值**：完全使用导入的信息替换旧设定
- [ ] **保留旧值**：保留已有设定，忽略导入的冲突信息
- [ ] **合并**：保留两者，创建一个包含所有信息的综合版本
```

### 处理优先级

- **命令行参数** > **文件参数** > **已有设定**
- 当同时存在命令行参数和文件参数时，以命令行参数为准

---

## Step 4: 添加或更新角色信息

### 4.1 角色不存在：创建新角色

使用以下命令添加新角色：

```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" entity add 角色名 --type 角色 --tier 次要 --desc "角色描述"
```

**注意**：如果需要将角色标记为龙套角色（仅推动剧情，无需重点描写），使用 `--tier 装饰`：
```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" entity add 角色名 --type 角色 --tier 装饰 --desc "角色描述"
```
此角色将记录到龙套角色库，无需创建完整角色卡。

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
    "relationships": {},
    "inner_monologue": {
      "enabled": true,
      "frequency": "高|中|低|无",
      "style": {
        "language": "语言风格",
        "content": "内容特点",
        "length": "长篇大论|简短精悍|点到即止",
        "sentence_pattern": "疑问句居多|陈述句为主|感叹强烈"
      },
      "examples": ["示例1", "示例2"],
      "trigger_scenes": ["触发场景1", "触发场景2"],
      "taboos": ["禁忌1", "禁忌2"]
    }
  },
  "first_appearance": 1,
  "last_appearance": 10
}
```

### 内心独白字段说明

| 字段 | 说明 | 可选值 |
|------|------|-------|
| inner_monologue.enabled | 是否启用内心独白 | true/false |
| inner_monologue.frequency | 使用频率 | 高/中/低/无 |
| inner_monologue.style.language | 内心独白语言风格 | 简洁有力/文绉绉/幽默/毒舌/直白等 |
| inner_monologue.style.content | 内心独白内容特点 | 擅长自嘲/喜欢分析/情绪化/理性冷静等 |
| inner_monologue.style.length | 内心独白长度 | 长篇大论/简短精悍/点到即止 |
| inner_monologue.style.sentence_pattern | 句式特点 | 疑问句居多/陈述句为主/感叹强烈 |
| inner_monologue.examples | 内心独白示例 | 字符串数组 |
| inner_monologue.trigger_scenes | 触发场景 | 字符串数组 |
| inner_monologue.taboos | 内心独白禁忌 | 字符串数组 |

**注意**：内心独白字段是可选的，如果不设置或 enabled 为 false，则该角色不使用内心独白。

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
