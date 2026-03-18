#!/usr/bin/env python3
"""
完整重建同步脚本
扫描所有设定集和章节，同步到数据库
"""

import sqlite3
import os
import re
import yaml
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

# 项目根目录
PROJECT_ROOT = Path("D:/Workspaces/wm/what-can-coder-do")
DB_PATH = PROJECT_ROOT / ".webnovel" / "index.db"

# 定义合法目录映射
ROLE_DIRS = {'主角卡', '女主卡', '配角', '反派', '龙套角色', '角色', '人物', '主要角色', '反派角色', '次要角色', '角色库', '人物库'}
ITEM_DIRS = {'丹药', '法宝', '符箓', '兵器', '防具', '材料', '灵宠', '阵法', '信物', '日常', '其他', '物品', '物品库', '道具库'}
MAP_DIRS = {'地点', '星球', '势力', '地图', '大陆地图', '城镇地图', '地图库'}
OTHER_DIRS = {'世界观', '境界', '力量体系', '金手指', '设计', '其他设定'}

# 角色类型
ROLE_TYPES = {'角色', '主角', '女主', '配角', '反派', '龙套', '主要角色', '反派角色', '次要角色'}

# 道具类型
ITEM_TYPES = {'丹药', '法宝', '符箓', '兵器', '防具', '材料', '灵宠', '阵法', '信物', '日常', '其他', '物品'}

# 地图类型
MAP_TYPES = {'地点', '星球', '势力', '地图', '大陆地图', '城镇地图'}

def get_db_connection():
    """获取数据库连接"""
    os.makedirs(DB_PATH.parent, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def clear_all_tables(conn: sqlite3.Connection):
    """清空所有数据库表"""
    cursor = conn.cursor()
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
        except Exception:
            pass

    conn.commit()

def parse_markdown_file(file_path: Path) -> Dict:
    """解析 Markdown 文件，提取 frontmatter 和内容"""
    content = file_path.read_text(encoding='utf-8')

    frontmatter = {}
    body = content

    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            frontmatter_text = parts[1]
            body = parts[2].strip()
            try:
                frontmatter = yaml.safe_load(frontmatter_text) or {}
            except:
                frontmatter = {}

    return {
        'frontmatter': frontmatter,
        'body': body,
        'file_path': str(file_path),
    }

def normalize_type(entity_type: str, category: str = None, dir_name: str = None) -> str:
    """规范化实体类型"""
    # 1. 角色类型统一
    if entity_type in ROLE_TYPES or category in ROLE_TYPES:
        return '角色'

    # 2. 道具类型加前缀
    if entity_type in ITEM_TYPES or category in ITEM_TYPES:
        return f'道具-{entity_type or category}'

    # 3. 地图类型
    if entity_type in MAP_TYPES or category in MAP_TYPES:
        return entity_type or category

    # 4. 其他设定类型
    if entity_type in OTHER_DIRS or category in OTHER_DIRS:
        return entity_type or category

    # 5. 从目录名推断
    if dir_name:
        if dir_name in ROLE_DIRS:
            return '角色'
        if dir_name in ITEM_DIRS:
            return f'道具-{dir_name}'
        if dir_name in MAP_DIRS:
            return '地点'
        if dir_name in OTHER_DIRS:
            return dir_name

    # 兜底
    return '其他设定'

def scan_settings_dir() -> List[Dict]:
    """扫描设定集目录，返回所有实体"""
    settings_dir = PROJECT_ROOT / "设定集"
    entities = []

    if not settings_dir.is_dir():
        return entities

    # 扫描所有 Markdown 文件
    for md_file in settings_dir.rglob("*.md"):
        if md_file.name.startswith('.'):
            continue

        # 获取相对于设定集目录的路径
        rel_path = md_file.relative_to(settings_dir)
        parts = rel_path.parts

        # 确定目录名（第一层或第二层）
        if len(parts) >= 2:
            dir_name = parts[0]  # 角色库/地图库/物品库/其他设定
            subdir_name = parts[1]  # 主要角色/反派角色/大陆地图
        elif len(parts) == 1:
            dir_name = parts[0]
            subdir_name = None
        else:
            continue

        # 确定默认类型
        if dir_name in ROLE_DIRS:
            default_type = '角色'
            # 如果有子目录，使用子目录名
            if subdir_name:
                if subdir_name in {'主要角色', '主角'}:
                    default_type = '角色'
                elif subdir_name in {'反派角色', '反派'}:
                    default_type = '角色'
                elif subdir_name in {'次要角色', '配角'}:
                    default_type = '角色'
        elif dir_name in ITEM_DIRS:
            default_type = f'道具-{subdir_name or dir_name}'
        elif dir_name in MAP_DIRS:
            default_type = '地点'
        elif dir_name in OTHER_DIRS:
            default_type = subdir_name or dir_name
        else:
            default_type = '其他设定'

        entity_data = parse_markdown_file(md_file)
        frontmatter = entity_data['frontmatter']
        body = entity_data['body']

        # 确定实体类型
        entity_type = frontmatter.get('type') or frontmatter.get('category')
        if entity_type:
            # 使用 frontmatter 中的类型，如果无法识别则使用默认值
            normalized = normalize_type(entity_type, None, None)
            normalized_type = normalized if normalized else default_type
        else:
            normalized_type = default_type

        # 提取实体ID和名称
        entity_id = frontmatter.get('id') or frontmatter.get('name') or md_file.stem
        canonical_name = frontmatter.get('name') or frontmatter.get('title') or md_file.stem
        tier = frontmatter.get('tier', '装饰')

        # 提取描述
        description = frontmatter.get('desc') or frontmatter.get('description') or body[:200]

        entities.append({
            'id': entity_id,
            'type': normalized_type,
            'canonical_name': canonical_name,
            'tier': tier,
            'desc': description,
            'file_path': str(md_file),
        })

    return entities

def scan_chapters() -> List[Dict]:
    """扫描所有章节"""
    chapters_dir = PROJECT_ROOT / "正文"
    chapters = []

    if not chapters_dir.is_dir():
        return chapters

    # 查找所有章节目录或直接找章节文件
    # 格式: 第0001章-逃生.md
    chapter_pattern = re.compile(r'第(\d+)章[-－](.+)')

    for md_file in chapters_dir.rglob("*.md"):
        if md_file.name.startswith('.'):
            continue

        match = chapter_pattern.match(md_file.name)
        if not match:
            continue

        chapter_num = int(match.group(1))
        title = match.group(2).strip()

        chapter_data = parse_markdown_file(md_file)
        body = chapter_data['body']

        # 计算字数
        text_without_whitespace = re.sub(r'\s+', '', body)
        word_count = len(text_without_whitespace)

        chapters.append({
            'chapter': chapter_num,
            'title': title,
            'word_count': word_count,
            'file_path': str(md_file),
            'frontmatter': chapter_data['frontmatter'],
        })

    # 按章节号排序
    chapters.sort(key=lambda x: x['chapter'])
    return chapters

def sync_entity(conn: sqlite3.Connection, entity: Dict) -> bool:
    """同步单个实体到数据库"""
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    # 检查是否已存在
    cursor.execute("SELECT id FROM entities WHERE id = ?", (entity['id'],))
    exists = cursor.fetchone() is not None

    if exists:
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

def sync_chapter(conn: sqlite3.Connection, chapter: Dict) -> bool:
    """同步章节到数据库"""
    cursor = conn.cursor()

    # 检查是否已存在
    cursor.execute("SELECT chapter FROM chapters WHERE chapter = ?", (chapter['chapter'],))
    exists = cursor.fetchone() is not None

    if exists:
        cursor.execute("""
            UPDATE chapters SET
                title = ?,
                word_count = ?,
                location = ?
            WHERE chapter = ?
        """, (
            chapter['title'],
            chapter['word_count'],
            chapter.get('location', ''),
            chapter['chapter']
        ))
    else:
        cursor.execute("""
            INSERT INTO chapters
                (chapter, title, word_count, location)
            VALUES (?, ?, ?, ?)
        """, (
            chapter['chapter'],
            chapter['title'],
            chapter['word_count'],
            chapter.get('location', ''),
        ))

    conn.commit()
    return True

def main():
    start_time = time.time()
    print("=" * 50)
    print("开始完整重建同步")
    print("=" * 50)

    # 1. 清空所有表
    print("\n[1/4] 清空所有现有数据...")
    conn = get_db_connection()
    clear_all_tables(conn)
    print("      数据已清空")

    # 2. 扫描设定集
    print("\n[2/4] 扫描设定集...")
    entities = scan_settings_dir()
    print(f"      找到 {len(entities)} 个实体")

    # 3. 扫描章节
    print("\n[3/4] 扫描章节...")
    chapters = scan_chapters()
    print(f"      找到 {len(chapters)} 个章节")

    # 4. 同步到数据库
    print("\n[4/4] 同步到数据库...")

    stats = {
        'entities_total': len(entities),
        'entities_synced': 0,
        'entities_errors': 0,
        'chapters_total': len(chapters),
        'chapters_synced': 0,
        'chapters_errors': 0,
    }

    # 同步实体
    for entity in entities:
        try:
            sync_entity(conn, entity)
            stats['entities_synced'] += 1
        except Exception as e:
            stats['entities_errors'] += 1
            print(f"      错误: {entity['id']} - {e}")

    # 同步章节
    for chapter in chapters:
        try:
            sync_chapter(conn, chapter)
            stats['chapters_synced'] += 1
        except Exception as e:
            stats['chapters_errors'] += 1
            print(f"      错误: 章节{chapter['chapter']} - {e}")

    conn.close()

    duration = time.time() - start_time

    # 输出报告
    print("\n" + "=" * 50)
    print("同步完成")
    print("=" * 50)
    print(f"""
## 同步统计

| 项目 | 数量 |
|------|------|
| 实体总数 | {stats['entities_total']} |
| 实体同步 | {stats['entities_synced']} |
| 实体错误 | {stats['entities_errors']} |
| 章节总数 | {stats['chapters_total']} |
| 章节同步 | {stats['chapters_synced']} |
| 章节错误 | {stats['chapters_errors']} |

## 耗时
{duration:.2f} 秒
    """)

if __name__ == "__main__":
    main()
