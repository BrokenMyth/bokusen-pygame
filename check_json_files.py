"""
检查 JSON 文件是否为空或格式错误
"""
import os
import json

json_dir = "./json"

print("=" * 60)
print("检查 JSON 文件")
print("=" * 60)

if not os.path.exists(json_dir):
    print(f"错误：找不到目录 {json_dir}")
else:
    files = [f for f in os.listdir(json_dir) if f.endswith('.json')]
    print(f"\n找到 {len(files)} 个 JSON 文件\n")

    empty_files = []
    invalid_files = []
    valid_files = []

    for filename in sorted(files):
        filepath = os.path.join(json_dir, filename)
        file_size = os.path.getsize(filepath)

        print(f"文件: {filename} ({file_size} bytes)")

        if file_size == 0:
            print(f"  ⚠️ 文件为空！")
            empty_files.append(filename)
        else:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:
                        print(f"  ⚠️ 文件内容为空白！")
                        empty_files.append(filename)
                    else:
                        json.loads(content)
                        print(f"  ✓ 格式正确")
                        valid_files.append(filename)
            except json.JSONDecodeError as e:
                print(f"  ✗ JSON 格式错误: {e}")
                invalid_files.append(filename)
            except Exception as e:
                print(f"  ✗ 读取错误: {e}")
                invalid_files.append(filename)

    print("\n" + "=" * 60)
    print("统计结果:")
    print("=" * 60)
    print(f"✓ 有效文件: {len(valid_files)}")
    print(f"✗ 空白文件: {len(empty_files)}")
    print(f"✗ 格式错误文件: {len(invalid_files)}")

    if empty_files:
        print("\n空白文件列表:")
        for f in empty_files:
            print(f"  - {f}")

    if invalid_files:
        print("\n格式错误文件列表:")
        for f in invalid_files:
            print(f"  - {f}")

    # 提示用户如何处理空文件
    if empty_files:
        print("\n" + "=" * 60)
        print("建议:")
        print("=" * 60)
        print("对于空文件，请在游戏中：")
        print("1. 先点击选中该文件")
        print("2. 再点击 'load' 按钮下载资源")
        print("3. 下载完成后才能播放")

print("\n按任意键退出...")
input()
