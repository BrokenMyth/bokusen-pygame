"""
BOKUSEN 自动更新程序
功能：检查并下载最新的 BOKUSEN.exe
"""
import os
import sys
import json
import requests
import hashlib
import time
from pathlib import Path
from urllib.parse import urlparse

def load_config():
    """加载配置文件"""
    config_file = "update_config.json"

    # 默认配置
    default_config = {
        "update_url": "https://github.com/BrokenMyth/bokusen-pygame/releases",
        "github_api": "https://api.github.com/repos/BrokenMyth/bokusen-pygame/releases/latest",
        "target_file": "BOKUSEN.exe",
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

def main():
    print("=" * 50)
    print("BOKUSEN_Update 自动更新程序")
    print("=" * 50)

    # 加载配置
    config = load_config()
    if not config:
        input("\n按任意键退出...")
        return

    target_file = config.get('target_file', 'BOKUSEN.exe')

    # 检查当前目录下是否有目标文件
    if not os.path.exists(target_file):
        print(f"\n警告：当前目录下找不到 {target_file}")
        response = input("是否继续下载最新版本？(y/n): ").strip().lower()
        if response != 'y':
            print("取消更新")
            return
    else:
        print(f"\n当前版本文件: {target_file}")
        print(f"文件大小: {get_file_size(target_file) / (1024*1024):.2f} MB")

    # 获取最新发布信息
    print("\n正在检查最新版本...")
    release_info = get_latest_release_info(config)
    if not release_info:
        print("无法获取最新版本信息")
        input("\n按任意键退出...")
        return

    print(f"最新版本: {release_info.get('tag_name', 'unknown')}")
    print(f"发布日期: {release_info.get('published_at', 'unknown')}")

    # 查找下载链接
    download_url, remote_size = find_download_asset(release_info, target_file)
    if not download_url:
        print(f"\n未找到 {target_file} 的下载链接")
        print("可用文件:")
        if 'assets' in release_info:
            for asset in release_info['assets']:
                print(f"  - {asset.get('name', 'unknown')}")
        input("\n按任意键退出...")
        return

    print(f"远程文件大小: {remote_size / (1024*1024):.2f} MB")

    # 比较本地和远程文件大小
    local_size = get_file_size(target_file)
    if local_size > 0 and local_size == remote_size:
        print("\n当前版本已经是最新（文件大小相同）")
        input("\n按任意键退出...")
        return

    if local_size > 0:
        print(f"\n发现新版本！")
        print(f"本地大小: {local_size / (1024*1024):.2f} MB")
        print(f"远程大小: {remote_size / (1024*1024):.2f} MB")
    else:
        print(f"\n准备下载最新版本...")

    # 询问是否更新
    response = input("\n是否下载并更新？(y/n): ").strip().lower()
    if response != 'y':
        print("取消更新")
        return

    # 下载文件
    print(f"\n开始下载...")
    print(f"下载地址: {download_url}")
    print(f"保存位置: {os.path.abspath(target_file)}")
    print()

    success = download_file(download_url, target_file, show_progress)
    print()  # 换行

    if success:
        print("\n✓ 下载完成！")
        new_size = get_file_size(target_file)
        print(f"文件大小: {new_size / (1024*1024):.2f} MB")
        print(f"保存位置: {os.path.abspath(target_file)}")
        print("\n更新完成！可以运行新版本了。")
    else:
        print("\n✗ 下载失败，请检查网络连接后重试")

    input("\n按任意键退出...")

if __name__ == "__main__":
    main()
