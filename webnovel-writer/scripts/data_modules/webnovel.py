#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
webnovel 统一入口（面向 skills / agents 的稳定 CLI）

设计目标：
- 只有一个入口命令，避免到处拼 `python -m data_modules.xxx ...` 导致参数位置/引号/路径炸裂。
- 自动解析正确的 book project_root（包含 `.webnovel/state.json` 的目录）。
- 所有写入类命令在解析到 project_root 后，统一前置 `--project-root` 传给具体模块。

典型用法（推荐，不依赖 PYTHONPATH / 不要求 cd）：
  python "<SCRIPTS_DIR>/webnovel.py" preflight
  python "<SCRIPTS_DIR>/webnovel.py" where
  python "<SCRIPTS_DIR>/webnovel.py" use D:\\wk\\xiaoshuo\\凡人资本论
  python "<SCRIPTS_DIR>/webnovel.py" --project-root D:\\wk\\xiaoshuo index stats
  python "<SCRIPTS_DIR>/webnovel.py" --project-root D:\\wk\\xiaoshuo state process-chapter --chapter 100 --data @payload.json
  python "<SCRIPTS_DIR>/webnovel.py" --project-root D:\\wk\\xiaoshuo extract-context --chapter 100 --format json

也支持（不推荐，容易踩 PYTHONPATH/cd/参数顺序坑）：
  python -m data_modules.webnovel where
"""

from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

from runtime_compat import normalize_windows_path
from project_locator import resolve_project_root, write_current_project_pointer, update_global_registry_current_project


def _scripts_dir() -> Path:
    # data_modules/webnovel.py -> data_modules -> scripts
    return Path(__file__).resolve().parent.parent


def _resolve_root(explicit_project_root: Optional[str]) -> Path:
    # 允许显式传入工作区根目录或书项目根目录
    raw = explicit_project_root
    if raw:
        return resolve_project_root(raw)
    return resolve_project_root()


def _strip_project_root_args(argv: list[str]) -> list[str]:
    """
    下游工具统一由本入口注入 `--project-root`，避免重复传参导致 argparse 报错/歧义。
    """
    out: list[str] = []
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok == "--project-root":
            i += 2
            continue
        if tok.startswith("--project-root="):
            i += 1
            continue
        out.append(tok)
        i += 1
    return out


def _run_data_module(module: str, argv: list[str]) -> int:
    """
    Import `data_modules.<module>` and call its main(), while isolating sys.argv.
    """
    mod = importlib.import_module(f"data_modules.{module}")
    main = getattr(mod, "main", None)
    if not callable(main):
        raise RuntimeError(f"data_modules.{module} 缺少可调用的 main()")

    old_argv = sys.argv
    try:
        sys.argv = [f"data_modules.{module}"] + argv
        try:
            main()
            return 0
        except SystemExit as e:
            return int(e.code or 0)
    finally:
        sys.argv = old_argv


def _run_script(script_name: str, argv: list[str]) -> int:
    """
    Run a script under `.claude/scripts/` via a subprocess.

    用途：兼容没有 main() 的脚本（例如 workflow_manager.py）。
    """
    script_path = _scripts_dir() / script_name
    if not script_path.is_file():
        raise FileNotFoundError(f"未找到脚本: {script_path}")
    proc = subprocess.run([sys.executable, str(script_path), *argv])
    return int(proc.returncode or 0)


def cmd_where(args: argparse.Namespace) -> int:
    root = _resolve_root(args.project_root)
    print(str(root))
    return 0


def _build_preflight_report(explicit_project_root: Optional[str]) -> dict:
    scripts_dir = _scripts_dir().resolve()
    plugin_root = scripts_dir.parent
    skill_root = plugin_root / "skills" / "webnovel-write"
    entry_script = scripts_dir / "webnovel.py"
    extract_script = scripts_dir / "extract_chapter_context.py"

    checks: list[dict[str, object]] = [
        {"name": "scripts_dir", "ok": scripts_dir.is_dir(), "path": str(scripts_dir)},
        {"name": "entry_script", "ok": entry_script.is_file(), "path": str(entry_script)},
        {"name": "extract_context_script", "ok": extract_script.is_file(), "path": str(extract_script)},
        {"name": "skill_root", "ok": skill_root.is_dir(), "path": str(skill_root)},
    ]

    project_root = ""
    project_root_error = ""
    try:
        resolved_root = _resolve_root(explicit_project_root)
        project_root = str(resolved_root)
        checks.append({"name": "project_root", "ok": True, "path": project_root})
    except Exception as exc:
        project_root_error = str(exc)
        checks.append({"name": "project_root", "ok": False, "path": explicit_project_root or "", "error": project_root_error})

    return {
        "ok": all(bool(item["ok"]) for item in checks),
        "project_root": project_root,
        "scripts_dir": str(scripts_dir),
        "skill_root": str(skill_root),
        "checks": checks,
        "project_root_error": project_root_error,
    }


def cmd_preflight(args: argparse.Namespace) -> int:
    report = _build_preflight_report(args.project_root)
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for item in report["checks"]:
            status = "OK" if item["ok"] else "ERROR"
            path = item.get("path") or ""
            print(f"{status} {item['name']}: {path}")
            if item.get("error"):
                print(f"  detail: {item['error']}")
    return 0 if report["ok"] else 1


def cmd_use(args: argparse.Namespace) -> int:
    project_root = normalize_windows_path(args.project_root).expanduser()
    try:
        project_root = project_root.resolve()
    except Exception:
        project_root = project_root

    workspace_root: Optional[Path] = None
    if args.workspace_root:
        workspace_root = normalize_windows_path(args.workspace_root).expanduser()
        try:
            workspace_root = workspace_root.resolve()
        except Exception:
            workspace_root = workspace_root

    # 1) 写入工作区指针（若工作区内存在 `.claude/`）
    pointer_file = write_current_project_pointer(project_root, workspace_root=workspace_root)
    if pointer_file is not None:
        print(f"workspace pointer: {pointer_file}")
    else:
        print("workspace pointer: (skipped)")

    # 2) 写入用户级 registry（保证全局安装/空上下文可恢复）
    reg_path = update_global_registry_current_project(workspace_root=workspace_root, project_root=project_root)
    if reg_path is not None:
        print(f"global registry: {reg_path}")
    else:
        print("global registry: (skipped)")

    return 0


def cmd_update_character_card(args: argparse.Namespace) -> int:
    """更新角色卡出场记录"""
    import json
    from pathlib import Path

    project_root = _resolve_root(args.project_root)
    chapter = args.chapter

    # 导入需要的模块
    from data_modules.state_manager import StateManager
    from data_modules.index_manager import IndexManager
    from data_modules.config import get_config

    config = get_config(project_root)
    sm = StateManager(config)
    im = IndexManager(config)

    # 获取本章出场角色
    chapter_data = im.get_chapter(chapter)
    if not chapter_data:
        print(f"未找到章节 {chapter} 的数据")
        return 1

    # 从 chapter_data 获取出场角色
    characters = chapter_data.get("characters", [])
    if isinstance(characters, str):
        try:
            characters = json.loads(characters)
        except:
            characters = []

    if not characters:
        print(f"章节 {chapter} 没有角色出场")
        return 0

    print(f"章节 {chapter} 出场角色: {characters}")

    # 获取设定集目录
    settings_dir = project_root / "设定集"

    # 定义角色卡文件路径映射
    character_card_paths = {
        # 主角名 -> 主角卡
        # 女主名 -> 女主卡
        # 其他 -> 角色库
    }

    # 从 state.json 获取主角和女主信息
    state = sm._state
    protagonist_name = state.get("protagonist", {}).get("name", "")
    heroines = state.get("relationship", {}).get("heroine_names", [])

    updated_cards = []

    for char_id in characters:
        # 获取角色详细信息
        entity = sm.get_entity(char_id, "角色")
        if not entity:
            # 尝试从 SQLite 获取
            entity = sm.get_entity(char_id)
            if entity and entity.get("type") != "角色":
                entity = None

        if not entity:
            print(f"未找到角色 {char_id} 的实体信息")
            continue

        char_name = entity.get("name", char_id)
        first_appearance = entity.get("first_appearance", 0)
        last_appearance = entity.get("last_appearance", 0)
        tier = entity.get("tier", "次要")

        # 龙套角色（tier="装饰"）跳过创建完整角色卡
        if tier == "装饰":
            print(f"跳过龙套角色（装饰）: {char_name}")
            continue

        # 确定角色卡文件路径
        card_path = None
        card_type = ""

        # 检查是否是主角
        if protagonist_name and (char_name == protagonist_name or char_id == protagonist_name):
            card_path = settings_dir / "主角卡.md"
            card_type = "主角"
        # 检查是否是女主
        elif heroines and char_name in heroines:
            card_path = settings_dir / "女主卡.md"
            card_type = "女主"
        else:
            # 其他角色，查找角色库
            tier = entity.get("tier", "次要")
            if tier == "核心":
                card_dir = settings_dir / "角色库" / "主要角色"
            elif tier == "重要":
                card_dir = settings_dir / "角色库" / "主要角色"
            elif tier == "次要":
                card_dir = settings_dir / "角色库" / "次要角色"
            else:
                card_dir = settings_dir / "角色库" / "次要角色"

            # 查找对应的角色卡文件
            if card_dir.exists():
                # 尝试查找与角色名匹配的文件
                for f in card_dir.glob("*.md"):
                    if char_name in f.stem or char_id in f.stem:
                        card_path = f
                        break

            if not card_path:
                # 如果没有找到，尝试创建新文件
                card_path = card_dir / f"{char_name}.md"
                card_type = f"角色（{tier}）"

        if card_path:
            # 读取现有角色卡内容
            if card_path.exists():
                content = card_path.read_text(encoding="utf-8")
            else:
                # 使用模板创建新角色卡
                content = _generate_character_card_template(char_name, entity)

            # 更新出场记录
            content = _update_appearance_record(content, chapter, first_appearance, last_appearance, char_type=card_type)

            # 写入更新后的内容
            card_path.parent.mkdir(parents=True, exist_ok=True)
            card_path.write_text(content, encoding="utf-8")
            updated_cards.append(str(card_path))
            print(f"已更新角色卡: {card_path} (角色: {char_name})")

    if updated_cards:
        print(f"共更新 {len(updated_cards)} 个角色卡")
    else:
        print("没有角色卡需要更新")

    return 0


def cmd_update_minor_characters(args: argparse.Namespace) -> int:
    """更新龙套角色库（轻量级记录）"""
    import json
    import re
    from pathlib import Path

    project_root = _resolve_root(args.project_root)
    chapter = args.chapter

    # 导入需要的模块
    from data_modules.state_manager import StateManager
    from data_modules.index_manager import IndexManager
    from data_modules.config import get_config

    config = get_config(project_root)
    sm = StateManager(config)
    im = IndexManager(config)

    # 获取本章出场角色
    chapter_data = im.get_chapter(chapter)
    if not chapter_data:
        print(f"未找到章节 {chapter} 的数据")
        return 1

    characters = chapter_data.get("characters", [])
    if isinstance(characters, str):
        try:
            characters = json.loads(characters)
        except:
            characters = []

    if not characters:
        print(f"章节 {chapter} 没有角色出场")
        return 0

    # 获取设定集目录
    settings_dir = project_root / "设定集"
    minor_dir = settings_dir / "角色库" / "龙套角色"
    minor_dir.mkdir(parents=True, exist_ok=True)

    def sanitize_filename(name: str) -> str:
        """清理文件名，移除非法字符"""
        # 替换不能用于文件名的字符
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        # 限制长度
        return name[:50] if len(name) > 50 else name

    def generate_minor_filename(entity: dict, relationships: list) -> str:
        """
        生成龙套角色的文件名
        优先使用：关系角色 + 关系描述，如 "温家车夫"、"秦鹏重病的父亲"
        回退：使用角色名
        """
        char_name = entity.get("name", "")
        desc = entity.get("desc", "")

        # 尝试从关系中提取
        for rel in relationships:
            to_entity = rel.get("to_entity", "")
            rel_type = rel.get("type", "")
            description = rel.get("description", "")

            if to_entity and rel_type:
                # 优先使用描述，如 "车夫"、"父亲"、"管家"
                if description:
                    return f"{to_entity}{description}"
                # 其次使用关系类型
                return f"{to_entity}{rel_type}"

        # 尝试从角色描述中提取身份描述
        if desc:
            # 提取常见的身份描述词
            identity_keywords = ["车夫", "管家", "父亲", "母亲", "兄长", "弟弟", "妹妹", "师父", "徒弟",
                               "大夫", "商人", "伙计", "小二", "丫鬟", "婢女", "护卫", "随从",
                               "村民", "老者", "少年", "中年人", "道士", "和尚", "书生"]
            for keyword in identity_keywords:
                if keyword in desc:
                    return f"{char_name}{keyword}"

        # 回退：直接使用角色名
        return char_name

    updated_count = 0

    for char_id in characters:
        # 获取角色详细信息
        entity = sm.get_entity(char_id, "角色")
        if not entity:
            entity = sm.get_entity(char_id)
            if entity and entity.get("type") != "角色":
                entity = None

        if not entity:
            continue

        char_name = entity.get("name", char_id)
        tier = entity.get("tier", "次要")
        first_appearance = entity.get("first_appearance", 0)
        last_appearance = entity.get("last_appearance", 0)
        desc = entity.get("desc", "")

        # 只处理龙套角色（tier="装饰"）
        if tier != "装饰":
            continue

        # 获取角色关系
        try:
            relationships = im.get_entity_relationships(char_id, "from")
        except:
            relationships = []

        # 生成文件名
        filename = generate_minor_filename(entity, relationships)
        filename = sanitize_filename(filename)

        if not filename:
            filename = char_name

        # 每个角色一个文件
        record_file = minor_dir / f"{filename}.md"

        # 读取现有内容或创建新文件
        if record_file.exists():
            content = record_file.read_text(encoding="utf-8")
        else:
            content = f"# {char_name}\n\n"

        # 检查是否已存在该角色的记录（通过首次出场章节判断）
        if "首次出场" not in content:
            # 添加新角色基本信息
            content += f"""## 基本信息

- **角色名**: {char_name}
- **首次出场**: 第{chapter}章
- **最后出场**: 第{chapter}章
- **出场章节**: [{chapter}]
- **角色描述**: {desc}

## 出场记录

| 章节 | 出场描述 |
|------|---------|
| 第{chapter}章 | {desc} |

"""
        else:
            # 更新已有记录
            # 更新最后出场章节
            content = re.sub(
                r'(- \*\*最后出场\*\*: )第\d+章',
                f'\\1第{chapter}章',
                content
            )
            # 更新出场章节列表
            old_chapters = re.search(r'\*\*出场章节\*\*: \[(.*?)\]', content)
            if old_chapters:
                existing_chapters = old_chapters.group(1)
                if str(chapter) not in existing_chapters:
                    new_chapters = f"{existing_chapters}, {chapter}"
                    content = content.replace(
                        f"**出场章节**: [{existing_chapters}]",
                        f"**出场章节**: [{new_chapters}]"
                    )
            else:
                content = content.replace(
                    "**出场章节**: [",
                    f"**出场章节**: [{chapter}, "
                )

            # 添加新的出场记录到表格
            if f"| 第{chapter}章 |" not in content:
                # 找到表格位置插入新行
                table_line = f"| 第{chapter}章 | {desc} |"
                content = content.replace(
                    "| 章节 | 出场描述 |",
                    f"| 章节 | 出场描述 |\n|------|---------|"
                )
                content = content.replace(
                    "| 章节 | 出场描述 |\n|------|---------|",
                    table_line
                )

        # 写入更新后的内容
        record_file.write_text(content, encoding="utf-8")

        updated_count += 1
        print(f"已更新龙套角色记录: {char_name} -> {record_file.name}")

    if updated_count > 0:
        print(f"共更新 {updated_count} 个龙套角色记录")
    else:
        print("本章没有新出场的龙套角色需要记录")

    return 0


def _generate_character_card_template(char_name: str, entity: dict) -> str:
    """生成角色卡模板"""
    tier = entity.get("tier", "次要")
    desc = entity.get("desc", "")
    aliases = entity.get("aliases", [])

    template = f"""# {char_name}

## 基本信息
- 姓名：{char_name}
- 身份：
- 起点状态：

## 出场记录
- 首次出场章节：
- 最后出场章节：
- 出场章节列表：
- 本章出场摘要：

## 核心标签
- 3个关键词：
- 读者第一印象：

## 性格与底色
- 核心性格：
- 行为底线：
- 情绪触发点：

## 动机与目标
- 短期目标：
- 中期目标：
- 长期目标：

## 缺陷与代价
- 性格缺陷：
- 能力限制：

## 关系
{'- 主角关系：' + (desc if desc else '')}

## OOC 警戒
- 绝不该做的事：
- 需要提前铺垫的事：
"""
    return template


def _update_appearance_record(content: str, chapter: int, first_appearance: int, last_appearance: int, char_type: str = "") -> str:
    """更新角色卡的出场记录部分"""
    lines = content.split("\n")

    # 查找"出场记录"部分
    in_appearance_section = False
    updated_lines = []
    first_found = False
    last_found = False
    list_found = False

    for i, line in enumerate(lines):
        # 检测是否进入出场记录部分
        if "出场记录" in line and ("##" in line or "#" in line):
            in_appearance_section = True
            updated_lines.append(line)
            continue

        if in_appearance_section:
            # 检测是否离开出场记录部分（遇到下一个 ## 标题）
            if line.strip().startswith("## ") and "出场记录" not in line:
                in_appearance_section = False
                updated_lines.append(line)
                continue

            # 更新首次出场章节
            if "首次出场章节" in line and ":" in line:
                first_found = True
                # 首次出场取较小值
                if first_appearance == 0 or first_appearance > chapter:
                    first_appearance = chapter
                updated_lines.append(f"- 首次出场章节：第{first_appearance}章")
                continue

            # 更新最后出场章节
            if "最后出场章节" in line and ":" in line:
                last_found = True
                # 最后出场取较大值
                if last_appearance < chapter:
                    last_appearance = chapter
                updated_lines.append(f"- 最后出场章节：第{last_appearance}章")
                continue

            # 更新出场章节列表
            if "出场章节列表" in line and ":" in line:
                list_found = True
                updated_lines.append(f"- 出场章节列表：第{chapter}章")
                continue

        updated_lines.append(line)

    return "\n".join(updated_lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="webnovel unified CLI")
    parser.add_argument("--project-root", help="书项目根目录或工作区根目录（可选，默认自动检测）")

    sub = parser.add_subparsers(dest="tool", required=True)

    p_where = sub.add_parser("where", help="打印解析出的 project_root")
    p_where.set_defaults(func=cmd_where)

    p_preflight = sub.add_parser("preflight", help="校验统一 CLI 运行环境与 project_root")
    p_preflight.add_argument("--format", choices=["text", "json"], default="text", help="输出格式")
    p_preflight.set_defaults(func=cmd_preflight)

    p_use = sub.add_parser("use", help="绑定当前工作区使用的书项目（写入指针/registry）")
    p_use.add_argument("project_root", help="书项目根目录（必须包含 .webnovel/state.json）")
    p_use.add_argument("--workspace-root", help="工作区根目录（可选；默认由运行环境推断）")
    p_use.set_defaults(func=cmd_use)

    # Pass-through to data modules
    p_index = sub.add_parser("index", help="转发到 index_manager")
    p_index.add_argument("args", nargs=argparse.REMAINDER)

    p_state = sub.add_parser("state", help="转发到 state_manager")
    p_state.add_argument("args", nargs=argparse.REMAINDER)

    p_rag = sub.add_parser("rag", help="转发到 rag_adapter")
    p_rag.add_argument("args", nargs=argparse.REMAINDER)

    p_style = sub.add_parser("style", help="转发到 style_sampler")
    p_style.add_argument("args", nargs=argparse.REMAINDER)

    p_entity = sub.add_parser("entity", help="转发到 entity_linker")
    p_entity.add_argument("args", nargs=argparse.REMAINDER)

    p_context = sub.add_parser("context", help="转发到 context_manager")
    p_context.add_argument("args", nargs=argparse.REMAINDER)

    p_migrate = sub.add_parser("migrate", help="转发到 migrate_state_to_sqlite")
    p_migrate.add_argument("args", nargs=argparse.REMAINDER)

    # Pass-through to scripts
    p_workflow = sub.add_parser("workflow", help="转发到 workflow_manager.py")
    p_workflow.add_argument("args", nargs=argparse.REMAINDER)

    p_status = sub.add_parser("status", help="转发到 status_reporter.py")
    p_status.add_argument("args", nargs=argparse.REMAINDER)

    p_update_state = sub.add_parser("update-state", help="转发到 update_state.py")
    p_update_state.add_argument("args", nargs=argparse.REMAINDER)

    p_backup = sub.add_parser("backup", help="转发到 backup_manager.py")
    p_backup.add_argument("args", nargs=argparse.REMAINDER)

    p_archive = sub.add_parser("archive", help="转发到 archive_manager.py")
    p_archive.add_argument("args", nargs=argparse.REMAINDER)

    p_init = sub.add_parser("init", help="转发到 init_project.py（初始化项目）")
    p_init.add_argument("args", nargs=argparse.REMAINDER)

    p_extract_context = sub.add_parser("extract-context", help="转发到 extract_chapter_context.py")
    p_extract_context.add_argument("--chapter", type=int, required=True, help="目标章节号")
    p_extract_context.add_argument("--format", choices=["text", "json"], default="text", help="输出格式")

    # 角色卡更新
    p_character_card = sub.add_parser("update-character-card", help="更新角色卡出场记录")
    p_character_card.add_argument("--chapter", type=int, required=True, help="目标章节号")
    p_character_card.set_defaults(func=cmd_update_character_card)

    # 龙套角色库更新
    p_minor_chars = sub.add_parser("update-minor-characters", help="更新龙套角色库")
    p_minor_chars.add_argument("--chapter", type=int, required=True, help="目标章节号")
    p_minor_chars.set_defaults(func=cmd_update_minor_characters)

    # 兼容：允许 `--project-root` 出现在任意位置（减少 agents/skills 拼命令的出错率）
    from .cli_args import normalize_global_project_root

    argv = normalize_global_project_root(sys.argv[1:])
    args = parser.parse_args(argv)

    # where/use 直接执行
    if hasattr(args, "func"):
        code = int(args.func(args) or 0)
        raise SystemExit(code)

    tool = args.tool
    rest = list(getattr(args, "args", []) or [])
    # argparse.REMAINDER 可能以 `--` 开头占位，这里去掉
    if rest[:1] == ["--"]:
        rest = rest[1:]
    rest = _strip_project_root_args(rest)

    # init 是创建项目，不应该依赖/注入已存在 project_root
    if tool == "init":
        raise SystemExit(_run_script("init_project.py", rest))

    # 其余工具：统一解析 project_root 后前置给下游
    project_root = _resolve_root(args.project_root)
    forward_args = ["--project-root", str(project_root)]

    if tool == "index":
        raise SystemExit(_run_data_module("index_manager", [*forward_args, *rest]))
    if tool == "state":
        raise SystemExit(_run_data_module("state_manager", [*forward_args, *rest]))
    if tool == "rag":
        raise SystemExit(_run_data_module("rag_adapter", [*forward_args, *rest]))
    if tool == "style":
        raise SystemExit(_run_data_module("style_sampler", [*forward_args, *rest]))
    if tool == "entity":
        raise SystemExit(_run_data_module("entity_linker", [*forward_args, *rest]))
    if tool == "context":
        raise SystemExit(_run_data_module("context_manager", [*forward_args, *rest]))
    if tool == "migrate":
        raise SystemExit(_run_data_module("migrate_state_to_sqlite", [*forward_args, *rest]))

    if tool == "workflow":
        raise SystemExit(_run_script("workflow_manager.py", [*forward_args, *rest]))
    if tool == "status":
        raise SystemExit(_run_script("status_reporter.py", [*forward_args, *rest]))
    if tool == "update-state":
        raise SystemExit(_run_script("update_state.py", [*forward_args, *rest]))
    if tool == "backup":
        raise SystemExit(_run_script("backup_manager.py", [*forward_args, *rest]))
    if tool == "archive":
        raise SystemExit(_run_script("archive_manager.py", [*forward_args, *rest]))
    if tool == "extract-context":
        return_args = [*forward_args, "--chapter", str(args.chapter), "--format", str(args.format)]
        raise SystemExit(_run_script("extract_chapter_context.py", return_args))

    raise SystemExit(2)


if __name__ == "__main__":
    main()
