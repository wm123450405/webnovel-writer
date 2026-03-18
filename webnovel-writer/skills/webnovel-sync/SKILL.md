---
name: webnovel-sync
description: 扫描并同步设定集目录和章节数据到数据库，支持增量更新、完整重建、归档处理。
allowed-tools: Read Write Edit Grep Bash Task AskUserQuestion
---

# Sync Settings Skill

## 目标

- 支持命令格式：`/webnovel-sync [--full] [--archive-deleted] [--chapters <范围>] [--entity <名称>]`
- 扫描整个 设定集 目录及其子目录
- 扫描章节目录，支持全部或部分章节扫描
- 读取所有 Markdown 文件及其内容
- 根据目录结构和 frontmatter 分类
- 同步到数据库 entities 表
- 支持增量更新和完整重建
- 支持将已删除的文件标记为归档
- 支持单个实体增量同步
- 验证实体类型格式，确保类型展示正确

## 设定集目录结构

```
设定集/
├── 角色库/           → type = '角色'
│   ├── 主角卡/
│   ├── 女主卡/
│   ├── 反派/
│   ├── 配角/
│   └── 龙套角色/
├── 道具库/           → type = 道具子类型
│   ├── 丹药/
│   ├── 法宝/
│   ├── 符箓/
│   ├── 兵器/
│   ├── 防具/
│   ├── 材料/
│   ├── 灵宠/
│   ├── 阵法/
│   ├── 信物/
│   ├── 日常/
│   ├── 其他/
│   └── 物品/
├── 地图库/           → type = 地点/星球/势力
│   ├── 地点/
│   ├── 星球/
│   └── 势力/
└── 其他设定/         → type = 世界观/境界/力量体系/金手指/设计
    ├── 世界观/
    ├── 境界/
    ├── 力量体系/
    ├── 金手指/
    └── 设计/
```

## 章节目录结构

```
正文/
├── 第1章/
│   └── 第1章.md
├── 第2章/
│   └── 第2章.md
└── ...
```

## Project Root Guard（必须先确认）

- Claude Code 的"工作区根目录"不一定等于"书项目根目录"。常见结构：工作区为 `D:\wk\xiaoshuo`，书项目为 `D:\wk\xiaoshuo\凡人资本论`。
- 必须先解析真实书项目根（必须包含 `.webnovel/state.json`），后续所有读写路径都以该目录为准。
- **禁止**在插件目录 `${CLAUDE_PLUGIN_ROOT}/` 下读取或写入项目文件

环境设置（bash 命令执行前）：
```bash
export WORKSPACE_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"

if [ -z "${CLAUDE_PLUGIN_ROOT}" ] || [ ! -d "${CLAUDE_PLUGIN_ROOT}/skills/webnovel-sync" ]; then
  echo "ERROR: 未设置 CLAUDE_PLUGIN_ROOT 或缺少目录: ${CLAUDE_PLUGIN_ROOT}/skills/webnovel-sync" >&2
  exit 1
fi
export SKILL_ROOT="${CLAUDE_PLUGIN_ROOT}/skills/webnovel-sync"

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
同步设置进度：
- [ ] Step 1: 解析命令参数（--full, --archive-deleted, --merge-pinyin, --chapters, --entity）
- [ ] Step 2: 确认项目根目录
- [ ] Step 3: 判断同步模式（设定集/章节/单个实体）
- [ ] Step 4: 扫描设定集目录结构（设定集模式）
- [ ] Step 5: 读取所有 Markdown 文件
- [ ] Step 6: 解析 frontmatter 和内容
- [ ] Step 7: 验证实体类型格式
- [ ] Step 8: 分类实体类型
- [ ] Step 9: 同步到数据库
- [ ] Step 10: 处理已删除文件（归档）
- [ ] Step 11: 检测拼音/英文命名实体
- [ ] Step 12: 归并或移除拼音/英文实体
- [ ] Step 13: 输出同步报告
```

---

## Step 1: 解析命令参数

支持的参数：
- `--full`: 完整重建，清空现有数据后重新导入
- `--archive-deleted`: 将数据库中存在但文件中已删除的实体标记为归档
- `--dry-run`: 模拟运行，不实际写入数据库
- `--merge-pinyin`: 自动归并拼音/英文命名的实体（默认开启）
- `--keep-pinyin`: 保留拼音/英文实体，不归并
- `--chapters <范围>`: 扫描章节，可选值：
  - `all`: 全部章节
  - `latest`: 最新章节（默认10章）
  - `1-100`: 指定范围章节
  - `50+`: 最新50章
- `--entity <名称>`: 单个实体增量同步，指定实体名称
- `--type <类型>`: 限定同步类型（角色/道具/地图/其他）

### 格式示例

```
# 使用 index 命令同步（推荐）
python "${SCRIPTS_DIR}/webnovel.py" index sync-all --full

# 增量同步
python "${SCRIPTS_DIR}/webnovel.py" index sync-all

# 只同步设定集
python "${SCRIPTS_DIR}/webnovel.py" index sync-all --type entities

# 只同步章节
python "${SCRIPTS_DIR}/webnovel.py" index sync-all --type chapters

# 旧格式（兼容）
/webnovel-sync                    # 增量同步设定集
/webnovel-sync --full             # 完整重建设定集
/webnovel-sync --archive-deleted  # 归档已删除
/webnovel-sync --dry-run          # 模拟运行
/webnovel-sync --merge-pinyin   # 归并拼音/英文实体
/webnovel-sync --keep-pinyin     # 保留拼音/英文实体

# 章节同步
/webnovel-sync --chapters all     # 同步全部章节
/webnovel-sync --chapters latest  # 同步最新10章
/webnovel-sync --chapters 1-100   # 同步第1-100章
/webnovel-sync --chapters 50+      # 同步最新50章

# 单个实体同步
/webnovel-sync --entity 角色名     # 增量同步单个角色
/webnovel-sync --entity 道具名 --type 道具  # 增量同步单个道具

# 限定类型同步
/webnovel-sync --type 角色         # 只同步角色
/webnovel-sync --type 道具         # 只同步道具
```

---

## Step 2: 确认项目根目录

执行以下命令确认项目根目录：

```bash
export PROJECT_ROOT="$(python "${SCRIPTS_DIR}/webnovel.py" --project-root "${WORKSPACE_ROOT}" where)"
echo "项目根目录: ${PROJECT_ROOT}"
```

验证目录存在：
```bash
if [ ! -d "${PROJECT_ROOT}/.webnovel" ]; then
  echo "ERROR: .webnovel 目录不存在" >&2
  exit 1
fi
if [ ! -d "${PROJECT_ROOT}/设定集" ]; then
  echo "ERROR: 设定集 目录不存在" >&2
  exit 1
fi
```

---

## Step 3: 判断同步模式

根据命令参数判断执行哪种同步模式：

```python
def determine_sync_mode(options: Dict) -> str:
    """判断同步模式"""
    if options.get('entity'):
        return 'single'  # 单个实体同步
    elif options.get('chapters'):
        return 'chapters'  # 章节同步
    else:
        return 'settings'  # 设定集同步
```

### 3.1 同步模式分支

| 模式 | 参数 | 说明 |
|------|------|------|
| 设定集 | 默认 | 扫描整个设定集目录 |
| 章节 | `--chapters` | 扫描章节目录 |
| 单个实体 | `--entity` | 增量同步单个实体 |

### 3.2 章节扫描（当模式为 chapters 时）

#### 3.2.1 解析章节范围

```python
def parse_chapter_range(chapters_arg: str) -> Tuple[int, int]:
    """
    解析章节范围参数

    参数格式:
    - "all": 全部章节
    - "latest": 最新10章
    - "1-100": 第1到100章
    - "50+": 最新50章
    """
    if chapters_arg == 'all':
        # 获取章节总数
        max_chapter = get_max_chapter(project_root)
        return 1, max_chapter
    elif chapters_arg == 'latest':
        max_chapter = get_max_chapter(project_root)
        return max(1, max_chapter - 9), max_chapter
    elif '-' in chapters_arg:
        # 范围格式: 1-100
        start, end = chapters_arg.split('-')
        return int(start), int(end)
    elif chapters_arg.endswith('+'):
        # 最新N章: 50+
        count = int(chapters_arg[:-1])
        max_chapter = get_max_chapter(project_root)
        return max(1, max_chapter - count + 1), max_chapter
    else:
        # 单章
        return int(chapters_arg), int(chapters_arg)

def get_max_chapter(project_root: str) -> int:
    """获取最大章节号"""
    chapters_dir = Path(project_root) / "正文"
    if not chapters_dir.is_dir():
        return 0

    max_chapter = 0
    for d in chapters_dir.iterdir():
        if d.is_dir() and d.name.startswith('第'):
            # 提取章节号
            match = re.match(r'第(\d+)章', d.name)
            if match:
                chapter_num = int(match.group(1))
                max_chapter = max(max_chapter, chapter_num)
    return max_chapter
```

#### 3.2.2 扫描章节

```python
def scan_chapters(project_root: str, start: int, end: int) -> List[Dict]:
    """扫描指定范围的章节"""
    chapters_dir = Path(project_root) / "正文"
    chapters = []

    for chapter_num in range(start, end + 1):
        chapter_dir = chapters_dir / f"第{chapter_num}章"
        if not chapter_dir.is_dir():
            continue

        # 查找章节文件
        chapter_files = list(chapter_dir.glob("*.md"))
        if not chapter_files:
            continue

        chapter_file = chapter_files[0]
        chapter_data = parse_chapter_file(chapter_file, chapter_num)
        chapters.append(chapter_data)

    return chapters

def parse_chapter_file(file_path: Path, chapter: int) -> Dict:
    """解析章节文件"""
    content = file_path.read_text(encoding='utf-8')

    # 去除 frontmatter
    body = content
    frontmatter = {}
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1]) or {}
                body = parts[2]
            except:
                body = content

    # 计算字数
    text_without_whitespace = re.sub(r'\s+', '', body)
    word_count = len(text_without_whitespace)

    # 提取标题
    title = frontmatter.get('title', file_path.stem.replace(f'第{chapter}章', '').strip('- '))

    return {
        'chapter': chapter,
        'title': title,
        'word_count': word_count,
        'file_path': str(file_path),
        'frontmatter': frontmatter,
    }
```

#### 3.2.3 同步章节到数据库

```python
def sync_chapters(project_root: str, chapters: List[Dict], full: bool = False) -> Dict:
    """同步章节到数据库"""
    db_path = Path(project_root) / ".webnovel" / "index.db"

    if full:
        # 完整重建：清空现有章节
        conn = get_db_connection(project_root)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chapters")
        cursor.execute("DELETE FROM scenes")
        cursor.execute("DELETE FROM appearances")
        conn.commit()
        conn.close()

    conn = get_db_connection(project_root)

    stats = {
        'total': len(chapters),
        'synced': 0,
        'errors': 0
    }

    for chapter_data in chapters:
        try:
            # 写入章节元数据
            add_chapter(conn, chapter_data)

            # 提取并写入出场实体
            entities = extract_chapter_entities(chapter_data)
            for entity in entities:
                record_appearance(conn, entity)

            stats['synced'] += 1
        except Exception as e:
            stats['errors'] += 1
            print(f"Error syncing chapter {chapter_data['chapter']}: {e}")

    conn.close()
    return stats

def add_chapter(conn: sqlite3.Connection, chapter_data: Dict):
    """添加章节到数据库"""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO chapters
        (chapter, title, word_count, location, characters, summary)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        chapter_data['chapter'],
        chapter_data['title'],
        chapter_data['word_count'],
        chapter_data.get('location', ''),
        '[]',
        chapter_data.get('summary', ''),
    ))
    conn.commit()

def extract_chapter_entities(chapter_data: Dict) -> List[Dict]:
    """从章节内容中提取出场实体"""
    # 略：复用现有的实体提取逻辑
    return []
```

### 3.3 单个实体同步（当模式为 single 时）

```python
def sync_single_entity(project_root: str, entity_name: str, entity_type: str = None) -> Dict:
    """增量同步单个实体"""

    # 1. 查找实体文件
    entity_file = find_entity_file(project_root, entity_name, entity_type)
    if not entity_file:
        return {'success': False, 'error': f'实体 {entity_name} 不存在'}

    # 2. 解析实体文件
    entity_data = parse_markdown_file(entity_file)

    # 3. 验证类型
    entity_type = entity_data['frontmatter'].get('type')
    normalized_type = normalize_type(entity_type)

    # 4. 同步到数据库
    conn = get_db_connection(project_root)
    result = sync_entity(conn, {
        'id': entity_name,
        'type': normalized_type,
        'canonical_name': entity_data['frontmatter'].get('name', entity_name),
        'tier': entity_data['frontmatter'].get('tier', '装饰'),
        'desc': entity_data['body'][:200],
    })
    conn.close()

    return {'success': True, 'entity': entity_name, 'type': normalized_type}

def find_entity_file(project_root: str, entity_name: str, entity_type: str = None) -> Optional[Path]:
    """查找实体文件"""
    settings_dir = Path(project_root) / "设定集"

    # 根据类型确定搜索目录
    search_dirs = []
    if entity_type == '角色' or entity_type is None:
        search_dirs.append(settings_dir / "角色库")
    if entity_type in {'道具', None}:
        search_dirs.append(settings_dir / "道具库")
    if entity_type in {'地点', '星球', '势力', None}:
        search_dirs.append(settings_dir / "地图库")
    if entity_type in {'世界观', '境界', '力量体系', '金手指', '设计', None}:
        search_dirs.append(settings_dir / "其他设定")

    # 搜索文件
    for search_dir in search_dirs:
        if not search_dir.is_dir():
            continue
        for md_file in search_dir.rglob("*.md"):
            if md_file.stem == entity_name:
                return md_file

    return None
```

---

## Step 4: 扫描设定集目录结构

### 3.1 定义合法目录映射

```python
# 角色库 → 角色
ROLE_DIRS = {'主角卡', '女主卡', '配角', '反派', '龙套角色', '角色', '人物'}

# 道具库 → 对应子类型
ITEM_DIRS = {
    '丹药', '法宝', '符箓', '兵器', '防具', '材料', '灵宠',
    '阵法', '信物', '日常', '其他', '物品'
}

# 地图库 → 地点/星球/势力
MAP_DIRS = {'地点', '星球', '势力', '地图'}

# 其他设定 → 对应子类型
OTHER_DIRS = {'世界观', '境界', '力量体系', '金手指', '设计'}
```

### 3.2 扫描目录

```python
def scan_settings_dir(project_root: str) -> List[Dict]:
    """扫描设定集目录，返回所有实体文件"""
    settings_dir = Path(project_root) / "设定集"
    entities = []

    # 扫描角色库
    role_dir = settings_dir / "角色库"
    if role_dir.is_dir():
        entities.extend(scan_directory(role_dir, '角色', ROLE_DIRS))

    # 扫描道具库
    item_dir = settings_dir / "道具库"
    if item_dir.is_dir():
        entities.extend(scan_directory(item_dir, '道具', ITEM_DIRS))

    # 扫描地图库
    map_dir = settings_dir / "地图库"
    if map_dir.is_dir():
        entities.extend(scan_directory(map_dir, '地点', MAP_DIRS))

    # 扫描其他设定
    other_dir = settings_dir / "其他设定"
    if other_dir.is_dir():
        entities.extend(scan_directory(other_dir, '其他', OTHER_DIRS))

    return entities
```

---

## Step 4: 读取所有 Markdown 文件

### 4.1 解析 Markdown 文件

```python
def parse_markdown_file(file_path: Path) -> Dict:
    """解析 Markdown 文件，提取 frontmatter 和内容"""
    content = file_path.read_text(encoding='utf-8')

    # 解析 frontmatter
    frontmatter = {}
    body = content

    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            frontmatter_text = parts[1]
            body = parts[2].strip()

            # 解析 YAML
            try:
                frontmatter = yaml.safe_load(frontmatter_text) or {}
            except:
                frontmatter = {}

    return {
        'frontmatter': frontmatter,
        'body': body,
        'file_path': str(file_path),
    }
```

### 4.2 提取实体信息

```python
def extract_entity_info(
    file_path: Path,
    frontmatter: Dict,
    body: str,
    default_type: str,
    valid_dirs: Set[str]
) -> Optional[Dict]:
    """从 frontmatter 和内容中提取实体信息"""

    # 确定实体类型
    entity_type = frontmatter.get('type') or frontmatter.get('category') or default_type

    # 如果是道具或地图，优先使用子目录名
    rel_path = file_path.relative_to(Path(project_root) / "设定集")
    if len(rel_path.parts) > 1:
        dir_name = rel_path.parts[0]
        if dir_name in valid_dirs:
            entity_type = dir_name

    # 提取基本信息
    entity_id = frontmatter.get('id') or frontmatter.get('name') or file_path.stem
    canonical_name = frontmatter.get('name') or frontmatter.get('title') or file_path.stem
    tier = frontmatter.get('tier', '装饰')

    # 提取描述（前200字）
    description = frontmatter.get('desc') or frontmatter.get('description') or body[:200]

    return {
        'id': entity_id,
        'type': entity_type,
        'canonical_name': canonical_name,
        'tier': tier,
        'desc': description,
        'file_path': str(file_path),
    }
```

---

## Step 5: 验证实体类型格式

### 5.1 定义实体类型分类

```python
# 角色类型（统一为 '角色'）
ROLE_TYPES = {'角色', '主角', '女主', '配角', '反派', '龙套'}

# 道具类型（统一加前缀 '道具-'）
ITEM_TYPES = {
    '丹药', '法宝', '符箓', '兵器', '防具', '材料', '灵宠',
    '阵法', '信物', '日常', '其他', '物品'
}

# 地图/地点类型
MAP_TYPES = {'地点', '星球', '势力', '地图'}

# 其他设定类型（兜底分类）
OTHER_CATCHALL = '其他设定'
```

### 5.2 类型验证与兜底机制

```python
def validate_entity_type(
    entity_type: str,
    category: str,
    file_path: Path
) -> str:
    """
    验证实体类型格式，无法识别时归类为 '其他设定'

    兜底策略：
    - 所有无法识别的类型都归入 '其他设定'
    - '其他设定' 是数据池，不限定具体内容
    """
    # 1. 优先使用 frontmatter 中的 type
    if entity_type:
        normalized = normalize_type(entity_type)
        if normalized:
            return normalized

    # 2. 检查 category
    if category:
        normalized = normalize_type(category)
        if normalized:
            return normalized

    # 3. 从文件路径推断
    try:
        rel_path = file_path.relative_to(Path(project_root) / "设定集")
        if len(rel_path.parts) > 1:
            dir_name = rel_path.parts[0]
            normalized = normalize_type_from_dir(dir_name)
            if normalized:
                return normalized
    except ValueError:
        pass

    # 4. 无法识别，归入 '其他设定'
    return OTHER_CATCHALL

def normalize_type(entity_type: str) -> Optional[str]:
    """规范化实体类型"""
    if not entity_type:
        return None

    # 角色类型统一
    if entity_type in ROLE_TYPES:
        return '角色'

    # 道具类型加前缀
    if entity_type in ITEM_TYPES:
        return f'道具-{entity_type}'

    # 地图类型
    if entity_type in MAP_TYPES:
        return entity_type

    # 其他已知类型
    known_types = {'世界观', '境界', '力量体系', '金手指', '设计'}
    if entity_type in known_types:
        return entity_type

    return None  # 无法识别

def normalize_type_from_dir(dir_name: str) -> Optional[str]:
    """从目录名推断类型"""
    if dir_name in ROLE_TYPES:
        return '角色'

    if dir_name in ITEM_TYPES:
        return f'道具-{dir_name}'

    if dir_name in MAP_TYPES:
        return dir_name

    # 未知目录名，归入其他设定
    return OTHER_CATCHALL
```

### 5.3 Dashboard 类型展示配置

```python
# Dashboard 展示用的类型映射
DASHBOARD_TYPE_MAP = {
    # 角色
    '角色': {'label': '角色', 'color': '#1890ff', 'icon': 'user'},
    # 道具（各子类型）
    '道具-丹药': {'label': '丹药', 'color': '#52c41a', 'icon': 'experiment'},
    '道具-法宝': {'label': '法宝', 'color': '#fa8c16', 'icon': 'tool'},
    '道具-符箓': {'label': '符箓', 'color': '#faad14', 'icon': 'file-text'},
    '道具-兵器': {'label': '兵器', 'color': '#f5222d', 'icon': 'fire'},
    '道具-防具': {'label': '防具', 'color': '#722ed1', 'icon': 'shield'},
    '道具-材料': {'label': '材料', 'color': '#13c2c2', 'icon': 'inbox'},
    '道具-灵宠': {'label': '灵宠', 'color': '#eb2f96', 'icon': 'heart'},
    '道具-阵法': {'label': '阵法', 'color': '#2f54eb', 'icon': 'cluster'},
    '道具-信物': {'label': '信物', 'color': '#a0d911', 'icon': 'key'},
    '道具-日常': {'label': '日常', 'color': '#8c8c8c', 'icon': 'home'},
    '道具-其他': {'label': '其他', 'color': '#595959', 'icon': 'question'},
    '道具-物品': {'label': '物品', 'color': '#434343', 'icon': 'appstore'},
    # 地图
    '地点': {'label': '地点', 'color': '#1890ff', 'icon': 'environment'},
    '星球': {'label': '星球', 'color': '#52c41a', 'icon': 'global'},
    '势力': {'label': '势力', 'color': '#f5222d', 'icon': 'flag'},
    # 其他设定（兜底）
    '其他设定': {'label': '其他', 'color': '#595959', 'icon': 'folder'},
    '世界观': {'label': '世界观', 'color': '#722ed1', 'icon': 'global'},
    '境界': {'label': '境界', 'color': '#fa8c16', 'icon': 'rise'},
    '力量体系': {'label': '力量体系', 'color': '#13c2c2', 'icon': 'thunderbolt'},
    '金手指': {'label': '金手指', 'color': '#eb2f96', 'icon': 'star'},
    '设计': {'label': '设计', 'color': '#2f54eb', 'icon': 'edit'},
}
```
            if dir_name in VALID_ROLE_TYPES:
                return '角色', True
            elif dir_name in VALID_ITEM_TYPES:
                return f'道具-{dir_name}', True
            elif dir_name in VALID_MAP_TYPES:
                return dir_name, True
            elif dir_name in VALID_OTHER_TYPES:
                return dir_name, True
    except ValueError:
        pass

    # 4. 类型无效，记录警告
    return entity_type or category or '未知', False
```

### 5.3 类型规范化

```python
def normalize_type(entity_type: str) -> str:
    """规范化实体类型名称"""
    # 道具类型统一加前缀
    if entity_type in VALID_ITEM_TYPES:
        return f'道具-{entity_type}'

    # 角色类型统一
    if entity_type in {'主角', '女主', '配角', '反派', '龙套'}:
        return '角色'

    return entity_type

def get_type_display(type_value: str) -> str:
    """获取用于展示的类型名称"""
    # 移除前缀用于展示
    if type_value.startswith('道具-'):
        return type_value[3:]  # 返回 "丹药" 而非 "道具-丹药"
    return type_value
```

### 5.4 Dashboard 类型展示配置

```python
# Dashboard 展示用的类型映射
DASHBOARD_TYPE_MAP = {
    # 角色
    '角色': {'label': '角色', 'color': '#1890ff'},
    # 道具
    '道具-丹药': {'label': '丹药', 'color': '#52c41a'},
    '道具-法宝': {'label': '法宝', 'color': '#fa8c16'},
    '道具-符箓': {'label': '符箓', 'color': '#faad14'},
    '道具-兵器': {'label': '兵器', 'color': '#f5222d'},
    '道具-防具': {'label': '防具', 'color': '#722ed1'},
    '道具-材料': {'label': '材料', 'color': '#13c2c2'},
    '道具-灵宠': {'label': '灵宠', 'color': '#eb2f96'},
    '道具-阵法': {'label': '阵法', 'color': '#2f54eb'},
    '道具-信物': {'label': '信物', 'color': '#a0d911'},
    '道具-日常': {'label': '日常', 'color': '#8c8c8c'},
    '道具-其他': {'label': '其他', 'color': '#595959'},
    '道具-物品': {'label': '物品', 'color': '#434343'},
    # 地图
    '地点': {'label': '地点', 'color': '#1890ff'},
    '星球': {'label': '星球', 'color': '#52c41a'},
    '势力': {'label': '势力', 'color': '#f5222d'},
    # 其他
    '世界观': {'label': '世界观', 'color': '#722ed1'},
    '境界': {'label': '境界', 'color': '#fa8c16'},
    '力量体系': {'label': '力量体系', 'color': '#13c2c2'},
    '金手指': {'label': '金手指', 'color': '#eb2f96'},
    '设计': {'label': '设计', 'color': '#2f54eb'},
}
```

---

## Step 6: 同步到数据库

### 6.1 数据库连接

```python
import sqlite3
from datetime import datetime

def get_db_connection(project_root: str) -> sqlite3.Connection:
    """获取数据库连接"""
    db_path = Path(project_root) / ".webnovel" / "index.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn
```

### 6.2 同步实体

```python
def sync_entity(conn: sqlite3.Connection, entity: Dict) -> bool:
    """同步单个实体到数据库"""
    cursor = conn.cursor()

    # 检查实体是否已存在
    cursor.execute("SELECT id FROM entities WHERE id = ?", (entity['id'],))
    exists = cursor.fetchone() is not None

    now = datetime.now().isoformat()

    if exists:
        # 更新现有实体
        cursor.execute("""
            UPDATE entities SET
                type = ?,
                canonical_name = ?,
                tier = ?,
                desc = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            entity['type'],
            entity['canonical_name'],
            entity['tier'],
            entity['desc'],
            now,
            entity['id']
        ))
    else:
        # 插入新实体
        cursor.execute("""
            INSERT INTO entities
                (id, type, canonical_name, tier, desc, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            entity['id'],
            entity['type'],
            entity['canonical_name'],
            entity['tier'],
            entity['desc'],
            now,
            now
        ))

    conn.commit()
    return True
```

### 6.3 完整重建（Full Rebuild）

当使用 `--full` 参数时，执行完整的数据库重建：

```python
def full_rebuild(project_root: str, options: Dict = None) -> Dict:
    """
    完整重建：清空并重建所有数据

    步骤：
    1. 备份并保留 state.json 中的关键数据（strand_tracker, plot_threads, progress）
    2. 清空所有现有数据和关系图谱
    3. 扫描所有章节并记录
    4. 扫描所有设定集并记录
    5. 分析并合并可能出现在不同文件的同一人/物
    6. 合并成一条入库数据
    7. 重建关系图谱
    8. 恢复 state.json 关键数据
    9. 迁移关键数据到数据库
    """
    options = options or {}
    start_time = time.time()

    stats = {
        'chapters_scanned': 0,
        'settings_scanned': 0,
        'entities_merged': 0,
        'entities_total': 0,
        'relationships_rebuilt': 0,
        'errors': []
    }

    # 0. 备份 state.json 关键数据
    print("步骤0: 备份 state.json 关键数据...")
    state_backup = backup_state_json(project_root)

    # 1. 清空所有表
    print("步骤1: 清空所有现有数据...")
    clear_all_tables(project_root)

    # 2. 扫描所有章节
    print("步骤2: 扫描所有章节...")
    chapters = scan_all_chapters(project_root)
    stats['chapters_scanned'] = len(chapters)

    # 3. 扫描所有设定集
    print("步骤3: 扫描所有设定集...")
    all_entities = scan_all_settings(project_root)
    stats['settings_scanned'] = len(all_entities)

    # 4. 分析并合并重复实体
    print("步骤4: 分析并合并重复实体...")
    merged_entities = analyze_and_merge_entities(all_entities)
    stats['entities_merged'] = len(all_entities) - len(merged_entities)
    stats['entities_total'] = len(merged_entities)

    # 5. 同步实体到数据库
    print("步骤5: 同步实体到数据库...")
    conn = get_db_connection(project_root)
    for entity in merged_entities:
        try:
            insert_entity(conn, entity)
        except Exception as e:
            stats['errors'].append(f"Entity error: {entity.get('id')} - {e}")

    # 6. 同步章节到数据库
    print("步骤6: 同步章节到数据库...")
    for chapter in chapters:
        try:
            insert_chapter(conn, chapter)
            stats['chapters_synced'] = stats.get('chapters_synced', 0) + 1
        except Exception as e:
            stats['errors'].append(f"Chapter error: {chapter.get('chapter')} - {e}")

    # 7. 重建关系图谱
    print("步骤7: 重建关系图谱...")
    relationships = rebuild_relationships(project_root, merged_entities, chapters)
    for rel in relationships:
        try:
            insert_relationship(conn, rel)
            stats['relationships_rebuilt'] += 1
        except Exception as e:
            stats['errors'].append(f"Relationship error: {e}")

    # 8. 迁移关键数据到数据库
    print("步骤8: 迁移关键数据到数据库...")
    migrate_state_to_database(conn, state_backup)

    conn.commit()
    conn.close()

    # 9. 恢复 state.json
    print("步骤9: 恢复 state.json 关键数据...")
    restore_state_json(project_root, state_backup)

    stats['duration'] = time.time() - start_time
    return stats
```

### 6.3.1 备份 state.json 关键数据

```python
import json
import shutil
from datetime import datetime

def backup_state_json(project_root: str) -> Dict:
    """
    备份 state.json 中的关键数据

    需要保留的数据：
    - strand_tracker: 线索编织追踪
    - plot_threads: 伏线/钩子数据
    - progress: 进度数据
    - review_checkpoints: 审查检查点
    - project_info: 项目信息
    """
    state_path = Path(project_root) / ".webnovel" / "state.json"
    backup = {}

    if state_path.is_file():
        try:
            state = json.loads(state_path.read_text(encoding='utf-8'))

            # 备份关键字段
            backup = {
                'strand_tracker': state.get('strand_tracker', {}),
                'plot_threads': state.get('plot_threads', {}),
                'progress': state.get('progress', {}),
                'review_checkpoints': state.get('review_checkpoints', []),
                'project_info': state.get('project_info', {}),
                'target_words': state.get('target_words'),
                'target_chapters': state.get('target_chapters'),
                'book_title': state.get('book_title'),
                'book_genre': state.get('book_genre'),
                'current_volume': state.get('current_volume', 1),
            }

            print(f"  已备份 strand_tracker: {len(backup.get('strand_tracker', {}).get('history', []))} 条")
            print(f"  已备份 plot_threads: {len(backup.get('plot_threads', {}).get('foreshadowing', []))} 条")

        except Exception as e:
            print(f"  警告：备份 state.json 失败: {e}")

    return backup


def migrate_state_to_database(conn: sqlite3.Connection, backup: Dict):
    """
    将 state.json 关键数据迁移到数据库

    迁移以下数据到数据库：
    - strand_tracker -> 使用现有的关系表
    - plot_threads.foreshadowing -> 存储在 current_json 或专用表
    - chapter_reading_power -> 从审查数据中获取
    """
    cursor = conn.cursor()

    # 迁移 strand_tracker 到数据库（如有需要）
    strand_tracker = backup.get('strand_tracker', {})
    if strand_tracker:
        # strand_tracker 数据会通过关系表展示，这里可以做一些统计
        print(f"  strand_tracker 历史记录: {len(strand_tracker.get('history', []))} 条")

    # 迁移 plot_threads
    plot_threads = backup.get('plot_threads', {})
    if plot_threads:
        foreshadowing = plot_threads.get('foreshadowing', [])
        print(f"  伏笔/钩子记录: {len(foreshadowing)} 条")

        # 可以存储到 entities 表的 current_json 中
        # 或者创建专门的表来存储


def restore_state_json(project_root: str, backup: Dict):
    """
    恢复 state.json 关键数据
    """
    state_path = Path(project_root) / ".webnovel" / "state.json"

    if not state_path.is_file():
        print("  警告：state.json 不存在，跳过恢复")
        return

    try:
        state = json.loads(state_path.read_text(encoding='utf-8'))

        # 恢复关键字段
        if backup.get('strand_tracker'):
            state['strand_tracker'] = backup['strand_tracker']

        if backup.get('plot_threads'):
            state['plot_threads'] = backup['plot_threads']

        if backup.get('progress'):
            state['progress'] = backup['progress']

        if backup.get('review_checkpoints'):
            state['review_checkpoints'] = backup['review_checkpoints']

        # 恢复项目基本信息
        if backup.get('target_words'):
            state['target_words'] = backup['target_words']

        if backup.get('target_chapters'):
            state['target_chapters'] = backup['target_chapters']

        if backup.get('book_title'):
            state['book_title'] = backup['book_title']

        if backup.get('book_genre'):
            state['book_genre'] = backup['book_genre']

        if backup.get('current_volume'):
            state['current_volume'] = backup['current_volume']

        # 写回 state.json
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
        print("  state.json 已恢复")

    except Exception as e:
        print(f"  警告：恢复 state.json 失败: {e}")
```

### 6.3.2 清空所有表

```python
def clear_all_tables(project_root: str):
    """清空所有数据库表"""
    db_path = Path(project_root) / ".webnovel" / "index.db"
    conn = get_db_connection(project_root)
    cursor = conn.cursor()

    # 按依赖顺序清空表
    tables = [
        'relationship_events',
        'relationships',
        'appearances',
        'state_changes',
        'scenes',
        'chapters',
        'entities',
        'aliases',
        'override_contracts',
        'chase_debt',
        'debt_events',
        'chapter_reading_power',
        'invalid_facts',
        'review_metrics',
    ]

    for table in tables:
        try:
            cursor.execute(f"DELETE FROM {table}")
        except Exception as e:
            # 表可能不存在
            pass

    conn.commit()
    conn.close()
```

### 6.3.2 扫描所有章节

```python
def scan_all_chapters(project_root: str) -> List[Dict]:
    """扫描所有章节"""
    chapters_dir = Path(project_root) / "正文"
    if not chapters_dir.is_dir():
        return []

    chapters = []
    for chapter_dir in chapters_dir.iterdir():
        if not chapter_dir.is_dir():
            continue

        # 匹配章节目录
        match = re.match(r'第(\d+)章', chapter_dir.name)
        if not match:
            continue

        chapter_num = int(match.group(1))
        chapter_files = list(chapter_dir.glob("*.md"))
        if not chapter_files:
            continue

        chapter_data = parse_chapter_file(chapter_files[0], chapter_num)

        # 提取出场实体
        entities = extract_entities_from_chapter(chapter_files[0])
        chapter_data['entities'] = entities

        chapters.append(chapter_data)

    # 按章节号排序
    chapters.sort(key=lambda x: x['chapter'])
    return chapters
```

### 6.3.3 扫描所有设定集

```python
def scan_all_settings(project_root: str) -> List[Dict]:
    """扫描所有设定集目录"""
    settings_dir = Path(project_root) / "设定集"
    entities = []

    # 扫描各子目录
    entities.extend(scan_role_settings(settings_dir / "角色库"))
    entities.extend(scan_item_settings(settings_dir / "道具库"))
    entities.extend(scan_map_settings(settings_dir / "地图库"))
    entities.extend(scan_other_settings(settings_dir / "其他设定"))

    return entities
```

### 6.3.4 分析并合并重复实体

```python
def analyze_and_merge_entities(all_entities: List[Dict]) -> List[Dict]:
    """
    分析并合并可能出现在不同文件的同一人/物

    合并策略：
    1. 按实体名称规范化后分组
    2. 相同名称的实体进行合并
    3. 保留最新的描述和完整的信息
    """
    # 1. 规范化实体名称（去除空格、标点）
    normalized_map = {}
    for entity in all_entities:
        name = entity.get('canonical_name') or entity.get('id', '')
        normalized = normalize_entity_name(name)

        if normalized not in normalized_map:
            normalized_map[normalized] = []
        normalized_map[normalized].append(entity)

    # 2. 合并相同名称的实体
    merged = []
    for normalized, group in normalized_map.items():
        if len(group) == 1:
            merged.append(group[0])
        else:
            # 多个实体合并为一个
            merged_entity = merge_entities(group)
            merged.append(merged_entity)

    return merged

def normalize_entity_name(name: str) -> str:
    """规范化实体名称用于比较"""
    import unicodedata
    # 转为小写
    name = name.lower()
    # 去除空格和标点
    name = re.sub(r'[\s\.,，。、；;：:\'\"''""【】\[\]（）\(\)]+', '', name)
    # 转为NFKC正规化
    name = unicodedata.normalize('NFKC', name)
    return name

def merge_entities(entities: List[Dict]) -> Dict:
    """合并多个相同实体"""
    # 选择最完整的实体作为基础
    entities.sort(key=lambda e: len(e.get('desc', '')), reverse=True)
    merged = dict(entities[0])

    # 记录所有来源文件
    merged['source_files'] = [e.get('file_path') for e in entities if e.get('file_path')]

    # 合并其他字段
    if len(entities) > 1:
        # 保留最早的出现章节
        first_chapters = [e.get('first_appearance', 9999) for e in entities]
        merged['first_appearance'] = min(first_chapters)

        # 更新描述（使用最长的）
        descriptions = [e.get('desc', '') for e in entities if e.get('desc')]
        merged['desc'] = max(descriptions, key=len) if descriptions else ''

    return merged
```

### 6.3.5 重建关系图谱

```python
def rebuild_relationships(project_root: str, entities: List[Dict], chapters: List[Dict]) -> List[Dict]:
    """重建所有实体之间的关系图谱"""
    relationships = []

    # 1. 从实体定义中提取关系
    for entity in entities:
        entity_id = entity.get('id')
        relations = entity.get('relations', []) or []

        for rel in relations:
            relationships.append({
                'from_entity': entity_id,
                'to_entity': rel.get('target'),
                'type': rel.get('type', '关联'),
                'description': rel.get('description', ''),
                'chapter': entity.get('first_appearance', 0),
            })

    # 2. 从章节内容中提取关系
    for chapter in chapters:
        chapter_num = chapter.get('chapter')
        entities_in_chapter = chapter.get('entities', [])

        for i, entity_a in enumerate(entities_in_chapter):
            for entity_b in entities_in_chapter[i+1:]:
                # 检测同章节实体间的关系
                rel_type = detect_relationship(entity_a, entity_b, chapter.get('body', ''))
                if rel_type:
                    relationships.append({
                        'from_entity': entity_a.get('id'),
                        'to_entity': entity_b.get('id'),
                        'type': rel_type,
                        'description': f'同章节出场',
                        'chapter': chapter_num,
                    })

    return relationships
```

### 6.4 增量同步

```python
def incremental_sync(project_root: str, entities: List[Dict]) -> Dict:
    """增量同步（默认模式）"""
    conn = get_db_connection(project_root)

    stats = {
        'total': len(entities),
        'inserted': 0,
        'updated': 0,
        'errors': 0
    }

    for entity in entities:
        try:
            # 检查是否已存在
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM entities WHERE id = ?", (entity['id'],))
            exists = cursor.fetchone() is not None

            if exists:
                # 更新
                update_entity(conn, entity)
                stats['updated'] += 1
            else:
                # 插入
                insert_entity(conn, entity)
                stats['inserted'] += 1
        except Exception as e:
            stats['errors'] += 1
            print(f"Error syncing {entity.get('id')}: {e}")

    conn.close()
    return stats
```

---

## Step 7: 处理已删除文件（归档）

### 7.1 获取数据库中现有实体

```python
def get_existing_entities(conn: sqlite3.Connection) -> Set[str]:
    """获取数据库中所有未归档的实体ID"""
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM entities WHERE is_archived = 0")
    return {row[0] for row in cursor.fetchall()}
```

### 7.2 归档已删除的实体

```python
def archive_deleted_entities(
    conn: sqlite3.Connection,
    existing_ids: Set[str],
    current_ids: Set[str],
    archive: bool = True
) -> int:
    """将数据库中存在但文件中已删除的实体标记为归档"""
    if not archive:
        return 0

    deleted_ids = existing_ids - current_ids

    if not deleted_ids:
        return 0

    cursor = conn.cursor()
    now = datetime.now().isoformat()

    for entity_id in deleted_ids:
        cursor.execute("""
            UPDATE entities SET
                is_archived = 1,
                updated_at = ?
            WHERE id = ?
        """, (now, entity_id))

    conn.commit()
    return len(deleted_ids)
```

---

## Step 8: 输出同步报告

### 8.1 生成报告

```python
def generate_report(
    stats: Dict,
    archived_count: int,
    duration: float
) -> str:
    """生成同步报告"""
    report = f"""
# 设定集同步报告

## 同步统计

| 项目 | 数量 |
|------|------|
| 总实体数 | {stats['total']} |
| 新增 | {stats['inserted']} |
| 更新 | {stats['updated']} |
| 错误 | {stats['errors']} |
| 归档 | {archived_count} |
| 归并 | {stats.get('merged', 0)} |

## 耗时

{duration:.2f} 秒

## 说明

- 新增：数据库中原本不存在的实体
- 更新：数据库中已存在且被修改的实体
- 归档：文件中已删除但数据库中仍存在的实体（已标记为归档）
- 归并：拼音/英文命名的实体已归并到对应的中文主实体
"""
    return report
```

### 8.2 输出示例

```
# 设定集同步报告

## 同步统计

| 项目 | 数量 |
|------|------|
| 总实体数 | 128 |
| 新增 | 15 |
| 更新 | 110 |
| 错误 | 3 |
| 归档 | 5 |
| 归并 | 8 |

## 耗时

2.35 秒
```

---

## 完整命令示例

### 增量同步（默认）
```
/webnovel-sync
```

### 完整重建
```
/webnovel-sync --full
# 或使用 index 命令
python "${SCRIPTS_DIR}/webnovel.py" index sync-all --full
```

### 审查报告自动入库

完整重建时会自动扫描 `审查报告/` 目录，解析审查报告并入库：

- 解析审查报告 frontmatter 中的追读力数据
  - hook_type（钩子类型）
  - hook_strength（钩子强度）
  - coolpoint_patterns（爽点模式）
  - micropayoffs（小爽点）
  - hard_violations（硬伤）
  - soft_suggestions（软建议）
  - is_transition（是否过渡章）
  - override_count（Override 数量）
  - debt_balance（债务余额）
- 提取伏笔信息并更新到 state.json
- 去重合并，保留最新状态

审查报告文件名格式：
- `第1-10章审查报告.md` → 覆盖章节 1-10
- `第10章审查报告.md` → 覆盖章节 10

### 同步并归档已删除
```
/webnovel-sync --archive-deleted
```

### 完整重建并归档
```
/webnovel-sync --full --archive-deleted
```

### 模拟运行（不实际写入）
```
/webnovel-sync --dry-run
```

### 同步并归并拼音/英文实体（默认）
```
/webnovel-sync --merge-pinyin
```

### 同步并保留拼音/英文实体
```
/webnovel-sync --keep-pinyin
```

### 完整重建并归并
```
/webnovel-sync --full --merge-pinyin
```

---

## 特殊处理：拼音/英文命名实体

在设定集中可能存在一些使用拼音或英文命名的元素，这些通常是其他已知中文设定的组成部分，需要进行归并或移除处理。

### 7.1 检测拼音/英文命名

```python
import re

def is_pinyin_or_english(name: str) -> bool:
    """检测名称是否为拼音或英文"""
    # 纯英文
    if re.match(r'^[a-zA-Z]+$', name):
        return True
    # 纯拼音（声母+韵母组合）
    pinyin_pattern = r'^[a-zA-Z]+[0-9]*$'
    if re.match(pinyin_pattern, name.lower()):
        return True
    # 混合格式（英文+数字）
    if re.match(r'^[a-zA-Z]+[0-9]+$', name):
        return True
    return False
```

### 7.2 匹配主实体

```python
def find_main_entity(
    entity_name: str,
    existing_entities: List[Dict]
) -> Optional[str]:
    """根据拼音/英文名称查找对应的中文主实体"""

    # 策略1：精确匹配（通过别名或关联）
    for entity in existing_entities:
        # 检查别名是否匹配
        if entity.get('aliases'):
            aliases = entity.get('aliases', [])
            if entity_name in aliases:
                return entity['id']

        # 检查英文名/拼音名是否匹配
        if entity.get('english_name') == entity_name:
            return entity['id']
        if entity.get('pinyin_name') == entity_name:
            return entity['id']

    # 策略2：模糊匹配（通过名称相似度）
    # 略...

    return None
```

### 7.3 归并处理

```python
def merge_pinyin_entities(
    conn: sqlite3.Connection,
    pinyin_entities: List[Dict],
    existing_entities: List[Dict]
) -> Dict:
    """归并拼音/英文命名的实体"""

    stats = {
        'merged': 0,
        'archived': 0,
        'kept': 0
    }

    for entity in pinyin_entities:
        main_entity_id = find_main_entity(
            entity['id'],
            existing_entities
        )

        if main_entity_id:
            # 归并：将当前实体的关系/出场记录转移到主实体
            merge_relationships(conn, entity['id'], main_entity_id)
            merge_appearances(conn, entity['id'], main_entity_id)

            # 归档当前实体
            archive_entity(conn, entity['id'])
            stats['merged'] += 1
        else:
            # 无法匹配：保留实体但标记为待处理
            mark_entity_pending(conn, entity['id'])
            stats['kept'] += 1

    return stats

def merge_relationships(
    conn: sqlite3.Connection,
    from_id: str,
    to_id: str
):
    """合并关系：将源实体的关系转移到目标实体"""
    cursor = conn.cursor()

    # 更新 from_entity
    cursor.execute("""
        UPDATE relationships
        SET from_entity = ?
        WHERE from_entity = ?
    """, (to_id, from_id))

    # 更新 to_entity
    cursor.execute("""
        UPDATE relationships
        SET to_entity = ?
        WHERE to_entity = ?
    """, (to_id, from_id))

    conn.commit()

def merge_appearances(
    conn: sqlite3.Connection,
    from_id: str,
    to_id: str
):
    """合并出场记录：合并两个实体的出场记录"""
    cursor = conn.cursor()

    # 保留目标实体的出场记录，删除源实体的
    cursor.execute("""
        DELETE FROM appearances
        WHERE entity_id = ?
    """, (from_id,))

    conn.commit()
```

### 7.4 在同步流程中集成

在 Step 6 同步完成后，添加拼音/英文实体处理：

```python
def sync_with_cleanup(project_root: str, entities: List[Dict], options: Dict) -> Dict:
    """同步并清理拼音/英文实体"""

    # 1. 同步所有实体
    stats = sync_all_entities(project_root, entities, options.get('full', False))

    # 2. 获取数据库连接
    conn = get_db_connection(project_root)

    # 3. 获取所有现有实体
    all_entities = get_all_entities(conn)

    # 4. 分离拼音/英文实体
    pinyin_entities = [e for e in all_entities if is_pinyin_or_english(e['id'])]
    chinese_entities = [e for e in all_entities if not is_pinyin_or_english(e['id'])]

    # 5. 归并处理
    if options.get('merge_pinyin', True):
        merge_stats = merge_pinyin_entities(
            conn,
            pinyin_entities,
            chinese_entities
        )
        stats.update(merge_stats)

    conn.close()
    return stats
```

### 7.5 命令行参数

新增以下参数：

- `--merge-pinyin`: 自动归并拼音/英文实体（默认开启）
- `--keep-pinyin`: 保留拼音/英文实体，不归并

---

## 错误处理

1. **目录不存在**: 跳过该目录，继续处理其他目录
2. **文件解析失败**: 记录错误，继续处理其他文件
3. **数据库错误**: 回滚当前事务，记录错误
4. **无写入权限**: 提示用户检查权限

---

## 注意事项

1. 同步前建议备份数据库
2. 大型设定集可能需要较长时间
3. 同步过程中可能会锁定数据库
4. 归档的实体仍保留在数据库中，只是标记为不活跃
5. frontmatter 中的 `id` 字段优先于文件名作为实体ID
