"""
BOKUSEN 自动更新程序
功能：检查并下载最新的 BOKUSEN.exe；同时可更新自身 BOKUSEN_Update.exe（同一次发布内），有更新则下载后提示重启，重启后即为新版本。
"""
import os
import sys
import json
import requests
import hashlib
import time
import subprocess
from pathlib import Path
from urllib.parse import urlparse

def get_work_dir():
    """当前程序所在目录（打包后为 exe 所在目录）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))

def load_config():
    """加载配置文件"""
    config_file = "update_config.json"
    #  #  #  #
    # 默认配置
    default_config = {
        "update_url": "https://github.com/BrokenMyth/bokusen-pygame/releases",
        "github_api": "https://api.github.com/repos/BrokenMyth/bokusen-pygame/releases/latest",
        "target_file": "BOKUSEN.exe",
        "updater_file": "BOKUSEN_Update.exe",
        "check_interval": 3600
    }

    # 如果配置文件不存在，创建默认配置
    if not os.path.exists(config_file):
        print(f"配置文件 {config_file} 不存在，正在创建默认配置...")
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            print(f"✓ 已创建默认配置文件: {config_file}")
        except Exception as e:
            print(f"✗ 创建配置文件失败: {e}")
            return default_config

    # 加载配置文件
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"警告：加载配置文件失败，使用默认配置 - {e}")
        return default_config

def get_file_size(filepath):
    """获取文件大小"""
    if not os.path.exists(filepath):
        return 0
    return os.path.getsize(filepath)

def get_file_md5(filepath):
    """获取文件的MD5哈希值"""
    if not os.path.exists(filepath):
        return None

    try:
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        print(f"计算MD5失败: {e}")
        return None

def get_latest_release_info(config):
    """从GitHub API获取最新发布信息"""
    try:
        headers = {
            'User-Agent': 'BOKUSEN-Updater'
        }
        response = requests.get(config['github_api'], headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"获取发布信息失败: {e}")
        return None

def find_download_asset(release_info, target_filename):
    """在发布信息中查找目标文件的下载链接"""
    if not release_info or 'assets' not in release_info:
        return None, None

    for asset in release_info['assets']:
        asset_name = asset.get('name', '')
        if asset_name == target_filename:
            download_url = asset.get('browser_download_url')
            size = asset.get('size', 0)
            return download_url, size

    # 如果没有找到完全匹配的，尝试模糊匹配
    for asset in release_info['assets']:
        asset_name = asset.get('name', '')
        if target_filename.lower() in asset_name.lower() and asset_name.endswith('.exe'):
            download_url = asset.get('browser_download_url')
            size = asset.get('size', 0)
            return download_url, size

    return None, None

def find_asset_by_name(release_info, target_filename):
    """在发布信息中按文件名查找任意资产，返回 (download_url, size)。"""
    if not release_info or 'assets' not in release_info:
        return None, None
    for asset in release_info['assets']:
        asset_name = asset.get('name', '')
        if asset_name == target_filename:
            return asset.get('browser_download_url'), asset.get('size', 0)
    for asset in release_info['assets']:
        asset_name = asset.get('name', '')
        if target_filename.lower() in asset_name.lower():
            return asset.get('browser_download_url'), asset.get('size', 0)
    return None, None

def download_file(url, filepath, progress_callback=None):
    """下载文件"""
    try:
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        # 下载到临时文件
        temp_filepath = filepath + ".tmp"
        with open(temp_filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    if progress_callback and total_size > 0:
                        progress = (downloaded / total_size) * 100
                        progress_callback(progress, downloaded, total_size)

        # 下载完成，重命名为正式文件名
        if os.path.exists(filepath):
            # 先删除旧文件
            try:
                os.remove(filepath)
            except:
                pass

        os.rename(temp_filepath, filepath)
        return True

    except Exception as e:
        print(f"下载失败: {e}")
        # 清理临时文件
        temp_filepath = filepath + ".tmp"
        if os.path.exists(temp_filepath):
            try:
                os.remove(temp_filepath)
            except:
                pass
        return False

def show_progress(progress, downloaded, total):
    """显示下载进度"""
    bar_length = 40
    filled = int(bar_length * progress / 100)
    bar = '█' * filled + '░' * (bar_length - filled)
    downloaded_mb = downloaded / (1024 * 1024)
    total_mb = total / (1024 * 1024)
    print(f"\r进度: [{bar}] {progress:.1f}% ({downloaded_mb:.1f} MB / {total_mb:.1f} MB)", end='', flush=True)

def _find_7z_or_unrar():
    """返回可用于解压 RAR 的可执行路径：优先 7-Zip，其次 UnRAR。"""
    work_dir = get_work_dir()
    candidates = [
        os.path.join(work_dir, "7z.exe"),
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
        os.path.join(work_dir, "UnRAR.exe"),
    ]
    for exe in candidates:
        if os.path.isfile(exe):
            return exe
    try:
        subprocess.run(["unrar"], capture_output=True, timeout=2, shell=True)
        return "unrar"
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return None

def extract_rar(archive_path, dest_dir):
    """解压 RAR 到指定目录。优先使用 7z，其次 unrar。返回 True 表示成功。"""
    archive_path = os.path.abspath(archive_path)
    dest_dir = os.path.abspath(dest_dir)
    exe = _find_7z_or_unrar()
    if not exe:
        print("未找到 7-Zip (7z.exe) 或 UnRAR，无法解压 RAR。请将 7z.exe 放到程序同目录或安装 7-Zip。")
        return False
    try:
        if "7z" in exe.lower() or exe.endswith("7z.exe"):
            cmd = [exe, "x", archive_path, f"-o{dest_dir}", "-y"]
        else:
            cmd = [exe, "x", archive_path, dest_dir + os.sep, "-y"]
        r = subprocess.run(cmd, capture_output=True, timeout=300, text=True, encoding='utf-8', errors='replace')
        if r.returncode != 0:
            print(f"解压失败: {r.stderr or r.stdout}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print("解压超时")
        return False
    except Exception as e:
        print(f"解压出错: {e}")
        return False

def check_self_update(config, release_info):
    """检查更新程序自身是否有新版本。返回 (有更新, download_url, remote_size)。"""
    updater_name = config.get('updater_file', 'BOKUSEN_Update.exe')
    work_dir = get_work_dir()
    self_path = os.path.join(work_dir, updater_name)
    download_url, remote_size = find_download_asset(release_info, updater_name)
    if not download_url:
        return False, None, 0
    local_size = get_file_size(self_path)
    has_update = local_size != remote_size
    return has_update, download_url, remote_size

def check_main_update(config, release_info):
    """检查主程序 BOKUSEN.exe 是否有新版本。返回 (有更新, download_url, remote_size)。"""
    target_file = config.get('target_file', 'BOKUSEN.exe')
    work_dir = get_work_dir()
    local_path = os.path.join(work_dir, target_file)
    download_url, remote_size = find_download_asset(release_info, target_file)
    if not download_url:
        return False, None, 0
    local_size = get_file_size(local_path)
    has_update = local_size != remote_size
    return has_update, download_url, remote_size

def check_extra_update(release_info, work_dir):
    """检查附加资源 extra.rar 是否需要下载（不存在或大小不同）。返回 (需要, download_url, remote_size)。"""
    extra_name = "extra.rar"
    download_url, remote_size = find_asset_by_name(release_info, extra_name)
    if not download_url:
        return False, None, 0
    local_rar = os.path.join(work_dir, extra_name)
    local_size = get_file_size(local_rar)
    need = local_size != remote_size
    return need, download_url, remote_size

def execute_self_update(config, release_info):
    """执行更新程序自更新：下载并重启，成功后本进程退出。"""
    updater_name = config.get('updater_file', 'BOKUSEN_Update.exe')
    work_dir = get_work_dir()
    self_path = os.path.join(work_dir, updater_name)
    new_path = os.path.join(work_dir, updater_name.replace('.exe', '_new.exe'))
    download_url, remote_size = find_download_asset(release_info, updater_name)
    if not download_url:
        print("未找到更新程序下载链接。")
        return
    print(f"\n正在下载 {updater_name} ...")
    success = download_file(download_url, new_path, show_progress)
    print()
    if not success:
        print("下载失败。")
        return
    bat_name = "restart_updater.bat"
    bat_path = os.path.join(work_dir, bat_name)
    bat_content = '''@echo off
chcp 65001 >nul
echo 更新程序即将重启...
timeout /t 2 /nobreak >nul
del "{}"
ren "{}" "{}"
start "" "{}"
del "%~f0"
'''.format(
        os.path.basename(self_path),
        os.path.basename(new_path),
        os.path.basename(self_path),
        os.path.basename(self_path)
    )
    try:
        with open(bat_path, 'w', encoding='utf-8') as f:
            f.write(bat_content)
        subprocess.Popen(
            [bat_path],
            cwd=work_dir,
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0,
            shell=True
        )
    except Exception as e:
        print(f"启动重启脚本失败: {e}")
        return
    print("更新程序已更新，正在重启...")
    sys.exit(0)

def execute_main_update(config, release_info):
    """执行主程序 BOKUSEN.exe 更新。"""
    target_file = config.get('target_file', 'BOKUSEN.exe')
    work_dir = get_work_dir()
    local_path = os.path.join(work_dir, target_file)
    download_url, remote_size = find_download_asset(release_info, target_file)
    if not download_url:
        print("未找到主程序下载链接。")
        return
    print(f"\n正在下载 {target_file} ...")
    success = download_file(download_url, local_path, show_progress)
    print()
    if success:
        print("✓ 主程序更新完成。")
    else:
        print("✗ 下载失败，请检查网络。")

def execute_extra_update(release_info, work_dir):
    """执行附加资源 extra.rar 的下载并解压（先下载到根目录，再尝试解压；无环境则提示手动解压）。"""
    try_download_and_extract_extra(release_info, work_dir, ask_before_download=False)

def try_download_and_extract_extra(release_info, work_dir, ask_before_download=True):
    """若本次发布中有 extra.rar，先下载到游戏根目录（便于下次跳过下载），再尝试解压；无解压环境则提示用户手动解压到根目录。ask_before_download=False 时不询问直接下载。"""
    extra_name = "extra.rar"
    download_url, remote_size = find_asset_by_name(release_info, extra_name)
    if not download_url:
        return
    local_rar = os.path.join(work_dir, extra_name)
    local_size = get_file_size(local_rar)
    need_download = local_size != remote_size
    if need_download:
        if ask_before_download:
            print(f"\n发现附加资源: {extra_name} ({remote_size / (1024*1024):.2f} MB)")
            response = input("是否下载到游戏目录？(y/n): ").strip().lower()
            if response != 'y':
                return
        print(f"\n正在下载 {extra_name} 到游戏根目录...")
        success = download_file(download_url, local_rar, show_progress)
        print()
        if not success:
            print("下载失败。")
            return
        print("✓ 已保存到游戏根目录，下次可跳过下载。")
    else:
        print(f"\n游戏根目录已有 {extra_name}，跳过下载。")

    exe_tool = _find_7z_or_unrar()
    if not exe_tool:
        print("未检测到解压环境（需要 7-Zip 或 UnRAR）。请手动将游戏根目录下的 extra.rar 解压到根目录。")
        print(f"  路径: {os.path.abspath(local_rar)}")
        return
    print("正在解压到游戏目录...")
    if extract_rar(local_rar, work_dir):
        print("✓ extra.rar 已解压到游戏根目录。")
    else:
        print("解压失败。请手动将游戏根目录下的 extra.rar 解压到根目录。")
        print(f"  路径: {os.path.abspath(local_rar)}")

def main():
    print("=" * 50)
    print("BOKUSEN_Update 自动更新程序")
    print("=" * 50)

    config = load_config()
    if not config:
        input("\n按任意键退出...")
        return

    work_dir = get_work_dir()
    print("\n正在检查最新版本（更新程序 / 主程序 / 附加资源）...")
    release_info = get_latest_release_info(config)
    if not release_info:
        print("无法获取最新版本信息")
        input("\n按任意键退出...")
        return

    print(f"最新发布: {release_info.get('tag_name', 'unknown')}")
    print(f"发布日期: {release_info.get('published_at', 'unknown')}")

    self_ok, _, _ = check_self_update(config, release_info)
    main_ok, _, _ = check_main_update(config, release_info)
    extra_ok, _, _ = check_extra_update(release_info, work_dir)

    if not self_ok and not main_ok and not extra_ok:
        print("\n当前均为最新，无需更新。")
        input("\n按任意键退出...")
        return

    opts = []
    if self_ok:
        opts.append(("更新程序 (BOKUSEN_Update.exe)", "self"))
    if main_ok:
        opts.append(("主程序 (BOKUSEN.exe)", "main"))
    if extra_ok:
        opts.append(("附加资源 (extra.rar)", "extra"))

    print("\n可更新项：")
    for i, (label, _) in enumerate(opts, 1):
        print(f"  {i}. {label}")
    print("  4. 全部更新")
    print("  0. 退出")
    choice = input("请选择 (0-4): ").strip()

    if choice == "0":
        input("\n按任意键退出...")
        return

    if choice == "4":
        if main_ok:
            execute_main_update(config, release_info)
        if extra_ok:
            execute_extra_update(release_info, work_dir)
        if self_ok:
            execute_self_update(config, release_info)
        input("\n按任意键退出...")
        return

    try:
        idx = int(choice)
        if 1 <= idx <= len(opts):
            _, kind = opts[idx - 1]
            if kind == "self":
                execute_self_update(config, release_info)
            elif kind == "main":
                execute_main_update(config, release_info)
            elif kind == "extra":
                execute_extra_update(release_info, work_dir)
            input("\n按任意键退出...")
            return
    except ValueError:
        pass

    print("无效选择。")
    input("\n按任意键退出...")

if __name__ == "__main__":
    main()
