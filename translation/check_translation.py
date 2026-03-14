# -*- coding: utf-8 -*-
"""
校验翻译完成度：对比剧本原文（data.code.articles）与译文文件（out/{剧本id}.json）的 key，
统计每个剧本及总体的「总句数 / 已译 / 未译 / 完成率」。
支持：仅校验喜好角色（config/favorites.json）、校验全部角色。
"""
import os
import sys
import re
import json
import argparse


def _script_dir():
    return os.path.dirname(os.path.abspath(__file__))


def _project_root():
    """游戏项目根目录（bokusen-pygame）"""
    return os.path.dirname(_script_dir())


def _out_dir():
    return os.path.join(_script_dir(), "out")


def _json_dir():
    """剧本 json：仅上一级到 py 脚本根目录，取该目录下的 json"""
    return os.path.join(_project_root(), "json")


def _favorites_path():
    return os.path.join(_project_root(), "config", "favorites.json")


def _trim_key(s):
    """与 translate 一致：原文 trim 后作为 key。"""
    if not isinstance(s, str):
        return s
    s = s.strip()
    while s and s[0] in "\ufeff\u200b\u200c\u200d\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u00a0":
        s = s[1:]
    while s and s[-1] in "\ufeff\u200b\u200c\u200d\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u00a0":
        s = s[:-1]
    return s


def story_id_to_num(story_id):
    s = str(story_id).strip()
    if s.isdigit():
        return int(s)
    m = re.search(r"\d+", s)
    return int(m.group()) if m else None


def load_favorites():
    path = _favorites_path()
    if not os.path.isfile(path):
        return set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return set()
        return set(
            int(x) for x in data
            if isinstance(x, (int, float)) or (isinstance(x, str) and x.strip().isdigit())
        )
    except Exception as e:
        print(f"加载收藏列表失败: {e}")
        return set()


def get_target_story_ids(favorites_only):
    jd = _json_dir()
    if not os.path.isdir(jd):
        print(f"json 目录不存在: {jd}")
        return []
    all_ids = [f[:-5] for f in os.listdir(jd) if f.endswith(".json")]
    if not favorites_only:
        return all_ids
    fav = load_favorites()
    return [sid for sid in all_ids if story_id_to_num(sid) in fav]


def check_one(story_id):
    """返回 (总句数, 已译数, 未译原文列表)。"""
    jd = _json_dir()
    od = _out_dir()
    script_path = os.path.join(jd, f"{story_id}.json")
    out_path = os.path.join(od, f"{story_id}.json")

    if not os.path.isfile(script_path):
        return 0, 0, []

    try:
        with open(script_path, "r", encoding="utf-8") as f:
            obj = json.load(f)
    except Exception as e:
        print(f"  读取失败 {story_id}.json: {e}")
        return 0, 0, []

    code = obj.get("data", {}).get("code")
    if not code:
        return 0, 0, []
    articles = code.get("articles", [])
    if not articles:
        return 0, 0, []

    # 原文集合：trim 后作为 key，与译文文件 key 一致
    originals = set()
    for raw in articles:
        if isinstance(raw, str) and raw.strip():
            k = _trim_key(raw.strip())
            if k:
                originals.add(k)

    total = len(originals)
    if total == 0:
        return 0, 0, []

    # 译文 key 集合
    trans_keys = set()
    if os.path.isfile(out_path):
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                trans = json.load(f)
            if isinstance(trans, dict):
                trans_keys = set(trans.keys())
        except Exception:
            pass

    translated = len(originals & trans_keys)
    missing = list(originals - trans_keys)
    return total, translated, missing


def main():
    parser = argparse.ArgumentParser(description="校验原文与译文 key 是否全部对上，输出统计信息")
    parser.add_argument("--favorites", action="store_true", help="仅校验 config/favorites.json 中的喜好角色")
    parser.add_argument("--all", action="store_true", help="校验全部角色")
    parser.add_argument("--verbose", "-v", action="store_true", help="输出每个剧本的未译原文片段（前 50 字）")
    args = parser.parse_args()
    if not args.favorites and not args.all:
        print("请指定 --favorites 或 --all")
        parser.print_help()
        sys.exit(1)

    target_ids = get_target_story_ids(args.favorites)
    if not target_ids:
        print("没有找到待校验剧本")
        sys.exit(0)

    out_dir = _out_dir()
    print(f"剧本目录: {_json_dir()}")
    print(f"译文目录: {out_dir}")
    print(f"校验范围: {'喜好角色' if args.favorites else '全部角色'}，共 {len(target_ids)} 个剧本")
    print("-" * 60)

    total_lines = 0
    total_done = 0
    completed_scripts = 0
    incomplete_scripts = []

    for story_id in target_ids:
        t, d, missing = check_one(story_id)
        total_lines += t
        total_done += d
        if t == 0:
            continue
        pct = 100.0 * d / t if t else 0
        if d == t:
            completed_scripts += 1
            status = "完成"
        else:
            incomplete_scripts.append((story_id, t, d, missing))
            status = f"缺 {len(missing)} 句"
        print(f"  {story_id}")
        print(f"    总句数: {t}  已译: {d}  未译: {t - d}  完成率: {pct:.1f}%  [{status}]")
        if args.verbose and missing:
            for i, text in enumerate(missing[:10]):
                snippet = (text[:50] + "…") if len(text) > 50 else text
                print(f"      未译[{i+1}] {snippet}")
            if len(missing) > 10:
                print(f"      ... 共 {len(missing)} 句未译")

    print("-" * 60)
    overall_pct = 100.0 * total_done / total_lines if total_lines else 0
    print(f"合计: 总句数 {total_lines}  已译 {total_done}  未译 {total_lines - total_done}  完成率 {overall_pct:.1f}%")
    print(f"剧本: 全部完成 {completed_scripts} 个，未完成 {len(incomplete_scripts)} 个")
    if incomplete_scripts:
        print("未完成剧本: " + ", ".join(s[0] for s in incomplete_scripts))


if __name__ == "__main__":
    main()
