---
name: webnovel-map
description: 生成和管理各类地图信息，包括大陆地图、势力范围、城镇地图、院落地图、副本地图等，并保存到设定集/地图库目录。
allowed-tools: Read Write Edit Grep Bash Task AskUserQuestion
---

# Map Management Skill

## 目标

- 支持生成和管理各类地图信息
- 将地图文件保存到 `设定集/地图库` 目录
- **【新增】支持导入外部文件**：接受 Markdown、Word文档、图片等格式的地图描述文件
- 支持以下地图类型：
  - **大陆地图**：城镇、道路、河流、山脉、森林等信息
  - **势力范围**：势力、宗门、家族等位置范围信息
  - **城镇地图**：世家门派范围、重要街道、重要店面、地标建筑、城镇周边
  - **院落地图**：主殿、别院等位置信息
  - **副本地图**：特殊空间、领域、幻境等
  - **其他地图**：可用地图表示的知识库信息

## 地图类型说明

| 地图类型 | 说明 | 存储位置 |
|---------|------|---------|
| 大陆地图 | 整个大陆的区域划分、城镇分布、自然地貌 | 设定集/地图库/大陆地图/ |
| 势力范围 | 各宗门、势力、家族的领地 | 设定集/地图库/势力范围/ |
| 城镇地图 | 城内布局、建筑、街道 | 设定集/地图库/城镇地图/ |
| 院落地图 | 建筑内部布局、房间分布 | 设定集/地图库/院落地图/ |
| 副本地图 | 秘境、幻境、领域等特殊空间 | 设定集/地图库/副本地图/ |
| 其他地图 | 自定义地图类型 | 设定集/地图库/其他地图/ |

## Project Root Guard（必须先确认）

- Claude Code 的"工作区根目录"不一定等于"书项目根目录"。常见结构：工作区为 `D:\wk\xiaoshuo`，书项目为 `D:\wk\xiaoshuo\凡人资本论`。
- 必须先解析真实书项目根（必须包含 `.webnovel/state.json`），后续所有读写路径都以该目录为准。
- **禁止**在插件目录 `${CLAUDE_PLUGIN_ROOT}/` 下读取或写入项目文件

环境设置（bash 命令执行前）：
```bash
export WORKSPACE_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"

if [ -z "${CLAUDE_PLUGIN_ROOT}" ] || [ ! -d "${CLAUDE_PLUGIN_ROOT}/skills/webnovel-map" ]; then
  echo "ERROR: 未设置 CLAUDE_PLUGIN_ROOT 或缺少目录: ${CLAUDE_PLUGIN_ROOT}/skills/webnovel-map" >&2
  exit 1
fi
export SKILL_ROOT="${CLAUDE_PLUGIN_ROOT}/skills/webnovel-map"

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
地图管理进度：
- [ ] Step 1: 解析命令参数（支持 --file 导入外部文件）
- [ ] Step 1.5: 解析外部文件（支持 Markdown/Word/图片）
- [ ] Step 2: 加载项目数据
- [ ] Step 3: 检查地图库目录结构
- [ ] Step 4: 生成地图内容
- [ ] Step 5: 保存地图文件到设定集/地图库
- [ ] Step 6: 更新索引和状态
```

---

## Step 1: 解析命令参数

从用户输入中提取：
- **地图类型**：大陆地图/势力范围/城镇地图/院落地图/副本地图/其他
- **地图名称**：地图的名称
- **地图描述**：地图的详细信息
- **--file 参数**：支持导入一个或多个外部文件

### 格式示例

#### 直接输入模式
```
/webnovel-map 大陆地图 大陆名称 地图描述
/webnovel-map 势力范围 势力名称 势力范围描述
/webnovel-map 城镇地图 城镇名称 城镇描述
/webnovel-map 院落地图 院落名称 院落描述
/webnovel-map 副本地图 副本名称 副本描述
/webnovel-map 其他 其他类型名称 描述
```

#### 文件导入模式（推荐）
```
/webnovel-map --file <文件路径1> [--file <文件路径2> ...]
/webnovel-map --file 地图设定.md
/webnovel-map --file 地图设定.docx
/webnovel-map --file 地图图.png
/webnovel-map --file 地图1.md --file 地图2.docx
```

#### 混合模式
```
/webnovel-map --file 地图.md --type 城镇地图
/webnovel-map --file 地图.docx --name 新城镇
```

### 快捷命令

```
/webnovel-map --continent 大陆名称
/webnovel-map --realm 势力名称
/webnovel-map --town 城镇名称
/webnovel-map --courtyard 院落名称
/webnovel-map --dungeon 副本名称
/webnovel-map --other 其他类型
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
name: 地图名
map_type: 大陆地图
tier: 重要
---

# 地图名

地图描述内容...
```

**JSON 格式**：
```json
{
  "地图名": {
    "name": "地图名",
    "map_type": "大陆地图",
    "tier": "重要",
    "description": "地图描述",
    "locations": [
      {"name": "地点名", "position": "位置", "distance": "距离"}
    ]
  }
}
```

---

### 多文件处理流程

当使用多个 --file 参数时：

1. **依次解析每个文件**：按顺序读取并解析外部文件
2. **提取地图信息**：从每个文件中提取地图名称、类型和属性
3. **合并地图数据**：将多个文件中的地图信息合并
4. **冲突检测**：检测同一地图的重复定义

```bash
# 示例：处理多个文件
/webnovel-map --file 大陆设定1.md --file 大陆设定2.json
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
1. 手动输入地图描述
2. 尝试 OCR 提取文字（仅图片）
3. 跳过此文件
```

---

## Step 2: 加载项目数据

```bash
cat "$PROJECT_ROOT/.webnovel/state.json"
```

### 获取现有地图列表

```bash
# 查看已有地图
ls -la "$PROJECT_ROOT/设定集/地图库/" 2>/dev/null || echo "地图库目录不存在"

# 按类型查看
ls "$PROJECT_ROOT/设定集/地图库/大陆地图/" 2>/dev/null
ls "$PROJECT_ROOT/设定集/地图库/势力范围/" 2>/dev/null
ls "$PROJECT_ROOT/设定集/地图库/城镇地图/" 2>/dev/null
ls "$PROJECT_ROOT/设定集/地图库/院落地图/" 2>/dev/null
ls "$PROJECT_ROOT/设定集/地图库/副本地图/" 2>/dev/null
ls "$PROJECT_ROOT/设定集/地图库/其他地图/" 2>/dev/null
```

---

## Step 3: 检查/创建地图库目录结构

地图库目录结构：
```
设定集/
└── 地图库/
    ├── 大陆地图/
    │   └── {大陆名}.md
    ├── 势力范围/
    │   └── {势力名}.md
    ├── 城镇地图/
    │   └── {城镇名}.md
    ├── 院落地图/
    │   └── {院落名}.md
    ├── 副本地图/
    │   └── {副本名}.md
    └── 其他地图/
        └── {类型名}.md
```

### 创建目录结构

```bash
# 创建地图库目录
mkdir -p "$PROJECT_ROOT/设定集/地图库"
mkdir -p "$PROJECT_ROOT/设定集/地图库/大陆地图"
mkdir -p "$PROJECT_ROOT/设定集/地图库/势力范围"
mkdir -p "$PROJECT_ROOT/设定集/地图库/城镇地图"
mkdir -p "$PROJECT_ROOT/设定集/地图库/院落地图"
mkdir -p "$PROJECT_ROOT/设定集/地图库/副本地图"
mkdir -p "$PROJECT_ROOT/设定集/地图库/其他地图"
```

---

## Step 4: 生成地图内容

### 4.1 大陆地图模板

```markdown
---
map_type: 大陆地图
name: {大陆名}
tier: 重要
---

# {大陆名}

## 概述
{大陆的整体描述}

## 地理位置

### 边界
- 东部：{边界描述}
- 西部：{边界描述}
- 南部：{边界描述}
- 北部：{边界描述}

### 地形分布

| 区域 | 地形类型 | 主要特征 |
|------|---------|---------|
| 区域名 | 地形类型 | 特征描述 |

## 主要势力

### 顶级势力
- {势力名}：{势力描述}

### 中型势力
- {势力名}：{势力描述}

### 小型势力
- {势力名}：{势力描述}

## 城镇分布

| 城镇名 | 位置 | 特点 |
|--------|------|------|
| 城镇名 | 坐标/区域 | 特点描述 |

## 自然地貌

### 山脉

| 山脉名 | 位置 | 特点 |
|--------|------|------|
| 山脉名 | 位置 | 特点描述 |

### 河流

| 河流名 | 起点 | 终点 | 长度 |
|--------|------|------|------|
| 河流名 | 起点 | 终点 | 长度 |

### 森林

| 森林名 | 位置 | 特点 |
|--------|------|------|
| 森林名 | 位置 | 特点描述 |

## 道路网络

### 主要道路
- {道路名}：{起点} → {终点}

### 次要道路
- {道路名}：{起点} → {终点}

## 重要资源分布

| 资源类型 | 主要分布区域 | 开采难度 |
|---------|-------------|---------|
| 资源类型 | 分布区域 | 难度 |

## 气候分区

| 区域 | 气候类型 | 特征 |
|------|---------|------|
| 区域 | 气候类型 | 特征描述 |

## 历史变迁
{大陆形成和历史演变}
```

### 4.2 势力范围模板

```markdown
---
map_type: 势力范围
name: {势力名}
tier: 核心|重要|次要
sub_type: 宗门|家族|王朝|商会|其他
---

# {势力名}

## 概述
{势力的整体描述}

## 基本信息

| 属性 | 内容 |
|------|------|
| 势力类型 | 宗门/家族/王朝/商会/其他 |
| 总部位置 | {位置描述} |
| 势力范围 | {范围描述} |
| 创立时间 | {时间} |
| 当前领袖 | {领袖名} |
| 实力等级 | {等级描述} |

## 势力范围地图

### 核心区域
{核心区域的详细描述}

### 控制区域
{势力控制范围的详细描述}

### 影响力辐射区域
{影响力辐射范围的描述}

## 重要据点

| 据点名 | 类型 | 位置 | 功能 |
|--------|------|------|------|
| 据点名 | 类型 | 位置 | 功能描述 |

## 势力组成

### 门派/家族结构
{组织结构描述}

### 重要成员

| 职位 | 姓名 | 实力 | 职责 |
|------|------|------|------|
| 职位 | 姓名 | 实力 | 职责描述 |

### 势力版图

```
[势力范围示意图]
```

## 资源产出

| 资源类型 | 产地 | 年产量 |
|---------|------|-------|
| 资源类型 | 产地 | 产量 |

## 附属势力

- {附属势力名}：{关系描述}

## 与其他势力关系

| 势力 | 关系 | 说明 |
|------|------|------|
| 势力名 | 关系类型 | 说明描述 |
```

### 4.3 城镇地图模板

```markdown
---
map_type: 城镇地图
name: {城镇名}
tier: 重要|次要
sub_type: 主城|巨城|大城|中城|小城
---

# {城镇名}

## 概述
{城镇的整体描述}

## 基本信息

| 属性 | 内容 |
|------|------|
| 城镇等级 | 主城/巨城/大城/中城/小城 |
| 所属势力 | {势力名} |
| 人口规模 | {人口数量} |
| 地理位置 | {位置描述} |
| 特色产业 | {产业描述} |

## 城镇布局

### 城区划分

| 区域名 | 位置 | 主要功能 |
|--------|------|---------|
| 区域名 | 位置 | 功能描述 |

### 重要街道

| 街道名 | 起点 | 终点 | 特点 |
|--------|------|------|------|
| 街道名 | 起点 | 终点 | 特点描述 |

## 世家门派

| 名称 | 类型 | 位置 | 势力 |
|------|------|------|------|
| 名称 | 类型 | 位置 | 势力描述 |

## 重要建筑

### 官方机构

| 建筑名 | 功能 | 位置 |
|--------|------|------|
| 建筑名 | 功能描述 | 位置 |

### 商业设施

| 店名 | 类型 | 位置 | 特色 |
|------|------|------|------|
| 店名 | 类型 | 位置 | 特色描述 |

### 地标建筑

| 建筑名 | 类型 | 历史 | 特点 |
|--------|------|------|------|
| 建筑名 | 类型 | 历史 | 特点描述 |

## 居住区

| 区域 | 居民类型 | 特点 |
|------|---------|------|
| 区域 | 居民类型 | 特点描述 |

## 城镇周边

### 周边村落
- {村落名}：{描述}

### 周边资源
- {资源名}：{位置} - {描述}

### 交通路线
- {路线名}：{起点} → {终点}

## 城镇平面图

```
[城镇布局示意图]
```

## 著名人物
- {人物名}：{与城镇的关系}
```

### 4.4 院落地图模板

```markdown
---
map_type: 院落地图
name: {院落名}
tier: 重要|次要
sub_type: 宗门|王府|府邸|商铺|其他
---

# {院落名}

## 概述
{院落的整体描述}

## 基本信息

| 属性 | 内容 |
|------|------|
| 院落类型 | 宗门/王府/府邸/商铺/其他 |
| 所属势力 | {势力名} |
| 位置 | {位置描述} |
| 占地规模 | {规模描述} |
| 建成时间 | {时间} |

## 布局结构

### 整体布局

| 区域名 | 功能 | 位置 |
|--------|------|------|
| 区域名 | 功能描述 | 位置 |

### 主要建筑

#### 主殿/正厅

| 建筑名 | 功能 | 面积 | 特色 |
|--------|------|------|------|
| 建筑名 | 功能 | 面积 | 特色描述 |

#### 别院/偏殿

| 建筑名 | 功能 | 位置 |
|--------|------|------|
| 建筑名 | 功能描述 | 位置 |

## 详细分区

### 核心区域
{核心区域的详细描述和地图}

### 居住区域
{居住区域的详细描述}

### 修炼区域
{修炼区域的详细描述}

### 储藏区域
{储藏区域的详细描述}

### 防卫设施
{防卫设施的描述}

## 房间分布

| 房间名 | 楼层 | 功能 | 重要程度 |
|--------|------|------|---------|
| 房间名 | 楼层 | 功能 | 重要程度 |

## 重要设施

| 设施名 | 功能 | 位置 | 特殊要求 |
|--------|------|------|---------|
| 设施名 | 功能描述 | 位置 | 要求描述 |

## 平面图

```
[院落布局示意图]
```

## 人员分布
- {身份}：{位置} - {人数或主要人员}
```

### 4.5 副本地图模板

```markdown
---
map_type: 副本地图
name: {副本名}
tier: 核心|重要|次要
sub_type: 秘境|遗迹|幻境|领域|神府|其他
---

# {副本名}

## 概述
{副本的整体描述}

## 基本信息

| 属性 | 内容 |
|------|------|
| 副本类型 | 秘境/遗迹/幻境/领域/神府/其他 |
| 入口位置 | {位置描述} |
| 进入条件 | {条件描述} |
| 开放时间 | {时间限制} |
| 危险等级 | {等级} |
| 刷新周期 | {周期} |

## 空间结构

### 入口区域
{入口区域的描述}

### 核心区域
{核心区域的描述}

### 危险区域
{危险区域的描述}

### 特殊区域
{特殊区域的描述}

## 地形地貌

| 区域名 | 地形类型 | 特点 | 危险程度 |
|--------|---------|------|---------|
| 区域名 | 地形类型 | 特点 | 危险程度 |

## 重要地点

| 地点名 | 类型 | 位置 | 描述 |
|--------|------|------|------|
| 地点名 | 类型 | 位置 | 描述 |

## 怪物分布

| 怪物类型 | 主要区域 | 实力等级 | 掉落物品 |
|----------|---------|---------|---------|
| 怪物类型 | 区域 | 等级 | 掉落 |

## 资源分布

| 资源类型 | 主要分布 | 稀有度 | 采集难度 |
|----------|---------|--------|---------|
| 资源类型 | 分布区域 | 稀有度 | 难度 |

## 机关陷阱

| 机关名 | 位置 | 类型 | 效果 |
|--------|------|------|------|
| 机关名 | 位置 | 类型 | 效果描述 |

## 传承/奖励

### 传承
| 传承名 | 位置 | 条件 | 效果 |
|--------|------|------|------|
| 传承名 | 位置 | 条件 | 效果描述 |

### 宝物
| 宝物名 | 位置 | 稀有度 | 效果 |
|--------|------|--------|------|
| 宝物名 | 位置 | 稀有度 | 效果描述 |

## 地图结构图

```
[副本布局示意图]
```

## 攻略建议

### 推荐实力
{进入副本的推荐实力}

### 注意事项
- {注意事项1}
- {注意事项2}

### 最佳路线
{推荐的探索路线}
```

---

## Step 5: 保存地图文件

### 文件命名规则

```
{地图名}.md
```

### 保存路径

```bash
# 根据地图类型选择保存路径
case "$MAP_TYPE" in
  "大陆地图")
    SAVE_DIR="$PROJECT_ROOT/设定集/地图库/大陆地图"
    ;;
  "势力范围")
    SAVE_DIR="$PROJECT_ROOT/设定集/地图库/势力范围"
    ;;
  "城镇地图")
    SAVE_DIR="$PROJECT_ROOT/设定集/地图库/城镇地图"
    ;;
  "院落地图")
    SAVE_DIR="$PROJECT_ROOT/设定集/地图库/院落地图"
    ;;
  "副本地图")
    SAVE_DIR="$PROJECT_ROOT/设定集/地图库/副本地图"
    ;;
  "其他")
    SAVE_DIR="$PROJECT_ROOT/设定集/地图库/其他地图"
    ;;
esac

# 保存文件
SAVE_PATH="${SAVE_DIR}/${MAP_NAME}.md"
cat > "$SAVE_PATH" << 'EOF'
{地图内容}
EOF
```

---

## Step 6: 更新索引和状态

### 更新 state.json

```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" entity add 地图名 --type 地点 --tier 重要 --desc "地图描述"
```

### 注册到索引数据库

```bash
python -c "
import sys
sys.path.insert(0, '${SCRIPTS_DIR}')
from data_modules.index_manager import IndexManager
im = IndexManager('${PROJECT_ROOT}/.webnovel/config.json')
im.upsert_entity({
    'id': '地图名',
    'type': '地点',
    'name': '地图名',
    'map_type': '地图类型',
    'tier': '重要',
    'desc': '地图描述'
}, update_metadata=True)
"
```

---

## 输出格式

### 成功输出

```markdown
# 地图创建完成：{地图名}

## 地图类型
{地图类型}

## 保存位置
- 路径：`设定集/地图库/{类型}/{地图名}.md`
- 目录已创建：✅ / ❌

## 地图摘要
{地图的简要描述}

## 包含内容
- 核心区域：{数量}
- 重要地点：{数量}
- 关联势力：{数量}
```

### 错误输出

```markdown
# 错误

{错误原因}

请检查：
1. 项目根目录是否正确
2. 是否有权限创建目录
3. 地图名称是否有效
```

---

## 完整执行流程示例

```
用户输入：/webnovel-map 城镇地图 青阳城 青云宗下属的主要城市，商业繁荣

1. 解析参数：
   - 地图类型：城镇地图
   - 地图名称：青阳城
   - 地图描述：青云宗下属的主要城市，商业繁荣

2. 加载项目数据：
   - 确认项目根目录存在
   - 检查现有地图库

3. 创建目录结构：
   - 创建设定集/地图库/
   - 创建设定集/地图库/城镇地图/

4. 生成地图内容：
   - 使用城镇地图模板
   - 填充详细信息

5. 保存地图文件：
   - 保存到设定集/地图库/城镇地图/青阳城.md

6. 更新索引：
   - 注册到 state.json
   - 注册到 index.db
```

---

## 快捷命令参考

| 命令 | 说明 |
|------|------|
| `/webnovel-map 大陆地图 <名称>` | 创建大陆地图 |
| `/webnovel-map 势力范围 <名称>` | 创建势力范围 |
| `/webnovel-map 城镇地图 <名称>` | 创建城镇地图 |
| `/webnovel-map 院落地图 <名称>` | 创建院落地图 |
| `/webnovel-map 副本地图 <名称>` | 创建副本地图 |
| `/webnovel-map 其他 <名称>` | 创建其他类型地图 |
| `/webnovel-map --list` | 列出所有地图 |
| `/webnovel-map --type <类型>` | 查看指定类型的地图 |
| `/webnovel-map <名称> --update` | 更新现有地图 |
