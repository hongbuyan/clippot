# main.py
import sys
import json
import base64
import os
from datetime import datetime, timedelta
from PySide6.QtWidgets import (QApplication, QInputDialog, QLineEdit, QMessageBox, 
                               QDialog, QVBoxLayout, QPushButton, QLabel)
from PySide6.QtGui import QIcon, QFont
from PySide6.QtCore import Qt, QTranslator, QLibraryInfo
from src.core.backend import ClipboardBackend
from src.ui.ui import ModernClipboardUI
from src.ui.settings import LanguageManager
from src.ui.welcome_dialog import WelcomeDialog

# --- 加密算法配置 ---
import hashlib
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.fernet import Fernet
import base64

# 内置盐（请务必修改为您自己的随机字符串！）
# 建议使用 64 字节以上的随机字符串
FIXED_SALT = b'YOUR_SECRET_SALT_HERE_PLEASE_REPLACE_WITH_YOUR_OWN_RANDOM_STRING_64BYTES_MINIMUM_RECOMMENDED'

def derive_key(random_part: str) -> str:
    """
    使用内置盐和随机部分派生最终密钥
    攻击者需要同时获取代码和配置文件才能解密
    """
    # 使用 PBKDF2 派生密钥
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=FIXED_SALT,
        iterations=100000,
    )
    # 将随机部分转换为密钥
    derived = kdf.derive(random_part.encode())
    # 转换为 Fernet 可用的 base64 格式
    return base64.urlsafe_b64encode(derived).decode()

def generate_random_part() -> str:
    """生成随机部分（存储在配置文件中）"""
    return Fernet.generate_key().decode()

def generate_auto_key():
    """
    自动生成加密密钥
    使用内置盐 + 随机部分派生，配置文件只存储随机部分
    """
    random_part = generate_random_part()
    return derive_key(random_part), random_part

# 获取应用程序目录（支持打包后路径）
def get_app_dir():
    """获取应用程序目录（支持打包后路径）"""
    if getattr(sys, 'frozen', False):
        # 打包后：exe所在目录
        return os.path.dirname(sys.executable)
    else:
        # 开发环境：项目根目录
        return os.path.dirname(__file__)

CONFIG_FILE = os.path.join(get_app_dir(), "config.json")

# 全局翻译器
qt_translator = None
app_instance = None

def get_config():
    """读取配置文件"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_config(config):
    """保存配置文件"""
    with open(CONFIG_FILE, "w", encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

def update_qt_translator(language):
    """更新Qt标准对话框的翻译器"""
    global qt_translator, app_instance
    if app_instance is None:
        return
    
    # 移除旧的翻译器
    if qt_translator is not None:
        app_instance.removeTranslator(qt_translator)
    
    # 加载新的翻译器
    qt_translator = QTranslator()
    path = QLibraryInfo.path(QLibraryInfo.LibraryLocation.TranslationsPath)
    
    if language == "zh_CN":
        if qt_translator.load("qtbase_zh_CN", path):
            app_instance.installTranslator(qt_translator)
        else:
            print("无法加载中文翻译文件，将使用默认英文界面")

def main():
    global app_instance
    app_instance = QApplication(sys.argv)
    
    # 设置应用图标
    icon_path = os.path.join(os.path.dirname(__file__), 'src', 'ui', 'assets', 'Clippot.ico')
    if os.path.exists(icon_path):
        app_instance.setWindowIcon(QIcon(icon_path))
    
    config = get_config()
    final_key = None
    
    # 1. 初始化语言管理器（需要在欢迎对话框之前）
    language_manager = LanguageManager()
    
    # 根据当前语言设置加载Qt标准对话框的翻译
    translator = QTranslator()
    path = QLibraryInfo.path(QLibraryInfo.LibraryLocation.TranslationsPath)
    if language_manager.current_language == "zh_CN":
        if translator.load("qtbase_zh_CN", path):
            app_instance.installTranslator(translator)
        else:
            print("无法加载中文翻译文件，将使用默认英文界面")
    
    # 2. 检查是否是首次启动
    if "first_run" not in config:
        welcome_dialog = WelcomeDialog(None, language_manager=language_manager)
        if welcome_dialog.exec() == QDialog.Accepted:
            settings = welcome_dialog.get_settings()
            
            # 复制exe到指定位置
            current_exe = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
            user_selected_path = settings['install_path']
            
            # 在用户选择的路径下创建Clippot子文件夹
            target_path = os.path.join(user_selected_path, 'Clippot')
            
            # 只有打包后的exe才复制
            if getattr(sys, 'frozen', False):
                try:
                    import shutil
                    import subprocess
                    
                    # 确保目标目录存在（创建Clippot子文件夹）
                    os.makedirs(target_path, exist_ok=True)
                    
                    # 目标exe路径
                    target_exe = os.path.join(target_path, 'Clippot.exe')
                    
                    # 如果当前exe不在目标位置，则复制
                    if os.path.normpath(current_exe).lower() != os.path.normpath(target_exe).lower():
                        shutil.copy2(current_exe, target_exe)
                        print(f"软件已复制到: {target_exe}")
                        
                        # 在目标位置创建初始配置文件
                        target_config = os.path.join(target_path, 'config.json')
                        initial_config = {
                            "first_run": False,
                            "install_path": target_path,
                            "auto_start": settings.get('auto_start', False)
                        }
                        with open(target_config, 'w', encoding='utf-8') as f:
                            json.dump(initial_config, f, indent=4, ensure_ascii=False)
                        
                        # 创建快捷方式指向新位置
                        if settings['create_shortcut']:
                            create_desktop_shortcut(target_path)
                        
                        # 启动新位置的exe并退出当前实例
                        subprocess.Popen([target_exe])
                        sys.exit()
                except Exception as e:
                    print(f"复制软件失败: {e}")
            
            # 保存当前配置
            config["first_run"] = False
            config["install_path"] = settings['install_path']
            save_config(config)
            
            # 如果需要创建桌面快捷方式
            if settings['create_shortcut']:
                create_desktop_shortcut(settings['install_path'])
        else:
            sys.exit()
    
    # 3. 自动生成或加载加密密钥
    # 新版本：使用内置盐 + 随机部分派生密钥
    if "random_part" in config:
        # 使用随机部分派生密钥
        final_key = derive_key(config["random_part"])
        print("使用派生密钥")
    elif "encryption_key" in config:
        # 向后兼容：旧版本直接存储的密钥
        final_key = config["encryption_key"]
        # 迁移到新方案：生成随机部分并派生新密钥
        random_part = generate_random_part()
        config["random_part"] = random_part
        # 使用新密钥重新加密数据（这里简化处理，直接使用派生密钥）
        final_key = derive_key(random_part)
        # 删除旧的明文密钥
        del config["encryption_key"]
        save_config(config)
        print("已迁移到派生密钥方案")
    else:
        # 首次运行：生成新的随机部分和派生密钥
        final_key, random_part = generate_auto_key()
        config["random_part"] = random_part
        save_config(config)
        print("生成新的派生密钥")
    
    # 4. 启动程序
    if final_key:
        backend = ClipboardBackend(key=final_key.encode())
        clipboard = app_instance.clipboard()
        
        window = ModernClipboardUI(backend, clipboard, language_manager)
        # 不在这里调用 show()，让 startup_animation() 来处理窗口显示
        
        if sys.platform == 'win32':
            window.set_title_bar_white()
        
        sys.exit(app_instance.exec())
    else:
        sys.exit()

def create_desktop_shortcut(install_path):
    """在桌面创建快捷方式"""
    try:
        import win32com.client
        desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
        
        shortcut_path = os.path.join(desktop, 'Clippot.lnk')
        shell = win32com.client.Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(shortcut_path)
        
        if getattr(sys, 'frozen', False):
            # 打包后：直接指向exe
            exe_path = os.path.join(install_path, 'Clippot.exe')
            shortcut.Targetpath = exe_path
            shortcut.WorkingDirectory = install_path
            # exe文件本身包含图标，不需要单独设置
        else:
            # 开发环境：使用Python解释器
            main_script = os.path.join(install_path, 'main.py')
            icon_path = os.path.join(install_path, 'src', 'ui', 'assets', 'Clippot.ico')
            shortcut.Targetpath = sys.executable
            shortcut.Arguments = f'"{main_script}"'
            shortcut.WorkingDirectory = install_path
            if os.path.exists(icon_path):
                shortcut.IconLocation = icon_path
        
        shortcut.save()
    except Exception as e:
        print(f"创建桌面快捷方式失败: {e}")

if __name__ == "__main__":
    main()