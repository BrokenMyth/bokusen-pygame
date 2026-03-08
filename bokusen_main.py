import sys,pygame
import os
import re
import json
from urllib.request import urlretrieve
from urllib.parse import quote
from pygame.locals import*
from sys import exit
import time
import threading
from pydub import AudioSegment
import math
import concurrent.futures

# 配置 ffmpeg 路径
def configure_ffmpeg():
    """自动检测并配置 ffmpeg 路径"""
    # 检查常见位置
    ffmpeg_paths = [
        'ffmpeg.exe',  # 当前目录
        './ffmpeg.exe',  # 当前目录
        os.path.join(os.path.dirname(__file__), 'ffmpeg.exe'),  # 脚本所在目录
        'C:/ffmpeg/bin/ffmpeg.exe',  # 常见安装路径
        os.path.join(os.path.dirname(sys.executable), 'ffmpeg.exe'),  # Python 目录
    ]

    for path in ffmpeg_paths:
        if os.path.exists(path):
            AudioSegment.converter = path
            print(f'找到 ffmpeg: {path}')
            return True

    # 检查系统 PATH
    try:
        import shutil
        if shutil.which('ffmpeg'):
            print('使用系统 ffmpeg')
            return True
    except:
        pass

    print('未找到 ffmpeg，m4a 音频将无法转换')
    return False

# 初始化时配置 ffmpeg
ffmpeg_available = configure_ffmpeg()

#用户设置
user_setting_file =  open("settings.json",'r',encoding='utf8') 
user_setting = json.load(user_setting_file)
user_name = user_setting['user']['name']
下载线程数 = user_setting['下载线程数']
print('----用户设置，请到setting.json中修改------')
print(user_setting)
print('----------------------------------------')
#常量
display_width = user_setting['窗口宽度']
display_height = user_setting['窗口高度']
bgm音量 = int(user_setting['bgm音量'].replace("%",''))*0.01
WHITE = (255, 255, 255)
RED = (255, 0, 0)    
GAME_SIZE = (display_width,display_height)
CG_SIZE = (960,540)



#初始化
pygame.init()
pygame.mixer.init()
pygame.display.set_caption("BOKUSEN")


screen = pygame.display.set_mode(GAME_SIZE, 0, 32)
game_font = pygame.font.Font('msgothic.ttc',50)
text_font = pygame.font.Font('msgothic.ttc',30)
small_text_font = pygame.font.Font('msgothic.ttc',15)
button_font = pygame.font.Font('msgothic.ttc',15)
all_text_rect = pygame.Rect(30, 550, 930, 200)



#指令相关方法
def get_json(json_file_name):
    """加载 JSON 文件"""
    global error_message

    json_path = "./json/"+json_file_name+".json"

    # 检查文件是否存在
    if not os.path.exists(json_path):
        print(f"错误：文件不存在 {json_path}")
        print(f"提示：请先点击 'load' 按钮下载资源")
        with error_message['lock']:
            error_message['active'] = True
            error_message['message'] = f"File not found: {json_file_name}.json"
        return None

    # 检查文件是否为空
    if os.path.getsize(json_path) == 0:
        print(f"错误：文件为空 {json_path}")
        print(f"提示：请先点击 'load' 按钮下载资源")
        with error_message['lock']:
            error_message['active'] = True
            error_message['message'] = f"File is empty: {json_file_name}.json"
        return None

    try:
        with open(json_path, 'r', encoding='utf-8') as load_f:
            content = load_f.read().strip()
            if not content:
                print(f"错误：文件内容为空白 {json_path}")
                print(f"提示：请先点击 'load' 按钮下载资源")
                with error_message['lock']:
                    error_message['active'] = True
                    error_message['message'] = f"File content is empty: {json_file_name}.json"
                return None
            bokujson = json.loads(content)
            return bokujson
    except json.JSONDecodeError as e:
        print(f"错误：JSON 格式错误 {json_path}")
        print(f"详细信息：{e}")
        print(f"提示：请重新下载该资源")
        with error_message['lock']:
            error_message['active'] = True
            error_message['message'] = f"JSON format error: {json_file_name}.json. Please click 'load' to download resources."
        return None
    except Exception as e:
        print(f"错误：加载 JSON 文件失败 {json_path}")
        print(f"详细信息：{e}")
        with error_message['lock']:
            error_message['active'] = True
            error_message['message'] = f"Failed to load: {json_file_name}.json. Error: {str(e)}"
        return None


def get_commands(jsonfile):        
    bokujson = jsonfile
    commands = bokujson['data']['code']['commands']
    return commands


def read_commands(jsonfile,num):
        bokujson = jsonfile
        commands= get_commands(jsonfile)

        global commands_count, fast_forward_mode, cg_control, txt_control, anime_control, sound_control, is_play, is_main, json_list_page, json_selected

        while(num<len(commands)):

            tags = bokujson['data']['code']['tags']
            tag = tags[int(commands[num][0])]

            parameters = bokujson['data']['code']['parameters']
            param = parameters[int(commands[num][1])]

            result = execut_commands(tag,param)

            num = num +1

            if result == "stop":
                commands_count = num
                break

            # 快进模式下：每帧只执行一个命令就返回
            if fast_forward_mode:
                commands_count = num
                return

        if num == len(commands):
            anime_control.set_loop(False)
            if anime_control.is_started:
                anime_control.join()
            se_channel.stop()  # 停止音效
            bgm_channel.stop()  # 停止 BGM
            cg_control = Cg_Controller()
            txt_control = Text_Controller()
            anime_control = Anime_Controller()
            commands_count = 0
            is_play = False
            is_main = True
            json_list_page = 0
            json_selected = False
            screen.fill((0,0,0))


            
def execut_commands(tag,param):
    global error_message, is_play, is_main, is_fast_forward, fast_forward_mode

    if tag=="bgmopt":
        pass
    
    if tag=="image":

        if param[16]!="1":
            image_num = int(param[-3])
            image_type = jsonfile['data']['code']['images'][image_num].replace("https://resource-asw.bokusen.net/resource/img/script/","").split("/")[0]
            image_order = param[-8]
            print("cg"+param[-3])

            cg = get_images(image_num)

            if not cg:
                print(f'image error: 图片文件不存在')
                # 显示错误提示
                with error_message['lock']:
                    error_message['active'] = True
                    error_message['message'] = f"Resources not found. Please click 'load' to download resources."
                # 停止播放并返回主菜单
                is_play = False
                is_main = True
                is_fast_forward = False
                fast_forward_mode = False
                return "stop"

            if image_order == "fore":
                cg_control.set_fore_img(cg)
            if image_order == "back":
                cg_control.set_back_img(cg)
            if image_type == "ev":
                cg_control.set_fore_img(cg)
                cg_control.set_back_img(cg)

            cg_control.show_cg()
        
    if tag=="trans":
        pass
    if tag=="wt":
        # 快进模式下跳过等待
        pass
    if tag=="move":
        pass
    if tag=="wm":
        pass
    if tag=="playse":

        sound_file = None
        try:
            sound_file = get_sounds(param[-1])

            if not sound_file:
                print('playse error: 音频文件不存在')
                return "end"

            # 检查文件格式，如果是 m4a 说明转换失败，跳过播放
            if sound_file.endswith('.m4a'):
                print(f'playse warning: 音频文件未转换 ({sound_file})，跳过播放')
                return "end"

            try:
                # 使用专用音效通道，播放前停止之前的音效
                global se_channel
                se_channel.stop()  # 停止之前的音效
                Sound = pygame.mixer.Sound(sound_file)
                se_channel.play(Sound)
            except Exception as e:
                print(f'playse play error: {e}')
                if sound_file:
                    print(f'音频文件: {sound_file}')
                    print(f'文件存在: {os.path.exists(sound_file)}')
        except Exception as e:
            print(f'playse error: {e}')
            # 如果是目录不存在的错误，提示用户下载资源
            if "No such file or directory" in str(e) or "系统找不到指定的路径" in str(e):
                print(f'提示: 请点击load按钮下载资源')
                # 显示错误提示
                with error_message['lock']:
                    error_message['active'] = True
                    error_message['message'] = f"Resources not found. Please click 'load' to download resources."
                # 停止播放并返回主菜单
                is_play = False
                is_main = True
                is_fast_forward = False
                fast_forward_mode = False
                return "stop"

    if tag=="articles":
        txt = get_articles(param[0])
        txt_control.set_text(txt)
        txt_control.show_text()
        
    if tag=="r":
        pass
    if tag=="p":
        pass

    if tag=="cm":
        txt_control.clear_text()
        return "stop"
    
    if tag=="stopse":
        pass

    if tag=="animstart":
        if len(param[-3])>10:
            anime_control.set_loop(True)
            anime_control.set_anime_list(param[-3])
            anime_control.start()

    if tag=="animstop":
        anime_control.set_loop(False)

    if tag=="wait":
        pass
    if tag=="wb":
        pass

    if tag=="playbgm":
        print('playbgm'+param[-1])

        sound_file = None
        try:
            sound_file = get_sounds(param[-1])

            if not sound_file:
                print('playbgm error: 音频文件不存在')
                return "end"

            # 检查文件格式
            if sound_file.endswith('.m4a'):
                print(f'playbgm warning: 音频文件未转换 ({sound_file})，跳过播放')
                return "end"

            Sound = pygame.mixer.Sound(sound_file)

            try:
                if bgm_channel.get_busy():
                    print('正在播放')
                    bgm_channel.stop()
                    bgm_channel.play(Sound, loops=-1)
                else:
                    print('没有播放')
                    bgm_channel.play(Sound, loops=-1)
            except:
                print('playbgm play error')
        except Exception as e:
            print(f'playbgm error: {e}')
            if sound_file:
                print(f'音频文件: {sound_file}')
                print(f'文件存在: {os.path.exists(sound_file)}')
            # 如果是目录不存在的错误，提示用户下载资源
            if "No such file or directory" in str(e) or "系统找不到指定的路径" in str(e):
                print(f'提示: 请点击load按钮下载资源')
                # 显示错误提示
                with error_message['lock']:
                    error_message['active'] = True
                    error_message['message'] = f"Resources not found. Please click 'load' to download resources."
                # 停止播放并返回主菜单
                is_play = False
                is_main = True
                is_fast_forward = False
                fast_forward_mode = False
                return "stop"

        

    if tag=="fadeinbgm":
        print('fadeinbgm'+param[1])

        sound_file = None
        try:
            sound_file = get_sounds(param[1])

            if not sound_file:
                print('fadeinbgm error: 音频文件不存在')
                return "end"

            # 检查文件格式
            if sound_file.endswith('.m4a'):
                print(f'fadeinbgm warning: 音频文件未转换 ({sound_file})，跳过播放')
                return "end"

            Sound = pygame.mixer.Sound(sound_file)

            try:
                if bgm_channel.get_busy():
                    bgm_channel.stop()
                    bgm_channel.play(Sound, loops=-1)
                else:
                    bgm_channel.play(Sound, loops=-1)
            except:
                print('fadeinbgm play error')
        except Exception as e:
            print(f'fadeinbgm error: {e}')
            if sound_file:
                print(f'音频文件: {sound_file}')
                print(f'文件存在: {os.path.exists(sound_file)}')
            # 如果是目录不存在的错误，提示用户下载资源
            if "No such file or directory" in str(e) or "系统找不到指定的路径" in str(e):
                print(f'提示: 请点击load按钮下载资源')
                # 显示错误提示
                with error_message['lock']:
                    error_message['active'] = True
                    error_message['message'] = f"Resources not found. Please click 'load' to download resources."
                # 停止播放并返回主菜单
                is_play = False
                is_main = True
                is_fast_forward = False
                fast_forward_mode = False
                return "stop"

    if tag=="fadeoutbgm":
        pass
        # print("fadeoutbgm")
        # try:
        #     if bgm_channel.get_busy():
        #         print('正在播放')
        #         bgm_channel.stop()
        # except:
        #     print("fadeoutbgm error")
            
    
    
    if tag=="fadebgm":
        pass
        # print("fadebgm")
        # try:
        #     if bgm_channel.get_busy():
        #         print('正在播放')

        #         bgm_channel.stop()
        # except:
        #     print("fadebgm error")

    if tag=="seopt":
        pass
    if tag=="fadese":
        pass
    if tag=="wf":
        pass
    return "end"

#加载资源
def get_images(num):
    global json_file_name
    resouce_path =  "./resource/"+json_file_name+"/images/"

    # 检查目录是否存在
    if not os.path.exists(resouce_path):
        print(f'图片目录不存在: {resouce_path}')
        return None

    file_names = os.listdir(resouce_path)
    pattern = re.compile("^"+str(num)+"\..*")
    matching_file_names = [f for f in file_names if pattern.match(f)]


    return  pygame.image.load(resouce_path+matching_file_names[0]).convert_alpha()   

def get_sounds(num):
    global json_file_name
    resouce_path =  "./resource/"+json_file_name+"/sounds/"

    # 检查目录是否存在
    if not os.path.exists(resouce_path):
        print(f'音频目录不存在: {resouce_path}')
        return None

    file_names = os.listdir(resouce_path)
    pattern = re.compile("^"+str(num)+"\..*")
    matching_file_names = [f for f in file_names if pattern.match(f)]

    # 优先返回 wav 文件（转换成功的情况）
    wav_files = [f for f in matching_file_names if f.endswith('.wav')]
    if wav_files:
        return resouce_path + wav_files[0]

    # 如果有 m4a 文件且 ffmpeg 可用，尝试转换
    m4a_files = [f for f in matching_file_names if f.endswith('.m4a')]
    if m4a_files and ffmpeg_available:
        m4a_file = resouce_path + m4a_files[0]
        wav_file = m4a_file.replace(".m4a", ".wav")

        try:
            print(f'转换音频: {m4a_files[0]} -> wav')
            AudioSegment.from_file(m4a_file).export(wav_file, format="wav")
            print(f'转换成功: {wav_file}')
            return wav_file
        except Exception as e:
            print(f'转换失败: {e}')

    # 如果没有 wav，返回其他格式（可能是转换失败的 m4a）
    if matching_file_names:
        return resouce_path + matching_file_names[0]

    return None

def get_articles(num):    
    global jsonfile
    bokujson = jsonfile
    articles = bokujson['data']['code']['articles']
    return articles[int(num)]


# 全局下载进度变量
download_progress = {
    'total_files': 0,
    'completed_files': 0,
    'current_file': '',
    'is_downloading': False,
    'lock': threading.Lock()
}

# 全局错误消息
error_message = {
    'active': False,
    'message': '',
    'lock': threading.Lock()
}

# 全局网格刷新标志
need_refresh_grid = {
    'refresh': False,
    'lock': threading.Lock()
}

class ErrorMessageBox:
    """错误提示框类"""
    def __init__(self):
        self.active = False
        self.rect = pygame.Rect(200, 300, 880, 150)
        self.button_rect = pygame.Rect(display_width // 2 - 60, 410, 120, 30)

    def show(self, message):
        """显示错误提示"""
        self.active = True
        message = message

        # 绘制背景框
        pygame.draw.rect(screen, (60, 40, 40), self.rect, 0)
        pygame.draw.rect(screen, (150, 50, 50), self.rect, 3)

        # 显示标题
        title_text = game_font.render("Error", True, (255, 100, 100))
        title_rect = title_text.get_rect(center=(display_width // 2, 325))
        screen.blit(title_text, title_rect)

        # 显示错误消息（分两行显示）
        words = message.split()
        line1 = ""
        line2 = ""
        current_line = line1

        for word in words:
            test_line = current_line + " " + word if current_line else word
            test_text = text_font.render(test_line, True, (255, 255, 255))
            if test_text.get_width() < 840:
                current_line = test_line
            else:
                if line1 == "":
                    line1 = current_line
                    current_line = word
                else:
                    line2 = current_line
                    break

        if line2 == "":
            line1 = current_line

        if line1:
            text1 = text_font.render(line1, True, (255, 255, 255))
            text1_rect = text1.get_rect(center=(display_width // 2, 375))
            screen.blit(text1, text1_rect)

        if line2:
            text2 = text_font.render(line2, True, (255, 255, 255))
            text2_rect = text2.get_rect(center=(display_width // 2, 405))
            screen.blit(text2, text2_rect)

        # 绘制OK按钮
        pygame.draw.rect(screen, (80, 80, 80), self.button_rect, 0)
        pygame.draw.rect(screen, (150, 150, 150), self.button_rect, 2)
        button_text = text_font.render("OK", True, (255, 255, 255))
        button_rect = button_text.get_rect(center=self.button_rect.center)
        screen.blit(button_text, button_rect)

        pygame.display.flip()

    def hide(self):
        """隐藏错误提示框"""
        self.active = False

    def is_clicked(self, x, y):
        """检查是否点击了OK按钮"""
        inx = (x > self.button_rect[0]) and (x < (self.button_rect[0] + self.button_rect[2]))
        iny = (y > self.button_rect[1]) and (y < (self.button_rect[1] + self.button_rect[3]))
        return inx and iny

class DownloadProgress:
    """下载进度框类"""
    def __init__(self):
        self.active = False
        self.rect = pygame.Rect(300, 250, 680, 120)
        self.bar_bg_rect = pygame.Rect(330, 310, 620, 30)
        self.bar_rect = pygame.Rect(330, 310, 0, 30)

    def show(self, current_file, progress_percent):
        """显示下载进度"""
        self.active = True

        # 绘制背景框
        pygame.draw.rect(screen, (50, 50, 50), self.rect, 0)
        pygame.draw.rect(screen, (100, 100, 100), self.rect, 2)

        # 绘制进度条背景
        pygame.draw.rect(screen, (30, 30, 30), self.bar_bg_rect, 0)
        pygame.draw.rect(screen, (150, 150, 150), self.bar_bg_rect, 1)

        # 计算进度条宽度
        bar_width = int(620 * progress_percent / 100)
        self.bar_rect.width = bar_width
        pygame.draw.rect(screen, (100, 200, 100), self.bar_rect, 0)

        # 显示标题
        title_text = game_font.render("Downloading...", True, (255, 255, 255))
        title_rect = title_text.get_rect(center=(display_width // 2, 275))
        screen.blit(title_text, title_rect)

        # 显示当前文件
        if len(current_file) > 50:
            display_name = "..." + current_file[-50:]
        else:
            display_name = current_file
        file_text = text_font.render(f"Current: {display_name}", True, (200, 200, 200))
        screen.blit(file_text, (330, 290))

        # 显示进度百分比
        percent_text = text_font.render(f"{progress_percent:.1f}%", True, (255, 255, 255))
        percent_rect = percent_text.get_rect(center=(display_width // 2, 355))
        screen.blit(percent_text, percent_rect)

        pygame.display.flip()

    def hide(self):
        """隐藏进度框"""
        self.active = False
        self.bar_rect.width = 0

def download_file(url, filename):
    global download_progress

    print(f'Downloading {filename}...')

    # 更新当前文件信息
    with download_progress['lock']:
        download_progress['current_file'] = os.path.basename(filename)

    download_times = 5
    success = False
    while download_times > 0:
        try:
            urlretrieve(url, filename)
            success = True
            break
        except:
            print("error downloading : " + filename)
            download_times = download_times - 1
            continue

    if not success:
        print(f'下载失败: {filename}')
        with download_progress['lock']:
            download_progress['completed_files'] += 1
        return

    if 'm4a' in filename:
        wav_file = filename.replace("m4a","wav")

        # 检查 ffmpeg 是否可用
        if not ffmpeg_available:
            print(f'跳过音频转换（ffmpeg 不可用）: {filename}')
            print(f'提示: 下载 ffmpeg.exe 并放到项目目录可启用 m4a 音频')
        else:
            try:
                AudioSegment.from_file(filename).export(wav_file, format="wav")
                os.remove(filename)
                print(f'音频转换成功: {wav_file}')
            except Exception as e:
                print(f'音频转换失败: {e}')
                print(f'保留原文件: {filename}')
                print(f'提示: 请确保 ffmpeg.exe 可用')

    print(f'{filename} downloaded.')

    # 更新完成计数
    with download_progress['lock']:
        download_progress['completed_files'] += 1



#资源下载（在后台线程中运行）
def get_resource(json_file_name):
    global download_progress, error_message

    os.makedirs("./resource/"+json_file_name+"/sounds/", exist_ok=True)
    os.makedirs("./resource/"+json_file_name+"/images/", exist_ok=True)

    print("你先别急")

    # 初始化下载进度
    with download_progress['lock']:
        download_progress['total_files'] = 0
        download_progress['completed_files'] = 0
        download_progress['current_file'] = ''
        download_progress['is_downloading'] = True

    # 检查JSON文件
    json_path = "./json/"+json_file_name+".json"
    json_valid = True

    # 如果JSON文件不存在或为空，尝试从服务器下载
    if not os.path.exists(json_path) or os.path.getsize(json_path) == 0:
        print(f"JSON文件不存在或为空，尝试从服务器下载: {json_path}")
        json_url = f"https://resource-asw.bokusen.net/resource/json/{quote(json_file_name)}.json"

        try:
            print(f"正在下载JSON文件: {json_url}")
            urlretrieve(json_url, json_path)
            print(f"JSON文件下载成功: {json_path}")

            # 检查下载的文件是否为空
            if os.path.getsize(json_path) == 0:
                print(f"错误：下载的JSON文件为空 {json_path}")
                json_valid = False
            else:
                # 验证JSON格式
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        json.load(f)
                    print(f"JSON文件格式验证通过")
                except json.JSONDecodeError as e:
                    print(f"错误：下载的JSON文件格式无效 {json_path}")
                    print(f"详细信息：{e}")
                    # 删除损坏的文件
                    os.remove(json_path)
                    json_valid = False
        except Exception as e:
            print(f"下载JSON文件失败: {e}")
            if not os.path.exists(json_path):
                json_valid = False

    if not json_valid:
        print(f"错误：JSON文件无效或无法下载 {json_path}")
        with download_progress['lock']:
            download_progress['is_downloading'] = False
        json_valid = False

    start_time = time.time()
    try:
        if json_valid:
            with open(json_path, 'r', encoding='utf-8') as load_f:
                content = load_f.read().strip()
                if not content:
                    print(f"错误：JSON文件内容为空白 {json_path}")
                    # 尝试重新下载JSON文件
                    json_valid = False
                    raise ValueError("JSON file is empty")
                else:
                    bokujson = json.loads(content)
                    images = bokujson['data']['code']['images']
                    sounds = bokujson['data']['code']['sounds']
                    file_dict = {}

                    count = 0
                    while(count<len(sounds)):
                        endname = '.'+sounds[count].split('.')[-1]
                        file_name = "./resource/"+json_file_name+"/sounds/"+str(count)+endname
                        url = sounds[count]
                        file_dict[url] = file_name
                        count=count+1

                    count = 0
                    while(count<len(images)):
                        endname = '.'+images[count].split('.')[-1]
                        file_name = "./resource/"+json_file_name+"/images/"+str(count)+endname
                        url = images[count]
                        file_dict[url] = file_name
                        count=count+1

                    total_files = len(file_dict)
                    with download_progress['lock']:
                        download_progress['total_files'] = total_files

                    # 使用包装器函数来更新进度（只更新数据，不调用pygame）
                    def download_with_progress(url, filename):
                        download_file(url, filename)

                    # 在单独线程中下载，同时主线程更新UI
                    with concurrent.futures.ThreadPoolExecutor(max_workers=下载线程数) as executor:
                        futures = [executor.submit(download_with_progress, url, filename) for url, filename in file_dict.items()]
                        concurrent.futures.wait(futures)

                    end_time = time.time()
                    run_time = end_time - start_time
                    print(f"耗时：{run_time}秒")
                    print("下好了，开冲！")

    except (json.JSONDecodeError, ValueError) as e:
        print(f"错误：JSON 文件无效 {json_path}")
        print(f"详细信息：{e}")
        print(f"提示：尝试从服务器重新下载JSON文件")

        # 尝试从服务器重新下载JSON文件
        json_url = f"https://resource-asw.bokusen.net/resource/json/{quote(json_file_name)}.json"
        try:
            print(f"正在重新下载JSON文件: {json_url}")
            # 备份旧文件
            backup_path = json_path + ".backup"
            if os.path.exists(json_path):
                os.rename(json_path, backup_path)

            # 下载新文件
            urlretrieve(json_url, json_path)

            # 验证新文件
            if os.path.getsize(json_path) == 0:
                print(f"错误：下载的JSON文件为空")
                json_valid = False
                # 恢复备份
                if os.path.exists(backup_path):
                    os.rename(backup_path, json_path)
            else:
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        json.load(f)
                    print(f"JSON文件重新下载成功")

                    # 删除备份
                    if os.path.exists(backup_path):
                        os.remove(backup_path)

                    # 重新加载并下载资源
                    json_valid = True
                    with open(json_path, 'r', encoding='utf-8') as load_f:
                        content = load_f.read().strip()
                        bokujson = json.loads(content)
                        images = bokujson['data']['code']['images']
                        sounds = bokujson['data']['code']['sounds']
                        file_dict = {}

                        count = 0
                        while(count<len(sounds)):
                            endname = '.'+sounds[count].split('.')[-1]
                            file_name = "./resource/"+json_file_name+"/sounds/"+str(count)+endname
                            url = sounds[count]
                            file_dict[url] = file_name
                            count=count+1

                        count = 0
                        while(count<len(images)):
                            endname = '.'+images[count].split('.')[-1]
                            file_name = "./resource/"+json_file_name+"/images/"+str(count)+endname
                            url = images[count]
                            file_dict[url] = file_name
                            count=count+1

                        total_files = len(file_dict)
                        with download_progress['lock']:
                            download_progress['total_files'] = total_files

                        def download_with_progress(url, filename):
                            download_file(url, filename)

                        with concurrent.futures.ThreadPoolExecutor(max_workers=下载线程数) as executor:
                            futures = [executor.submit(download_with_progress, url, filename) for url, filename in file_dict.items()]
                            concurrent.futures.wait(futures)

                        end_time = time.time()
                        run_time = end_time - start_time
                        print(f"耗时：{run_time}秒")
                        print("下好了，开冲！")

                except json.JSONDecodeError:
                    print(f"错误：重新下载的JSON文件仍然无效")
                    json_valid = False
                    # 恢复备份
                    if os.path.exists(backup_path):
                        os.rename(backup_path, json_path)
        except Exception as e2:
            print(f"重新下载JSON文件失败: {e2}")
            json_valid = False
            # 恢复备份
            if os.path.exists(backup_path):
                os.rename(backup_path, json_path)

    except Exception as e:
        print(f"错误：加载资源失败 {json_path}")
        print(f"详细信息：{e}")
        json_valid = False
    finally:
        # 标记下载完成
        with download_progress['lock']:
            download_progress['is_downloading'] = False

        # 只有在JSON有效的情况下才尝试重新加载
        if json_valid:
            global jsonfile, commands, json_selected, need_refresh_grid
            jsonfile = get_json(json_file_name)
            if jsonfile is not None:
                commands = get_commands(jsonfile)
                print(f"重新加载成功: {json_file_name}")
                # 标记需要刷新网格列表
                with need_refresh_grid['lock']:
                    need_refresh_grid['refresh'] = True
            else:
                print(f"重新加载失败: {json_file_name}")
        else:
            # JSON文件损坏，显示错误提示
            with error_message['lock']:
                error_message['active'] = True
                error_message['message'] = f"JSON file corrupted: {json_file_name}.json. Please redownload from server."

def get_cover_image(json_name):
    try:
        resource_path = "./resource/"+json_name+"/images/"
        if not os.path.exists(resource_path):
            return None

        file_names = os.listdir(resource_path)
        pattern = re.compile(r"^(\d+)\..*")
        matching_files = [f for f in file_names if pattern.match(f)]

        if not matching_files:
            return None

        max_num = -1
        cover_file = None
        for f in matching_files:
            num = int(pattern.match(f).group(1))
            if num > max_num:
                max_num = num
                cover_file = f

        if cover_file:
            return pygame.image.load(resource_path + cover_file).convert_alpha()
        return None
    except:
        return None

class Button:
    is_button_on_screen = False
    rect=(0,0,0,0)
    text=0
    text_color = (255, 0, 0)
    button_color = (255, 255, 255)

    def __init__(self, rect, text):
        self.rect = rect
        self.text = text

    def set_rect(self,r):
        self.rect = r

    def set_text(self,t):
        self.text = t

    def set_rect_x(self,x):
        new_rect = (x,self.rect[1],self.rect[2],self.rect[3])
        self.rect  = new_rect

    def set_rect_y(self,y):
        new_rect = (self.rect[0],y,self.rect[2],self.rect[3])
        self.rect  = new_rect

    def set_rect_w(self,w):
        new_rect = (self.rect[0],self.rect[1],w,self.rect[3])
        self.rect  = new_rect

    def set_rect_h(self,h):
        new_rect = (self.rect[0],self.rect[1],self.rect[2],h)
        self.rect  = new_rect

    def show_button(self):
        self.is_button_on_screen= True
        # 使用更小的字体（15px，缩小一半）
        button_text = button_font.render(self.text, True, self.text_color, self.button_color)
        li_rect = (self.rect[0]-1,self.rect[1]-1,self.rect[2]+2,self.rect[3]+2)
        pygame.draw.rect(screen, self.button_color, li_rect, 0)

        # 计算文本居中位置
        text_rect = button_text.get_rect(center=(self.rect[0] + self.rect[2]//2,
                                                self.rect[1] + self.rect[3]//2))
        screen.blit(button_text, text_rect)

    def in_rect(self, x, y):
        inx = (x>self.rect[0]) and (x<(self.rect[0]+self.rect[2]))
        iny = (y>self.rect[1]) and (y<(self.rect[1]+self.rect[3]))
        return inx and iny

class GridItem:
    is_item_on_screen = False
    rect=(0,0,0,0)
    text=0
    text_color = (255, 255, 255)
    cover_img=None
    bg_color=(50, 50, 50)
    border_color=(100, 100, 100)
    is_selected=False

    def __init__(self, rect, text, cover_img=None):
        self.rect = rect
        self.text = text
        self.cover_img = cover_img
        self.is_selected = False

    def set_rect(self,r):
        self.rect = r

    def set_text(self,t):
        self.text = t

    def set_cover_img(self,img):
        self.cover_img = img

    def set_selected(self, selected):
        self.is_selected = selected

    def show_item(self):
        self.is_item_on_screen= True

        bg_rect = (self.rect[0]-2, self.rect[1]-2, self.rect[2]+4, self.rect[3]+4)

        # 根据选中状态改变颜色
        if self.is_selected:
            pygame.draw.rect(screen, (80, 80, 120), bg_rect, 0)
            pygame.draw.rect(screen, (100, 150, 255), bg_rect, 3)
        else:
            pygame.draw.rect(screen, self.bg_color, bg_rect, 0)
            pygame.draw.rect(screen, self.border_color, bg_rect, 2)

        text_area_height = 25
        img_area_height = self.rect[3] - text_area_height

        if self.cover_img:
            aspect_ratio = 960 / 540
            img_width = int(img_area_height * aspect_ratio)

            if img_width > self.rect[2]:
                img_width = self.rect[2]
                img_height = int(img_width / aspect_ratio)
            else:
                img_height = img_area_height

            scaled_img = pygame.transform.scale(self.cover_img, (img_width, img_height))
            img_x = self.rect[0] + (self.rect[2] - img_width) // 2
            img_y = self.rect[1]
            screen.blit(scaled_img, (img_x, img_y))
        else:
            img_width = int(img_area_height * (960 / 540))
            if img_width > self.rect[2]:
                img_width = self.rect[2]
                img_height = int(img_width / (960 / 540))
            else:
                img_height = img_area_height

            img_x = self.rect[0] + (self.rect[2] - img_width) // 2
            img_rect = pygame.Rect(img_x, self.rect[1], img_width, img_height)
            pygame.draw.rect(screen, (30, 30, 30), img_rect, 0)

        text_surface = small_text_font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(centerx=self.rect[0] + self.rect[2] // 2,
                                        centery=self.rect[1] + self.rect[3] - text_area_height // 2)
        screen.blit(text_surface, text_rect)

    def in_rect(self, x, y):
        inx = (x>self.rect[0]) and (x<(self.rect[0]+self.rect[2]))
        iny = (y>self.rect[1]) and (y<(self.rect[1]+self.rect[3]))
        return inx and iny

class Cg_Controller():
    fore_img = pygame.image.load("base_back.png").convert_alpha()
    back_img = pygame.image.load("base_back.png").convert_alpha()

    def set_fore_img(self,img):
        self.fore_img = img

    def set_back_img(self,img):
        self.back_img = img

    def show_cg(self):
        # 缩放图片到 CG_SIZE
        self.fore_img = pygame.transform.scale(self.fore_img, CG_SIZE)
        self.back_img = pygame.transform.scale(self.back_img, CG_SIZE)

        # 计算水平居中位置，垂直方向置顶
        cg_x = (display_width - CG_SIZE[0]) // 2
        cg_y = 0

        # 在水平居中、垂直置顶位置绘制图片
        screen.blit(self.back_img, (cg_x, cg_y))
        screen.blit(self.fore_img, (cg_x, cg_y))
        pygame.display.flip() 

class Text_Controller():

    textRect =[(30,550,930,50),(30,600,930,50),(30,650,930,50),(30,700,930,50)] 
    text = ["","","",""]
    controller_stack=0

    def set_text(self,txt):
        
        self.text[self.controller_stack] = txt
        self.controller_stack = self.controller_stack+1

    def show_text(self):
        i = 0
        while(i<len(self.text)):
            message = text_font.render(self.text[i],True,WHITE,(0,0,0))
            screen.blit(message,self.textRect[i])
            i=i+1

    def clear_text(self):
        self.text = ["","","",""]
        self.controller_stack=0
        
class Anime_Controller(threading.Thread):
    anime_list=[]
    fps = 15
    loop = True
    is_started = False
    is_animating = False  # 添加动画播放状态标志

    def __init__(self):
        threading.Thread.__init__(self)
        self.is_started = False
        self.is_animating = False

    def set_anime_list(self,str):
        self.anime_list = str.rstrip().split(" ")

    def set_loop(self,status):
        self.loop = status

    def run(self):
        self.is_started = True
        self.is_animating = True
        while self.loop:
            i = 0
            while i<len(self.anime_list):
                img = get_images(int(self.anime_list[i]))
                if not img:  # 如果图片不存在，跳过
                    i += 1
                    continue

                img = pygame.transform.scale(img, CG_SIZE)

                # 计算水平居中位置，垂直方向置顶
                cg_x = (display_width - CG_SIZE[0]) // 2
                cg_y = 0

                screen.blit(img, (cg_x, cg_y))
                pygame.display.flip()
                time.sleep(1/self.fps)
                i+=1
                if i==len(self.anime_list):
                    i=0
                if not self.loop:
                    break
        self.is_animating = False

#hs列表
#获取列表
def get_list():
    json_list = []
    files= os.listdir('./json/')
    for file in files:
        json_list.append(file.replace('.json',''))
    return json_list

#列表分页 - 改为每页12个项目（3x4网格）
def page_list(p,page_list):
    new_list=[]
    list_len = len(json_list)
    i=0
    while (i<12) and (p*12+i <list_len):
        new_list.append(page_list[p*12+i])
        i= i+1
    return new_list

#显示网格列表 - 3x4网格布局（适配1280x720）
def load_grid(json_list):
    grid_cols = 3
    grid_rows = 4
    item_width = 350
    item_height = 130
    gap_x = 30
    gap_y = 15

    grid_total_width = grid_cols * item_width + (grid_cols - 1) * gap_x
    start_x = (display_width - grid_total_width) // 2
    start_y = 30

    grid_list = []
    for idx, li in enumerate(json_list):
        row = idx // grid_cols
        col = idx % grid_cols

        x = start_x + col * (item_width + gap_x)
        y = start_y + row * (item_height + gap_y)
        li_rect = (x, y, item_width, item_height)

        cover_img = get_cover_image(li)
        li_text = li
        li_item = GridItem(li_rect, li_text, cover_img)
        li_item.show_item()
        grid_list.append(li_item)

    return grid_list

#显示页码信息
def show_page_info(current_page, total_pages):
    if total_pages <= 1:
        return []

    page_buttons = []
    button_width = 30
    button_height = 25
    button_gap = 5

    max_visible_pages = 12

    pages_to_show = []
    if total_pages <= max_visible_pages:
        pages_to_show = list(range(total_pages))
    else:
        if current_page < max_visible_pages // 2:
            pages_to_show = list(range(max_visible_pages - 1)) + [total_pages - 1]
        elif current_page >= total_pages - max_visible_pages // 2:
            pages_to_show = [0] + list(range(total_pages - max_visible_pages + 1, total_pages))
        else:
            half = max_visible_pages // 2
            pages_to_show = [0] + list(range(current_page - half + 1, current_page + half)) + [total_pages - 1]

    total_width = len(pages_to_show) * (button_width + button_gap)
    start_x = (display_width - total_width) // 2
    page_y = 600

    idx = 0
    for i in pages_to_show:
        is_ellipsis = False

        if idx > 0 and pages_to_show[idx - 1] is not None and i - pages_to_show[idx - 1] > 1:
            ellipsis_x = start_x + idx * (button_width + button_gap)
            ellipsis_text = small_text_font.render("...", True, (200, 200, 200))
            ellipsis_rect = ellipsis_text.get_rect(centerx=ellipsis_x + button_width // 2,
                                                  centery=page_y + button_height // 2)
            screen.blit(ellipsis_text, ellipsis_rect)
            idx += 1

        x = start_x + idx * (button_width + button_gap)
        rect = (x, page_y, button_width, button_height)

        if i == current_page:
            btn_color = (100, 100, 255)
        else:
            btn_color = (70, 70, 70)

        page_btn = Button(rect, str(i + 1))
        page_btn.button_color = btn_color
        page_btn.text_color = (255, 255, 255)
        page_btn.page_index = i
        page_btn.show_button()
        page_buttons.append(page_btn)
        idx += 1

    return page_buttons



#数据
json_file_name = ""
jsonfile ={} #get_json(json_file_name)
commands = []#get_commands(jsonfile)
json_list = get_list()
pages_size = math.ceil(len(json_list)/12)



#控制器
cg_control = Cg_Controller()
txt_control = Text_Controller()
anime_control = Anime_Controller()

commands_count = 0
is_play = False
is_main = True
json_list_page = 0
json_selected = False
bgm_channel = pygame.mixer.Channel(1)
bgm_channel.set_volume(bgm音量)
se_channel = pygame.mixer.Channel(2)  # 音效专用通道

# 快进功能
is_fast_forward = False
fast_forward_start_time = 0
fast_forward_commands_per_second = 20  # 每秒播放的命令数
fast_forward_mode = False  # 标记是否处于快进模式
last_command_time = 0  # 上次执行命令的时间

buttons_start_y = 600
button_width = 80
button_height = 25
button_gap = 10

# 左下角按钮
left_x = 50
right_x = display_width - 50 - button_width

pages_down_rect = (left_x, buttons_start_y, button_width, button_height)
pages_up_rect = (right_x, buttons_start_y, button_width, button_height)
load_rect = (left_x, buttons_start_y + button_height + button_gap, button_width, button_height)
play_rect = (right_x, buttons_start_y + button_height + button_gap, button_width, button_height)


pages_up_button = Button(pages_up_rect,"Next")
pages_down_button = Button(pages_down_rect,"Prev")
load_button = Button(load_rect,"load")
play_button = Button(play_rect,"play")

# 跟踪当前选中的GridItem
selected_grid_item = None

# 初始化网格列表（在循环外部）
json_grid_list = []
page_buttons = []




if __name__ == '__main__':
    # 初始化第一页的网格
    new_list = page_list(json_list_page,json_list)
    json_grid_list = load_grid(new_list)

    # 进度框实例
    progress_box = None

    # 错误提示框实例
    error_box = ErrorMessageBox()

    while True:
        current_time = time.time()

        for event in pygame.event.get():
            if is_play:

                if event.type == MOUSEBUTTONDOWN and event.button == 1:
                    pygame.draw.rect(screen, (0, 0, 0), all_text_rect)

                    read_commands(jsonfile,commands_count)

                # 检测 Ctrl 键按下
                if event.type == KEYDOWN:
                    if event.key in [K_LCTRL, K_RCTRL]:
                        is_fast_forward = True
                        fast_forward_start_time = current_time

                # 检测 Ctrl 键释放
                if event.type == KEYUP:
                    if event.key in [K_LCTRL, K_RCTRL]:
                        is_fast_forward = False

            if is_main:
                # 清除整个屏幕,避免内容叠加
                screen.fill((0, 0, 0))

                # 显示网格列表（不再每次循环都重新创建）
                for item in json_grid_list:
                    item.show_item()

                if pages_size > 1:
                    pages_up_button.show_button()
                    pages_down_button.show_button()
                    page_buttons = show_page_info(json_list_page, pages_size)

                # 如果选中了某个项目，显示load和play按钮
                if json_selected:
                    load_button.show_button()
                    play_button.show_button()

                # 如果错误提示框激活，显示错误提示框
                with error_message['lock']:
                    if error_message['active']:
                        error_box.show(error_message['message'])

                if event.type == MOUSEBUTTONDOWN and event.button == 1:
                    x = event.pos[0]
                    y = event.pos[1]
                    print(json_list_page)

                    # 检查是否点击了错误提示框的OK按钮
                    if error_box.active and error_box.is_clicked(x, y):
                        with error_message['lock']:
                            error_message['active'] = False
                            error_message['message'] = ''
                        error_box.hide()
                        continue

                    for item in json_grid_list:
                        if item.in_rect(x,y):
                            # 如果点击的是已经选中的项，直接播放
                            if selected_grid_item == item:
                                json_file_name = item.text
                                jsonfile = get_json(json_file_name)
                                if jsonfile is None:
                                    print(f"无法加载 {json_file_name}，请先点击 'load' 下载资源")
                                    continue
                                commands = get_commands(jsonfile)

                                is_play = True
                                json_selected = False
                                is_main = False
                                selected_grid_item = None
                                screen.fill((0,0,0))
                                print(f"直接播放: {item.text}")
                            else:
                                # 取消之前选中的项
                                if selected_grid_item:
                                    selected_grid_item.set_selected(False)

                                # 选中当前项
                                item.set_selected(True)
                                selected_grid_item = item
                                json_file_name = item.text
                                jsonfile = get_json(json_file_name)
                                if jsonfile is None:
                                    # JSON加载失败，但仍然允许用户点击load按钮重新下载
                                    print(f"无法加载 {json_file_name}，请先点击 'load' 下载资源")
                                    commands = []
                                    json_selected = True
                                else:
                                    commands = get_commands(jsonfile)
                                    json_selected = True
                                print(f"选中: {item.text}")

                    if pages_size > 1:
                        if pages_up_button.in_rect(x,y):
                            json_list_page = json_list_page + 1
                            if json_list_page >= pages_size:
                                json_list_page = 0
                            # 翻页时取消选中
                            if selected_grid_item:
                                selected_grid_item.set_selected(False)
                                selected_grid_item = None
                            new_list = page_list(json_list_page,json_list)
                            json_grid_list = load_grid(new_list)

                        if pages_down_button.in_rect(x,y):
                            json_list_page = json_list_page - 1
                            if json_list_page < 0 :
                                json_list_page = pages_size-1
                            # 翻页时取消选中
                            if selected_grid_item:
                                selected_grid_item.set_selected(False)
                                selected_grid_item = None
                            new_list = page_list(json_list_page,json_list)
                            json_grid_list = load_grid(new_list)

                        if 'page_buttons' in locals():
                            for page_btn in page_buttons:
                                if page_btn.in_rect(x, y):
                                    json_list_page = page_btn.page_index
                                    # 翻页时取消选中
                                    if selected_grid_item:
                                        selected_grid_item.set_selected(False)
                                        selected_grid_item = None
                                    new_list = page_list(json_list_page,json_list)
                                    json_grid_list = load_grid(new_list)

                    # 处理load和play按钮的点击
                    if json_selected:
                        if load_button.in_rect(x, y):
                            # 在后台线程中启动下载，避免阻塞主界面
                            download_thread = threading.Thread(target=get_resource, args=(json_file_name,))
                            download_thread.daemon = True
                            download_thread.start()
                        if play_button.in_rect(x, y):
                            # 检查JSON是否成功加载
                            if jsonfile is None:
                                # 显示错误提示，要求先点击load按钮
                                with error_message['lock']:
                                    error_message['active'] = True
                                    error_message['message'] = f"Cannot play. Please click 'load' to download resources first."
                            else:
                                # 播放时取消选中
                                if selected_grid_item:
                                    selected_grid_item.set_selected(False)
                                    selected_grid_item = None
                                is_play = True
                                json_selected = False
                                is_main = False
                                screen.fill((0, 0, 0))

            if event.type == QUIT:
                anime_control.set_loop(False)
                if anime_control.is_started:
                    anime_control.join()
                se_channel.stop()  # 停止音效
                bgm_channel.stop()  # 停止 BGM
                exit()

        # 快进逻辑
        if is_play:
            # 每帧都重新绘制 CG 和文本，让 Skip 提示被自然覆盖
            # 只有在动画未播放时才绘制CG，避免和动画线程冲突
            if not anime_control.is_animating:
                cg_control.show_cg()
            txt_control.show_text()

            # 检查键盘状态（支持直接检测，不依赖 KEYDOWN/KEYUP）
            keys = pygame.key.get_pressed()
            is_ctrl_pressed = keys[K_LCTRL] or keys[K_RCTRL]

            if is_ctrl_pressed:
                if not is_fast_forward:
                    # Ctrl 刚被按下
                    is_fast_forward = True
                    fast_forward_mode = True
                    fast_forward_start_time = current_time
                    last_command_time = current_time

                # 根据时间间隔执行命令
                time_since_last_command = current_time - last_command_time
                command_interval = 1.0 / fast_forward_commands_per_second  # 每个命令的时间间隔

                if time_since_last_command >= command_interval:
                    # 快进模式下执行一个命令
                    pygame.draw.rect(screen, (0, 0, 0), all_text_rect)
                    read_commands(jsonfile, commands_count)

                    # 更新上次执行命令的时间
                    last_command_time = current_time

                # 如果场景结束或回到主菜单，停止快进
                if not is_play:
                    is_fast_forward = False
                    fast_forward_mode = False
            else:
                # Ctrl 释放，停止快进
                is_fast_forward = False
                fast_forward_mode = False

        # 检查是否正在下载，如果是则显示进度框
        if download_progress['is_downloading']:
            with download_progress['lock']:
                if download_progress['total_files'] > 0:
                    percent = (download_progress['completed_files'] / download_progress['total_files']) * 100
                    if progress_box is None:
                        progress_box = DownloadProgress()
                    progress_box.show(download_progress['current_file'], percent)
        else:
            if progress_box is not None:
                progress_box.hide()
                progress_box = None

            # 检查是否需要刷新网格列表
            with need_refresh_grid['lock']:
                if need_refresh_grid['refresh']:
                    need_refresh_grid['refresh'] = False
                    # 重新加载当前页的网格列表
                    new_list = page_list(json_list_page, json_list)
                    json_grid_list = load_grid(new_list)
                    print("网格列表已刷新")

        pygame.display.flip()         