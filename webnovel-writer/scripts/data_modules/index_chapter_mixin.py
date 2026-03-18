#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IndexChapterMixin extracted from IndexManager.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional


class IndexChapterMixin:
    def add_chapter(self, meta: ChapterMeta):
        """添加/更新章节元数据"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO chapters
                (chapter, title, location, word_count, characters, summary)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    meta.chapter,
                    meta.title,
                    meta.location,
                    meta.word_count,
                    json.dumps(meta.characters, ensure_ascii=False),
                    meta.summary,
                ),
            )
            conn.commit()

    def get_chapter(self, chapter: int) -> Optional[Dict]:
        """获取章节元数据"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM chapters WHERE chapter = ?", (chapter,))
            row = cursor.fetchone()
            if row:
                return self._row_to_dict(row, parse_json=["characters"])
            return None

    def get_recent_chapters(self, limit: int = None) -> List[Dict]:
        """获取最近章节"""
        if limit is None:
            limit = self.config.query_recent_chapters_limit
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM chapters
                ORDER BY chapter DESC
                LIMIT ?
            """,
                (limit,),
            )
            return [
                self._row_to_dict(row, parse_json=["characters"])
                for row in cursor.fetchall()
            ]

    # ==================== 场景操作 ====================

    def add_scenes(self, chapter: int, scenes: List[SceneMeta]):
        """添加章节场景"""
        with self._get_conn() as conn:
            cursor = conn.cursor()

            # 先删除该章节旧场景
            cursor.execute("DELETE FROM scenes WHERE chapter = ?", (chapter,))

            # 插入新场景
            for scene in scenes:
                cursor.execute(
                    """
                    INSERT INTO scenes
                    (chapter, scene_index, start_line, end_line, location, summary, characters)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        scene.chapter,
                        scene.scene_index,
                        scene.start_line,
                        scene.end_line,
                        scene.location,
                        scene.summary,
                        json.dumps(scene.characters, ensure_ascii=False),
                    ),
                )

            conn.commit()

    def get_scenes(self, chapter: int) -> List[Dict]:
        """获取章节场景"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM scenes
                WHERE chapter = ?
                ORDER BY scene_index
            """,
                (chapter,),
            )
            return [
                self._row_to_dict(row, parse_json=["characters"])
                for row in cursor.fetchall()
            ]

    def search_scenes_by_location(self, location: str, limit: int = None) -> List[Dict]:
        """按地点搜索场景"""
        if limit is None:
            limit = self.config.query_scenes_by_location_limit
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM scenes
                WHERE location LIKE ?
                ORDER BY chapter DESC
                LIMIT ?
            """,
                (f"%{location}%", limit),
            )
            return [
                self._row_to_dict(row, parse_json=["characters"])
                for row in cursor.fetchall()
            ]

    # ==================== 出场记录操作 ====================

    def record_appearance(
        self,
        entity_id: str,
        chapter: int,
        mentions: List[str],
        confidence: float = 1.0,
        skip_if_exists: bool = False,
    ):
        """记录实体出场

        Args:
            entity_id: 实体ID
            chapter: 章节号
            mentions: 提及列表
            confidence: 置信度
            skip_if_exists: 如果为True，当记录已存在时跳过（避免覆盖已有mentions）
        """
        with self._get_conn() as conn:
            cursor = conn.cursor()

            if skip_if_exists:
                # 先检查是否已存在
                cursor.execute(
                    "SELECT 1 FROM appearances WHERE entity_id = ? AND chapter = ?",
                    (entity_id, chapter),
                )
                if cursor.fetchone():
                    return  # 已存在，跳过

            cursor.execute(
                """
                INSERT OR REPLACE INTO appearances
                (entity_id, chapter, mentions, confidence)
                VALUES (?, ?, ?, ?)
            """,
                (
                    entity_id,
                    chapter,
                    json.dumps(mentions, ensure_ascii=False),
                    confidence,
                ),
            )
            conn.commit()

    def get_entity_appearances(self, entity_id: str, limit: int = None) -> List[Dict]:
        """获取实体出场记录"""
        if limit is None:
            limit = self.config.query_entity_appearances_limit
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM appearances
                WHERE entity_id = ?
                ORDER BY chapter DESC
                LIMIT ?
            """,
                (entity_id, limit),
            )
            return [
                self._row_to_dict(row, parse_json=["mentions"])
                for row in cursor.fetchall()
            ]

    def get_recent_appearances(self, limit: int = None) -> List[Dict]:
        """获取最近出场的实体"""
        if limit is None:
            limit = self.config.query_recent_appearances_limit
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT entity_id, MAX(chapter) as last_chapter, COUNT(*) as total
                FROM appearances
                GROUP BY entity_id
                ORDER BY last_chapter DESC
                LIMIT ?
            """,
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_chapter_appearances(self, chapter: int) -> List[Dict]:
        """获取某章所有出场实体"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM appearances
                WHERE chapter = ?
                ORDER BY confidence DESC
            """,
                (chapter,),
            )
            return [
                self._row_to_dict(row, parse_json=["mentions"])
                for row in cursor.fetchall()
            ]

    # ==================== v5.1 实体操作 ====================

    def process_chapter_data(
        self,
        chapter: int,
        title: str,
        location: str,
        word_count: int,
        entities: List[Dict],
        scenes: List[Dict],
    ) -> Dict[str, int]:
        """
        处理章节数据，批量写入索引

        返回写入统计
        """
        from .index_manager import ChapterMeta, SceneMeta

        stats = {"chapters": 0, "scenes": 0, "appearances": 0}

        # 提取出场角色
        characters = [e.get("id") for e in entities if e.get("type") == "角色"]

        # 写入章节元数据
        self.add_chapter(
            ChapterMeta(
                chapter=chapter,
                title=title,
                location=location,
                word_count=word_count,
                characters=characters,
                summary="",  # 可后续由 Data Agent 生成
            )
        )
        stats["chapters"] = 1

        # 写入场景
        scene_metas = []
        for s in scenes:
            scene_metas.append(
                SceneMeta(
                    chapter=chapter,
                    scene_index=s.get("index", 0),
                    start_line=s.get("start_line", 0),
                    end_line=s.get("end_line", 0),
                    location=s.get("location", ""),
                    summary=s.get("summary", ""),
                    characters=s.get("characters", []),
                )
            )
        self.add_scenes(chapter, scene_metas)
        stats["scenes"] = len(scene_metas)

        # 写入出场记录
        for entity in entities:
            entity_id = entity.get("id")
            if entity_id and entity_id != "NEW":
                self.record_appearance(
                    entity_id=entity_id,
                    chapter=chapter,
                    mentions=entity.get("mentions", []),
                    confidence=entity.get("confidence", 1.0),
                )
                stats["appearances"] += 1

        return stats

    def update_chapter_from_file(self, chapter: int, chapter_file: str, project_root: str) -> Dict[str, Any]:
        """
        从章节文件更新章节数据到索引库

        Args:
            chapter: 章节号
            chapter_file: 章节文件路径
            project_root: 项目根目录

        Returns:
            更新结果统计
        """
        import re
        from pathlib import Path
        from .index_manager import ChapterMeta

        result = {
            "success": False,
            "chapter": chapter,
            "word_count": 0,
            "title": "",
            "entities_extracted": 0,
            "error": None,
        }

        try:
            chapter_path = Path(chapter_file)
            if not chapter_path.exists():
                result["error"] = f"章节文件不存在: {chapter_file}"
                return result

            # 读取章节内容
            content = chapter_path.read_text(encoding='utf-8')

            # 计算字数（去除空白字符）
            # 使用更准确的中文字数统计方式
            # 去除 YAML frontmatter
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    content = parts[2]  # 取正文部分

            # 去除所有空白字符后统计
            text_without_whitespace = re.sub(r'\s+', '', content)
            word_count = len(text_without_whitespace)

            # 提取标题（从文件名或内容中）
            title = chapter_path.stem.replace(f'第{chapter}章', '').strip('- ')

            result["word_count"] = word_count
            result["title"] = title

            # TODO: 后续可以添加实体提取逻辑
            # 目前只更新章节基本信息

            # 写入章节元数据
            self.add_chapter(ChapterMeta(
                chapter=chapter,
                title=title,
                location="",  # 可以后续提取
                word_count=word_count,
                characters=[],  # 可以后续提取
                summary="",
            ))

            result["success"] = True
            return result

        except Exception as e:
            result["error"] = str(e)
            return result

    # ==================== 同步数据方法 ====================

    def sync_all_data(self, full: bool = False, sync_type: str = None) -> Dict[str, Any]:
        """
        同步所有数据

        Args:
            full: 是否完整重建
            sync_type: 同步类型 entities/chapters/all

        Returns:
            同步结果统计
        """
        import json
        import re
        from pathlib import Path

        result = {
            "success": True,
            "entities_synced": 0,
            "chapters_synced": 0,
            "relationships_rebuilt": 0,
            "errors": [],
        }

        try:
            # 1. 加载 state.json 备份关键数据
            state_backup = {}
            state_path = self.config.project_root / ".webnovel" / "state.json"
            if state_path.exists():
                state_data = json.loads(state_path.read_text(encoding='utf-8'))
                state_backup = {
                    'strand_tracker': state_data.get('strand_tracker', {}),
                    'plot_threads': state_data.get('plot_threads', {}),
                    'progress': state_data.get('progress', {}),
                    'review_checkpoints': state_data.get('review_checkpoints', []),
                    'project_info': state_data.get('project_info', {}),
                    'target_words': state_data.get('target_words'),
                    'target_chapters': state_data.get('target_chapters'),
                }
                print(f"已备份 strand_tracker: {len(state_backup.get('strand_tracker', {}).get('history', []))} 条")
                print(f"已备份 plot_threads: {len(state_backup.get('plot_threads', {}).get('foreshadowing', []))} 条伏笔")

            # 2. 完整重建时清空表
            if full:
                print("清空数据库表...")
                with self._get_conn() as conn:
                    cursor = conn.cursor()
                    # 按依赖顺序清空
                    for table in ['relationship_events', 'relationships', 'appearances', 'scenes', 'chapters', 'entities']:
                        try:
                            cursor.execute(f"DELETE FROM {table}")
                        except:
                            pass
                    conn.commit()

            # 3. 同步实体（从设定集目录）
            if sync_type in (None, 'all', 'entities'):
                print("同步设定集...")
                entities_synced = self._sync_entities_from_settings()
                result["entities_synced"] = entities_synced

            # 4. 同步章节
            if sync_type in (None, 'all', 'chapters'):
                print("同步章节...")
                chapters_synced = self._sync_chapters_from_directory()
                result["chapters_synced"] = chapters_synced

            # 5. 扫描并解析审查报告
            print("扫描审查报告...")
            review_count = self._sync_review_reports(state_backup)
            result["reviews_synced"] = review_count

            # 6. 重建关系图谱
            print("重建关系图谱...")
            rel_count = self._rebuild_relationships()
            result["relationships_rebuilt"] = rel_count

            # 6. 恢复 state.json
            if state_path.exists() and state_backup:
                try:
                    state_data = json.loads(state_path.read_text(encoding='utf-8'))
                    # 更新关键字段
                    if state_backup.get('progress'):
                        state_data['progress'] = state_backup['progress']
                    if state_backup.get('strand_tracker'):
                        state_data['strand_tracker'] = state_backup['strand_tracker']
                    if state_backup.get('plot_threads'):
                        state_data['plot_threads'] = state_backup['plot_threads']
                    if state_backup.get('review_checkpoints'):
                        state_data['review_checkpoints'] = state_backup['review_checkpoints']
                    state_path.write_text(json.dumps(state_data, ensure_ascii=False, indent=2), encoding='utf-8')
                    print("state.json 已恢复")
                except Exception as e:
                    result["errors"].append(f"恢复state.json失败: {e}")

        except Exception as e:
            result["success"] = False
            result["errors"].append(str(e))

        return result

    def _sync_entities_from_settings(self) -> int:
        """从设定集目录同步实体"""
        import re
        import yaml

        settings_dir = self.config.project_root / "设定集"
        if not settings_dir.exists():
            return 0

        count = 0
        role_dirs = {'主角卡', '女主卡', '配角', '反派', '龙套角色', '角色', '人物'}
        item_dirs = {'丹药', '法宝', '符箓', '兵器', '防具', '材料', '灵宠', '阵法', '信物', '日常', '其他', '物品'}
        map_dirs = {'地点', '星球', '势力', '地图'}
        other_dirs = {'世界观', '境界', '力量体系', '金手指', '设计'}

        # 扫描角色库
        role_dir = settings_dir / "角色库"
        if role_dir.exists():
            for md_file in role_dir.rglob("*.md"):
                try:
                    self._sync_single_entity(md_file, '角色', role_dirs)
                    count += 1
                except Exception as e:
                    print(f"同步角色失败 {md_file}: {e}")

        # 扫描道具库
        item_dir = settings_dir / "道具库"
        if item_dir.exists():
            for md_file in item_dir.rglob("*.md"):
                try:
                    self._sync_single_entity(md_file, '道具', item_dirs)
                    count += 1
                except Exception as e:
                    print(f"同步道具失败 {md_file}: {e}")

        # 扫描地图库
        map_dir = settings_dir / "地图库"
        if map_dir.exists():
            for md_file in map_dir.rglob("*.md"):
                try:
                    self._sync_single_entity(md_file, '地点', map_dirs)
                    count += 1
                except Exception as e:
                    print(f"同步地图失败 {md_file}: {e}")

        # 扫描其他设定
        other_dir = settings_dir / "其他设定"
        if other_dir.exists():
            for md_file in other_dir.rglob("*.md"):
                try:
                    self._sync_single_entity(md_file, '其他设定', other_dirs)
                    count += 1
                except Exception as e:
                    print(f"同步其他设定失败 {md_file}: {e}")

        return count

    def _sync_single_entity(self, md_file: Path, default_type: str, valid_dirs: set) -> bool:
        """同步单个实体文件"""
        import yaml
        from .index_manager import EntityMeta

        content = md_file.read_text(encoding='utf-8')

        # 解析 frontmatter
        frontmatter = {}
        body = content
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1]) or {}
                    body = parts[2]
                except:
                    pass

        # 确定类型
        entity_type = frontmatter.get('type') or frontmatter.get('category') or default_type

        # 从目录推断类型
        try:
            rel_path = md_file.relative_to(self.config.project_root / "设定集")
            if len(rel_path.parts) > 1:
                dir_name = rel_path.parts[0]
                if dir_name in valid_dirs:
                    if default_type == '角色':
                        entity_type = '角色'
                    elif default_type == '道具':
                        entity_type = f'道具-{dir_name}'
                    else:
                        entity_type = dir_name
        except ValueError:
            pass

        # 获取名称
        entity_id = frontmatter.get('id') or frontmatter.get('name') or md_file.stem
        canonical_name = frontmatter.get('name') or frontmatter.get('title') or md_file.stem

        # 获取层级 - 修复龙套问题
        tier = frontmatter.get('tier', '装饰')
        # 如果是主角/女主/反派/配角，明确设置对应层级
        if entity_type == '角色':
            role_type = frontmatter.get('role_type', '')
            if role_type == '主角':
                tier = '核心'
            elif role_type == '女主':
                tier = '核心'
            elif '反派' in str(frontmatter.get('title', '')) or '反派' in str(frontmatter.get('desc', '')):
                tier = '重要'
            elif role_type == '配角':
                tier = '次要'
            elif role_type == '龙套':
                tier = '装饰'

        # 写入数据库
        entity = EntityMeta(
            id=entity_id,
            type=entity_type,
            canonical_name=canonical_name,
            tier=tier,
            desc=body[:200] if body else '',
        )
        self.upsert_entity(entity, update_metadata=True)
        return True

    def _sync_chapters_from_directory(self) -> int:
        """从章节目录同步章节

        支持两种目录结构：
        1. 正文/第X章/第X章.md (原始结构)
        2. 正文/第1卷/第XXXX章-标题.md (卷目录结构)
        """
        import re

        chapters_dir = self.config.project_root / "正文"
        if not chapters_dir.exists():
            return 0

        count = 0

        # 遍历正文目录下的所有条目
        for entry in chapters_dir.iterdir():
            # 情况1: 直接是章节目录 (正文/第X章/)
            if entry.is_dir():
                match = re.match(r'第(\d+)章', entry.name)
                if match:
                    chapter_num = int(match.group(1))
                    chapter_files = list(entry.glob("*.md"))
                    if chapter_files:
                        try:
                            self._sync_single_chapter(chapter_files[0], chapter_num)
                            count += 1
                        except Exception as e:
                            print(f"同步章节 {chapter_num} 失败: {e}")
                    continue

            # 情况2: 是卷目录 (正文/第1卷/)
            if entry.is_dir():
                # 检查卷目录下是否有章节文件
                for chapter_file in entry.glob("*.md"):
                    # 匹配 第XXXX章-标题.md 格式
                    match = re.match(r'第(\d+)章', chapter_file.stem)
                    if match:
                        chapter_num = int(match.group(1))
                        try:
                            self._sync_single_chapter(chapter_file, chapter_num)
                            count += 1
                        except Exception as e:
                            print(f"同步章节 {chapter_num} 失败: {e}")

        return count

    def _sync_single_chapter(self, chapter_file: Path, chapter: int) -> bool:
        """同步单个章节"""
        import re
        from .index_manager import ChapterMeta

        content = chapter_file.read_text(encoding='utf-8')

        # 去除 frontmatter
        body = content
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                body = parts[2]

        # 计算字数
        text_without_whitespace = re.sub(r'\s+', '', body)
        word_count = len(text_without_whitespace)

        # 提取标题
        title = chapter_file.stem.replace(f'第{chapter}章', '').strip('- ')

        # 写入章节
        chapter_meta = ChapterMeta(
            chapter=chapter,
            title=title,
            location="",
            word_count=word_count,
            characters=[],
            summary="",
        )
        self.add_chapter(chapter_meta)
        return True

    def _rebuild_relationships(self) -> int:
        """重建关系图谱"""
        from .index_manager import RelationshipMeta

        count = 0

        with self._get_conn() as conn:
            cursor = conn.cursor()

            # 获取所有实体
            cursor.execute("SELECT id, canonical_name, type FROM entities")
            entities = {row[0]: row[1] for row in cursor.fetchall()}

            # 获取所有出场记录
            cursor.execute("SELECT entity_id, chapter FROM appearances ORDER BY chapter")
            appearances = cursor.fetchall()

            # 按章节分组
            chapter_entities = {}
            for entity_id, chapter in appearances:
                if chapter not in chapter_entities:
                    chapter_entities[chapter] = []
                if entity_id in entities and entity_id not in chapter_entities[chapter]:
                    chapter_entities[chapter].append(entity_id)

            # 为同一章节出场的实体建立关系
            relationships_set = set()
            for chapter, entity_list in chapter_entities.items():
                for i, e1 in enumerate(entity_list):
                    for e2 in entity_list[i+1:]:
                        rel_key = tuple(sorted([e1, e2]))
                        if rel_key not in relationships_set:
                            relationships_set.add(rel_key)
                            rel = RelationshipMeta(
                                from_entity=e1,
                                to_entity=e2,
                                type="同章节出场",
                                description=f"第{chapter}章同时出场",
                                chapter=chapter,
                            )
                            self.upsert_relationship(rel)
                            count += 1

        return count

    def _sync_review_reports(self, state_backup: Dict) -> int:
        """
        扫描审查报告目录，解析报告内容并入库

        审查报告格式：
        - 目录：审查报告/
        - 文件名：第{start}-{end}章审查报告.md
        - 内容格式：YAML frontmatter + Markdown 正文
        """
        import re
        import yaml

        project_root = self.config.project_root
        review_dir = project_root / "审查报告"
        if not review_dir.exists():
            print("  审查报告目录不存在，跳过")
            return 0

        count = 0
        all_foreshadowing = []

        # 查找所有审查报告文件
        for md_file in review_dir.glob("*.md"):
            try:
                # 解析文件名获取章节范围
                # 格式：第1-10章审查报告.md 或 第10章审查报告.md
                filename = md_file.stem
                match = re.match(r'第(\d+)(?:-(\d+))?章审查报告', filename)
                if not match:
                    continue

                start_chapter = int(match.group(1))
                end_chapter = int(match.group(2)) if match.group(2) else start_chapter

                # 读取并解析审查报告
                content = md_file.read_text(encoding='utf-8')

                # 解析 frontmatter
                frontmatter = {}
                body = content
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        try:
                            frontmatter = yaml.safe_load(parts[1]) or {}
                            body = parts[2]
                        except:
                            pass

                # 提取关键数据
                hook_type = frontmatter.get('hook_type', '')
                hook_strength = frontmatter.get('hook_strength', 'medium')
                coolpoint_patterns = frontmatter.get('coolpoint_patterns', [])
                micropayoffs = frontmatter.get('micropayoffs', [])
                hard_violations = frontmatter.get('hard_violations', [])
                soft_suggestions = frontmatter.get('soft_suggestions', [])
                is_transition = frontmatter.get('is_transition', False)
                override_count = frontmatter.get('override_count', 0)
                debt_balance = frontmatter.get('debt_balance', 0.0)

                # 保存追读力数据（每个章节）
                for chapter in range(start_chapter, end_chapter + 1):
                    self._save_chapter_reading_power(
                        chapter=chapter,
                        hook_type=hook_type,
                        hook_strength=hook_strength,
                        coolpoint_patterns=coolpoint_patterns,
                        micropayoffs=micropayoffs,
                        hard_violations=hard_violations,
                        soft_suggestions=soft_suggestions,
                        is_transition=is_transition,
                        override_count=override_count,
                        debt_balance=debt_balance,
                    )

                # 提取伏笔信息
                foreshadowing = self._extract_foreshadowing(body, start_chapter)
                all_foreshadowing.extend(foreshadowing)

                count += 1
                print(f"  已处理审查报告：第{start_chapter}-{end_chapter}章")

            except Exception as e:
                print(f"  处理审查报告失败 {md_file}: {e}")

        # 保存伏笔到 state.json
        if count > 0 and all_foreshadowing:
            self._update_foreshadowing_in_state(all_foreshadowing, state_backup)

        return count

    def _save_chapter_reading_power(
        self,
        chapter: int,
        hook_type: str,
        hook_strength: str,
        coolpoint_patterns: list,
        micropayoffs: list,
        hard_violations: list,
        soft_suggestions: list,
        is_transition: bool,
        override_count: int,
        debt_balance: float,
    ) -> bool:
        """保存章节追读力数据"""
        from .index_manager import ChapterReadingPowerMeta

        meta = ChapterReadingPowerMeta(
            chapter=chapter,
            hook_type=hook_type,
            hook_strength=hook_strength,
            coolpoint_patterns=coolpoint_patterns,
            micropayoffs=micropayoffs,
            hard_violations=hard_violations,
            soft_suggestions=soft_suggestions,
            is_transition=is_transition,
            override_count=override_count,
            debt_balance=debt_balance,
        )
        self.save_chapter_reading_power(meta)
        return True

    def _extract_foreshadowing(self, body: str, start_chapter: int) -> list:
        """
        从审查报告正文中提取伏笔信息

        伏笔格式：
        - ### 伏笔 [ID]: 描述 @章节
        - - [ID] 描述
        """
        import re
        foreshadowing = []
        lines = body.split('\n')
        current_foreshadowing = None

        for line in lines:
            line = line.strip()

            # 匹配伏笔标题
            # ### 伏笔 [foreshadow_1]: xxx @第5章
            match = re.match(r'###\s*伏笔\s*\[([^\]]+)\]:\s*(.+)', line)
            if match:
                fs_id = match.group(1).strip()
                fs_desc = match.group(2).strip()
                # 提取章节号
                chapter_match = re.search(r'@第(\d+)章', fs_desc)
                chapter = int(chapter_match.group(1)) if chapter_match else start_chapter
                fs_desc = re.sub(r'@\S+', '', fs_desc).strip()

                foreshadowing.append({
                    'id': fs_id,
                    'description': fs_desc,
                    'created_chapter': chapter,
                    'status': 'active',
                })
                continue

            # 匹配列表格式的伏笔
            # - [foreshadow_2] 描述
            match = re.match(r'-\s*\[([^\]]+)\]\s*(.+)', line)
            if match and '伏笔' in '\n'.join(lines[max(0, lines.index(line)-5):lines.index(line)]):
                fs_id = match.group(1).strip()
                fs_desc = match.group(2).strip()
                foreshadowing.append({
                    'id': fs_id,
                    'description': fs_desc,
                    'created_chapter': start_chapter,
                    'status': 'active',
                })

        return foreshadowing

    def _update_foreshadowing_in_state(self, new_foreshadowing: list, state_backup: Dict):
        """更新 state.json 中的伏笔数据（去重合并）"""
        state_path = self.config.project_root / ".webnovel" / "state.json"
        if not state_path.exists():
            return

        try:
            state_data = json.loads(state_path.read_text(encoding='utf-8'))
            plot_threads = state_data.get('plot_threads', {})
            existing_foreshadowing = plot_threads.get('foreshadowing', [])

            # 去重合并
            existing_ids = {f.get('id') for f in existing_foreshadowing}
            added_count = 0
            for f in new_foreshadowing:
                if f.get('id') not in existing_ids:
                    existing_foreshadowing.append(f)
                    added_count += 1

            plot_threads['foreshadowing'] = existing_foreshadowing
            state_data['plot_threads'] = plot_threads
            state_path.write_text(json.dumps(state_data, ensure_ascii=False, indent=2), encoding='utf-8')
            print(f"  已更新伏笔数据，新增 {added_count} 条，共 {len(existing_foreshadowing)} 条")
        except Exception as e:
            print(f"  更新伏笔失败: {e}")

    # ==================== 辅助方法 ====================

