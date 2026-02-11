"""
Pygame项目打包脚本
将bokusen_main.py打包成exe文件
"""
import os
import subprocess
import sys

def build_exe():
    """使用PyInstaller打包项目"""
    print("开始打包项目...")

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

    # PyInstaller命令（使用python -m PyInstaller方式）
    cmd = [
        python_exe,
        "-m",
        "PyInstaller",
        "--name=BOKUSEN",
        "--onefile",  # 打包成单个exe文件
        "--windowed",  # 不显示控制台窗口
        "--clean",  # 清理旧的构建文件
        "--noconfirm",  # 不询问确认
        # 添加数据文件
        "--add-data=msgothic.ttc;.",
        "--add-data=settings.json;.",
        "--add-data=json;json",
        # 添加依赖
        "--hidden-import=pygame",
        "--hidden-import=pygame.mixer",
        "--hidden-import=pydub",
        "bokusen_main.py"
    ]

    print("\n执行打包命令:")
    print(" ".join(cmd))
    print("\n正在打包，请稍候（这可能需要几分钟）...")

    try:
        result = subprocess.run(cmd, check=True, shell=True)
        print("\n✓ 打包成功！")
        print("exe文件位置: dist/BOKUSEN.exe")

        # 提示复制资源文件
        print("\n注意：如果运行exe时找不到资源文件，需要将以下文件/文件夹复制到exe同级目录：")
        print("  - msgothic.ttc")
        print("  - settings.json")
        print("  - json/")
        print("  - resource/")

    except subprocess.CalledProcessError as e:
        print(f"\n✗ 打包失败: {e}")
        print("\n请检查：")
        print("1. 是否安装了所有依赖：pip install -r requirements.txt")
        print("2. 是否安装了PyInstaller：pip install pyinstaller")
        print("3. 是否安装了ffmpeg（pydub需要）")

if __name__ == "__main__":
    build_exe()
