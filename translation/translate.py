# -*- coding: utf-8 -*-
"""
剧本翻译脚本：从 json 场景中提取对话，调用本地 Sakura 大模型翻译，
译文统一写入本项目的 out 目录，格式为 out/{剧本id}.json -> {"原文": "译文"}，
已有条目下次跳过。游戏从 out 目录读取实现实时替换。
支持：仅翻译喜好角色（config/favorites.json）、翻译全部角色。
"""
import os
import sys
import re
import json
import argparse
import time

try:
    import requests
except ImportError:
    print("请先安装 requests: pip install requests")
    sys.exit(1)

# 本地 Sakura 服务
SAKURA_HOST = "127.0.0.1"
SAKURA_PORT = 8080
SAKURA_BASE_URL = f"http://{SAKURA_HOST}:{SAKURA_PORT}"
SAKURA_MODEL = "sakura"
REQUEST_TIMEOUT = 120
REQUEST_DELAY = 0.5


def _script_dir():
    return os.path.dirname(os.path.abspath(__file__))


def _project_root():
    """游戏项目根目录（bokusen-pygame），translation 在其下"""
    return os.path.dirname(_script_dir())


def _out_dir():
    """译文输出目录：项目内 translation/out"""
    return os.path.join(_script_dir(), "out")


def _json_dir():
    """剧本 json：仅上一级到 py 脚本根目录，取该目录下的 json"""
    return os.path.join(_project_root(), "json")


def _favorites_path():
    """喜好列表：项目内 config/favorites.json"""
    return os.path.join(_project_root(), "config", "favorites.json")


def _trim_key(s):
    """原文做 trim 后作为译文 key，避免首尾空白/零宽字符等导致查不到。"""
    if not isinstance(s, str):
        return s
    s = s.strip()
    # 去除首尾零宽字符、BOM、不间断空格等
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


def call_sakura(text):
    url = f"{SAKURA_BASE_URL}/v1/chat/completions"
    prompt = f"将以下日文翻译成简体中文，只输出译文，不要任何解释或换行外的内容：\n\n{text}"
    payload = {
        "model": SAKURA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 2048,
    }
    try:
        r = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        choices = data.get("choices")
        if not choices:
            return None
        content = choices[0].get("message", {}).get("content", "")
        return (content or "").strip()
    except requests.exceptions.ConnectionError:
        print(f"无法连接 Sakura 服务 {SAKURA_BASE_URL}，请确认已启动且端口为 {SAKURA_PORT}")
        return None
    except Exception as e:
        print(f"调用 Sakura 失败: {e}")
        return None


def translate_json_file(story_id, dry_run=False):
    """从剧本 json 提取 articles，翻译写入 translation/out/{story_id}.json，不修改原剧本。"""
    jd = _json_dir()
    od = _out_dir()
    script_path = os.path.join(jd, f"{story_id}.json")
    out_path = os.path.join(od, f"{story_id}.json")

    if not os.path.isfile(script_path):
        return 0, 0
    try:
        with open(script_path, "r", encoding="utf-8") as f:
            obj = json.load(f)
    except Exception as e:
        print(f"读取失败 {story_id}.json: {e}")
        return 0, 0
    code = obj.get("data", {}).get("code")
    if not code:
        return 0, 0
    articles = code.get("articles", [])
    if not articles:
        return 0, 0

    # 已有译文从 out 目录读入
    cache = {}
    if os.path.isfile(out_path):
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                cache = json.load(f)
            if not isinstance(cache, dict):
                cache = {}
        except Exception:
            cache = {}

    SAVE_EVERY = 10  # 每翻译满 10 条就写入一次
    added = 0
    skipped = 0
    for raw in articles:
        if not isinstance(raw, str):
            continue
        text = raw.strip()
        if not text:
            continue
        key = _trim_key(text)
        if not key:
            continue
        if key in cache:
            skipped += 1
            continue
        if dry_run:
            added += 1
            continue
        translated = call_sakura(text)
        if translated is not None:
            cache[key] = translated
            added += 1
            # 每翻译满 10 条就写入一次，避免中断丢失进度
            if added % SAVE_EVERY == 0:
                try:
                    os.makedirs(od, exist_ok=True)
                    with open(out_path, "w", encoding="utf-8") as f:
                        json.dump(cache, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    print(f"写入失败 out/{story_id}.json: {e}")
        time.sleep(REQUEST_DELAY)

    # 最后再写一次，保证未满 10 条的尾巴也落盘
    if added or (dry_run and added) or cache:
        if not dry_run:
            try:
                os.makedirs(od, exist_ok=True)
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(cache, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"写入失败 out/{story_id}.json: {e}")
                return added, skipped
    return added, skipped


def main():
    parser = argparse.ArgumentParser(description="剧本翻译：译文写入 translation/out/*.json，游戏从 out 目录读取")
    parser.add_argument("--favorites", action="store_true", help="仅翻译 config/favorites.json 中的喜好角色")
    parser.add_argument("--all", action="store_true", help="翻译全部角色（所有 json）")
    parser.add_argument("--dry-run", action="store_true", help="只统计待翻译条数，不请求 API、不写文件")
    args = parser.parse_args()
    if not args.favorites and not args.all:
        print("请指定 --favorites 或 --all")
        parser.print_help()
        sys.exit(1)
    target_ids = get_target_story_ids(args.favorites)
    if not target_ids:
        print("没有找到待处理剧本（--favorites 时请确认 config/favorites.json 存在且有数字 id）")
        sys.exit(0)
    print(f"译文输出目录: {_out_dir()}")
    print(f"待处理剧本数: {len(target_ids)}")
    total_added = 0
    total_skipped = 0
    for story_id in target_ids:
        a, s = translate_json_file(story_id, dry_run=args.dry_run)
        total_added += a
        total_skipped += s
        if a or s:
            print(f"  {story_id}: 新增 {a}, 跳过(已有缓存) {s}")
    print(f"合计: 新增 {total_added}, 跳过 {total_skipped}")


if __name__ == "__main__":
    main()
