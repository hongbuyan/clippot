# settings.py
import sqlite3
import os
import sys
import subprocess
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QPushButton, QGroupBox, QFormLayout,
                             QCheckBox, QSpinBox, QTabWidget, QWidget, QSlider,
                             QColorDialog, QMessageBox, QApplication, QLineEdit,
                             QFrame)
from PySide6.QtCore import Qt, Signal, QTranslator, QLibraryInfo
from PySide6.QtGui import QFont, QColor, QIcon, QPixmap
import qtawesome as qta

def get_config_path():
    """获取配置文件路径（支持打包后路径）"""
    if getattr(sys, 'frozen', False):
        # 打包后：exe所在目录
        app_dir = os.path.dirname(sys.executable)
    else:
        # 开发环境：项目根目录
        app_dir = os.path.join(os.path.dirname(__file__), '..', '..')
    return os.path.join(app_dir, 'config.json')


class LanguageManager:
    """语言管理器，负责处理多语言文本"""
    
    def __init__(self):
        self.current_language = "zh_CN"
        self.translations = {}
        self._load_translations()
        self._load_current_language()
    
    def _get_resource_path(self, relative_path):
        """获取资源文件的绝对路径，支持打包后的路径"""
        try:
            # PyInstaller 打包后的路径
            base_path = sys._MEIPASS
        except Exception:
            # 开发环境路径
            base_path = os.path.abspath(".")
        
        return os.path.join(base_path, relative_path)
    
    def _load_translations(self):
        """从 JSON 文件加载翻译"""
        import json
        
        # 获取 locales 目录路径（支持打包后路径）
        try:
            # PyInstaller 打包后的路径
            base_path = sys._MEIPASS
            locales_dir = os.path.join(base_path, 'src', 'locales')
        except Exception:
            # 开发环境路径
            locales_dir = os.path.join(os.path.dirname(__file__), '..', 'locales')
        
        # 支持的语言列表
        languages = ["zh_CN", "en_US"]
        
        for lang in languages:
            lang_file = os.path.join(locales_dir, f"{lang}.json")
            try:
                with open(lang_file, 'r', encoding='utf-8') as f:
                    self.translations[lang] = json.load(f)
            except FileNotFoundError:
                print(f"警告: 未找到语言文件 {lang_file}")
                self.translations[lang] = {}
            except Exception as e:
                print(f"加载语言文件 {lang_file} 失败: {e}")
                self.translations[lang] = {}
    
    def _load_current_language(self):
        """从配置文件加载当前语言设置"""
        import json
        
        config_path = get_config_path()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            if 'language' in config:
                self.current_language = config['language']
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"加载语言设置失败: {e}")
    
    def get_text(self, key):
        """获取指定键的文本"""
        if self.current_language in self.translations:
            return self.translations[self.current_language].get(key, key)
        return key
    
    def set_language(self, language):
        """设置当前语言"""
        if language in ["zh_CN", "en_US"]:
            self.current_language = language
            
            # 保存到配置文件
            import json
            config_path = get_config_path()
            
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except FileNotFoundError:
                config = {}
            except Exception as e:
                print(f"读取配置文件失败: {e}")
                config = {}
            
            config['language'] = language
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            
            return True
        return False


class ThemeRestartDialog(QDialog):
    """主题切换重启确认对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.qta = qta
        self.setModal(False)
        self.setFixedWidth(315)
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 图标
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignCenter)
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'Clippot.png')
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path).scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_label.setPixmap(pixmap)
        else:
            icon_label.setPixmap(self.qta.icon('fa5s.sync', color='#4A90E2', scale_factor=1.5).pixmap(64, 64))
        layout.addWidget(icon_label)
        
        # 消息文本
        self.message_label = QLabel()
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #333333;
                line-height: 1.5;
            }
        """)
        layout.addWidget(self.message_label)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(100, 32)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f5;
                border: 1px solid #d0d0d0;
                border-radius: 6px;
                color: #333333;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #e8e8e8;
            }
            QPushButton:pressed {
                background-color: #d8d8d8;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        # 确认按钮
        confirm_btn = QPushButton("立即重启")
        confirm_btn.setFixedSize(100, 32)
        confirm_btn.setCursor(Qt.PointingHandCursor)
        confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A90E2;
                border: none;
                border-radius: 6px;
                color: white;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #3A80D2;
            }
            QPushButton:pressed {
                background-color: #2A70C2;
            }
        """)
        confirm_btn.clicked.connect(self.accept)
        button_layout.addWidget(confirm_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # 设置对话框样式
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                border-radius: 12px;
            }
        """)
        
    def set_message(self, message):
        """设置消息文本"""
        self.message_label.setText(message)


class SettingsWindow(QDialog):
    """设置窗口"""
    
    # 定义信号
    language_changed = Signal(str)
    ui_scale_changed = Signal(float)
    trigger_bar_settings_changed = Signal()
    theme_changed = Signal(str)
    opacity_changed = Signal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.language_manager = LanguageManager()
        
        self.setWindowTitle(self.language_manager.get_text("settings_title"))
        self.setModal(False)
        self.resize(280, 480)  # 设置窗口宽度与剪贴板窗口一致
        
        # 导入qtawesome
        self.qta = qta
        
        self.setup_ui()
        self.setup_style()
        
        # 连接语言变更信号
        self.language_changed.connect(self.update_ui_language)
        
        # 添加定时刷新内容状态
        from PySide6.QtCore import QTimer
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_content_status)
        self.refresh_timer.start(2000)  # 每2秒刷新一次
        
    def setup_ui(self):
        """设置UI组件"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 创建标签页控件
        self.tab_widget = QTabWidget()
        
        # 创建各个设置页面
        self.create_display_page()
        self.create_general_page()
        self.create_security_page()
        
        main_layout.addWidget(self.tab_widget)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 应用按钮
        self.apply_btn = QPushButton(self.language_manager.get_text("apply"))
        self.apply_btn.clicked.connect(self.apply_settings)
        button_layout.addWidget(self.apply_btn)
        
        # 确定按钮
        self.ok_btn = QPushButton(self.language_manager.get_text("ok"))
        self.ok_btn.clicked.connect(self.accept_settings)
        button_layout.addWidget(self.ok_btn)
        
        main_layout.addLayout(button_layout)
    
    def create_display_page(self):
        """创建显示设置页面（包含语言设置）"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 语言设置组
        self.language_group = QGroupBox(self.language_manager.get_text("language_settings"))
        language_layout = QFormLayout(self.language_group)
        
        # 语言选择下拉框
        language_combo = QComboBox()
        language_combo.addItem(self.language_manager.get_text("chinese"), "zh_CN")
        language_combo.addItem(self.language_manager.get_text("english"), "en_US")
        
        # 设置当前选择
        current_lang = self.language_manager.current_language
        for i in range(language_combo.count()):
            if language_combo.itemData(i) == current_lang:
                language_combo.setCurrentIndex(i)
                break
        
        self.language_combo = language_combo
        self.language_label = QLabel(self.language_manager.get_text("select_language"))
        language_layout.addRow(self.language_label, language_combo)
        
        layout.addWidget(self.language_group)
        
        # 显示设置组（合并字体大小和UI缩放）
        self.display_group = QGroupBox(self.language_manager.get_text("display_settings"))
        display_layout = QFormLayout(self.display_group)
        
        # 字体大小选择器
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(12)
        self.font_size_spin.setSuffix(" px")
        
        # 从设置中加载当前字体大小
        current_font_size = self.get_setting("font_size", 13)
        self.font_size_spin.setValue(current_font_size)
        
        # 连接字体大小变化信号
        self.font_size_spin.valueChanged.connect(self.update_font_size)
        
        # 创建字体大小标签
        self.font_size_label = QLabel(self.language_manager.get_text("font_size_setting"))
        
        display_layout.addRow(self.font_size_label, self.font_size_spin)
        
        # UI缩放滑块
        self.ui_scale_slider = QSlider(Qt.Horizontal)
        self.ui_scale_slider.setMinimum(50)  # 50%
        self.ui_scale_slider.setMaximum(200)  # 200%
        self.ui_scale_slider.setValue(100)    # 100%
        self.ui_scale_slider.setTickPosition(QSlider.TicksBelow)
        self.ui_scale_slider.setTickInterval(25)  # 每25%一个刻度
        
        # 显示当前缩放值的标签
        self.ui_scale_label = QLabel(self.language_manager.get_text("ui_scale_value").format(value="100"))
        
        # 从设置中加载当前UI缩放
        current_ui_scale = self.get_setting("ui_scale", 1.0)
        slider_value = int(current_ui_scale * 100)
        self.ui_scale_slider.setValue(slider_value)
        self.ui_scale_label.setText(self.language_manager.get_text("ui_scale_value").format(value=slider_value))
        
        # 创建UI缩放标题标签
        self.ui_scale_title_label = QLabel(self.language_manager.get_text("ui_scale"))
        
        # 连接滑块值变化信号
        self.ui_scale_slider.valueChanged.connect(self.update_ui_scale_label)
        
        display_layout.addRow(self.ui_scale_title_label, self.ui_scale_slider)
        display_layout.addRow("", self.ui_scale_label)
        
        # 主题模式选择器
        self.theme_combo = QComboBox()
        self.theme_combo.addItem(self.language_manager.get_text("light_mode"), "light")
        self.theme_combo.addItem(self.language_manager.get_text("dark_mode"), "dark")
        
        # 从设置中加载当前主题模式
        current_theme = self.get_setting("theme_mode", "dark")
        for i in range(self.theme_combo.count()):
            if self.theme_combo.itemData(i) == current_theme:
                self.theme_combo.setCurrentIndex(i)
                break
        
        # 创建主题模式标签
        self.theme_label = QLabel(self.language_manager.get_text("theme_mode"))
        
        # 连接主题变更信号
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)
        
        display_layout.addRow(self.theme_label, self.theme_combo)
        
        # 界面透明度滑块
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setMinimum(20)  # 20%
        self.opacity_slider.setMaximum(99)  # 最大99%，避免白边问题
        self.opacity_slider.setValue(99)    # 默认99%
        self.opacity_slider.setTickPosition(QSlider.TicksBelow)
        self.opacity_slider.setTickInterval(10)  # 每10%一个刻度
        
        # 显示当前透明度值的标签
        self.opacity_label = QLabel(self.language_manager.get_text("opacity_value").format(value="100"))
        
        # 从设置中加载当前透明度
        current_opacity = self.get_setting("window_opacity", 0.99)  # 默认99%，避免白边问题
        opacity_value = int(current_opacity * 100)
        self.opacity_slider.setValue(opacity_value)
        self.opacity_label.setText(self.language_manager.get_text("opacity_value").format(value=opacity_value))
        
        # 创建界面透明度标题标签
        self.opacity_title_label = QLabel(self.language_manager.get_text("window_opacity"))
        
        # 连接滑块值变化信号
        self.opacity_slider.valueChanged.connect(self.update_opacity_label)
        
        display_layout.addRow(self.opacity_title_label, self.opacity_slider)
        display_layout.addRow("", self.opacity_label)
        
        layout.addWidget(self.display_group)
        
        # 触发条设置组
        self.trigger_bar_group = QGroupBox(self.language_manager.get_text("trigger_bar_settings"))
        trigger_bar_layout = QFormLayout(self.trigger_bar_group)
        
        # 小白条宽度设置
        self.trigger_bar_width_spin = QSpinBox()
        self.trigger_bar_width_spin.setRange(1, 20)
        self.trigger_bar_width_spin.setValue(4)
        self.trigger_bar_width_spin.setSuffix(f" {self.language_manager.get_text('trigger_bar_size_unit')}")
        
        # 从设置中加载当前小白条宽度
        current_trigger_bar_width = self.get_setting("trigger_bar_width", 4)
        self.trigger_bar_width_spin.setValue(current_trigger_bar_width)
        
        # 创建小白条宽度标签
        self.trigger_bar_width_label = QLabel(self.language_manager.get_text("trigger_bar_width"))
        
        trigger_bar_layout.addRow(self.trigger_bar_width_label, self.trigger_bar_width_spin)
        
        # 小白条高度设置
        self.trigger_bar_height_spin = QSpinBox()
        self.trigger_bar_height_spin.setRange(20, 200)
        self.trigger_bar_height_spin.setValue(60)
        self.trigger_bar_height_spin.setSuffix(f" {self.language_manager.get_text('trigger_bar_size_unit')}")
        
        # 从设置中加载当前小白条高度
        current_trigger_bar_height = self.get_setting("trigger_bar_height", 60)
        self.trigger_bar_height_spin.setValue(current_trigger_bar_height)
        
        # 创建小白条高度标签
        self.trigger_bar_height_label = QLabel(self.language_manager.get_text("trigger_bar_height"))
        
        trigger_bar_layout.addRow(self.trigger_bar_height_label, self.trigger_bar_height_spin)
        
        # 小白条颜色设置
        color_layout = QHBoxLayout()
        self.trigger_bar_color_label = QLabel(self.language_manager.get_text("trigger_bar_color"))
        self.trigger_bar_color_btn = QPushButton()
        self.trigger_bar_color_btn.setFixedSize(50, 25)
        
        # 从设置中加载当前小白条颜色
        current_trigger_bar_color = self.get_setting("trigger_bar_color", "#ffffffc8")
        self.trigger_bar_color = current_trigger_bar_color
        
        # 将颜色转换为rgba格式以便正确显示
        if len(current_trigger_bar_color) == 9:
            r = int(current_trigger_bar_color[1:3], 16)
            g = int(current_trigger_bar_color[3:5], 16)
            b = int(current_trigger_bar_color[5:7], 16)
            a = int(current_trigger_bar_color[7:9], 16)
            color_str = f"rgba({r}, {g}, {b}, {a/255:.2f})"
        elif len(current_trigger_bar_color) == 7:
            r = int(current_trigger_bar_color[1:3], 16)
            g = int(current_trigger_bar_color[3:5], 16)
            b = int(current_trigger_bar_color[5:7], 16)
            color_str = f"rgba({r}, {g}, {b}, 0.78)"
        else:
            color_str = "rgba(255, 255, 255, 0.78)"
            
        self.trigger_bar_color_btn.setStyleSheet(f"background-color: {color_str}; border: 1px solid #ccc;")
        
        # 连接颜色选择对话框
        self.trigger_bar_color_btn.clicked.connect(self.select_trigger_bar_color)
        
        color_layout.addWidget(self.trigger_bar_color_label)
        color_layout.addWidget(self.trigger_bar_color_btn)
        
        # 添加小白条隐藏选项
        self.trigger_bar_visible_check = QCheckBox(self.language_manager.get_text("trigger_bar_visible"))
        current_trigger_bar_visible = self.get_setting("trigger_bar_visible", 1)
        self.trigger_bar_visible_check.setChecked(current_trigger_bar_visible == 1)
        
        color_layout.addWidget(self.trigger_bar_visible_check)
        color_layout.addStretch()
        
        trigger_bar_layout.addRow("", color_layout)
        
        layout.addWidget(self.trigger_bar_group)
        layout.addStretch()
        
        self.tab_widget.addTab(page, self.language_manager.get_text("nav_display"))
    
    def create_general_page(self):
        """创建通用设置页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 系统设置组
        self.system_group = QGroupBox(self.language_manager.get_text("system_settings"))
        system_layout = QVBoxLayout(self.system_group)
        
        # 开机自启动选项
        auto_start_widget = QWidget()
        auto_start_layout = QVBoxLayout(auto_start_widget)
        auto_start_layout.setContentsMargins(0, 0, 0, 0)
        
        self.auto_start_check = QCheckBox(self.language_manager.get_text("auto_start"))
        
        # 检查当前是否已设置开机自启动（优先从配置文件读取）
        import json
        config_file = get_config_path()
        current_auto_start = False
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    current_auto_start = config.get("auto_start", False)
            except:
                pass
        
        # 如果配置文件中没有，则从注册表读取
        if not current_auto_start:
            current_auto_start = self.check_auto_start()
        
        self.auto_start_check.setChecked(current_auto_start)
        
        # 连接开机自启动变更信号
        self.auto_start_check.stateChanged.connect(self.on_auto_start_changed)
        
        # 创建描述标签
        self.auto_start_desc_label = QLabel(self.language_manager.get_text("auto_start_desc"))
        self.auto_start_desc_label.setStyleSheet("color: #666; font-size: 11px;")
        self.auto_start_desc_label.setWordWrap(True)
        
        auto_start_layout.addWidget(self.auto_start_check)
        auto_start_layout.addWidget(self.auto_start_desc_label)
        
        system_layout.addWidget(auto_start_widget)
        
        # 添加分隔线
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.HLine)
        separator1.setFrameShadow(QFrame.Sunken)
        separator1.setStyleSheet("background-color: #ddd; max-height: 1px;")
        system_layout.addWidget(separator1)
        
        # 吸附距离设置
        snap_distance_widget = QWidget()
        snap_distance_main_layout = QVBoxLayout(snap_distance_widget)
        snap_distance_main_layout.setContentsMargins(0, 0, 0, 0)
        
        snap_distance_top_layout = QHBoxLayout()
        self.snap_distance_label = QLabel(self.language_manager.get_text("snap_distance"))
        self.snap_distance_label.setMinimumWidth(80)
        
        self.snap_distance_spin = QSpinBox()
        self.snap_distance_spin.setRange(5, 50)
        
        # 从数据库中加载当前吸附距离
        current_snap_distance = self.get_setting("snap_distance", 10)
        self.snap_distance_spin.setValue(current_snap_distance)
        self.snap_distance_spin.setSuffix(f" {self.language_manager.get_text('snap_distance_unit')}")
        
        # 连接吸附距离变更信号
        self.snap_distance_spin.valueChanged.connect(self.on_snap_distance_changed)
        
        snap_distance_top_layout.addWidget(self.snap_distance_label)
        snap_distance_top_layout.addWidget(self.snap_distance_spin)
        snap_distance_top_layout.addStretch()
        
        # 创建吸附距离描述标签
        self.snap_distance_desc_label = QLabel(self.language_manager.get_text("snap_distance_desc"))
        self.snap_distance_desc_label.setStyleSheet("color: #666; font-size: 11px;")
        self.snap_distance_desc_label.setWordWrap(True)
        
        snap_distance_main_layout.addLayout(snap_distance_top_layout)
        snap_distance_main_layout.addWidget(self.snap_distance_desc_label)
        
        system_layout.addWidget(snap_distance_widget)
        
        layout.addWidget(self.system_group)
        
        # 数据管理组
        self.data_group = QGroupBox(self.language_manager.get_text("data_settings"))
        data_layout = QVBoxLayout(self.data_group)
        
        # 获取当前数据库信息
        current_count, current_size_value, current_size_unit = self.get_database_info()
        
        # 创建当前状态信息标签
        self.status_group = QGroupBox(self.language_manager.get_text("current_status"))
        status_layout = QHBoxLayout(self.status_group)
        self.content_count_label = QLabel(self.language_manager.get_text("content_current_count").format(count=current_count))
        self.content_count_label.setStyleSheet("color: #666; font-size: 12px;")
        self.content_size_label = QLabel(self.language_manager.get_text("content_current_size").format(size=current_size_value, unit=current_size_unit))
        self.content_size_label.setStyleSheet("color: #666; font-size: 12px;")
        
        status_layout.addWidget(self.content_count_label)
        status_layout.addStretch()
        status_layout.addWidget(self.content_size_label)
        
        data_layout.addWidget(self.status_group)
        
        # 内容保存设置
        self.content_settings_group = QGroupBox(self.language_manager.get_text("content_settings"))
        content_layout = QFormLayout(self.content_settings_group)
        
        # 保存内容的条数设置
        content_limit_layout = QHBoxLayout()
        self.content_limit_check = QCheckBox(self.language_manager.get_text("content_limit_enabled"))
        self.content_limit_spin = QSpinBox()
        self.content_limit_spin.setRange(1, 999999)
        self.content_limit_spin.setValue(2000)
        self.content_limit_spin.setSuffix(f" {self.language_manager.get_text('content_limit_unit')}")
        
        # 从设置中加载当前内容条数限制
        current_content_limit = self.get_setting("content_limit", 2000)
        self.content_limit_spin.setValue(current_content_limit)
        current_content_limit_enabled = self.get_setting("content_limit_enabled", 1)
        self.content_limit_check.setChecked(current_content_limit_enabled == 1)
        
        content_limit_layout.addWidget(self.content_limit_check)
        content_limit_layout.addWidget(self.content_limit_spin)
        content_limit_layout.addStretch()
        
        content_layout.addRow("", content_limit_layout)
        
        # 保存内容的最大大小设置
        content_size_layout = QHBoxLayout()
        self.content_size_check = QCheckBox(self.language_manager.get_text("content_size_enabled"))
        self.content_size_spin = QSpinBox()
        self.content_size_spin.setRange(1, 1000)
        self.content_size_spin.setValue(5)
        self.content_size_spin.setSuffix(f" {self.language_manager.get_text('content_size_unit')}")
        
        # 从设置中加载当前内容大小限制
        current_content_size = self.get_setting("content_size_limit", 5)
        self.content_size_spin.setValue(current_content_size)
        current_content_size_enabled = self.get_setting("content_size_enabled", 0)
        self.content_size_check.setChecked(current_content_size_enabled == 1)
        
        content_size_layout.addWidget(self.content_size_check)
        content_size_layout.addWidget(self.content_size_spin)
        content_size_layout.addStretch()
        
        content_layout.addRow("", content_size_layout)
        
        data_layout.addWidget(self.content_settings_group)
        
        layout.addWidget(self.data_group)
        layout.addStretch()
        
        self.tab_widget.addTab(page, self.language_manager.get_text("nav_general"))
    
    def get_database_info(self):
        """获取数据库信息（记录数和大小）"""
        try:
            # 获取历史记录数据库文件路径（支持打包后路径）
            if getattr(sys, 'frozen', False):
                data_dir = os.path.join(os.path.dirname(sys.executable), 'data')
            else:
                data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
            
            # 查找所有分卷数据库文件
            import glob
            pattern = os.path.join(data_dir, 'clipboard_history_vol*.db')
            db_files = sorted(glob.glob(pattern))
            
            if not db_files:
                return 0, 0.0, "B"
            
            # 计算所有分卷的总大小
            total_size_bytes = 0
            total_count = 0
            
            for db_file in db_files:
                if os.path.exists(db_file):
                    total_size_bytes += os.path.getsize(db_file)
                    
                    # 连接数据库获取记录数
                    conn = sqlite3.connect(db_file)
                    c = conn.cursor()
                    
                    try:
                        c.execute("SELECT COUNT(*) FROM history")
                        total_count += c.fetchone()[0]
                    except:
                        pass
                    
                    # 也统计notes表
                    try:
                        c.execute("SELECT COUNT(*) FROM notes")
                        total_count += c.fetchone()[0]
                    except:
                        pass
                    
                    conn.close()
            
            # 动态转换大小单位
            if total_size_bytes < 1024:
                db_size_value = total_size_bytes
                db_size_unit = "B"
            elif total_size_bytes < 1024 * 1024:
                db_size_value = round(total_size_bytes / 1024, 2)
                db_size_unit = "KB"
            elif total_size_bytes < 1024 * 1024 * 1024:
                db_size_value = round(total_size_bytes / (1024 * 1024), 2)
                db_size_unit = "MB"
            else:
                db_size_value = round(total_size_bytes / (1024 * 1024 * 1024), 3)
                db_size_unit = "GB"
            
            return total_count, db_size_value, db_size_unit
        except Exception as e:
            print(f"获取数据库信息时出错: {e}")
            return 0, 0.0, "B"
    
    def refresh_content_status(self):
        """刷新内容状态显示"""
        if hasattr(self, 'content_count_label') and hasattr(self, 'content_size_label'):
            current_count, current_size_value, current_size_unit = self.get_database_info()
            self.content_count_label.setText(self.language_manager.get_text("content_current_count").format(count=current_count))
            self.content_size_label.setText(self.language_manager.get_text("content_current_size").format(size=current_size_value, unit=current_size_unit))
    
    def create_security_page(self):
        """创建安全设置页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 安全设置组
        self.security_group = QGroupBox(self.language_manager.get_text("security_settings"))
        security_layout = QVBoxLayout(self.security_group)
        
        # 说明文字
        info_label = QLabel(self.language_manager.get_text("auto_encryption_info"))
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666666; font-size: 12px; padding: 10px;")
        security_layout.addWidget(info_label)
        
        layout.addWidget(self.security_group)
        
        # 删除软件按钮
        self.delete_software_btn = QPushButton(self.language_manager.get_text("delete_software"))
        self.delete_software_btn.setFixedHeight(40)
        self.delete_software_btn.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #C0392B;
            }
            QPushButton:pressed {
                background-color: #96281B;
            }
        """)
        self.delete_software_btn.clicked.connect(self.delete_software)
        layout.addWidget(self.delete_software_btn)
        
        layout.addStretch()
        
        self.tab_widget.addTab(page, self.language_manager.get_text("nav_security"))
    
    def delete_software(self):
        """删除软件及其所有数据"""
        import shutil
        import sys
        
        # 显示警告对话框
        reply = QMessageBox.warning(
            self,
            self.language_manager.get_text("delete_software"),
            self.language_manager.get_text("delete_software_warning"),
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 再次确认
            confirm_reply = QMessageBox.question(
                self,
                self.language_manager.get_text("delete_software"),
                self.language_manager.get_text("delete_software_confirm"),
                QMessageBox.Yes | QMessageBox.No
            )
            
            if confirm_reply == QMessageBox.Yes:
                try:
                    # 获取实际安装目录（exe所在目录）
                    if getattr(sys, 'frozen', False):
                        install_dir = os.path.dirname(sys.executable)
                    else:
                        install_dir = os.path.dirname(os.path.dirname(__file__))
                    
                    # 获取桌面路径
                    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                    shortcut_path = os.path.join(desktop, "Clippot.lnk")
                    
                    # 创建卸载脚本
                    uninstall_script = os.path.join(install_dir, 'uninstall.bat')
                    uninstall_content = f'''@echo off
chcp 65001 >nul
echo 正在卸载 Clippot...
timeout /t 2 /nobreak >nul
taskkill /f /im Clippot.exe >nul 2>&1
del /f /q "{shortcut_path}" >nul 2>&1
rmdir /s /q "{install_dir}"
del "%~f0"
'''
                    with open(uninstall_script, 'w', encoding='utf-8') as f:
                        f.write(uninstall_content)
                    
                    # 关闭设置窗口
                    self.close()
                    
                    # 获取主窗口并关闭
                    if hasattr(self, 'parent') and self.parent():
                        self.parent().close()
                    
                    # 启动卸载脚本并退出
                    subprocess.Popen(['cmd', '/c', uninstall_script], shell=True, creationflags=0x08000000)
                    QApplication.instance().quit()
                    
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        self.language_manager.get_text("error"),
                        f"{self.language_manager.get_text('error')}: {str(e)}"
                    )
    
    def check_auto_start(self):
        """检查是否已设置开机自启动"""
        import winreg
        
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                r"Software\Microsoft\Windows\CurrentVersion\Run", 
                                0, winreg.KEY_READ)
            
            # 获取应用程序名称
            app_name = "Clippot"
            
            # 尝试读取注册表项
            try:
                value, _ = winreg.QueryValueEx(key, app_name)
                winreg.CloseKey(key)
                return True
            except WindowsError:
                winreg.CloseKey(key)
                return False
        except Exception as e:
            print(f"检查开机自启动时出错: {e}")
            return False
    
    def save_auto_start_to_config(self, enabled):
        """保存开机自启动状态到配置文件"""
        import json
        
        config_file = get_config_path()
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                config = {}
            
            config["auto_start"] = enabled
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"保存开机自启动状态到配置文件时出错: {e}")
    
    def on_auto_start_changed(self, state):
        """开机自启动选项变更时更新注册表"""
        import winreg
        import sys
        
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                r"Software\Microsoft\Windows\CurrentVersion\Run", 
                                0, winreg.KEY_SET_VALUE)
            
            # 获取应用程序名称
            app_name = "Clippot"
            
            # 获取当前可执行文件路径
            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
            else:
                exe_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'main.py')
                exe_path = f'"{sys.executable}" "{exe_path}"'
            
            if state == 2:  # 选中状态
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
                print(f"已设置开机自启动: {exe_path}")
                
                # 同时保存到配置文件
                self.save_auto_start_to_config(True)
            else:  # 未选中状态
                try:
                    winreg.DeleteValue(key, app_name)
                    print("已取消开机自启动")
                    
                    # 同时保存到配置文件
                    self.save_auto_start_to_config(False)
                except WindowsError:
                    pass
            
            winreg.CloseKey(key)
        except Exception as e:
            print(f"设置开机自启动时出错: {e}")
            QMessageBox.warning(self, self.language_manager.get_text("error"), 
                              self.language_manager.get_text("auto_start_failed"))
    
    def on_snap_distance_changed(self, value):
        """吸附距离变更时保存设置"""
        self.save_setting("snap_distance", value)
        print(f"吸附距离已更新为: {value}")
    
    def showEvent(self, event):
        """窗口显示时刷新内容状态"""
        super().showEvent(event)
        self.refresh_content_status()
    
    def get_setting(self, key, default=None):
        """从配置文件中获取值"""
        import json
        
        config_path = get_config_path()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            if key in config:
                value = config[key]
                
                # 尝试转换为数字
                if isinstance(value, str):
                    try:
                        if '.' in value:
                            return float(value)
                        else:
                            return int(value)
                    except ValueError:
                        return value
                return value
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"读取配置文件失败: {e}")
        
        return default
    
    def update_ui_scale_label(self, value):
        """更新UI缩放标签显示"""
        self.ui_scale_label.setText(self.language_manager.get_text("ui_scale_value").format(value=value))
    
    def update_opacity_label(self, value):
        """更新透明度标签显示"""
        self.opacity_label.setText(self.language_manager.get_text("opacity_value").format(value=value))
    
    def on_theme_changed(self, index):
        """主题变更处理"""
        theme_mode = self.theme_combo.itemData(index)
        self.save_setting("theme_mode", theme_mode)
        self.theme_changed.emit(theme_mode)
    
    def save_setting(self, key, value):
        """保存设置值到配置文件"""
        import json
        
        config_path = get_config_path()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except FileNotFoundError:
            config = {}
        except Exception as e:
            print(f"读取配置文件失败: {e}")
            config = {}
        
        config[key] = value
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        
    def setup_style(self):
        """设置样式"""
        # 从数据库读取字体大小设置
        font_size = self.get_setting("font_size", 13)
        
        # 设置应用程序默认字体
        app = QApplication.instance()
        if app:
            font = app.font()
            font.setPointSize(font_size)
            app.setFont(font)
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #f8f9fa;
                font-size: {font_size}px;
            }}
            QGroupBox {{
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-size: {font_size}px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
            QPushButton {{
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: {font_size}px;
            }}
            QPushButton:hover {{
                background-color: #45a049;
            }}
            QPushButton:pressed {{
                background-color: #3d8b40;
            }}
            QComboBox {{
                padding: 5px;
                border: 1px solid #cccccc;
                border-radius: 4px;
                background-color: white;
                font-size: {font_size}px;
            }}
            QSpinBox {{
                padding: 5px;
                border: 1px solid #cccccc;
                border-radius: 4px;
                background-color: white;
                font-size: {font_size}px;
            }}
            QCheckBox {{
                font-size: {font_size}px;
            }}
            QLabel {{
                font-size: {font_size}px;
            }}
            QSlider::groove:horizontal {{
                border: 1px solid #cccccc;
                height: 8px;
                background: white;
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: #4CAF50;
                border: 1px solid #4CAF50;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }}
            QTabWidget::pane {{
                border: 1px solid #cccccc;
                border-radius: 4px;
            }}
            QTabBar::tab {{
                background: #e0e0e0;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-size: {font_size}px;
            }}
            QTabBar::tab:selected {{
                background: #f8f9fa;
                border-bottom: 2px solid #4CAF50;
            }}
            QTabBar::tab:hover {{
                background: #d0d0d0;
            }}
        """)
    
    def update_font_size(self, font_size):
        """更新字体大小"""
        # 保存字体大小设置
        self.save_setting("font_size", font_size)
        
        # 设置应用程序默认字体
        app = QApplication.instance()
        if app:
            font = app.font()
            font.setPointSize(font_size)
            app.setFont(font)
        
        # 更新样式表中的字体大小
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #f8f9fa;
                font-size: {font_size}px;
            }}
            QGroupBox {{
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-size: {font_size}px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
            QPushButton {{
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: {font_size}px;
            }}
            QPushButton:hover {{
                background-color: #45a049;
            }}
            QPushButton:pressed {{
                background-color: #3d8b40;
            }}
            QComboBox {{
                padding: 5px;
                border: 1px solid #cccccc;
                border-radius: 4px;
                background-color: white;
                font-size: {font_size}px;
            }}
            QSpinBox {{
                padding: 5px;
                border: 1px solid #cccccc;
                border-radius: 4px;
                background-color: white;
                font-size: {font_size}px;
            }}
            QCheckBox {{
                font-size: {font_size}px;
            }}
            QLabel {{
                font-size: {font_size}px;
            }}
            QSlider::groove:horizontal {{
                border: 1px solid #cccccc;
                height: 8px;
                background: white;
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: #4CAF50;
                border: 1px solid #4CAF50;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }}
            QTabWidget::pane {{
                border: 1px solid #cccccc;
                border-radius: 4px;
            }}
            QTabBar::tab {{
                background: #e0e0e0;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-size: {font_size}px;
            }}
            QTabBar::tab:selected {{
                background: #f8f9fa;
                border-bottom: 2px solid #4CAF50;
            }}
            QTabBar::tab:hover {{
                background: #d0d0d0;
            }}
        """)
    
    def select_trigger_bar_color(self):
        """选择小白条颜色"""
        # 将当前颜色转换为QColor对象
        current_color = self.trigger_bar_color
        
        # 处理透明度
        if len(current_color) == 9:  # #RRGGBBAA格式
            r = int(current_color[1:3], 16)
            g = int(current_color[3:5], 16)
            b = int(current_color[5:7], 16)
            a = int(current_color[7:9], 16)
            color = QColor(r, g, b, a)
        elif len(current_color) == 7:  # #RRGGBB格式
            r = int(current_color[1:3], 16)
            g = int(current_color[3:5], 16)
            b = int(current_color[5:7], 16)
            color = QColor(r, g, b, 200)  # 默认透明度200
        else:
            color = QColor(255, 255, 255, 200)  # 默认白色半透明
        
        # 打开颜色选择对话框，使用QColorDialog.Option.ShowAlphaChannel显示透明度选项
        selected_color = QColorDialog.getColor(color, self, self.language_manager.get_text("trigger_bar_color"), QColorDialog.ShowAlphaChannel)
        
        if selected_color.isValid():
            # 将QColor转换为十六进制字符串
            r = selected_color.red()
            g = selected_color.green()
            b = selected_color.blue()
            a = selected_color.alpha()
            
            # 保存颜色值
            self.trigger_bar_color = f"#{r:02x}{g:02x}{b:02x}{a:02x}"
            
            # 更新按钮背景色，使用rgba格式确保透明度正确显示
            self.trigger_bar_color_btn.setStyleSheet(f"background-color: rgba({r}, {g}, {b}, {a/255:.2f}); border: 1px solid #ccc;")
    
    def apply_settings(self):
        """应用设置"""
        # 获取选择的语言
        selected_language = self.language_combo.currentData()
        
        # 更新语言设置
        if self.language_manager.set_language(selected_language):
            # 发出语言变更信号
            self.language_changed.emit(selected_language)
        
        # 保存字体大小设置
        font_size = self.font_size_spin.value()
        self.save_setting("font_size", font_size)
        
        # 保存UI缩放设置
        ui_scale = self.ui_scale_slider.value() / 100.0  # 将滑块值转换为缩放比例
        self.save_setting("ui_scale", ui_scale)
        
        # 发出UI缩放变更信号
        self.ui_scale_changed.emit(ui_scale)
        
        # 保存透明度设置
        opacity = self.opacity_slider.value() / 100.0  # 将滑块值转换为透明度比例
        self.save_setting("window_opacity", opacity)
        
        # 发出透明度变更信号
        self.opacity_changed.emit(opacity)
        
        # 保存内容保存设置
        content_limit_enabled = 1 if self.content_limit_check.isChecked() else 0
        self.save_setting("content_limit_enabled", content_limit_enabled)
        content_limit = self.content_limit_spin.value()
        self.save_setting("content_limit", content_limit)
        
        content_size_enabled = 1 if self.content_size_check.isChecked() else 0
        self.save_setting("content_size_enabled", content_size_enabled)
        content_size_limit = self.content_size_spin.value()
        self.save_setting("content_size_limit", content_size_limit)
        
        # 保存小白条设置
        trigger_bar_width = self.trigger_bar_width_spin.value()
        self.save_setting("trigger_bar_width", trigger_bar_width)
        
        trigger_bar_height = self.trigger_bar_height_spin.value()
        self.save_setting("trigger_bar_height", trigger_bar_height)
        
        self.save_setting("trigger_bar_color", self.trigger_bar_color)
        
        # 保存小白条可见性设置
        trigger_bar_visible = 1 if self.trigger_bar_visible_check.isChecked() else 0
        self.save_setting("trigger_bar_visible", trigger_bar_visible)
        
        # 发出小白条设置变更信号
        if hasattr(self, 'trigger_bar_settings_changed'):
            self.trigger_bar_settings_changed.emit()
    
    def update_qt_translator(self, language):
        """更新Qt标准对话框的翻译器"""
        try:
            from main import update_qt_translator
            update_qt_translator(language)
        except Exception as e:
            print(f"更新Qt翻译器失败: {e}")
    
    def accept_settings(self):
        """确定并关闭窗口"""
        # 先应用设置
        self.apply_settings()
        # 然后关闭窗口
        self.accept()
    
    def update_ui_language(self, language):
        """更新界面语言"""
        # 更新Qt标准对话框的翻译器
        self.update_qt_translator(language)
        
        # 更新窗口标题
        self.setWindowTitle(self.language_manager.get_text("settings_title"))
        
        # 更新标签页标题
        if hasattr(self, 'tab_widget'):
            self.tab_widget.setTabText(0, self.language_manager.get_text("nav_display"))
            self.tab_widget.setTabText(1, self.language_manager.get_text("nav_general"))
            self.tab_widget.setTabText(2, self.language_manager.get_text("nav_security"))
        
        # 更新语言设置组
        if hasattr(self, 'language_group'):
            self.language_group.setTitle(self.language_manager.get_text("language_settings"))
        
        # 更新语言下拉框选项
        if hasattr(self, 'language_combo'):
            # 保存当前选择
            current_data = self.language_combo.currentData()
            
            # 清空并重新添加选项
            self.language_combo.clear()
            self.language_combo.addItem(self.language_manager.get_text("chinese"), "zh_CN")
            self.language_combo.addItem(self.language_manager.get_text("english"), "en_US")
            
            # 恢复之前的选择
            for i in range(self.language_combo.count()):
                if self.language_combo.itemData(i) == current_data:
                    self.language_combo.setCurrentIndex(i)
                    break
        
        # 更新标签和按钮文本
        if hasattr(self, 'language_label'):
            self.language_label.setText(self.language_manager.get_text("select_language"))
        
        # 更新显示设置组（合并字体大小和UI缩放）
        if hasattr(self, 'display_group'):
            self.display_group.setTitle(self.language_manager.get_text("display_settings"))
        
        # 更新字体大小设置
        if hasattr(self, 'font_size_label'):
            self.font_size_label.setText(self.language_manager.get_text("font_size_setting"))
        
        # 更新UI缩放设置
        if hasattr(self, 'ui_scale_title_label'):
            self.ui_scale_title_label.setText(self.language_manager.get_text("ui_scale"))
        
        # 更新UI缩放值标签
        if hasattr(self, 'ui_scale_label'):
            current_value = self.ui_scale_slider.value()
            self.ui_scale_label.setText(self.language_manager.get_text("ui_scale_value").format(value=current_value))
        
        # 更新主题模式设置
        if hasattr(self, 'theme_label'):
            self.theme_label.setText(self.language_manager.get_text("theme_mode"))
        
        # 更新主题下拉框选项
        if hasattr(self, 'theme_combo'):
            # 临时断开信号连接，防止触发主题变更
            self.theme_combo.currentIndexChanged.disconnect(self.on_theme_changed)
            
            # 保存当前选择
            current_data = self.theme_combo.currentData()
            
            # 清空并重新添加选项
            self.theme_combo.clear()
            self.theme_combo.addItem(self.language_manager.get_text("light_mode"), "light")
            self.theme_combo.addItem(self.language_manager.get_text("dark_mode"), "dark")
            
            # 恢复之前的选择
            for i in range(self.theme_combo.count()):
                if self.theme_combo.itemData(i) == current_data:
                    self.theme_combo.setCurrentIndex(i)
                    break
            
            # 重新连接信号
            self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)
        
        # 更新内容保存设置组
        if hasattr(self, 'content_group'):
            self.content_group.setTitle(self.language_manager.get_text("content_settings"))
        
        if hasattr(self, 'content_settings_group'):
            self.content_settings_group.setTitle(self.language_manager.get_text("content_settings"))
        
        if hasattr(self, 'status_group'):
            self.status_group.setTitle(self.language_manager.get_text("current_status"))
        
        # 更新内容状态标签
        if hasattr(self, 'content_count_label') and hasattr(self, 'content_size_label'):
            self.refresh_content_status()
        
        if hasattr(self, 'content_limit_check'):
            self.content_limit_check.setText(self.language_manager.get_text("content_limit_enabled"))
        
        if hasattr(self, 'content_limit_spin'):
            self.content_limit_spin.setSuffix(f" {self.language_manager.get_text('content_limit_unit')}")
        
        if hasattr(self, 'content_size_check'):
            self.content_size_check.setText(self.language_manager.get_text("content_size_enabled"))
        
        if hasattr(self, 'content_size_spin'):
            self.content_size_spin.setSuffix(f" {self.language_manager.get_text('content_size_unit')}")
        
        if hasattr(self, 'apply_btn'):
            self.apply_btn.setText(self.language_manager.get_text("apply"))
        
        if hasattr(self, 'ok_btn'):
            self.ok_btn.setText(self.language_manager.get_text("ok"))
        
        # 更新小白条设置组
        if hasattr(self, 'trigger_bar_group'):
            self.trigger_bar_group.setTitle(self.language_manager.get_text("trigger_bar_settings"))
        
        if hasattr(self, 'trigger_bar_width_label'):
            self.trigger_bar_width_label.setText(self.language_manager.get_text("trigger_bar_width"))
            self.trigger_bar_width_spin.setSuffix(f" {self.language_manager.get_text('trigger_bar_size_unit')}")
        
        if hasattr(self, 'trigger_bar_height_label'):
            self.trigger_bar_height_label.setText(self.language_manager.get_text("trigger_bar_height"))
            self.trigger_bar_height_spin.setSuffix(f" {self.language_manager.get_text('trigger_bar_size_unit')}")
        
        if hasattr(self, 'trigger_bar_color_label'):
            self.trigger_bar_color_label.setText(self.language_manager.get_text("trigger_bar_color"))
            
        # 更新小白条可见性复选框文本
        if hasattr(self, 'trigger_bar_visible_check'):
            self.trigger_bar_visible_check.setText(self.language_manager.get_text("trigger_bar_visible"))
        
        # 更新安全设置组
        if hasattr(self, 'security_group'):
            self.security_group.setTitle(self.language_manager.get_text("security_settings"))
        
        # 更新通用设置组
        if hasattr(self, 'general_group'):
            self.general_group.setTitle(self.language_manager.get_text("general_settings"))
        
        # 更新系统设置组
        if hasattr(self, 'system_group'):
            self.system_group.setTitle(self.language_manager.get_text("system_settings"))
        
        # 更新数据管理组
        if hasattr(self, 'data_group'):
            self.data_group.setTitle(self.language_manager.get_text("data_settings"))
        
        if hasattr(self, 'auto_start_check'):
            self.auto_start_check.setText(self.language_manager.get_text("auto_start"))
        
        if hasattr(self, 'auto_start_desc_label'):
            self.auto_start_desc_label.setText(self.language_manager.get_text("auto_start_desc"))
        
        # 更新吸附距离设置
        if hasattr(self, 'snap_distance_label'):
            self.snap_distance_label.setText(self.language_manager.get_text("snap_distance"))
        
        if hasattr(self, 'snap_distance_spin'):
            self.snap_distance_spin.setSuffix(f" {self.language_manager.get_text('snap_distance_unit')}")
        
        if hasattr(self, 'snap_distance_desc_label'):
            self.snap_distance_desc_label.setText(self.language_manager.get_text("snap_distance_desc"))
        
        # 更新删除软件按钮
        if hasattr(self, 'delete_software_btn'):
            self.delete_software_btn.setText(self.language_manager.get_text("delete_software"))