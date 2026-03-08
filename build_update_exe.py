"""
更新程序打包脚本
将 update_exe.py 打包成 update_exe.exe
"""
import os
import subprocess
import sys

def build_update_exe():
    """使用PyInstaller打包更新程序"""
    print("开始打包更新程序...")

    # 获取Python解释器路径
    python_exe = sys.executable
    print(f"使用Python: {python_exe}")

    # 检查是否安装了PyInstaller
    try:
        import PyInstaller
        print(f"PyInstaller版本: {PyInstaller.__version__}")
    except ImportError:
        print("PyInstaller未安装，正在安装...")
        subprocess.run([python_exe, "-m", "pip", "install", "pyinstaller"], check=True)
        print("PyInstaller安装完成")

    # 检查是否安装了requests
    try:
        import requests
        print(f"requests版本: {requests.__version__}")
    except ImportError:
        print("requests未安装，正在安装...")
        subprocess.run([python_exe, "-m", "pip", "install", "requests"], check=True)
        print("requests安装完成")

    # PyInstaller命令
    cmd = [
        python_exe,
        "-m",
        "PyInstaller",
        "--name=BOKUSEN_Update",
        "--onefile",  # 打包成单个exe文件
        "--console",  # 显示控制台窗口
        "--clean",  # 清理旧的构建文件
        "--noconfirm",  # 不询问确认
        "--add-data=update_config.json;.",
        "update_exe.py"
    ]

    print("\n执行打包命令:")
    print(" ".join(cmd))
    print("\n正在打包，请稍候...")

    try:
        result = subprocess.run(cmd, check=True, shell=True)
        print("\n✓ 打包成功！")
        print("exe文件位置: dist/BOKUSEN_Update.exe")

    except subprocess.CalledProcessError as e:
        print(f"\n✗ 打包失败: {e}")
        print("\n请检查：")
        print("1. 是否安装了所有依赖：pip install -r requirements.txt")
        print("2. 是否安装了PyInstaller：pip install pyinstaller")
        print("3. 是否安装了requests：pip install requests")

if __name__ == "__main__":
    build_update_exe()
