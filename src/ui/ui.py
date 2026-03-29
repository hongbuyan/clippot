# ui.py
import json
import base64
import sys
import os
import tempfile
import uuid
import sqlite3
from datetime import datetime
from PySide6.QtWidgets import (QMainWindow, QListWidget, QVBoxLayout, 
                               QLabel, QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QFrame, 
                               QWidget, QHBoxLayout, QPushButton, QScrollArea,
                               QSizePolicy, QToolTip, QMenu, QScrollBar, QLineEdit,
                               QDialog, QTextEdit, QToolBar, QComboBox, QColorDialog, QFontComboBox, QSystemTrayIcon, QApplication)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QRect, QEasingCurve, QPoint, QByteArray, QBuffer, QMimeData, QUrl, QSize
from PySide6.QtGui import QColor, QCursor, QGuiApplication, QIcon, QPixmap, QAction
from qtawesome import IconicFont
from src.core.category import CategoryManager

def get_config_path():
    """获取配置文件路径（支持打包后路径）"""
    if getattr(sys, 'frozen', False):
        # 打包后：exe所在目录
        app_dir = os.path.dirname(sys.executable)
    else:
        # 开发环境：项目根目录
        app_dir = os.path.join(os.path.dirname(__file__), '..', '..')
    return os.path.join(app_dir, 'config.json')

# Windows API 导入，用于设置标题栏颜色
if sys.platform == 'win32':
    import ctypes
    from ctypes import wintypes

class CustomScrollBar(QScrollBar):
    """自定义滚动条，集成顶部/底部按钮"""
    def __init__(self, parent=None, theme_colors=None, current_theme_mode='dark'):
        super().__init__(parent)
        # 导入qtawesome并设为类属性
        import qtawesome as qta
        self.qta = qta
        self.theme_colors = theme_colors
        self.current_theme_mode = current_theme_mode
        self.setOrientation(Qt.Vertical)
        self.setup_ui()
        self.setup_style()
        
        # 设置滚动属性，减少闪烁
        self.setSingleStep(1)
        self.setPageStep(10)
        self.setTracking(True)
        
    def setup_ui(self):
        """设置UI组件"""
        colors = self.theme_colors.get(self.current_theme_mode, self.theme_colors['dark']) if self.theme_colors else {'icon_color': '#333333'}
        
        # 创建顶部按钮
        self.top_button = QPushButton()
        self.top_button.setFixedSize(10, 16)  # 宽度与滚动条宽度一致，高度16px
        self.top_button.clicked.connect(self.scroll_to_top)
        self.top_button.setParent(self)
        self.top_button.setIcon(self.qta.icon('fa5s.angle-up', color=colors['icon_color']))
        self.top_button.show()  # 永久显示按钮
        
        # 创建底部按钮
        self.bottom_button = QPushButton()
        self.bottom_button.setFixedSize(10, 16)  # 宽度与滚动条宽度一致，高度16px
        self.bottom_button.clicked.connect(self.scroll_to_bottom)
        self.bottom_button.setParent(self)
        self.bottom_button.setIcon(self.qta.icon('fa5s.angle-down', color=colors['icon_color']))
        self.bottom_button.show()  # 永久显示按钮
        
    def setup_style(self):
        """设置样式"""
        colors = self.theme_colors.get(self.current_theme_mode, self.theme_colors['dark']) if self.theme_colors else {
            'scrollbar_bg': 'rgba(240, 240, 240, 100)',
            'scrollbar_handle': 'rgba(192, 192, 192, 200)',
            'scrollbar_handle_hover': 'rgba(160, 160, 160, 220)',
            'icon_color': '#333333',
            'icon_hover_color': '#555555'
        }
        
        # 滚动条整体样式
        self.setStyleSheet(f"""
            QScrollBar:vertical {{
                background-color: {colors['scrollbar_bg']};
                width: 10px;
                border-radius: 5px;
                margin-top: 0px;
                margin-bottom: 0px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {colors['scrollbar_handle']};
                border-radius: 5px;
                min-height: 20px;
                margin: 16px 0px 16px 0px;  /* 为顶部和底部按钮留出空间 */
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {colors['scrollbar_handle_hover']};
            }}
            QScrollBar::handle:vertical:pressed {{
                background-color: {colors['scrollbar_handle_hover']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
            QPushButton {{
                background-color: transparent;
                color: {colors['icon_color']};
                border: none;
                border-radius: 0px;
                font-size: 8px;
                font-weight: bold;
                padding: 0px;
                margin: 0px;
            }}
            QPushButton:hover {{
                color: {colors['icon_hover_color']};
            }}
            QPushButton:pressed {{
                color: {colors['icon_color']};
            }}
        """)
        
    def resizeEvent(self, event):
        """调整大小时更新按钮位置"""
        super().resizeEvent(event)
        self.update_button_positions()
        
    def update_button_positions(self):
        """更新按钮位置"""
        if not self.top_button or not self.bottom_button:
            return
            
        # 获取滚动条高度
        height = self.height()
        
        # 设置顶部按钮位置（在滚动条顶部）
        self.top_button.move(0, 0)
        
        # 设置底部按钮位置（在滚动条底部）
        self.bottom_button.move(0, height - 16)  # 使用16px高度匹配按钮大小
        
        # 不再在这里更新悬浮加号按钮位置，由主窗口的resizeEvent处理
        
    def scroll_to_top(self):
        """滚动到顶部"""
        self.setValue(self.minimum())
        
    def scroll_to_bottom(self):
        """滚动到底部"""
        self.setValue(self.maximum())
        
    def mousePressEvent(self, event):
        """重写鼠标按压事件，防止闪黑"""
        super().mousePressEvent(event)
        # 确保滚动条立即更新，避免闪烁
        self.update()
        
    def mouseReleaseEvent(self, event):
        """重写鼠标释放事件，确保状态正确"""
        super().mouseReleaseEvent(event)
        # 确保滚动条立即更新，避免闪烁
        self.update()

class ToastWidget(QLabel):
    """自定义提示框"""
    def __init__(self, text, parent=None, theme_colors=None, current_theme_mode='dark'):
        super().__init__(text, parent)
        colors = theme_colors.get(current_theme_mode, theme_colors['dark']) if theme_colors else {'text_color': 'white', 'card_bg': 'rgba(0, 0, 0, 200)'}
        
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {colors['card_bg']};
                color: {colors['text_color']};
                padding: 8px 12px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            }}
        """)
        # 设置窗口标志，确保它显示在最前面
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAlignment(Qt.AlignCenter)
        
    def show_at(self, pos):
        """在指定位置显示提示框"""
        self.adjustSize()  # 确保大小适应内容
        self.move(pos)
        self.show()
        # 1.5秒后自动隐藏
        QTimer.singleShot(1500, self.hide)

class WordWrapLabel(QLabel):
    """支持自动换行的标签"""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setWordWrap(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
    def minimumSizeHint(self):
        # 返回最小大小提示，确保有足够空间显示内容
        size = super().minimumSizeHint()
        # 设置最小高度为字体高度的两倍，确保至少能显示两行
        font_height = self.fontMetrics().height()
        size.setHeight(font_height * 2)
        return size
        
    def sizeHint(self):
        # 返回推荐大小
        size = super().sizeHint()
        # 确保有足够的宽度
        if size.width() < 100:
            size.setWidth(100)
        return size
        
    def heightForWidth(self, width):
        # 根据宽度计算所需高度
        if self.wordWrap():
            # 获取文本内容
            text = self.text()
            # 使用字体度量计算文本在指定宽度下的高度
            fm = self.fontMetrics()
            # 计算换行后的文本高度
            bounding_rect = fm.boundingRect(0, 0, width - 10, 1000, Qt.TextFlag.TextWordWrap, text)
            return bounding_rect.height() + 10  # 添加一些边距
        return super().heightForWidth(width)


class MessageWidget(QFrame):
    """自定义消息小部件，类似聊天框样式"""
    def __init__(self, text, time, is_favorite=False, parent=None, backend=None, language_manager=None, theme_colors=None, current_theme_mode='dark'):
        super().__init__(parent)
        self.text = text  # 保存完整文本内容用于复制
        self.is_favorite = is_favorite
        self.backend = backend
        self.language_manager = language_manager
        self.index = None  # 消息索引，用于删除操作
        self.theme_colors = theme_colors
        self.current_theme_mode = current_theme_mode
        # 导入qtawesome
        import qtawesome as qta
        self.qta = qta
        # 检测内容类型
        from src.core.category import CategoryManager
        # 使用CategoryManager的检测方法
        temp_category_manager = CategoryManager(backend)
        self.content_type = temp_category_manager._detect_content_type(text)
        # 限制显示的文本为2-3行，超出部分显示省略号
        if self.content_type == "image":
            self.display_text = self.language_manager.get_text("image_content")
        elif self.content_type == "file":
            # 对于文件类型，显示文件名而不是完整路径
            import os
            self.display_text = os.path.basename(text)
        else:
            self.display_text = self._truncate_text(text)
        self.setup_ui(self.display_text, time)
        
    def _truncate_text(self, text, max_lines=3, max_chars_per_line=50):
        """截断文本，最多显示max_lines行，每行最多max_chars_per_line字符，从文本头部开始截断"""
        if not text:
            return ""
            
        # 替换换行符为空格
        clean_text = text.replace('\n', ' ')
        
        # 如果文本本身就不长，直接返回
        if len(clean_text) <= max_chars_per_line * max_lines:
            return clean_text
            
        # 从文本头部开始截断
        # 首先计算出最多能显示的字符数
        max_chars = max_chars_per_line * max_lines - 3  # 减去省略号的长度
        
        # 从开头截取指定长度的文本
        truncated_text = clean_text[:max_chars]
        
        # 尝试在单词边界处截断，避免截断单词
        # 找到最后一个空格位置，在那里截断
        last_space_index = truncated_text.rfind(' ')
        if last_space_index != -1 and last_space_index > max_chars_per_line * (max_lines - 1):  # 确保不会截断太多
            truncated_text = truncated_text[:last_space_index]  # 去掉最后的部分单词
            
        # 在末尾添加省略号，表示后面有更多内容
        result = truncated_text + "..."
        
        # 将长文本分成多行
        lines = []
        current_line = ""
        for char in result:
            if len(current_line) < max_chars_per_line:
                current_line += char
            else:
                lines.append(current_line)
                current_line = char
                
        if current_line:
            lines.append(current_line)
            
        # 限制行数
        if len(lines) > max_lines:
            lines = lines[:max_lines]  # 只保留前几行
            # 确保最后一行以省略号结尾
            if not lines[-1].endswith("..."):
                if len(lines[-1]) >= max_chars_per_line - 3:
                    lines[-1] = lines[-1][:max_chars_per_line-3] + "..."
                else:
                    lines[-1] = lines[-1] + "..."
                
        return '\n'.join(lines)
    
    def update_text_display(self):
        """根据当前窗口宽度更新文本显示"""
        if hasattr(self, 'content_label') and self.content_type not in ["image", "file"]:
            # 根据当前窗口宽度计算每行能显示的字符数
            # 假设平均每个字符宽度为8像素（可根据实际字体调整）
            available_width = self.width() - 40  # 减去边距
            max_chars_per_line = max(20, available_width // 8)  # 最少20个字符
            
            # 重新截断文本
            truncated_text = self._truncate_text(self.text, max_lines=3, max_chars_per_line=max_chars_per_line)
            
            # 更新显示文本
            self.content_label.setText(truncated_text)
    
    def update_max_width(self):
        """更新最大宽度约束，确保不超过父容器"""
        if self.parent():
            # 获取滚动区域的实际可用宽度
            # 需要找到顶层的滚动区域
            parent = self.parent()
            while parent and not isinstance(parent, QScrollArea):
                parent = parent.parent()
            
            if parent:
                # 滚动区域宽度减去滚动条宽度和边距
                available_width = parent.width() - 18  # 15px滚动条 + 3px边距
                self.setMaximumWidth(max(200, available_width))  # 最小宽度200px
            else:
                # 如果找不到滚动区域，使用直接父容器的宽度
                parent_width = self.parent().width()
                self.setMaximumWidth(max(200, parent_width - 30))  # 最小宽度200px
            
            # 同时更新文本显示
            self.update_text_display()
        
    def setup_ui(self, text, time):
        self.setFrameStyle(QFrame.NoFrame)
        
        colors = self.theme_colors.get(self.current_theme_mode, self.theme_colors['dark']) if self.theme_colors else {'card_bg': '#f8f8ff', 'card_hover_bg': '#f0f0ff', 'border_color': '#d0d0ff'}
        
        # 添加宽度约束，确保不超过滚动区域
        # 需要找到顶层的滚动区域
        parent = self.parent()
        while parent and not isinstance(parent, QScrollArea):
            parent = parent.parent()
        
        if parent:
            # 滚动区域宽度减去滚动条宽度和边距
            available_width = parent.width() - 18  # 15px滚动条 + 3px边距
            self.setMaximumWidth(max(200, available_width))  # 最小宽度200px
        elif self.parent():
            # 如果找不到滚动区域，使用直接父容器的宽度
            parent_width = self.parent().width()
            self.setMaximumWidth(max(200, parent_width - 30))  # 最小宽度200px
        
        # 统一所有内容类型的样式
        self.setStyleSheet(f"""
            MessageWidget {{
                background-color: {colors['card_bg']};
                border-radius: 12px;
                border: 1px solid {colors['border_color']};
                margin: 5px;
                padding: 10px;
            }}
            MessageWidget:hover {{
                background-color: {colors['card_hover_bg']};
            }}
        """)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(5)
        
        # 如果是图片内容，创建水平布局显示缩略图和文件名
        if self.content_type == "image":
            image_layout = QHBoxLayout()
            
            # 创建图片标签
            image_label = QLabel()
            image_label.setFixedSize(60, 60)
            image_label.setScaledContents(False)  # 不自动缩放，保持比例
            image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # 居中对齐
            image_label.setStyleSheet("""
                QLabel {
                    background-color: #f8f9fa;
                    border: 1px solid #e9ecef;
                    border-radius: 4px;
                }
            """)
            
            # 尝试加载图片
            try:
                from PySide6.QtGui import QPixmap
                import base64
                import re
                
                # 如果是新的图片引用格式
                if self.text.startswith('IMG_REF:'):
                    # 获取父窗口
                    parent_window = self.parent()
                    while parent_window and not isinstance(parent_window, ModernClipboardUI):
                        parent_window = parent_window.parent()
                    
                    # 从父窗口获取图片
                    if parent_window:
                        reference_id = self.text[8:]  # 去掉"IMG_REF:"前缀
                        pixmap = parent_window.get_image_from_reference(reference_id)
                        
                        if pixmap and not pixmap.isNull():
                            # 等比例缩放图片以适应标签，保持比例
                            scaled_pixmap = pixmap.scaled(
                                60, 60, 
                                Qt.AspectRatioMode.KeepAspectRatio, 
                                Qt.TransformationMode.SmoothTransformation
                            )
                            image_label.setPixmap(scaled_pixmap)
                        else:
                            # 如果引用失效，显示默认图标
                            image_label.setText("🖼️")
                            image_label.setFixedSize(60, 60)
                            image_label.setStyleSheet("font-size: 24px; color: #6c757d; background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 4px;")
                    else:
                        # 如果找不到父窗口，显示默认图标
                        image_label.setText("🖼️")
                        image_label.setFixedSize(60, 60)
                        image_label.setStyleSheet("font-size: 24px; color: #6c757d; background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 4px;")
                        
                # 如果是base64图片数据
                elif self.text.startswith('data:image/') and ';base64,' in self.text:
                    # 提取base64数据
                    base64_data = self.text.split(';base64,')[1]
                    image_data = base64.b64decode(base64_data)
                    pixmap = QPixmap()
                    pixmap.loadFromData(image_data)
                    
                    if pixmap.isNull():
                        # 如果base64解码失败，显示默认图标
                        image_label.setText("🖼️")
                        image_label.setFixedSize(60, 60)
                        image_label.setStyleSheet("font-size: 24px; color: #6c757d; background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 4px;")
                    else:
                        # 等比例缩放图片以适应标签，保持比例
                        scaled_pixmap = pixmap.scaled(
                            60, 60, 
                            Qt.AspectRatioMode.KeepAspectRatio, 
                            Qt.TransformationMode.SmoothTransformation
                        )
                        image_label.setPixmap(scaled_pixmap)
                        
                # 如果是图片路径
                else:
                    pixmap = QPixmap(self.text)
                    if pixmap.isNull():
                        # 如果图片加载失败，显示默认图标
                        image_label.setText("🖼️")
                        image_label.setFixedSize(60, 60)
                        image_label.setStyleSheet("font-size: 24px; color: #6c757d; background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 4px;")
                    else:
                        # 等比例缩放图片以适应标签，保持比例
                        scaled_pixmap = pixmap.scaled(
                            60, 60, 
                            Qt.AspectRatioMode.KeepAspectRatio, 
                            Qt.TransformationMode.SmoothTransformation
                        )
                        image_label.setPixmap(scaled_pixmap)
                        
            except Exception as e:
                # 如果出错，显示默认图标
                image_label.setText("🖼️")
                image_label.setFixedSize(60, 60)
                image_label.setStyleSheet("font-size: 24px; color: #6c757d; background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 4px;")
            
            image_layout.addWidget(image_label)
            
            # 创建文件名标签
            filename_label = WordWrapLabel()
            if self.text.startswith('IMG_REF:'):
                # 如果是图片引用，显示为图片
                filename = self.language_manager.get_text("file_image")
            elif self.text.startswith('data:image/') and ';base64,' in self.text:
                # 如果是base64，尝试从data URL中提取文件类型
                match = re.search(r'data:image/(\w+);base64,', self.text)
                if match:
                    file_type = match.group(1)
                    filename = f"{self.language_manager.get_text('image')}.{file_type}"
                else:
                    filename = self.language_manager.get_text("file_image")
            else:
                # 如果是路径，提取文件名
                import os
                if os.path.exists(self.text):
                    filename = os.path.basename(self.text)
                else:
                    # 如果文件不存在，可能是网络路径或其他格式
                    filename = self.language_manager.get_text("file_image")
                
            filename_label.setText(filename)
            filename_label.setStyleSheet(f"""
                QLabel {{
                    color: {colors['text_color']};
                    font-size: 12px;
                    font-weight: bold;
                }}
            """)
            # 设置最小宽度，确保有足够空间显示文件名
            filename_label.setMinimumWidth(100)
            
            image_layout.addWidget(filename_label, 1)  # 添加拉伸因子1，让文件名占据剩余空间
            
            main_layout.addLayout(image_layout)
            
        else:
            # 非图片内容，使用原来的布局
            # 如果是文件类型，创建水平布局显示图标和文件名
            if self.content_type == "file":
                file_layout = QHBoxLayout()
                
                # 创建文件图标标签
                file_icon_label = QLabel()
                file_icon_label.setFixedSize(24, 24)
                file_icon_label.setScaledContents(True)
                
                # 获取文件图标
                file_icon = self.get_file_icon(self.text)
                if file_icon:
                    file_icon_label.setPixmap(file_icon.pixmap(24, 24))
                else:
                    # 如果获取图标失败，显示默认图标
                    file_icon_label.setText("📄")
                    file_icon_label.setStyleSheet("font-size: 16px;")
                
                file_layout.addWidget(file_icon_label)
                
                # 创建文件名标签
                filename_label = WordWrapLabel()
                import os
                filename = os.path.basename(self.text) if os.path.isfile(self.text) else self.display_text
                filename_label.setText(filename)
                filename_label.setStyleSheet(f"""
                    QLabel {{
                        color: {colors['text_color']};
                        font-size: 12px;
                        font-weight: bold;
                    }}
                """)
                # 设置最小宽度，确保有足够空间显示文件名
                filename_label.setMinimumWidth(100)
                
                file_layout.addWidget(filename_label, 1)  # 添加拉伸因子1，让文件名占据剩余空间
                
                main_layout.addLayout(file_layout)
            else:
                # 非文件内容，使用原来的布局
                # 消息内容
                self.content_label = QLabel(text)  # 保存为实例变量
                self.content_label.setWordWrap(True)
                # 移除TextSelectableByMouse标志，让鼠标事件可以传递到父级
                self.content_label.setTextInteractionFlags(Qt.NoTextInteraction)
                # 移除固定高度限制，让内容自适应高度
                self.content_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
                
                # 根据内容类型设置不同的文本样式
                if self.content_type == "image":
                    self.content_label.setStyleSheet(f"""
                        QLabel {{
                            color: {colors['text_color']};
                            font-size: 13px;
                            font-family: "Segoe UI", sans-serif;
                            line-height: 1.4;
                            font-style: italic;
                        }}
                    """)
                else:
                    self.content_label.setStyleSheet(f"""
                        QLabel {{
                            color: {colors['text_color']};
                            font-size: 13px;
                            font-family: "Segoe UI", sans-serif;
                            line-height: 1.4;
                        }}
                    """)
                
                main_layout.addWidget(self.content_label)
        
        # 底部布局（时间和收藏按钮）
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 5, 0, 0)
        
        # 时间标签
        self.time_label = QLabel(time)
        self.time_label.setStyleSheet(f"""
            QLabel {{
                color: {colors['secondary_text']};
                font-size: 11px;
                font-family: "Segoe UI", sans-serif;
            }}
        """)
        bottom_layout.addWidget(self.time_label)
        
        # 弹性空间
        bottom_layout.addStretch()
        
        # 收藏按钮
        self.favorite_btn = QPushButton()
        self.favorite_btn.setFixedSize(24, 24)  # 从20x20放大到24x24
        self.favorite_btn.setFlat(True)
        self.favorite_btn.setCursor(Qt.PointingHandCursor)
        # 设置特定样式，移除所有边框和背景
        self.favorite_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                background: transparent;
                border: none;
            }
            QPushButton:pressed {
                background: transparent;
                border: none;
            }
        """)
        self.favorite_btn.enterEvent = lambda e: self.update_favorite_hover(True)
        self.favorite_btn.leaveEvent = lambda e: self.update_favorite_hover(False)
        self.favorite_btn.clicked.connect(self.toggle_favorite)
        self.update_favorite_style()
        bottom_layout.addWidget(self.favorite_btn)
        
        main_layout.addLayout(bottom_layout)
        
        # 设置整个消息框的大小策略，允许高度根据内容调整
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        
    def mouseDoubleClickEvent(self, event):
        """双击消息区域打开查看器"""
        if event.button() == Qt.LeftButton:
            # 获取父窗口
            parent_window = self.parent()
            while parent_window and not isinstance(parent_window, ModernClipboardUI):
                parent_window = parent_window.parent()
            
            if parent_window:
                # 如果是图片内容，直接使用系统默认图片查看器
                if self.content_type == "image":
                    parent_window.open_image_viewer(self.text)
                else:
                    parent_window.open_content_viewer(self.text)
        
        super().mouseDoubleClickEvent(event)
        
    def mousePressEvent(self, event):
        """点击消息区域复制内容"""
        if event.button() == Qt.LeftButton:
            # 获取父窗口
            parent_window = self.parent()
            while parent_window and not isinstance(parent_window, ModernClipboardUI):
                parent_window = parent_window.parent()
            
            if parent_window:
                # 设置标志位，防止重复记录 - 使用计数器机制，忽略接下来的2次剪贴板变化
                parent_window.ignore_next_clipboard_changes(2)
                
                # 根据内容类型复制不同内容
                if self.content_type == "image":
                    # 检查是否是新的图片引用格式
                    if self.text.startswith('IMG_REF:'):
                        # 提取引用ID
                        reference_id = self.text[8:]  # 去掉"IMG_REF:"前缀
                        
                        # 从父窗口获取图片
                        pixmap = parent_window.get_image_from_reference(reference_id)
                        if pixmap and not pixmap.isNull():
                            parent_window.sys_clipboard.setPixmap(pixmap)
                        else:
                            # 如果引用失效，显示错误信息
                            parent_window.sys_clipboard.setText("[图片引用已失效]")
                    elif self.text.startswith('data:image/') and ';base64,' in self.text:
                        # 处理旧的base64格式（向后兼容）
                        # 提取base64数据
                        base64_data = self.text.split(';base64,')[1]
                        image_data = base64.b64decode(base64_data)
                        
                        # 创建QPixmap并复制到剪贴板
                        pixmap = QPixmap()
                        pixmap.loadFromData(image_data)
                        if not pixmap.isNull():
                            parent_window.sys_clipboard.setPixmap(pixmap)
                        else:
                            # 如果图片加载失败，复制原始文本
                            parent_window.sys_clipboard.setText(self.text)
                    else:
                        # 如果是图片路径，尝试加载图片数据放入剪贴板
                        pixmap = QPixmap(self.text)
                        if not pixmap.isNull():
                            # 核心修改：这里使用 setPixmap 放入图片数据，而不是 setText/pyperclip
                            parent_window.sys_clipboard.setPixmap(pixmap)
                        else:
                            # 如果图片文件被删或者加载失败，检查是否是文件URL格式
                            if os.path.exists(self.text):
                                # 如果文件存在但加载失败，可能是格式问题，尝试复制文件路径
                                import os
                                file_path = self.text.strip().strip('"')
                                if file_path.startswith('file:///'):
                                    file_path = file_path[8:]
                                
                                # 创建文件URL并复制
                                mime_data = QMimeData()
                                url = QUrl.fromLocalFile(file_path)
                                mime_data.setUrls([url])
                                parent_window.sys_clipboard.setMimeData(mime_data)
                            else:
                                # 只有当图片文件被删或者加载失败时，才回退到复制路径文本
                                parent_window.sys_clipboard.setText(self.text)
                elif self.content_type == "file":
                    # 【新增】文件复制核心逻辑
                    import os
                    
                    # --- 1. 路径清洗 (关键步骤) ---
                    # 去除首尾空格和可能存在的双引号
                    file_path = self.text.strip().strip('"')
                    
                    # 如果是 file:/// 开头的，去掉头部
                    if file_path.startswith('file:///'):
                        file_path = file_path[8:]
                    
                    # 规范化路径 (把 / 变成 \，适应 Windows)
                    file_path = os.path.normpath(file_path)
                    
                    # --- 2. 检查文件是否存在 ---
                    if os.path.exists(file_path):
                        # 创建 MimeData 对象
                        mime_data = QMimeData()
                        
                        # 将清洗后的路径转换为 QUrl
                        url = QUrl.fromLocalFile(file_path)
                        mime_data.setUrls([url])
                        
                        # 3. 写入剪贴板 (设置 MimeData 而不是 Text)
                        parent_window.sys_clipboard.setMimeData(mime_data)
                    else:
                        # 如果文件真的不存在了，回退到复制路径文本
                        parent_window.sys_clipboard.setText(file_path)
                else:
                    # 非图片内容，使用Qt剪贴板复制文本
                    parent_window.sys_clipboard.setText(self.text)
                
                # 在父窗口中显示复制成功的提示
                parent_window.show_notification(self.language_manager.get_text("status_copied"))
                
                # 0.9秒后隐藏窗口（比提示框稍晚一点）
                QTimer.singleShot(900, parent_window.animate_hide)
        
        super().mousePressEvent(event)
        
    def contextMenuEvent(self, event):
        """右键菜单"""
        # 获取父窗口
        parent_window = self.parent()
        while parent_window and not isinstance(parent_window, ModernClipboardUI):
            parent_window = parent_window.parent()
        
        if parent_window:
            # 创建右键菜单
            context_menu = QMenu(self)
            context_menu.setStyleSheet("""
                QMenu {
                    background-color: white;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    padding: 4px;
                }
                QMenu::item {
                    padding: 8px 20px;
                    border-radius: 4px;
                    font-size: 13px;
                }
                QMenu::item:selected {
                    background-color: #f0f0f0;
                }
            """)
            
            # 删除（直接删除当前项）
            delete_action = context_menu.addAction("删除")
            delete_action.triggered.connect(lambda: self.delete_message(parent_window))
            
            # 分隔线
            context_menu.addSeparator()
            
            # 更多选项（批量删除）
            more_action = context_menu.addAction("更多")
            more_menu = QMenu(self)
            more_menu.setStyleSheet("""
                QMenu {
                    background-color: white;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    padding: 4px;
                }
                QMenu::item {
                    padding: 8px 20px;
                    border-radius: 4px;
                    font-size: 13px;
                }
                QMenu::item:selected {
                    background-color: #f0f0f0;
                }
            """)
            
            # 删除今天
            delete_today_action = more_menu.addAction("删除今天")
            delete_today_action.triggered.connect(lambda: parent_window.batch_delete_by_time('today'))
            
            # 删除近7天
            delete_7days_action = more_menu.addAction("删除近7天")
            delete_7days_action.triggered.connect(lambda: parent_window.batch_delete_by_time('7days'))
            
            # 删除近30天
            delete_30days_action = more_menu.addAction("删除近30天")
            delete_30days_action.triggered.connect(lambda: parent_window.batch_delete_by_time('30days'))
            
            # 删除全部
            delete_all_action = more_menu.addAction("删除全部")
            delete_all_action.triggered.connect(lambda: parent_window.batch_delete_by_time('all'))
            
            more_action.setMenu(more_menu)
            
            # 显示菜单
            context_menu.exec(event.globalPos())
    
    def show_delete_confirmation(self, parent_window, global_pos):
        """显示删除确认弹窗"""
        # 创建弹窗部件
        delete_widget = QWidget(parent_window)
        delete_widget.setObjectName("DeleteConfirmationWidget")
        
        # 设置样式，与日期搜索框保持一致
        delete_widget.setStyleSheet("""
            QWidget#DeleteConfirmationWidget {
                background-color: white;
                border-radius: 18px;
                border: 1px solid #e0e0e0;
            }
        """)
        
        # 创建水平布局
        layout = QHBoxLayout(delete_widget)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)
        
        # 添加删除图标
        delete_icon = QLabel()
        delete_icon.setPixmap(self.qta.icon('fa5s.trash', color='#E74C3C').pixmap(16, 16))
        layout.addWidget(delete_icon)
        
        # 添加删除文本
        delete_label = QLabel("删除")
        delete_label.setStyleSheet("""
            QLabel {
                color: #333333;
                font-size: 12px;
                font-weight: 500;
            }
        """)
        layout.addWidget(delete_label)
        
        # 设置弹窗大小
        delete_widget.adjustSize()
        delete_widget.setFixedSize(80, 36)
        
        # 将全局坐标转换为父窗口坐标
        parent_pos = parent_window.mapFromGlobal(global_pos)
        
        # 计算弹窗位置，确保在窗口内
        x = parent_pos.x() - delete_widget.width() // 2
        y = parent_pos.y() - delete_widget.height() - 5  # 在鼠标上方5px
        
        # 确保弹窗不超出窗口边界
        if x < 5:
            x = 5
        elif x + delete_widget.width() > parent_window.width() - 5:
            x = parent_window.width() - delete_widget.width() - 5
            
        if y < 5:
            y = parent_pos.y() + 5  # 如果上方空间不够，显示在下方
        
        # 设置弹窗位置并显示
        delete_widget.move(x, y)
        delete_widget.show()
        delete_widget.raise_()  # 确保在最上层
        
        # 创建定时器，点击后执行删除
        delete_widget.mousePressEvent = lambda e: self.execute_delete(parent_window, delete_widget)
        
        # 创建定时器，1秒后自动隐藏
        auto_hide_timer = QTimer(delete_widget)
        auto_hide_timer.timeout.connect(lambda: self.hide_delete_confirmation(delete_widget, auto_hide_timer))
        auto_hide_timer.start(1000)  # 1秒后自动隐藏
    
    def execute_delete(self, parent_window, delete_widget):
        """执行删除操作"""
        # 隐藏弹窗
        self.hide_delete_confirmation(delete_widget, None)
        
        # 执行删除
        self.delete_message(parent_window)
    
    def hide_delete_confirmation(self, delete_widget, timer):
        """隐藏删除确认弹窗"""
        if timer:
            timer.stop()
        if delete_widget:
            delete_widget.hide()
            delete_widget.deleteLater()
    
    def delete_message(self, parent_window):
        """删除消息"""
        if self.index is not None:
            parent_window.delete_message_by_index(self.index)
        
    def update_favorite_style(self):
        """根据收藏状态更新按钮样式"""
        colors = self.theme_colors.get(self.current_theme_mode, self.theme_colors['dark']) if self.theme_colors else {'secondary_text': '#CCCCCC', 'icon_active_color': '#4A90E2'}
        if self.is_favorite:
            self.favorite_btn.setIcon(self.qta.icon('fa5s.star', color=colors['icon_active_color']))
        else:
            self.favorite_btn.setIcon(self.qta.icon('fa5s.star', color=colors['secondary_text']))
    
    def get_file_icon(self, file_path):
        """根据文件扩展名返回相应的QtAwesome图标"""
        import os
        import qtawesome as qta
        
        # 获取文件扩展名
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        # 根据文件扩展名返回相应图标
        if ext in ['.zip', '.rar', '.7z', '.tar', '.gz']:
            return self.qta.icon('fa5s.file-archive', color='#FF6B35')
        elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp']:
            return self.qta.icon('fa5s.file-image', color='#4ECDC4')
        elif ext in ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm']:
            return self.qta.icon('fa5s.file-video', color='#45B7D1')
        elif ext in ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma']:
            return self.qta.icon('fa5s.file-audio', color='#9B59B6')
        elif ext in ['.pdf']:
            return self.qta.icon('fa5s.file-pdf', color='#E74C3C')
        elif ext in ['.doc', '.docx']:
            return self.qta.icon('fa5s.file-word', color='#2980B9')
        elif ext in ['.xls', '.xlsx']:
            return self.qta.icon('fa5s.file-excel', color='#27AE60')
        elif ext in ['.ppt', '.pptx']:
            return self.qta.icon('fa5s.file-powerpoint', color='#D35400')
        elif ext in ['.txt', '.rtf']:
            return self.qta.icon('fa5s.file-alt', color='#95A5A6')
        elif ext in ['.py', '.js', '.html', '.css', '.cpp', '.java', '.php', '.rb', '.go', '.rs']:
            return self.qta.icon('fa5s.file-code', color='#F39C12')
        elif ext in ['.exe', '.msi', '.dmg', '.pkg', '.deb', '.rpm']:
            return self.qta.icon('fa5s.cogs', color='#E67E22')
        else:
            return self.qta.icon('fa5s.file', color='#7F8C8D')
    
    def update_favorite_hover(self, is_hovering):
        """更新收藏按钮悬停状态"""
        # 如果已收藏，不改变颜色
        if self.is_favorite:
            return
        
        # 获取主题颜色
        colors = self.theme_colors.get(self.current_theme_mode, self.theme_colors['dark']) if self.theme_colors else {'text_color': '#333333', 'secondary_text': '#CCCCCC'}
        
        # 根据是否悬停更新图标颜色
        if is_hovering:
            # 悬停时使用金色
            self.favorite_btn.setIcon(self.qta.icon('fa5s.star', color='#FFD700'))
        else:
            # 非悬停时使用主题次要文本颜色
            self.favorite_btn.setIcon(self.qta.icon('fa5s.star', color=colors['secondary_text']))
    
    def toggle_favorite(self):
        """切换收藏状态"""
        self.is_favorite = not self.is_favorite
        self.update_favorite_style()
        return self.is_favorite

# 引用独立的笔记编辑窗口
from src.ui.text_editor import NoteEditWindow


class NoteWidget(QFrame):
    """笔记显示组件，与粘贴板样式一致"""
    def __init__(self, note_data, parent=None, backend=None, formatted_time=None, theme_colors=None, current_theme_mode='dark'):
        super().__init__(parent)
        self.note_data = note_data
        self.backend = backend
        self.note_id = note_data.get("id")
        self.title = note_data.get("title", "")
        self.content = note_data.get("text", "")
        # 使用传入的格式化时间，如果没有则使用原始时间
        self.formatted_time = formatted_time or (note_data.get("created_at") or note_data.get("time", ""))
        # 保留原始时间用于其他用途
        self.created_at = note_data.get("created_at") or note_data.get("time", "")
        self.updated_at = note_data.get("updated_at", "")
        self.is_favorite = note_data.get("favorite", False)
        self.theme_colors = theme_colors
        self.current_theme_mode = current_theme_mode
        
        # 导入qtawesome
        import qtawesome as qta
        self.qta = qta
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI组件"""
        colors = self.theme_colors.get(self.current_theme_mode, self.theme_colors['dark']) if self.theme_colors else {'card_bg': '#f8f8ff', 'card_hover_bg': '#f0f0ff', 'border_color': '#d0d0ff', 'text_color': '#333333', 'secondary_text': '#888888'}
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(5)
        
        # 标题区域
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(8)
        
        # 标题文本
        title_label = QLabel(self.title)
        title_label.setStyleSheet(f"""
            QLabel {{
                font-size: 16px;
                font-weight: bold;
                color: {colors['text_color']};
            }}
        """)
        title_layout.addWidget(title_label)
        
        title_layout.addStretch()
        main_layout.addLayout(title_layout)
        
        # 内容预览区域
        content_preview = self.content.replace('\n', ' ')[:100] + ("..." if len(self.content) > 100 else "")
        content_label = QLabel(content_preview)
        content_label.setStyleSheet(f"""
            QLabel {{
                font-size: 14px;
                color: {colors['secondary_text']};
                line-height: 1.4;
            }}
        """)
        content_label.setWordWrap(True)
        main_layout.addWidget(content_label)
        
        # 底部布局（时间和收藏按钮）
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 5, 0, 0)
        
        # 时间标签
        time_label = QLabel(self.formatted_time)
        time_label.setStyleSheet(f"""
            QLabel {{
                color: {colors['secondary_text']};
                font-size: 11px;
                font-family: "Segoe UI", sans-serif;
            }}
        """)
        bottom_layout.addWidget(time_label)
        
        # 弹性空间
        bottom_layout.addStretch()
        
        # 置顶按钮
        self.pin_btn = QPushButton()
        self.pin_btn.setFixedSize(24, 24)  # 与粘贴板组件一致
        self.pin_btn.setFlat(True)
        self.pin_btn.setCursor(Qt.PointingHandCursor)
        # 设置特定样式，移除所有边框和背景
        self.pin_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                background: transparent;
                border: none;
            }
            QPushButton:pressed {
                background: transparent;
                border: none;
            }
        """)
        self.pin_btn.setIcon(self.qta.icon('fa5s.bookmark', color=colors['secondary_text']))
        self.pin_btn.enterEvent = lambda e: self.update_pin_hover(True)
        self.pin_btn.leaveEvent = lambda e: self.update_pin_hover(False)
        self.pin_btn.clicked.connect(self.toggle_pin)
        self.update_pin_style()
        bottom_layout.addWidget(self.pin_btn)
        
        main_layout.addLayout(bottom_layout)
        
        # 设置整体样式，与粘贴板组件一致
        self.setStyleSheet(f"""
            NoteWidget {{
                background-color: {colors['card_bg']};
                border-radius: 12px;
                border: 1px solid {colors['border_color']};
                margin: 5px;
                padding: 10px;
            }}
            NoteWidget:hover {{
                background-color: {colors['card_hover_bg']};
            }}
        """)
        
        # 添加阴影效果，与粘贴板组件一致
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 10))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
        
        # 设置整个消息框的大小策略，允许高度根据内容调整
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        
    def update_pin_style(self):
        """更新置顶按钮样式"""
        colors = self.theme_colors.get(self.current_theme_mode, self.theme_colors['dark']) if self.theme_colors else {'secondary_text': '#888888', 'icon_active_color': '#4A90E2'}
        
        if self.is_favorite:
            self.pin_btn.setIcon(self.qta.icon('fa5s.bookmark', color=colors['icon_active_color']))
        else:
            self.pin_btn.setIcon(self.qta.icon('fa5s.bookmark', color=colors['secondary_text']))
            
    def update_pin_hover(self, is_hovering):
        """更新置顶按钮悬停状态"""
        colors = self.theme_colors.get(self.current_theme_mode, self.theme_colors['dark']) if self.theme_colors else {'secondary_text': '#888888', 'icon_active_color': '#4A90E2'}
        
        # 如果已置顶，不改变颜色
        if self.is_favorite:
            return
        
        # 根据是否悬停更新图标颜色
        if is_hovering:
            # 悬停时使用主题色
            self.pin_btn.setIcon(self.qta.icon('fa5s.bookmark', color=colors['icon_active_color']))
        else:
            # 非悬停时使用次要文字颜色
            self.pin_btn.setIcon(self.qta.icon('fa5s.bookmark', color=colors['secondary_text']))
            
    def toggle_pin(self):
        """切换置顶状态"""
        self.is_favorite = not self.is_favorite
        self.update_pin_style()
        
        # 更新数据库中的置顶状态
        if self.backend and self.note_id:
            self.backend.toggle_note_favorite(self.note_id)
            
            # 获取父窗口并刷新列表
            parent_window = self.parent()
            while parent_window and not hasattr(parent_window, 'debounce_refresh_list'):
                parent_window = parent_window.parent()
            
            if parent_window:
                parent_window.debounce_refresh_list()
        
        return self.is_favorite
        
    def mouseDoubleClickEvent(self, event):
        """双击编辑笔记"""
        if event.button() == Qt.LeftButton:
            # 获取父窗口
            parent_window = self.parent()
            while parent_window and not hasattr(parent_window, 'edit_note'):
                parent_window = parent_window.parent()
            
            if parent_window:
                parent_window.edit_note(self)
        
        # 不调用super()以避免对象已删除时的错误
        event.accept()

class NoteInputWindow(QWidget):
    """笔记输入窗口"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.language_manager = parent.language_manager  # 添加language_manager属性
        self.setup_ui()
        self.setup_style()
        self.setup_animation()
        
    def setup_ui(self):
        """设置UI组件"""
        # 设置窗口属性
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(300, 120)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # 标题输入框
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText(self.language_manager.get_text("placeholder_note_title"))
        self.title_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 2px solid #4A90E2;
            }
        """)
        main_layout.addWidget(self.title_input)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(10)
        
        # 取消按钮
        self.cancel_btn = QPushButton(self.language_manager.get_text("cancel"))
        self.cancel_btn.setFixedSize(60, 30)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #F0F0F0;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                color: #666666;
            }
            QPushButton:hover {
                background-color: #E0E0E0;
            }
        """)
        self.cancel_btn.clicked.connect(self.close)
        button_layout.addWidget(self.cancel_btn)
        
        # 确定按钮
        self.confirm_btn = QPushButton(self.language_manager.get_text("confirm"))
        self.confirm_btn.setFixedSize(60, 30)
        self.confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A90E2;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                color: white;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
        """)
        self.confirm_btn.clicked.connect(self.confirm_note)
        button_layout.addWidget(self.confirm_btn)
        
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        
        # 设置焦点到标题输入框
        self.title_input.setFocus()
        
        # 设置回车键确认
        self.title_input.returnPressed.connect(self.confirm_note)
        
    def setup_style(self):
        """设置窗口样式"""
        self.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 12px;
            }
        """)
        
        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
        
    def setup_animation(self):
        """设置动画效果"""
        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)
        
        self.opacity_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.opacity_animation.setDuration(200)
        self.opacity_animation.setStartValue(0.0)
        self.opacity_animation.setEndValue(1.0)
        
    def show_at_position(self, x, y):
        """在指定位置显示窗口"""
        # 确保窗口在屏幕范围内
        screen = QGuiApplication.primaryScreen().geometry()
        if x + self.width() > screen.width():
            x = screen.width() - self.width() - 20
        if y + self.height() > screen.height():
            y = screen.height() - self.height() - 20
        if x < 20:
            x = 20
        if y < 20:
            y = 20
            
        self.move(x, y)
        self.show()
        self.opacity_animation.start()
        
    def confirm_note(self):
        """确认创建笔记"""
        title = self.title_input.text().strip()
        if title:
            # 调用父窗口的创建笔记方法
            if self.parent_window:
                self.parent_window.create_note_with_title(title)
            self.close()
        else:
            # 如果标题为空，显示提示
            self.title_input.setStyleSheet("""
                QLineEdit {
                    border: 2px solid #E74C3C;
                    border-radius: 8px;
                    padding: 8px 12px;
                    font-size: 14px;
                    background-color: white;
                }
            """)

class ModernClipboardUI(QMainWindow):
    def __init__(self, backend, app_clipboard, language_manager):
        super().__init__()
        self.backend = backend
        self.sys_clipboard = app_clipboard 
        self.language_manager = language_manager  # 添加语言管理器
        
        # 导入qtawesome并设为类属性
        import qtawesome as qta
        self.qta = qta
        
        # --- 核心修复：防止自己监听自己的标志位 ---
        # 初始化剪贴板变化忽略计数器
        self.ignore_clipboard_changes_count = 0 
        
        # 初始化图片引用字典 - 存储临时图片文件引用
        self.image_references = {}  # 格式: {reference_id: {"path": temp_file_path, "created_at": timestamp}}
        
        # 设置定时清理临时文件
        self.cleanup_timer = QTimer(self)
        self.cleanup_timer.timeout.connect(self.cleanup_temp_images)
        self.cleanup_timer.start(60000)  # 每分钟清理一次过期图片
        
        # 程序启动时立即清理一次临时文件
        QTimer.singleShot(5000, self.cleanup_temp_images)  # 启动5秒后清理
        
        # 初始化分类管理器
        self.category_manager = CategoryManager(backend)
        
        # 初始化当前分类为None
        self._current_category = None
        
        # 初始化主题颜色参数
        self.theme_colors = {
            'light': {
                'main_bg': '#FFFFFF',
                'card_bg': '#f8f8ff',
                'card_hover_bg': '#f0f0ff',
                'border_color': '#d0d0ff',
                'text_color': '#333333',
                'secondary_text': '#888888',
                'accent_color': '#4A90E2',
                'category_text': '#666666',
                'category_hover_bg': '#e0e0e0',
                'category_checked_bg': '#0078d4',
                'category_checked_text': '#FFFFFF',
                'toolbar_border': 'rgba(0, 0, 0, 0.1)',
                'toolbar_hover_bg': 'rgba(0, 0, 0, 0.05)',
                'toolbar_pressed_bg': 'rgba(0, 0, 0, 0.1)',
                'scrollbar_bg': 'rgba(240, 240, 240, 100)',
                'scrollbar_handle': 'rgba(192, 192, 192, 200)',
                'scrollbar_handle_hover': 'rgba(160, 160, 160, 220)',
                'search_bg': 'white',
                'search_border': '#ddd',
                'search_focus_border': '#4A90E2',
                'add_button_bg': '#4A90E2',
                'add_button_hover': '#357ABD',
                'add_button_pressed': '#2968AA',
                'window_bg': '#f5f5f5',
                'icon_color': '#333333',
                'icon_hover_color': '#555555',
                'icon_active_color': '#4A90E2'
            },
            'dark': {
                'main_bg': '#1A1A1A',
                'card_bg': '#2D2D2D',
                'card_hover_bg': '#3D3D3D',
                'border_color': '#4D4D4D',
                'text_color': '#E0E0E0',
                'secondary_text': '#AAAAAA',
                'accent_color': '#5A9FF2',
                'category_text': '#AAAAAA',
                'category_hover_bg': '#3D3D3D',
                'category_checked_bg': '#5A9FF2',
                'category_checked_text': '#FFFFFF',
                'toolbar_border': 'rgba(255, 255, 255, 0.1)',
                'toolbar_hover_bg': 'rgba(255, 255, 255, 0.05)',
                'toolbar_pressed_bg': 'rgba(255, 255, 255, 0.1)',
                'scrollbar_bg': 'rgba(60, 60, 60, 100)',
                'scrollbar_handle': 'rgba(100, 100, 100, 200)',
                'scrollbar_handle_hover': 'rgba(130, 130, 130, 220)',
                'search_bg': '#2D2D2D',
                'search_border': '#4D4D4D',
                'search_focus_border': '#5A9FF2',
                'add_button_bg': '#5A9FF2',
                'add_button_hover': '#4A90E2',
                'add_button_pressed': '#357ABD',
                'window_bg': '#1A1A1A',
                'icon_color': '#E0E0E0',
                'icon_hover_color': '#FFFFFF',
                'icon_active_color': '#5A9FF2'
            }
        }
        
        # 加载显示设置
        self.load_display_settings()
        
        self.is_hidden = False
        
        # 【新增】记录当前吸附的边缘 (默认顶部)
        self.dock_edge = "top"
        
        # 【新增】跟踪窗口是否正在被拖动或调整大小
        self.is_moving = False
        
        # 初始化悬浮触发条
        self.trigger_bar = None
        self.init_trigger_bar()
        
        # 初始化系统托盘
        self.init_system_tray()
        
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)  # 禁用透明背景，使用原生背景
        
        # 隐藏标题栏但保留窗口功能
        self.setWindowTitle(self.language_manager.get_text("window_title"))
        self.setWindowOpacity(0.99)  # 默认99%，避免白边问题
        
        # 添加原生边框以支持系统默认的调整大小功能
        if hasattr(Qt, 'WA_NativeWindow'):
            self.setAttribute(Qt.WA_NativeWindow)
        
        # 设置Windows原生标题栏为白色
        self.set_title_bar_white()
        
        self.resize(315, 380)  # 调整初始窗口大小为更小的尺寸
        self.setMinimumWidth(315)  # 设置最小宽度为315px
        
        # 1. 开启鼠标追踪 (为了检测鼠标是否悬停在边缘)
        self.setMouseTracking(True)
        
        # 3. 加载上次保存的大小和位置
        position_loaded = self.load_window_config()
        
        # 如果没有加载到位置信息，则根据dock_edge设置默认位置
        if not position_loaded:
            screen = QGuiApplication.primaryScreen().geometry()
            # 4. 根据上次保存的吸附位置设置初始位置
            if self.dock_edge == "top":
                self.setGeometry(screen.width() - self.width() - 60, 0, self.width(), self.height())
            elif self.dock_edge == "bottom":
                self.setGeometry(screen.width() - self.width() - 60, screen.height() - self.height() - 30, self.width(), self.height())
            elif self.dock_edge == "left":
                self.setGeometry(0, 100, self.width(), self.height())
            elif self.dock_edge == "right":
                self.setGeometry(screen.width() - self.width(), 100, self.width(), self.height())
            else:
                # 默认位置（右上角）
                self.setGeometry(screen.width() - self.width() - 60, 30, self.width(), self.height())

        self.setup_ui()
        
        # 保存原始窗口标志，用于显示时恢复
        self._original_window_flags = self.windowFlags()
        
        # 在UI创建后立即应用UI缩放设置，确保保存的缩放倍数被正确应用
        self.apply_ui_scale(save_config=False)
        
        # 1. 连接 Qt 自带的高效监听信号（解决卡顿和重复的核心）
        self.sys_clipboard.dataChanged.connect(self.on_clipboard_change)
        
        # 2. 添加备用定时器监听机制，提高监听灵敏度
        self.last_clipboard_hash = self._get_clipboard_hash()  # 初始化时获取当前剪贴板哈希
        self.backup_clipboard_timer = QTimer(self)
        self.backup_clipboard_timer.setInterval(200)  # 每200ms检查一次
        self.backup_clipboard_timer.timeout.connect(self.backup_clipboard_check)
        self.backup_clipboard_timer.start()
        
        self.hide_timer = QTimer(self)
        self.hide_timer.setInterval(1500) 
        self.hide_timer.timeout.connect(self.animate_hide)

        self.monitor_timer = QTimer(self)
        self.monitor_timer.setInterval(100)
        self.monitor_timer.timeout.connect(self.check_mouse_trigger)
        self.monitor_timer.start()

        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(350)
        self.animation.setEasingCurve(QEasingCurve.OutQuad)
        
        # 搜索状态跟踪
        self.is_searching = False
        self.search_timer = QTimer(self)
        self.search_timer.setInterval(300)  # 300ms延迟，避免频繁搜索
        self.search_timer.timeout.connect(self.perform_search)
        
        # 添加列表刷新防抖定时器
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setSingleShot(True)
        self.refresh_timer.timeout.connect(self.refresh_list)

        self.refresh_list()
        QTimer.singleShot(500, self.startup_animation)
        # 确保初始加载时消息布局正确
        QTimer.singleShot(600, self.update_all_message_displays)

    def setup_ui(self):
        # 设置窗口背景色
        colors = self.theme_colors.get(self.current_theme_mode, self.theme_colors['dark'])
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {colors['window_bg']};
            }}
        """)
        
        self.main_widget = QFrame()
        self.main_widget.setObjectName("MainCard")
        self.main_widget.setMouseTracking(True)  # 确保子控件也开启
        self.setCentralWidget(self.main_widget)

        layout = QVBoxLayout(self.main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 分类标签栏
        category_layout = QHBoxLayout()
        category_layout.setContentsMargins(3, 3, 3, 3)  # 进一步减小边距
        category_layout.setSpacing(2)  # 进一步减小按钮间距
        
        # 创建分类按钮
        self.clipboard_btn = QPushButton()
        self.clipboard_btn.setObjectName("CategoryButton")
        self.clipboard_btn.setCheckable(True)
        self.clipboard_btn.setChecked(True)  # 默认选中剪贴板
        self.clipboard_btn.clicked.connect(lambda: self.switch_category("clipboard"))
        self.clipboard_btn.setFixedSize(24, 24)  # 统一按钮大小为24x24
        self.clipboard_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # 使用固定大小
        colors = self.theme_colors.get(self.current_theme_mode, self.theme_colors['dark'])
        clipboard_icon = self.qta.icon('fa5s.clipboard', color=colors['icon_active_color'])
        self.clipboard_btn.setIcon(clipboard_icon)
        self.clipboard_btn.setIconSize(QSize(16, 16))  # 统一图标大小为16x16
        self.clipboard_btn.setText("")  # 移除文字，只保留图标
        self.clipboard_btn.enterEvent = lambda e: self.update_category_hover(self.clipboard_btn, "clipboard", True)
        self.clipboard_btn.leaveEvent = lambda e: self.update_category_hover(self.clipboard_btn, "clipboard", False)
        # 应用按钮样式
        self.clipboard_btn.setStyleSheet(self.get_button_style("category"))
        
        self.image_btn = QPushButton()
        self.image_btn.setObjectName("CategoryButton")
        self.image_btn.setCheckable(True)
        self.image_btn.clicked.connect(lambda: self.switch_category("image"))
        self.image_btn.setFixedSize(24, 24)  # 统一按钮大小为24x24
        self.image_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # 使用固定大小
        colors = self.theme_colors.get(self.current_theme_mode, self.theme_colors['dark'])
        image_icon = self.qta.icon('fa5s.image', color=colors['icon_color'])
        self.image_btn.setIcon(image_icon)
        self.image_btn.setIconSize(QSize(16, 16))  # 统一图标大小为16x16
        self.image_btn.setText("")  # 移除文字，只保留图标
        self.image_btn.enterEvent = lambda e: self.update_category_hover(self.image_btn, "image", True)
        self.image_btn.leaveEvent = lambda e: self.update_category_hover(self.image_btn, "image", False)
        # 应用按钮样式
        self.image_btn.setStyleSheet(self.get_button_style("category"))
        
        self.file_btn = QPushButton()
        self.file_btn.setObjectName("CategoryButton")
        self.file_btn.setCheckable(True)
        self.file_btn.clicked.connect(lambda: self.switch_category("file"))
        self.file_btn.setFixedSize(24, 24)  # 统一按钮大小为24x24
        self.file_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # 使用固定大小
        colors = self.theme_colors.get(self.current_theme_mode, self.theme_colors['dark'])
        file_icon = self.qta.icon('fa5s.file', color=colors['icon_color'])
        self.file_btn.setIcon(file_icon)
        self.file_btn.setIconSize(QSize(16, 16))  # 统一图标大小为16x16
        self.file_btn.setText("")  # 移除文字，只保留图标
        self.file_btn.enterEvent = lambda e: self.update_category_hover(self.file_btn, "file", True)
        self.file_btn.leaveEvent = lambda e: self.update_category_hover(self.file_btn, "file", False)
        # 应用按钮样式
        self.file_btn.setStyleSheet(self.get_button_style("category"))
        
        self.notebook_btn = QPushButton()
        self.notebook_btn.setObjectName("CategoryButton")
        self.notebook_btn.setCheckable(True)
        self.notebook_btn.clicked.connect(lambda: self.switch_category("notebook"))
        self.notebook_btn.setFixedSize(24, 24)  # 统一按钮大小为24x24
        self.notebook_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # 使用固定大小
        colors = self.theme_colors.get(self.current_theme_mode, self.theme_colors['dark'])
        notebook_icon = self.qta.icon('fa5s.book', color=colors['icon_color'])
        self.notebook_btn.setIcon(notebook_icon)
        self.notebook_btn.setIconSize(QSize(16, 16))  # 统一图标大小为16x16
        self.notebook_btn.setText("")  # 只保留图标，不显示文字
        self.notebook_btn.enterEvent = lambda e: self.update_category_hover(self.notebook_btn, "notebook", True)
        self.notebook_btn.leaveEvent = lambda e: self.update_category_hover(self.notebook_btn, "notebook", False)
        # 应用按钮样式
        self.notebook_btn.setStyleSheet(self.get_button_style("category"))
        
        self.favorite_btn = QPushButton()
        self.favorite_btn.setObjectName("CategoryButton")
        self.favorite_btn.setCheckable(True)
        self.favorite_btn.clicked.connect(lambda: self.switch_category("favorite"))
        self.favorite_btn.setFixedSize(24, 24)  # 统一按钮大小为24x24
        self.favorite_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # 使用固定大小
        colors = self.theme_colors.get(self.current_theme_mode, self.theme_colors['dark'])
        favorite_icon = self.qta.icon('fa5s.star', color=colors['icon_color'])
        self.favorite_btn.setIcon(favorite_icon)
        self.favorite_btn.setIconSize(QSize(16, 16))  # 统一图标大小为16x16
        self.favorite_btn.setText("")  # 移除文字，只保留图标
        self.favorite_btn.enterEvent = lambda e: self.update_category_hover(self.favorite_btn, "favorite", True)
        self.favorite_btn.leaveEvent = lambda e: self.update_category_hover(self.favorite_btn, "favorite", False)
        # 应用按钮样式
        self.favorite_btn.setStyleSheet(self.get_button_style("category"))
        
        # 将按钮添加到布局，不使用stretch factor，让按钮自适应窗口宽度
        category_layout.addWidget(self.clipboard_btn)
        category_layout.addWidget(self.image_btn)
        category_layout.addWidget(self.file_btn)
        category_layout.addWidget(self.favorite_btn)
        category_layout.addWidget(self.notebook_btn)  # 将记事本按钮移到收藏后面
        
        # 创建分类标签容器
        self.category_widget = QWidget()
        self.category_widget.setObjectName("CategoryWidget")
        self.category_widget.setLayout(category_layout)
        self.category_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(self.category_widget)

        # 消息滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setObjectName("MessageScrollArea")
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
                padding-right: 5px;  /* 添加右边距，让滚动条与窗口边框有一定距离 */
            }
            QScrollBar:vertical {
                background-color: transparent;
                width: 10px;
                border-radius: 5px;
                margin-top: 0px;
                margin-bottom: 0px;  /* 移除底部边距，让滚动条更贴近内容 */
            }
            QScrollBar::handle:vertical {
                background-color: #c0c0c0;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #a0a0a0;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # 添加自定义滚动条
        self.custom_scrollbar = CustomScrollBar(theme_colors=self.theme_colors, current_theme_mode=self.current_theme_mode)
        self.custom_scrollbar.valueChanged.connect(self.on_scroll_value_changed)
        self.scroll_area.setVerticalScrollBar(self.custom_scrollbar)
        
        # 消息容器
        self.message_container = QWidget()
        self.message_container.setObjectName("MessageContainer")
        self.message_container.setStyleSheet("""
            #MessageContainer {
                background-color: transparent;
                /* 移除自定义圆角 */
                margin-right: 0px;  /* 完全移除右边距，让滚动条紧贴内容 */
            }
        """)
        self.message_layout = QVBoxLayout(self.message_container)
        self.message_layout.setContentsMargins(5, 5, 1, 5)  # 右边距设为1px，让滚动条与内容几乎紧贴
        self.message_layout.setSpacing(5)
        
        # 添加记录数量显示标签
        self.record_count_label = QLabel()
        self.record_count_label.setAlignment(Qt.AlignCenter)
        self.record_count_label.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 11px;
                padding: 5px;
                background-color: transparent;
            }
        """)
        self.message_layout.addWidget(self.record_count_label)
        
        # 添加"加载更多"按钮
        self.load_more_btn = QPushButton(self.language_manager.get_text("load_more"))
        self.load_more_btn.setFixedHeight(35)
        self.load_more_btn.setCursor(Qt.PointingHandCursor)
        self.load_more_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A90E2;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
                margin: 5px 10px;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
            QPushButton:pressed {
                background-color: #2A6496;
            }
        """)
        self.load_more_btn.clicked.connect(self.load_all_records)
        self.load_more_btn.hide()  # 初始隐藏
        self.message_layout.addWidget(self.load_more_btn)
        
        self.message_layout.addStretch()  # 添加弹性空间，使消息从底部开始显示
        
        self.scroll_area.setWidget(self.message_container)
        layout.addWidget(self.scroll_area)
        
        # 日期搜索悬浮框（初始隐藏）
        self.date_search_widget = QWidget(self)
        self.date_search_widget.setObjectName("DateSearchWidget")
        self.date_search_widget.hide()  # 初始隐藏
        # 获取当前主题颜色并设置样式，圆角效果
        colors = self.theme_colors.get(self.current_theme_mode, self.theme_colors['dark'])
        self.date_search_widget.setStyleSheet(f"""
            QWidget#DateSearchWidget {{
                background-color: {colors['window_bg']};
                border-radius: 18px;
                border: 1px solid {colors['border_color']};
            }}
        """)
        
        # 分类按钮提示框（初始隐藏）
        self.category_tooltip = QWidget(self)
        self.category_tooltip.setObjectName("CategoryTooltip")
        self.category_tooltip.hide()  # 初始隐藏
        # 设置样式，参考日期搜索框
        self.category_tooltip.setStyleSheet("""
            QWidget#CategoryTooltip {
                background-color: rgba(0, 0, 0, 200);
                border-radius: 8px;
                border: none;
                padding: 4px 8px;
            }
        """)
        
        # 提示框标签
        self.tooltip_label = QLabel(self.category_tooltip)
        self.tooltip_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 12px;
                font-weight: bold;
                background-color: transparent;
                padding: 0px;
            }
        """)
        
        tooltip_layout = QHBoxLayout(self.category_tooltip)
        tooltip_layout.setContentsMargins(6, 4, 6, 4)
        tooltip_layout.addWidget(self.tooltip_label)
        
        # 悬浮计时器
        self.hover_timer = QTimer()
        self.hover_timer.setSingleShot(True)  # 只触发一次
        self.hover_timer.timeout.connect(self.show_category_tooltip)
        
        # 当前悬浮的按钮信息
        self.current_hover_button = None
        self.current_hover_category = None
        self.current_hover_tooltip_text = None
        
        date_search_layout = QHBoxLayout(self.date_search_widget)
        date_search_layout.setContentsMargins(8, 6, 8, 6)
        date_search_layout.setSpacing(5)
        
        # 日期输入框
        self.date_input = QLineEdit()
        self.date_input.setPlaceholderText(self.language_manager.get_text("placeholder_date"))
        self.date_input.setObjectName("DateInput")
        # 应用搜索框样式，包括字体大小，使用透明背景
        self.date_input.setStyleSheet(self.get_search_input_style(transparent=True))
        # 在日期输入框左侧添加日历图标
        colors = self.theme_colors.get(self.current_theme_mode, self.theme_colors['dark'])
        date_action = self.date_input.addAction(self.qta.icon('fa5s.calendar', color=colors['icon_color']), QLineEdit.LeadingPosition)
        # 在日期输入框右侧添加搜索图标按钮
        self.date_search_action = self.date_input.addAction(self.qta.icon('fa5s.search', color=colors['icon_color']), QLineEdit.TrailingPosition)
        # 连接搜索动作的点击事件
        self.date_search_action.triggered.connect(self.perform_date_search)
        # 连接文本变化和回车事件
        self.date_input.textChanged.connect(self.on_date_input_changed)
        self.date_input.returnPressed.connect(self.perform_date_search)
        date_search_layout.addWidget(self.date_input)
        
        # 重新应用样式，确保字体大小根据输入框高度动态调整
        self.date_input.setStyleSheet(self.get_search_input_style(transparent=True))
        
        # 底部工具栏
        bottom_toolbar = QWidget()
        bottom_toolbar.setObjectName("BottomToolbar")
        bottom_toolbar_layout = QHBoxLayout(bottom_toolbar)
        bottom_toolbar_layout.setContentsMargins(10, 5, 10, 5)
        bottom_toolbar_layout.setSpacing(5)
        
        # 搜索框
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(self.language_manager.get_text("placeholder_search"))
        self.search_box.setObjectName("SearchBox")
        # 应用搜索框样式，包括字体大小
        self.search_box.setStyleSheet(self.get_search_input_style())
        # 基于字体大小计算搜索框高度，确保文字完全显示
        # 对于中文文字，需要适当的垂直空间
        font_height = int(13 * self.ui_scale)  # 适中的字体高度计算值
        padding = int(6 * self.ui_scale)  # 减少上下内边距
        border = 2  # 边框宽度
        # 为中文文字提供适当的行高空间
        line_spacing = int(2 * self.ui_scale)
        scaled_height = font_height + (padding * 2) + border + line_spacing  # 总高度 = 字体高度 + 上下内边距 + 边框 + 行间距
        # 确保最小高度，特别是在小缩放比例时
        scaled_height = max(scaled_height, int(26 * self.ui_scale))
        self.search_box.setFixedHeight(scaled_height)
        # 设置搜索框的大小策略，让它尽可能占满空间
        self.search_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # 在搜索框左侧添加放大镜图标
        colors = self.theme_colors.get(self.current_theme_mode, self.theme_colors['dark'])
        search_action = self.search_box.addAction(self.qta.icon('fa5s.search', color=colors['icon_color']), QLineEdit.LeadingPosition)
        # 连接文本变化信号
        self.search_box.textChanged.connect(self.on_search_text_changed)
        bottom_toolbar_layout.addWidget(self.search_box)
        
        # 重新应用样式，确保字体大小根据搜索框高度动态调整
        self.search_box.setStyleSheet(self.get_search_input_style())
        
        # 减小弹性空间
        bottom_toolbar_layout.addSpacing(5)
        
        # 日期按钮
        self.date_btn = QPushButton()
        self.date_btn.setObjectName("ToolbarButton")
        self.date_btn.setFixedSize(24, 24)  # 改为与设置按钮相同的大小
        self.date_btn.setFlat(True)  # 添加扁平样式
        self.date_btn.setCursor(Qt.PointingHandCursor)  # 添加手型光标
        colors = self.theme_colors.get(self.current_theme_mode, self.theme_colors['dark'])
        date_icon = self.qta.icon('fa5s.calendar', color=colors['icon_color'])
        self.date_btn.setIcon(date_icon)
        self.date_btn.setIconSize(QSize(16, 16))  # 设置初始图标大小
        self.date_btn.enterEvent = lambda e: self.update_toolbar_hover(self.date_btn, self.language_manager.get_text("tooltip_date_filter"), True)
        self.date_btn.leaveEvent = lambda e: self.update_toolbar_hover(self.date_btn, self.language_manager.get_text("tooltip_date_filter"), False)
        self.date_btn.clicked.connect(self.toggle_date_search)  # 添加点击事件
        # 应用按钮样式
        self.date_btn.setStyleSheet(self.get_button_style("toolbar"))
        bottom_toolbar_layout.addWidget(self.date_btn)
        
        # 固定按钮
        self.pin_btn = QPushButton()
        self.pin_btn.setObjectName("ToolbarButton")
        self.pin_btn.setFixedSize(24, 24)  # 改为与设置按钮相同的大小
        self.pin_btn.setFlat(True)  # 添加扁平样式
        self.pin_btn.setCursor(Qt.PointingHandCursor)  # 添加手型光标
        colors = self.theme_colors.get(self.current_theme_mode, self.theme_colors['dark'])
        pin_icon = self.qta.icon('fa5s.thumbtack', color=colors['icon_color'])
        self.pin_btn.setIcon(pin_icon)
        self.pin_btn.setIconSize(QSize(16, 16))  # 设置初始图标大小
        self.pin_btn.enterEvent = lambda e: self.update_toolbar_hover(self.pin_btn, self.language_manager.get_text("tooltip_pin_window"), True)
        self.pin_btn.leaveEvent = lambda e: self.update_toolbar_hover(self.pin_btn, self.language_manager.get_text("tooltip_pin_window"), False)
        self.pin_btn.clicked.connect(self.toggle_pin_window)  # 添加点击事件
        self.is_pinned = False  # 跟踪窗口是否已固定
        # 应用按钮样式
        self.pin_btn.setStyleSheet(self.get_button_style("toolbar"))
        bottom_toolbar_layout.addWidget(self.pin_btn)
        
        # 设置按钮（从顶部移到底部）
        self.settings_btn = QPushButton()
        self.settings_btn.setObjectName("ToolbarButton")
        self.settings_btn.setFixedSize(24, 24)
        self.settings_btn.setFlat(True)
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        colors = self.theme_colors.get(self.current_theme_mode, self.theme_colors['dark'])
        settings_icon = self.qta.icon('fa5s.cog', color=colors['icon_color'])
        self.settings_btn.setIcon(settings_icon)
        self.settings_btn.setIconSize(QSize(16, 16))  # 设置初始图标大小
        self.settings_btn.enterEvent = lambda e: self.update_toolbar_hover(self.settings_btn, self.language_manager.get_text("tooltip_settings"), True)
        self.settings_btn.leaveEvent = lambda e: self.update_toolbar_hover(self.settings_btn, self.language_manager.get_text("tooltip_settings"), False)
        self.settings_btn.clicked.connect(self.show_settings)
        # 应用按钮样式
        self.settings_btn.setStyleSheet(self.get_button_style("toolbar"))
        bottom_toolbar_layout.addWidget(self.settings_btn)
        
        layout.addWidget(bottom_toolbar)

        # 创建悬浮的加号按钮（只在记事本页面显示）
        self.add_note_btn = QPushButton(self)
        self.add_note_btn.setObjectName("AddNoteButton")
        self.add_note_btn.setFixedSize(36, 36)  # 缩小按钮尺寸
        self.add_note_btn.setCursor(Qt.PointingHandCursor)
        self.add_note_btn.setIcon(self.qta.icon('fa5s.plus', color='#FFFFFF'))
        self.add_note_btn.setVisible(False)  # 初始隐藏，只在记事本页面显示
        self.pin_btn.setVisible(True)  # 固定按钮在所有模式下都可见
        # 设置圆形样式
        self.add_note_btn.setStyleSheet("""
            QPushButton#AddNoteButton {
                border-radius: 18px;
                background-color: #4A90E2;
                border: none;
            }
            QPushButton#AddNoteButton:hover {
                background-color: #357ABD;
            }
            QPushButton#AddNoteButton:pressed {
                background-color: #2968A8;
            }
        """)
        self.add_note_btn.clicked.connect(self.add_new_note)  # 连接添加新笔记的功能
        
        # 设置按钮位置（底部工具栏上方左侧）
        self.add_note_btn.move(20, self.height() - 120)  # 初始位置，将在窗口大小改变时更新

        self.setStyleSheet("""
            #MainCard {
                background-color: #FFFFFF;
                /* 移除自定义圆角和边框，使用Windows原生样式 */
            }
            #CategoryWidget {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
            }
            #CategoryButton {
                background-color: transparent;
                color: #888888;
                font-size: 12px;
                font-family: "Segoe UI", sans-serif;
                border: none;
                padding: 5px 10px;
                border-radius: 12px;
                min-width: 40px;
                max-width: 60px;
            }
            #CategoryButton:hover {
                background-color: #F0F0F0;
                color: #555555;
                border-radius: 12px;
            }
            #CategoryButton:checked {
                background-color: #E0E0E0;
                color: #333333;
                font-weight: bold;
                border-radius: 12px;
                padding: 4px 8px;
            }
            #BottomToolbar {
                background-color: #FFFFFF;
                border-top: 1px solid #E0E0E0;
            }
            #SearchBox {
                border: 1px solid #E0E0E0;
                border-radius: 12px;
                padding: 0 8px;
                font-size: 12px;
                color: #333333;
                background-color: #F8F8F8;
            }
            #SearchBox:focus {
                border: 1px solid #4A90E2;
                background-color: #FFFFFF;
            }
            #ToolbarButton {
                background-color: transparent;
                color: #888888;
                font-size: 12px;
                border: 1px solid #E0E0E0;
                border-radius: 12px;
                padding: 2px;
            }
            #ToolbarButton:hover {
                background-color: #F0F0F0;
                color: #555555;
                border: 1px solid #D0D0D0;
            }
            #ToolbarButton:pressed {
                background-color: #E0E0E0;
                color: #333333;
            }
            #DateSearchWidget {
                background-color: #F8F8F8;
                border-bottom: 1px solid #E0E0E0;
            }
            #DateInput {
                border: 1px solid #E0E0E0;
                border-radius: 12px;
                padding: 0 8px;
                font-size: 12px;
                color: #333333;
                background-color: #FFFFFF;
            }
            #DateInput:focus {
                border: 1px solid #4A90E2;
            }
            #DateSearchButton {
                background-color: #4A90E2;
                color: #FFFFFF;
                border: none;
                border-radius: 12px;
                font-size: 12px;
                font-weight: bold;
            }
            #DateSearchButton:hover {
                background-color: #3A80D2;
            }
            #DateSearchButton:pressed {
                background-color: #2A70C2;
            }
            #DateClearButton {
                background-color: transparent;
                color: #888888;
                border: 1px solid #E0E0E0;
                border-radius: 12px;
                padding: 2px;
            }
            #DateClearButton:hover {
                background-color: #F0F0F0;
                color: #555555;
                border: 1px solid #D0D0D0;
            }
            #DateClearButton:pressed {
                background-color: #E0E0E0;
                color: #333333;
            }
            QScrollArea {
                background-color: transparent;
                border: none;
                /* 移除自定义圆角 */
            }
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 6px;
                margin: 0px;
                margin-bottom: 12px;  /* 为右下角圆角留出空间 */
            }
            QScrollBar::handle:vertical {
                background: #CCCCCC;
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QToolTip {
                background-color: rgba(0, 0, 0, 200);
                color: white;
                padding: 5px 8px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 4)
        self.main_widget.setGraphicsEffect(shadow)

    # --- 核心修改区域 Start ---
    
    def create_temp_image_reference(self, pixmap):
        """创建临时图片引用，返回引用ID"""
        # 生成唯一ID
        reference_id = str(uuid.uuid4())
        
        # 创建临时文件
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, f"clipboard_img_{reference_id}.png")
        
        # 保存图片到临时文件
        pixmap.save(temp_file_path, "PNG")
        
        # 存储引用信息
        self.image_references[reference_id] = {
            "path": temp_file_path,
            "created_at": datetime.now().timestamp()
        }
        
        return reference_id
    
    def get_image_from_reference(self, reference_id):
        """根据引用ID获取图片"""
        if reference_id in self.image_references:
            ref_info = self.image_references[reference_id]
            if os.path.exists(ref_info["path"]):
                return QPixmap(ref_info["path"])
        return None
    
    def cleanup_temp_images(self):
        """清理过期的临时图片文件"""
        current_time = datetime.now().timestamp()
        expired_refs = []
        
        # 清理超过10分钟的图片引用
        for ref_id, ref_info in self.image_references.items():
            # 删除超过10分钟的图片
            if current_time - ref_info["created_at"] > 600:
                # 删除临时文件
                try:
                    if os.path.exists(ref_info["path"]):
                        os.remove(ref_info["path"])
                    expired_refs.append(ref_id)
                except Exception as e:
                    print(f"Error removing temp file: {e}")
        
        # 从字典中删除过期引用
        for ref_id in expired_refs:
            del self.image_references[ref_id]
        
        # 如果临时文件过多，保留最新的50个
        if len(self.image_references) > 50:
            # 按创建时间排序，删除最旧的
            sorted_refs = sorted(self.image_references.items(), key=lambda x: x[1]["created_at"])
            for ref_id, _ in sorted_refs[:-50]:  # 保留最新的50个
                try:
                    if os.path.exists(self.image_references[ref_id]["path"]):
                        os.remove(self.image_references[ref_id]["path"])
                    del self.image_references[ref_id]
                except Exception as e:
                    print(f"Error removing excess temp file: {e}")
    
    def _is_image_file(self, file_path):
        """检查文件是否是图片文件"""
        if not os.path.exists(file_path):
            return False
            
        # 检查文件扩展名
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico']
        if any(file_path.lower().endswith(ext) for ext in image_extensions):
            return True
            
        # 尝试加载文件判断是否是图片
        try:
            pixmap = QPixmap(file_path)
            return not pixmap.isNull()
        except:
            return False
    
    def _try_get_image_source(self):
        """尝试获取图片来源路径"""
        import win32clipboard
        import win32con
        
        try:
            # 打开剪贴板
            win32clipboard.OpenClipboard()
            
            # 1. 首先尝试获取文件路径（最常见的情况）
            if win32clipboard.IsClipboardFormatAvailable(win32con.CF_HDROP):
                files = win32clipboard.GetClipboardData(win32con.CF_HDROP)
                if files and len(files) > 0:
                    # 返回第一个文件路径
                    file_path = files[0]
                    # 验证文件是否存在且是图片
                    if os.path.exists(file_path) and self._is_image_file(file_path):
                        return file_path
            
            # 2. 尝试获取文本格式的路径
            formats = [win32con.CF_UNICODETEXT, win32con.CF_TEXT]
            for fmt in formats:
                if win32clipboard.IsClipboardFormatAvailable(fmt):
                    data = win32clipboard.GetClipboardData(fmt)
                    if data:
                        # 检查是否是有效的文件路径
                        if os.path.exists(data) and self._is_image_file(data):
                            return data
                        # 检查是否是URL格式的文件路径
                        if data.startswith('file://') or data.startswith('File://'):
                            import urllib.parse
                            file_path = urllib.parse.unquote(data[8:])  # 去掉file://前缀
                            if os.path.exists(file_path) and self._is_image_file(file_path):
                                return file_path
            
            # 3. 尝试检查其他可能包含路径信息的格式
            # 检查HTML格式（可能包含img标签）
            if win32clipboard.IsClipboardFormatAvailable(win32con.CF_HTML):
                try:
                    html_data = win32clipboard.GetClipboardData(win32con.CF_HTML)
                    if html_data:
                        # 简单的HTML解析，查找img标签的src属性
                        import re
                        img_matches = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html_data, re.IGNORECASE)
                        for src in img_matches:
                            if src.startswith('file://'):
                                import urllib.parse
                                file_path = urllib.parse.unquote(src[8:])
                                if os.path.exists(file_path) and self._is_image_file(file_path):
                                    return file_path
                except Exception as e:
                    print(f"Error parsing HTML clipboard data: {e}")
            
            win32clipboard.CloseClipboard()
        except Exception as e:
            try:
                win32clipboard.CloseClipboard()
            except:
                pass
            print(f"Error getting image source: {e}")
        
        return None

    def ignore_next_clipboard_changes(self, count=2):
        """设置忽略接下来的剪贴板变化次数，防止应用内部复制操作触发新的记录"""
        self.ignore_clipboard_changes_count = count
    
    def on_clipboard_change(self):
        """系统剪贴板变化时调用"""
        # 1. 检查标志位：如果是我们自己设置的，直接忽略，不保存
        if hasattr(self, 'ignore_clipboard_changes_count') and self.ignore_clipboard_changes_count > 0:
            self.ignore_clipboard_changes_count -= 1  # 减少计数器
            return 

        # 2. 检查剪贴板内容类型并保存
        mime_data = self.sys_clipboard.mimeData()
        
        # 检查是否有图片内容
        if mime_data.hasImage():
            # 首先检查是否有文件URL（图片文件）
            if mime_data.hasUrls():
                urls = mime_data.urls()
                if urls and urls[0].isLocalFile():
                    file_path = urls[0].toLocalFile()
                    # 检查是否是图片文件
                    if self._is_image_file(file_path):
                        # 直接保存图片文件路径
                        if self.category_manager.save_content(file_path):
                            self.debounce_refresh_list()
                        return
            
            # 如果没有文件URL，但有图片数据，进一步检查是否真的需要临时文件
            image = self.sys_clipboard.pixmap()
            if not image.isNull():
                # 尝试从剪贴板获取图片来源信息
                image_source = self._try_get_image_source()
                
                if image_source and os.path.exists(image_source):
                    # 如果能获取到有效的图片来源，保存路径
                    if self.category_manager.save_content(image_source):
                        self.debounce_refresh_list()
                else:
                    # 检查是否是重复的图片内容（避免创建多个临时文件）
                    current_image_hash = self._get_image_hash(image)
                    if hasattr(self, 'last_image_hash') and current_image_hash == self.last_image_hash:
                        # 如果是相同图片，不重复处理
                        return
                    
                    # 只有在确实无法获取图片来源且是新图片时，才创建临时引用
                    reference_id = self.create_temp_image_reference(image)
                    image_reference = f"IMG_REF:{reference_id}"
                    
                    # 记录当前图片哈希，避免重复处理
                    self.last_image_hash = current_image_hash
                    
                    # 保存图片引用
                    if self.category_manager.save_content(image_reference):
                        self.debounce_refresh_list()
        
        # 检查是否有文件路径
        elif mime_data.hasUrls():
            urls = mime_data.urls()
            if urls:
                # 只处理第一个URL
                url = urls[0]
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    # 保存文件路径
                    if self.category_manager.save_content(file_path):
                        self.debounce_refresh_list()
        # 处理文本内容
        else:
            text = self.sys_clipboard.text()
            if self.category_manager.save_content(text):
                self.debounce_refresh_list()
    
    def backup_clipboard_check(self):
        """备用剪贴板检查机制，提高监听灵敏度"""
        try:
            # 获取当前剪贴板内容的哈希值
            current_hash = self._get_clipboard_hash()
            
            # 如果哈希值发生变化，说明剪贴板内容有变化
            if current_hash != self.last_clipboard_hash:
                # 调用剪贴板变化处理方法
                self.on_clipboard_change()
            
            # 更新上次记录的哈希值
            self.last_clipboard_hash = current_hash
            
        except Exception as e:
            # 如果检查过程中出现异常，记录但不中断程序
            print(f"备用剪贴板检查异常: {e}")
    
    def _get_image_hash(self, pixmap):
        """计算图片的哈希值，用于检测重复图片"""
        try:
            import hashlib
            
            # 将QPixmap转换为QByteArray
            byte_array = QByteArray()
            buffer = QBuffer(byte_array)
            buffer.open(QBuffer.WriteOnly)
            # 使用低质量JPEG格式减小计算量
            pixmap.save(buffer, "JPEG", quality=50)
            
            # 计算哈希值
            hash_obj = hashlib.md5()
            hash_obj.update(byte_array)
            
            return hash_obj.hexdigest()
        except Exception as e:
            print(f"Error calculating image hash: {e}")
            return str(datetime.now().timestamp())
    
    def _get_clipboard_hash(self):
        """获取剪贴板内容的哈希值，用于检测变化"""
        try:
            import hashlib
            
            # 获取剪贴板MIME数据
            mime_data = self.sys_clipboard.mimeData()
            
            # 创建哈希对象
            hash_obj = hashlib.md5()
            
            # 根据不同类型的内容生成哈希
            if mime_data.hasImage():
                # 对于图片，我们不需要计算实际图片数据的哈希，只需要知道有图片即可
                # 因为应用保存的是图片路径或引用，而不是图片数据本身
                hash_obj.update(b"has_image")
            
            elif mime_data.hasUrls():
                # 对于文件URL，使用URL列表的哈希
                urls = mime_data.urls()
                url_text = "|".join([url.toString() for url in urls])
                hash_obj.update(url_text.encode('utf-8'))
            
            elif mime_data.hasText():
                # 对于文本，使用文本内容的哈希，但限制长度以提高性能
                text = mime_data.text()
                # 只取前1000个字符来计算哈希，避免处理超长文本
                text = text[:1000] if len(text) > 1000 else text
                hash_obj.update(text.encode('utf-8'))
            
            # 返回十六进制哈希值
            return hash_obj.hexdigest()
            
        except Exception as e:
            # 如果获取哈希失败，返回当前时间戳作为变化标识
            import time
            return str(time.time())

    def toggle_favorite(self, index):
        """切换指定项目的收藏状态"""
        # 获取当前项目的收藏状态
        data = self.category_manager.get_category_data()
        if 0 <= index < len(data):
            is_favorite = data[index]['favorite']
            status_text = self.language_manager.get_text("status_favorite_removed") if is_favorite else self.language_manager.get_text("status_favorite_added")
            
            # 切换收藏状态
            if self.category_manager.toggle_favorite(index):
                # 刷新列表以更新收藏状态
                self.debounce_refresh_list()
                # 显示状态变化的提示
                self.show_notification(status_text)
    
    def _hide_notification(self, notification):
        """隐藏并删除通知标签"""
        if notification:
            notification.hide()
            notification.deleteLater()
    
    def show_notification(self, message, auto_hide=True):
        """显示通知消息"""
        colors = self.theme_colors.get(self.current_theme_mode, self.theme_colors['dark'])
        
        notification = QLabel(message, self)
        notification.setStyleSheet(f"""
            QLabel {{
                background-color: {colors['card_bg']};
                color: {colors['text_color']};
                padding: 8px 12px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            }}
        """)
        notification.setAlignment(Qt.AlignCenter)
        
        # 计算居中位置
        window_width = self.width()
        window_height = self.height()
        notification_width = 150  # 预估宽度
        notification_height = 30  # 预估高度
        
        x = (window_width - notification_width) // 2
        y = (window_height - notification_height) // 2
        
        notification.setGeometry(x, y, notification_width, notification_height)
        
        # 立即显示并强制更新UI
        notification.show()
        notification.raise_()  # 确保在最上层
        notification.repaint()  # 强制立即重绘
        
        # 如果需要自动隐藏，0.8秒后自动隐藏并删除
        if auto_hide:
            QTimer.singleShot(800, lambda: self._hide_notification(notification))
        
        return notification  # 返回通知对象，以便需要时可以手动控制
    
    def _format_time(self, timestamp_str):
        """格式化时间显示，今天的只显示时间，今年的显示月日时间，非今年的显示年月日时间"""
        try:
            # 尝试解析时间戳，支持两种格式
            try:
                # 尝试解析带秒的格式
                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                # 如果失败，尝试解析不带秒的格式
                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M")
            
            now = datetime.now()
            
            # 检查是否是今天
            if timestamp.date() == now.date():
                # 今天的只显示时间
                return timestamp.strftime("%H:%M")
            # 检查是否是今年
            elif timestamp.year == now.year:
                # 今年的显示月日和时间
                return timestamp.strftime("%m-%d %H:%M")
            else:
                # 非今年的显示年月日和时间
                return timestamp.strftime("%Y-%m-%d %H:%M")
        except:
            # 如果解析失败，返回原始字符串
            return timestamp_str
    
    def show_settings(self):
        """显示设置对话框"""
        # 导入设置窗口
        from src.ui.settings import SettingsWindow
        
        # 创建并显示设置窗口
        if not hasattr(self, 'settings_window') or not self.settings_window:
            self.settings_window = SettingsWindow(parent=self)
            # 连接语言变更信号
            self.settings_window.language_changed.connect(self.on_language_changed)
            # 连接UI缩放变更信号
            self.settings_window.ui_scale_changed.connect(self.on_ui_scale_changed)
            # 连接透明度变更信号
            self.settings_window.opacity_changed.connect(self.on_opacity_changed)
            # 连接小白条设置变更信号
            self.settings_window.trigger_bar_settings_changed.connect(self.on_trigger_bar_settings_changed)
            # 连接主题变更信号
            self.settings_window.theme_changed.connect(self.on_theme_changed)
            # 连接设置窗口关闭事件，重新加载显示设置
            self.settings_window.finished.connect(self.on_settings_closed)
        
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()
    
    def on_trigger_bar_settings_changed(self):
        """处理小白条设置变更"""
        if hasattr(self, 'trigger_bar') and self.trigger_bar:
            # 更新小白条设置
            self.update_trigger_bar_settings()
            
            # 如果小白条当前可见，重新显示以应用新设置
            if self.trigger_bar.isVisible():
                # 获取当前位置
                current_position = getattr(self, 'dock_edge', 'left')
                # 重新显示小白条
                self.show_trigger_bar(current_position)
    
    def on_settings_closed(self):
        """设置窗口关闭后重新加载显示设置"""
        # 重新加载显示设置
        self.load_display_settings()
        # 应用UI缩放并保存配置
        self.apply_ui_scale(save_config=True)
        # 刷新列表以应用新的字体大小
        self.refresh_list()
    
    def on_language_changed(self, language):
        """处理语言切换事件"""
        # 更新Qt标准对话框的翻译器
        try:
            from main import update_qt_translator
            update_qt_translator(language)
        except Exception as e:
            print(f"更新Qt翻译器失败: {e}")
        
        # 更新语言管理器的语言设置
        self.language_manager.set_language(language)
        
        # 更新窗口标题
        self.setWindowTitle(self.language_manager.get_text("window_title"))
        
        # 更新搜索框占位符
        self.search_box.setPlaceholderText(self.language_manager.get_text("placeholder_search"))
        
        # 更新日期输入框占位符
        if hasattr(self, 'date_input'):
            self.date_input.setPlaceholderText(self.language_manager.get_text("placeholder_date"))
        
        # 更新分类按钮提示文本
        category_names = {
            "clipboard": self.language_manager.get_text("tooltip_clipboard"),
            "image": self.language_manager.get_text("tooltip_image"),
            "file": self.language_manager.get_text("tooltip_file"),
            "notebook": self.language_manager.get_text("tooltip_notebook"),
            "favorite": self.language_manager.get_text("tooltip_favorite")
        }
        
        # 不需要调用setToolTip，因为使用的是自定义悬浮提示系统
        # 只需要在update_toolbar_hover和update_category_hover中获取最新的翻译即可
        
        # 更新所有打开的笔记编辑窗口
        if hasattr(self, 'note_edit_windows'):
            for window in self.note_edit_windows:
                window.update_ui_language()
        
        # 刷新列表以更新消息组件的文本
        self.refresh_list()
    
    def on_ui_scale_changed(self, ui_scale):
        """处理UI缩放变更事件"""
        # 更新UI缩放值
        self.ui_scale = ui_scale
        
        # 应用UI缩放并保存配置
        self.apply_ui_scale(save_config=True)
        
        # 刷新列表以应用新的缩放
        self.refresh_list()
    
    def on_opacity_changed(self, opacity):
        """处理透明度变更事件"""
        # 设置窗口透明度
        self.setWindowOpacity(opacity)
        # 保存到配置文件
        self.save_window_config()
    
    def on_theme_changed(self, theme_mode):
        """处理主题变更事件"""
        # 应用主题样式
        self.apply_theme(theme_mode)
    
    def add_new_note(self):
        """添加新笔记"""
        # 创建笔记输入窗口
        if not hasattr(self, 'note_input_window') or not self.note_input_window:
            self.note_input_window = NoteInputWindow(self)
        
        # 获取加号按钮在主窗口中的位置
        button_rect = self.add_note_btn.geometry()
        # 计算输入窗口应该显示的位置（在按钮上方）
        x = button_rect.x() + (button_rect.width() - 300) // 2  # 居中对齐
        y = button_rect.y() - 150  # 显示在按钮上方
        
        # 确保窗口在主窗口范围内
        if x < 10:
            x = 10
        if x + 300 > self.width():
            x = self.width() - 310
        if y < 10:
            y = button_rect.y() + button_rect.height() + 10  # 如果上方空间不够，显示在下方
            
        # 相对于主窗口定位
        self.note_input_window.move(self.mapToGlobal(QPoint(x, y)))
        self.note_input_window.show()
        self.note_input_window.opacity_animation.start()
    
    def create_note_with_title(self, title):
        """根据标题创建笔记"""
        # 创建笔记编辑对话框
        dialog = NoteEditWindow({"title": title}, self.language_manager, self)
        
        # 以非模态方式显示对话框
        dialog.show()
        
        # 刷新笔记列表
        self.debounce_refresh_list()
    
    def toggle_pin_window(self):
        """切换窗口置顶状态"""
        if self.is_pinned:
            # 取消置顶
            self.is_pinned = False
            self.pin_btn.setIcon(self.qta.icon('fa5s.thumbtack', color='#333333'))
            # 使用 Windows API 取消置顶，避免闪烁
            if sys.platform == 'win32':
                import ctypes
                from ctypes import wintypes
                hwnd = int(self.winId())
                # 设置窗口不在最顶层
                ctypes.windll.user32.SetWindowPos(hwnd, -2, 0, 0, 0, 0, 0x1 | 0x2)  # HWND_NOTOPMOST = -2
            else:
                # 非Windows平台使用Qt方法
                self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
                self.show()
        else:
            # 设置置顶
            self.is_pinned = True
            self.pin_btn.setIcon(self.qta.icon('fa5s.thumbtack', color='#357ABD'))  # 使用与悬停时相同的深蓝色
            # 使用 Windows API 设置置顶，避免闪烁
            if sys.platform == 'win32':
                import ctypes
                from ctypes import wintypes
                hwnd = int(self.winId())
                # 设置窗口为最顶层
                ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x1 | 0x2)  # HWND_TOPMOST = -1
            else:
                # 非Windows平台使用Qt方法
                self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
                self.show()
    
    
    
    def on_search_text_changed(self, text):
        """搜索框文本变化时的处理"""
        # 如果文本为空，恢复显示当前分类的内容
        if not text.strip():
            self.is_searching = False
            self.search_timer.stop()
            self.refresh_list()
            return
            
        # 标记为搜索状态，并启动搜索计时器
        self.is_searching = True
        self.search_timer.start()  # 重启计时器
    
    def perform_search(self):
        """执行搜索"""
        self.search_timer.stop()  # 停止计时器
        
        query = self.search_box.text().strip()
        if not query:
            self.is_searching = False
            self.refresh_list()
            return
            
        # 获取当前选中的分类
        current_category = self.category_manager.current_category
        
        # 根据分类确定内容类型过滤器
        content_type_filter = None
        if current_category == "image":
            content_type_filter = "image"
        elif current_category == "file":
            content_type_filter = "file"
        elif current_category == "clipboard":
            content_type_filter = "text"
        elif current_category == "notebook":
            content_type_filter = "note"
        # favorite 分类不限制内容类型，但需要过滤出已收藏的
        # notebook 分类只搜索笔记内容
            
        # 初始化搜索结果列表
        search_results = []
        
        # 根据分类执行不同的搜索
        if current_category == "notebook":
            # 只搜索笔记内容
            search_results = self.backend.search_notes(query)
        else:
            # 搜索剪贴板内容
            search_results = self.backend.search_content(query, content_type_filter=content_type_filter)
            
            # 如果是favorite分类，需要进一步过滤出已收藏的结果
            if current_category == "favorite":
                search_results = [item for item in search_results if item["favorite"] and item.get("content_type") != "note"]
        
        # 清空当前消息列表，但保留 record_count_label、load_more_btn 和弹性空间
        items_to_remove = []
        for i in range(self.message_layout.count()):
            item = self.message_layout.itemAt(i)
            widget = item.widget() if item else None
            if widget and widget not in [self.record_count_label, self.load_more_btn]:
                items_to_remove.append(widget)
        for widget in items_to_remove:
            widget.deleteLater()
        
        # 隐藏记录数量标签和加载更多按钮
        self.record_count_label.hide()
        self.load_more_btn.hide()
        
        # 显示搜索结果
        for i, item in enumerate(search_results):
            # 根据内容类型选择不同的组件
            if item.get("content_type") == "note":
                # 使用笔记组件显示笔记内容
                message_widget = NoteWidget(
                    item,
                    parent=self.message_container,
                    backend=self.backend,
                    theme_colors=self.theme_colors,
                    current_theme_mode=self.current_theme_mode
                )
                # 笔记组件使用自己的toggle_favorite方法
                # 不需要额外连接，已经在NoteWidget.__init__中处理
            else:
                # 使用消息组件显示剪贴板内容
                message_widget = MessageWidget(
                    item["text"], 
                    item["time"], 
                    item["favorite"], 
                    parent=self.message_container, 
                    backend=self.backend,
                    language_manager=self.language_manager,
                    theme_colors=self.theme_colors,
                    current_theme_mode=self.current_theme_mode
                )
                # 连接收藏按钮点击事件
                message_widget.favorite_btn.clicked.connect(
                    lambda checked, idx=i: self.toggle_favorite(idx)
                )
            
            message_widget.index = i  # 设置索引，用于删除操作
            
            # 设置最大宽度约束，确保不超过滚动区域
            # 使用更保守的宽度计算，确保不会压到滚动条
            available_width = self.scroll_area.width() - 18  # 15px滚动条 + 3px边距
            message_widget.setMaximumWidth(max(200, available_width))  # 最小宽度200px
            
            # 找到 record_count_label 的位置，将消息小部件插入到它之前
            insert_index = 0
            for j in range(self.message_layout.count()):
                layout_item = self.message_layout.itemAt(j)
                if layout_item and layout_item.widget() == self.record_count_label:
                    insert_index = j
                    break
            self.message_layout.insertWidget(insert_index, message_widget)
    
    def toggle_date_search(self):
        """切换日期搜索悬浮框的显示/隐藏"""
        if self.date_search_widget.isVisible():
            # 隐藏日期搜索悬浮框
            self.date_search_widget.hide()
            # 重置日期搜索状态
            self.reset_date_search()
            # 重置日期按钮图标颜色为灰色
            self.date_btn.setIcon(self.qta.icon('fa5s.calendar', color='#333333'))
            
            # 恢复加号按钮默认位置
            if hasattr(self, 'add_note_btn'):
                self.add_note_btn.move(20, self.height() - 120)
        else:
            # 计算悬浮框位置和大小 - 占满窗口左边，留出右侧滚动条距离
            window_width = self.width()
            # 估算滚动条宽度，通常为15-20px
            scrollbar_width = 20
            # 设置悬浮框宽度为窗口宽度减去滚动条宽度和边距
            widget_width = window_width - scrollbar_width - 10  # 左右各留5px边距
            self.date_search_widget.resize(widget_width, int(36 * self.ui_scale))
            
            # 设置悬浮框位置，在底部工具栏上方
            btn_geometry = self.date_btn.geometry()
            widget_pos = self.date_btn.parentWidget().mapTo(self, btn_geometry.topLeft())
            
            # 悬浮框在日期按钮上方，左边对齐，留5px边距
            x = 5
            y = widget_pos.y() - self.date_search_widget.height() - 5  # 5px的间距
            
            self.date_search_widget.move(x, y)
            self.date_search_widget.show()  # 显示悬浮框
            self.date_input.setFocus()  # 设置焦点到输入框
            
            # 更新加号按钮位置，避免与日期筛选悬浮框重叠
            if hasattr(self, 'add_note_btn'):
                # 日期筛选框高度约为36 * ui_scale，再加上一些间距
                offset_y = int(36 * self.ui_scale) + 20  # 20px额外间距
                self.add_note_btn.move(20, self.height() - 120 - offset_y)
    
    def closeEvent(self, event):
        """窗口关闭时保存配置并清理临时文件"""
        self.save_window_config()
        
        # 停止备用剪贴板监听定时器
        if hasattr(self, 'backup_clipboard_timer'):
            self.backup_clipboard_timer.stop()
            
        # 停止悬浮提示计时器
        if hasattr(self, 'hover_timer'):
            self.hover_timer.stop()
        
        # 隐藏托盘图标
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()
        
        # 清理所有临时图片文件
        self.cleanup_all_temp_images()
        
        # 退出应用程序
        QApplication.quit()
    
    def cleanup_all_temp_images(self):
        """清理所有临时图片文件"""
        for ref_id, ref_info in self.image_references.items():
            try:
                if os.path.exists(ref_info["path"]):
                    os.remove(ref_info["path"])
            except Exception as e:
                print(f"Error removing temp file on close: {e}")
        
        # 清空引用字典
        self.image_references.clear()
    
    def moveEvent(self, event):
        """窗口移动时保存位置（非Windows平台）"""
        super().moveEvent(event)
        # 只在非Windows平台或Windows平台但不在移动状态下保存
        if sys.platform != 'win32' or not getattr(self, 'is_moving', False):
            # 使用定时器延迟保存，避免频繁保存
            if not hasattr(self, 'move_save_timer'):
                self.move_save_timer = QTimer(self)
                self.move_save_timer.setSingleShot(True)
                self.move_save_timer.timeout.connect(self.save_window_config)
            self.move_save_timer.start(500)  # 500ms后保存
    
    def on_date_input_changed(self, text):
        """处理日期输入框内容变化"""
        # 当输入框内容为空时，搜索图标变为灰色
        if text.strip():
            self.date_search_action.setIcon(self.qta.icon('fa5s.search', color='#4A90E2'))
        else:
            self.date_search_action.setIcon(self.qta.icon('fa5s.search', color='#333333'))
    

    
    def perform_date_search(self):
        """执行日期搜索"""
        date_text = self.date_input.text().strip()
        if not date_text:
            return
            
        # 解析日期输入
        parts = date_text.split()
        year = None
        month = None
        day = None
        
        try:
            if len(parts) >= 1:
                year = int(parts[0])
            if len(parts) >= 2:
                month = int(parts[1])
            if len(parts) >= 3:
                day = int(parts[2])
        except ValueError:
            # 如果输入不是有效的数字，显示错误提示
            self.show_notification(self.language_manager.get_text("status_invalid_date"))
            return
        
        # 标记为日期搜索状态
        self.is_date_searching = True
        
        # 获取当前选中的分类
        current_category = self.category_manager.current_category
        
        # 根据分类确定内容类型过滤器
        content_type_filter = None
        if current_category == "image":
            content_type_filter = "image"
        elif current_category == "file":
            content_type_filter = "file"
        elif current_category == "clipboard":
            content_type_filter = "text"
        # favorite 分类不限制内容类型，但需要过滤出已收藏的
        
        # 调用后端日期搜索方法
        search_results = self.backend.search_by_date(year, month, day, content_type_filter=content_type_filter)
        
        # 如果是favorite分类，需要进一步过滤出已收藏的结果
        if current_category == "favorite":
            search_results = [item for item in search_results if item["favorite"] and item.get("content_type") != "note"]
        
        # 清空当前消息列表，但保留 record_count_label、load_more_btn 和弹性空间
        items_to_remove = []
        for i in range(self.message_layout.count()):
            item = self.message_layout.itemAt(i)
            widget = item.widget() if item else None
            if widget and widget not in [self.record_count_label, self.load_more_btn]:
                items_to_remove.append(widget)
        for widget in items_to_remove:
            widget.deleteLater()
        
        # 隐藏记录数量标签和加载更多按钮
        self.record_count_label.hide()
        self.load_more_btn.hide()
        
        # 显示搜索结果
        for i, item in enumerate(search_results):
            message_widget = MessageWidget(
                item["text"], 
                item["time"], 
                item["favorite"], 
                parent=self.message_container, 
                backend=self.backend,
                language_manager=self.language_manager,
                theme_colors=self.theme_colors,
                current_theme_mode=self.current_theme_mode
            )
            message_widget.index = i  # 设置索引，用于删除操作
            
            # 设置最大宽度约束，确保不超过滚动区域
            available_width = self.scroll_area.width() - 15  # 10px滚动条 + 5px边距
            message_widget.setMaximumWidth(max(200, available_width))  # 最小宽度200px
            
            # 连接收藏按钮点击事件
            message_widget.favorite_btn.clicked.connect(
                lambda checked, idx=i: self.toggle_favorite(idx)
            )
            
            # 找到 record_count_label 的位置，将消息小部件插入到它之前
            insert_index = 0
            for j in range(self.message_layout.count()):
                layout_item = self.message_layout.itemAt(j)
                if layout_item and layout_item.widget() == self.record_count_label:
                    insert_index = j
                    break
            self.message_layout.insertWidget(insert_index, message_widget)
    
    def reset_date_search(self):
        """重置日期搜索状态"""
        # 清空日期输入框
        self.date_input.clear()
        # 重置搜索图标颜色
        self.date_search_action.setIcon(self.qta.icon('fa5s.search', color='#333333'))
        # 如果当前是日期搜索状态，恢复到正常显示
        if hasattr(self, 'is_date_searching') and self.is_date_searching:
            self.is_date_searching = False
            self.refresh_list()
    
    def toggle_favorite(self, index):
        """切换收藏状态"""
        if self.is_searching:
            # 搜索状态下，需要特殊处理索引
            # 先获取当前搜索结果
            query = self.search_box.text().strip()
            search_results = self.backend.search_content(query)
            if index < len(search_results):
                # 获取原始记录的ID
                # 这里需要通过内容找到原始记录的ID
                content = search_results[index]["text"]
                conn = sqlite3.connect(self.backend.db_name)
                c = conn.cursor()
                c.execute("SELECT id FROM history ORDER BY id DESC")
                all_ids = c.fetchall()
                conn.close()
                
                # 找到匹配的记录ID
                for i, record_id in enumerate(all_ids):
                    # 获取该记录的内容
                    record = self.backend.get_history(limit=len(all_ids))[i]
                    if record["text"] == content:
                        # 切换收藏状态
                        self.backend.toggle_favorite(i)
                        # 刷新搜索结果
                        self.perform_search()
                        break
        else:
            # 非搜索状态，使用原有逻辑
            self.backend.toggle_favorite(index)
            self.debounce_refresh_list()
    
    def open_content_viewer(self, text):
        """打开自定义文本编辑器查看内容"""
        from core.category import CategoryManager
        
        # 创建临时分类管理器实例用于检测内容类型
        temp_category_manager = CategoryManager(self.backend)
        content_type = temp_category_manager._detect_content_type(text)
        
        try:
            if content_type == "image":
                # 图片内容仍使用系统默认查看器
                import tempfile
                import os
                import subprocess
                
                # 创建临时文件
                with tempfile.NamedTemporaryFile(delete=False, suffix=self._get_file_extension(text, content_type)) as temp_file:
                    # 处理base64图片
                    import base64
                    header, data = text.split(',', 1)
                    temp_file.write(base64.b64decode(data))
                    temp_file_path = temp_file.name
                
                # 使用系统默认程序打开图片
                if os.name == 'nt':  # Windows
                    os.startfile(temp_file_path)
                elif os.name == 'posix':  # macOS 和 Linux
                    if subprocess.call(['which', 'xdg-open']) == 0:  # Linux
                        subprocess.call(['xdg-open', temp_file_path])
                    else:  # macOS
                        subprocess.call(['open', temp_file_path])
                
                # 设置定时器，延迟删除临时文件
                QTimer.singleShot(60000, lambda: self._delete_temp_file(temp_file_path))
            else:
                # 文本内容使用自定义编辑器
                from ui.text_editor import NoteEditWindow
                
                # 创建一个包含文本内容的笔记数据对象
                note_data = {
                    "title": self.language_manager.get_text("view_clipboard_content"),
                    "content": text,
                    "text": text  # 兼容性字段
                }
                
                # 创建并显示文本编辑窗口
                editor_window = NoteEditWindow(note_data, self.language_manager, self)
                editor_window.show()
            
        except Exception as e:
            print(f"无法打开内容查看器: {e}")
    
    def _get_file_extension(self, text, content_type):
        """根据内容类型获取文件扩展名"""
        import os
        
        if content_type == "image":
            if text.startswith('data:image/'):
                # 从data URL中提取图片格式
                if 'png' in text.split(';')[0]:
                    return '.png'
                elif 'jpeg' in text.split(';')[0] or 'jpg' in text.split(';')[0]:
                    return '.jpg'
                elif 'gif' in text.split(';')[0]:
                    return '.gif'
                elif 'bmp' in text.split(';')[0]:
                    return '.bmp'
                elif 'svg' in text.split(';')[0]:
                    return '.svg'
                elif 'webp' in text.split(';')[0]:
                    return '.webp'
                else:
                    return '.png'  # 默认为png
            else:
                # 从文件路径中提取扩展名
                if '.' in text:
                    return os.path.splitext(text)[1]
                return '.png'  # 默认为png
        elif content_type == "file":
            # 从文件路径中提取扩展名
            if '.' in text:
                return os.path.splitext(text)[1]
            return '.txt'  # 默认为txt
        else:
            return '.txt'  # 默认为txt
    
    def open_image_viewer(self, text):
        """打开系统默认图片查看器"""
        import tempfile
        import os
        import subprocess
        
        try:
            # 首先检查是否是文件路径
            if os.path.isfile(text):
                # 如果是有效的文件路径，直接使用该文件
                image_path = text
            else:
                # 处理base64图片
                import base64
                
                # 检查是否是有效的base64图片格式
                if text.startswith('data:image/') and ';base64,' in text:
                    header, data = text.split(',', 1)
                    
                    # 创建临时文件
                    with tempfile.NamedTemporaryFile(delete=False, suffix=self._get_file_extension(text, "image")) as temp_file:
                        temp_file.write(base64.b64decode(data))
                        image_path = temp_file.name
                else:
                    # 如果不是base64格式也不是文件路径，尝试作为路径处理
                    image_path = text
                    if not os.path.exists(image_path):
                        print(f"图片路径不存在: {image_path}")
                        return
            
            # 使用系统默认程序打开图片
            if os.name == 'nt':  # Windows
                os.startfile(image_path)
            elif os.name == 'posix':  # macOS 和 Linux
                if subprocess.call(['which', 'xdg-open']) == 0:  # Linux
                    subprocess.call(['xdg-open', image_path])
                else:  # macOS
                    subprocess.call(['open', image_path])
            
            # 如果是临时文件，设置定时器删除
            if not os.path.isfile(text) and text.startswith('data:image/'):
                QTimer.singleShot(60000, lambda: self._delete_temp_file(image_path))
            
        except Exception as e:
            print(f"无法打开图片查看器: {e}")
    
    def _delete_temp_file(self, file_path):
        """删除临时文件"""
        import os
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f"删除临时文件失败: {e}")

    # --- 核心修改区域 End ---

    def add_message(self, text, time, is_favorite=False, index=None, content_type="text"):
        """添加新消息到界面"""
        message_widget = MessageWidget(text, time, is_favorite, parent=self.message_container, backend=self.backend, language_manager=self.language_manager, theme_colors=self.theme_colors, current_theme_mode=self.current_theme_mode)
        # 设置消息框的大小策略，确保能够根据内容自适应高度和宽度
        message_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        # 设置最大宽度约束，确保不超过滚动区域
        available_width = self.scroll_area.width() - 18  # 15px滚动条 + 3px边距
        message_widget.setMaximumWidth(max(200, available_width))  # 最小宽度200px
        
        # 设置消息索引
        message_widget.index = index
        
        # 连接收藏按钮的点击事件
        if index is not None:
            message_widget.favorite_btn.clicked.connect(
                lambda checked, idx=index: self.toggle_favorite(idx)
            )
        
        # 找到 record_count_label 的位置，将消息小部件插入到它之前
        insert_index = 0
        for i in range(self.message_layout.count()):
            item = self.message_layout.itemAt(i)
            if item and item.widget() == self.record_count_label:
                insert_index = i
                break
        self.message_layout.insertWidget(insert_index, message_widget)
        return message_widget
    
    def debounce_refresh_list(self):
        """防抖刷新列表，避免频繁更新"""
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()
            self.refresh_timer.start(300)  # 300ms后执行刷新
    
    def refresh_list(self):
        """清除现有消息小部件（保留记录数量标签、加载更多按钮和弹性空间）"""
        # 从后往前遍历，删除消息小部件，但保留 record_count_label、load_more_btn 和弹性空间
        items_to_remove = []
        for i in range(self.message_layout.count()):
            item = self.message_layout.itemAt(i)
            widget = item.widget() if item else None
            # 保留 record_count_label、load_more_btn 和弹簧(spacer)
            if widget and widget not in [self.record_count_label, self.load_more_btn]:
                items_to_remove.append(widget)
            elif item and item.spacerItem():
                # 保留弹簧
                pass
        
        # 删除消息小部件
        for widget in items_to_remove:
            widget.deleteLater()
        
        # 获取当前分类的数据
        data = self.category_manager.get_category_data()
        
        # 获取总记录数
        total_count = self.category_manager.get_total_count()
        displayed_count = len(data)
        
        # 更新记录数量显示
        if hasattr(self, 'record_count_label') and self.record_count_label is not None:
            try:
                if not self.category_manager.show_all and total_count > 500:
                    self.record_count_label.setText(
                        self.language_manager.get_text("show_limited_records").format(count=displayed_count) + 
                        " | " + self.language_manager.get_text("total_records").format(total=total_count)
                    )
                    self.record_count_label.show()
                else:
                    self.record_count_label.setText(
                        self.language_manager.get_text("total_records").format(total=total_count)
                    )
                    self.record_count_label.show()
            except RuntimeError:
                pass  # 对象已被删除，忽略
        
        # 更新"加载更多"按钮的可见性
        if hasattr(self, 'load_more_btn') and self.load_more_btn is not None:
            try:
                if not self.category_manager.show_all and total_count > 500:
                    self.load_more_btn.show()
                else:
                    self.load_more_btn.hide()
            except RuntimeError:
                pass  # 对象已被删除，忽略
        
        # 创建消息小部件并添加到布局中（倒序插入，使最新消息在底部）
        for i, item in enumerate(data):
            # 检查是否是笔记类型
            if item.get('content_type') == 'note':
                self.add_note_widget(
                    note_data=item,
                    index=i
                )
            else:
                self.add_message(
                    text=item['text'],
                    time=self._format_time(item['time']),  # 使用格式化后的时间
                    is_favorite=item['favorite'],
                    index=i,
                    content_type=item.get('content_type', 'text')
                )
        
        # 应用字体大小设置到所有消息项
        self.update_message_font_size()
    
    def load_all_records(self):
        """加载全部记录"""
        self.category_manager.set_show_all(True)
        self.load_more_btn.hide()
        self.refresh_list()
    
    def add_note_widget(self, note_data, index):
        """添加笔记小部件到消息列表"""
        # 使用格式化后的时间
        formatted_time = self._format_time(note_data.get('created_at') or note_data.get('time', ''))
        note_widget = NoteWidget(note_data, self.message_container, self.backend, formatted_time, theme_colors=self.theme_colors, current_theme_mode=self.current_theme_mode)
        note_widget.index = index  # 设置索引，用于删除操作
        
        # 设置笔记小部件的大小策略，确保能够根据内容自适应高度和宽度
        note_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        # 设置最大宽度约束，确保不超过滚动区域
        # 使用更保守的宽度计算，确保不会压到滚动条
        available_width = self.scroll_area.width() - 18  # 15px滚动条 + 3px边距
        note_widget.setMaximumWidth(max(200, available_width))  # 最小宽度200px
        
        # 找到 record_count_label 的位置，将笔记小部件插入到它之前
        insert_index = 0
        for i in range(self.message_layout.count()):
            item = self.message_layout.itemAt(i)
            if item and item.widget() == self.record_count_label:
                insert_index = i
                break
        self.message_layout.insertWidget(insert_index, note_widget)
        
        # 为笔记小部件添加右键菜单
        note_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        note_widget.customContextMenuRequested.connect(lambda pos: self.show_note_context_menu(pos, note_widget))
    
    def show_note_context_menu(self, pos, note_widget):
        """显示笔记右键菜单"""
        context_menu = QMenu(self)
        
        # 删除笔记
        delete_action = context_menu.addAction(self.language_manager.get_text("delete_note"))
        delete_action.triggered.connect(lambda: self.delete_note_by_index(note_widget.index))
        
        context_menu.exec_(note_widget.mapToGlobal(pos))
    
    def edit_note(self, note_widget):
        """编辑笔记"""
        # 创建编辑对话框
        dialog = NoteEditWindow(note_widget.note_data, self.language_manager, self)
        
        # 保存对话框引用，以便在语言切换时更新
        if not hasattr(self, 'note_edit_windows'):
            self.note_edit_windows = []
        self.note_edit_windows.append(dialog)
        
        # 连接对话框关闭事件，从列表中移除
        dialog.finished.connect(lambda: self.note_edit_windows.remove(dialog) if dialog in self.note_edit_windows else None)
        
        # 以非模态方式显示对话框
        dialog.show()
    
    def delete_note_by_index(self, index):
        """根据索引删除笔记"""
        try:
            # 通过分类管理器删除笔记
            success = self.category_manager.delete_item(index)
            if success:
                # 刷新列表显示
                self.debounce_refresh_list()
                # 显示删除成功的提示
                self.show_notification(self.language_manager.get_text("status_delete_success"))
            else:
                self.show_notification(self.language_manager.get_text("status_delete_failed"))
        except Exception as e:
            print(f"删除笔记时出错: {e}")
            self.show_notification(self.language_manager.get_text("status_delete_failed"))
    
    def delete_message_by_index(self, index):
        """根据索引删除消息"""
        try:
            # 通过分类管理器删除消息
            success = self.category_manager.delete_item(index)
            if success:
                # 刷新列表显示
                self.debounce_refresh_list()
                # 显示删除成功的提示
                self.show_notification(self.language_manager.get_text("status_delete_success"))
            else:
                self.show_notification(self.language_manager.get_text("status_delete_failed"))
        except Exception as e:
            print(f"删除消息时出错: {e}")
            self.show_notification(self.language_manager.get_text("status_delete_failed"))
    
    def batch_delete_by_time(self, time_range):
        """根据时间范围批量删除记录
        
        Args:
            time_range: 时间范围，可选值: 'today', '7days', '30days', 'all'
        """
        try:
            # 通过分类管理器批量删除
            deleted_count = self.category_manager.batch_delete_by_time(time_range)
            
            # 刷新列表显示
            self.debounce_refresh_list()
            
            # 显示删除成功的提示
            if deleted_count > 0:
                self.show_notification(f"已删除 {deleted_count} 条记录")
            else:
                self.show_notification("没有找到符合条件的记录")
        except Exception as e:
            print(f"批量删除时出错: {e}")
            self.show_notification("删除失败")
    
    def update_category_hover(self, button, category, is_hovering):
        """更新分类按钮悬停状态"""
        colors = self.theme_colors.get(self.current_theme_mode, self.theme_colors['dark'])
        # 获取当前选中的分类
        current_category = self.category_manager.current_category
        
        # 根据是否悬停更新图标颜色
        if is_hovering:
            # 如果是当前选中的分类，不改变颜色
            if current_category != category:
                # 悬停时使用深色
                if category == "clipboard":
                    button.setIcon(self.qta.icon('fa5s.clipboard', color=colors['icon_hover_color']))
                elif category == "image":
                    button.setIcon(self.qta.icon('fa5s.image', color=colors['icon_hover_color']))
                elif category == "file":
                    button.setIcon(self.qta.icon('fa5s.file', color=colors['icon_hover_color']))
                elif category == "notebook":
                    button.setIcon(self.qta.icon('fa5s.book', color=colors['icon_hover_color']))
                elif category == "favorite":
                    button.setIcon(self.qta.icon('fa5s.star', color=colors['icon_hover_color']))
                
            # 设置当前悬浮的按钮信息
            self.current_hover_button = button
            self.current_hover_category = category
            
            # 启动悬浮计时器，2秒后显示提示框
            self.hover_timer.start(2000)  # 2000毫秒 = 2秒
        else:
            # 如果是当前选中的分类，不改变颜色
            if current_category != category:
                # 非悬停时恢复默认颜色
                if category == "clipboard":
                    button.setIcon(self.qta.icon('fa5s.clipboard', color=colors['icon_color']))
                elif category == "image":
                    button.setIcon(self.qta.icon('fa5s.image', color=colors['icon_color']))
                elif category == "file":
                    button.setIcon(self.qta.icon('fa5s.file', color=colors['icon_color']))
                elif category == "notebook":
                    button.setIcon(self.qta.icon('fa5s.book', color=colors['icon_color']))
                elif category == "favorite":
                    button.setIcon(self.qta.icon('fa5s.star', color=colors['icon_color']))
                
            # 停止计时器并隐藏提示框
            self.hover_timer.stop()
            self.category_tooltip.hide()
            self.current_hover_button = None
            self.current_hover_category = None
    
    def update_toolbar_hover(self, button, tooltip_text, is_hovering):
        """更新工具栏按钮悬停状态"""
        colors = self.theme_colors.get(self.current_theme_mode, self.theme_colors['dark'])
        # 根据是否悬停更新图标颜色
        if is_hovering:
            # 悬停时使用深色
            if button == self.date_btn:
                # 如果日期搜索悬浮框可见，保持蓝色图标
                if self.date_search_widget.isVisible():
                    button.setIcon(self.qta.icon('fa5s.calendar', color=colors['icon_active_color']))
                else:
                    button.setIcon(self.qta.icon('fa5s.calendar', color=colors['icon_hover_color']))
            elif button == self.pin_btn:
                # 悬停时根据是否已固定使用不同颜色
                if self.is_pinned:
                    button.setIcon(self.qta.icon('fa5s.thumbtack', color=colors['icon_active_color']))
                else:
                    button.setIcon(self.qta.icon('fa5s.thumbtack', color=colors['icon_hover_color']))
            elif button == self.settings_btn:
                button.setIcon(self.qta.icon('fa5s.cog', color=colors['icon_hover_color']))
                
            # 设置当前悬浮的按钮信息
            self.current_hover_button = button
            self.current_hover_tooltip_text = tooltip_text
            
            # 启动悬浮计时器，2秒后显示提示框
            self.hover_timer.start(2000)  # 2000毫秒 = 2秒
        else:
            # 非悬停时恢复默认颜色
            if button == self.date_btn:
                # 如果日期搜索悬浮框可见，保持蓝色图标
                if self.date_search_widget.isVisible():
                    button.setIcon(self.qta.icon('fa5s.calendar', color=colors['icon_active_color']))
                else:
                    button.setIcon(self.qta.icon('fa5s.calendar', color=colors['icon_color']))
            elif button == self.pin_btn:
                # 非悬停时根据是否已固定使用不同颜色
                if self.is_pinned:
                    button.setIcon(self.qta.icon('fa5s.thumbtack', color=colors['icon_active_color']))
                else:
                    button.setIcon(self.qta.icon('fa5s.thumbtack', color=colors['icon_color']))
            elif button == self.settings_btn:
                button.setIcon(self.qta.icon('fa5s.cog', color=colors['icon_color']))
                
            # 停止计时器并隐藏提示框
            self.hover_timer.stop()
            self.category_tooltip.hide()
            self.current_hover_button = None
            self.current_hover_tooltip_text = None
    
    def show_category_tooltip(self):
        """显示分类按钮或工具栏按钮提示框"""
        if not self.current_hover_button:
            return
            
        # 设置提示文本
        if hasattr(self, 'current_hover_category') and self.current_hover_category:
            # 分类按钮的提示文本
            category_names = {
                "clipboard": self.language_manager.get_text("tooltip_clipboard"),
                "image": self.language_manager.get_text("tooltip_image"),
                "file": self.language_manager.get_text("tooltip_file"),
                "notebook": self.language_manager.get_text("tooltip_notebook"),
                "favorite": self.language_manager.get_text("tooltip_favorite")
            }
            tooltip_text = category_names.get(self.current_hover_category, "")
        elif hasattr(self, 'current_hover_tooltip_text') and self.current_hover_tooltip_text:
            # 工具栏按钮的提示文本
            tooltip_text = self.current_hover_tooltip_text
        else:
            return
            
        self.tooltip_label.setText(tooltip_text)
        
        # 调整提示框大小
        self.category_tooltip.adjustSize()
        
        # 计算提示框位置
        button_geometry = self.current_hover_button.geometry()
        button_pos = self.current_hover_button.parentWidget().mapTo(self, button_geometry.topLeft())
        
        # 判断是否为工具栏按钮（在底部）
        is_toolbar_button = self.current_hover_button in [self.date_btn, self.pin_btn, self.settings_btn]
        
        # 如果是置顶按钮但不在记事本模式，不显示提示框
        if self.current_hover_button == self.pin_btn:
            current_category = getattr(self, '_current_category', 'clipboard')
            if current_category != "notebook":
                return
        
        if is_toolbar_button:
            # 工具栏按钮的提示框在按钮上方居中显示
            tooltip_x = button_pos.x() + (button_geometry.width() - self.category_tooltip.width()) // 2
            tooltip_y = button_pos.y() - self.category_tooltip.height() - 5  # 5px的间距
        else:
            # 分类按钮的提示框在按钮上方居中显示
            tooltip_x = button_pos.x() + (button_geometry.width() - self.category_tooltip.width()) // 2
            tooltip_y = button_pos.y() - self.category_tooltip.height() - 5  # 5px的间距
        
        # 确保提示框不会超出窗口边界
        if tooltip_x < 0:
            tooltip_x = 5
        elif tooltip_x + self.category_tooltip.width() > self.width():
            tooltip_x = self.width() - self.category_tooltip.width() - 5
            
        if tooltip_y < 0:
            tooltip_y = button_pos.y() + button_geometry.height() + 5  # 如果上方空间不够，显示在下方
            
        self.category_tooltip.move(tooltip_x, tooltip_y)
        self.category_tooltip.show()
    
    def switch_category(self, category):
        """切换分类标签"""
        # 如果当前分类已经是目标分类，不执行任何操作
        if hasattr(self, '_current_category') and self._current_category == category:
            return
            
        # 记录当前分类
        self._current_category = category
        
        # 更新分类管理器中的当前分类
        self.category_manager.set_category(category)
        
        # 切换分类时重置show_all状态
        self.category_manager.set_show_all(False)
        
        # 更新按钮选中状态
        self.clipboard_btn.setChecked(category == "clipboard")
        self.image_btn.setChecked(category == "image")
        self.file_btn.setChecked(category == "file")
        self.notebook_btn.setChecked(category == "notebook")  # 添加记事本按钮状态
        self.favorite_btn.setChecked(category == "favorite")
        
        # 控制加号按钮的显示/隐藏
        self.add_note_btn.setVisible(category == "notebook")
        # 如果切换到其他分类，关闭记事本输入窗口
        if category != "notebook" and hasattr(self, 'note_input_window') and self.note_input_window:
            self.note_input_window.close()
            self.note_input_window = None
        # 固定按钮在所有模式下都可见
        self.pin_btn.setVisible(True)
        
        # 更新按钮图标颜色
        colors = self.theme_colors.get(self.current_theme_mode, self.theme_colors['dark'])
        self.clipboard_btn.setIcon(self.qta.icon('fa5s.clipboard', color=colors['icon_active_color'] if category == "clipboard" else colors['icon_color']))
        self.image_btn.setIcon(self.qta.icon('fa5s.image', color=colors['icon_active_color'] if category == "image" else colors['icon_color']))
        self.file_btn.setIcon(self.qta.icon('fa5s.file', color=colors['icon_active_color'] if category == "file" else colors['icon_color']))
        self.notebook_btn.setIcon(self.qta.icon('fa5s.book', color=colors['icon_active_color'] if category == "notebook" else colors['icon_color']))
        self.favorite_btn.setIcon(self.qta.icon('fa5s.star', color=colors['icon_active_color'] if category == "favorite" else colors['icon_color']))
        
        # 检查搜索框是否有内容，如果有则执行搜索
        search_text = self.search_box.text().strip()
        if search_text:
            # 如果搜索框有内容，执行搜索
            self.perform_search()
        # 检查是否是日期搜索状态
        elif hasattr(self, 'is_date_searching') and self.is_date_searching:
            # 如果是日期搜索状态，重新执行日期搜索
            date_text = self.date_input.text().strip()
            if date_text:
                self.perform_date_search()
            else:
                # 如果日期输入框为空，重置日期搜索状态
                self.reset_date_search()
                self.debounce_refresh_list()
        else:
            # 刷新列表显示
            self.debounce_refresh_list()

    def startup_animation(self):
        self.animate_show()
        # 只有在窗口未固定时才自动隐藏
        if not self.is_pinned:
            QTimer.singleShot(2000, self.animate_hide)

    def animate_show(self):
        """根据dock_edge决定弹出方向"""
        # 【重要】删除了原来的第一行 if 判断，因为它会拦截左右侧的弹出
        
        # 停止当前动画（如果正在运行）
        if self.animation.state() == QPropertyAnimation.Running:
            self.animation.stop()
        
        # 获取原始位置（用于恢复正确的Y坐标）
        if hasattr(self, 'original_pos'):
            original_rect = self.original_pos
        else:
            original_rect = self.geometry()
        
        # 根据dock_edge计算屏幕外的起始位置
        screen_geometry = QGuiApplication.primaryScreen().availableGeometry()
        
        if self.dock_edge == "top":
            # 从上边弹出，起始位置在屏幕上方
            start_rect = QRect(original_rect.x(), -original_rect.height() - 20, original_rect.width(), original_rect.height())
            target_rect = QRect(original_rect.x(), 30, original_rect.width(), original_rect.height())
        elif self.dock_edge == "bottom":
            # 从下边弹出，起始位置在屏幕下方
            start_rect = QRect(original_rect.x(), screen_geometry.height() + 20, original_rect.width(), original_rect.height())
            target_rect = QRect(original_rect.x(), screen_geometry.height() - original_rect.height(), original_rect.width(), original_rect.height())
        elif self.dock_edge == "left":
            # 从左边弹出，起始位置在屏幕左侧
            start_rect = QRect(-original_rect.width() - 20, original_rect.y(), original_rect.width(), original_rect.height())
            target_rect = QRect(0, original_rect.y(), original_rect.width(), original_rect.height())
        elif self.dock_edge == "right":
            # 从右边弹出，起始位置在屏幕右侧
            start_rect = QRect(screen_geometry.width() + 20, original_rect.y(), original_rect.width(), original_rect.height())
            target_rect = QRect(screen_geometry.width() - original_rect.width(), original_rect.y(), original_rect.width(), original_rect.height())
        else:
            # 默认从上边弹出
            start_rect = QRect(original_rect.x(), -original_rect.height() - 20, original_rect.width(), original_rect.height())
            target_rect = QRect(original_rect.x(), 30, original_rect.width(), original_rect.height())
        
        # 恢复窗口标志，显示任务栏图标
        if hasattr(self, '_original_window_flags'):
            self.setWindowFlags(self._original_window_flags)
        
        # 确保标题栏颜色正确
        self.set_title_bar_white()
        
        # 先将窗口移动到起始位置（屏幕外），然后再显示
        self.setGeometry(start_rect)
        self.show()
        
        # 设置动画从屏幕外到屏幕内
        self.animation.setStartValue(start_rect)
        self.animation.setEndValue(target_rect)
        self.animation.start()
        self.is_hidden = False
        
        # 显示窗口时隐藏触发条
        self.hide_trigger_bar()
        
        # 隐藏系统托盘图标
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()

    def animate_hide(self):
        # 如果窗口已固定，不执行隐藏
        if self.is_pinned:
            return
            
        # 如果窗口正在被拖动或调整大小，不执行隐藏
        if self.is_moving:
            return
            
        # 检查鼠标是否在窗口或标题栏区域
        cursor_pos = QCursor.pos()
        geo = self.geometry()
        title_bar_height = 30  # 标题栏高度
        border_width = 5  # 边框宽度
        
        # 扩大检测区域，包括边框
        expanded_geo = QRect(
            geo.x() - border_width,
            geo.y() - title_bar_height - border_width,
            geo.width() + 2 * border_width,
            geo.height() + title_bar_height + 2 * border_width
        )
        
        # 如果鼠标在扩展区域内，不执行隐藏
        if expanded_geo.contains(cursor_pos):
            return
            
        if self.y() < -self.height() and self.x() < -self.width(): return

        # 保存当前窗口位置，用于后续的触发检测
        self.original_pos = geo
        
        # 保存当前位置，用于设置窗口标志后恢复
        current_rect = self.geometry()
        
        screen_geometry = QGuiApplication.primaryScreen().availableGeometry()
        
        # 根据dock_edge设置隐藏方向
        if self.dock_edge == "top":
            # 向上隐藏
            target_rect = QRect(current_rect.x(), -current_rect.height() - 20, current_rect.width(), current_rect.height())
        elif self.dock_edge == "bottom":
            # 向下隐藏，确保完全隐藏
            target_rect = QRect(current_rect.x(), screen_geometry.height() + current_rect.height() + 20, current_rect.width(), current_rect.height())
        elif self.dock_edge == "left":
            # 向左隐藏
            target_rect = QRect(-current_rect.width() - 20, current_rect.y(), current_rect.width(), current_rect.height())
        elif self.dock_edge == "right":
            # 向右隐藏
            target_rect = QRect(screen_geometry.width() + 20, current_rect.y(), current_rect.width(), current_rect.height())
        else:
            # 默认向上隐藏
            target_rect = QRect(current_rect.x(), -current_rect.height() - 20, current_rect.width(), current_rect.height())
        
        # 先开始动画，不改变窗口标志，避免闪烁
        self.animation.setStartValue(current_rect)
        self.animation.setEndValue(target_rect)
        self.animation.start()
        self.is_hidden = True
        self.hide_timer.stop()
        
        # 动画结束后再改变窗口标志，隐藏任务栏图标
        self.animation.finished.connect(lambda: self._on_hide_animation_finished())
        
        # 清空搜索框
        self.search_box.clear()
        self.is_searching = False
        
        # 总是关闭日期筛选功能，无论是否在使用
        if hasattr(self, 'date_search_widget') and self.date_search_widget.isVisible():
            self.date_search_widget.hide()
            # 重置日期搜索状态
            self.reset_date_search()
            # 重置日期按钮图标颜色为灰色
            self.date_btn.setIcon(self.qta.icon('fa5s.calendar', color='#333333'))
        
        # 根据dockedge和设置显示触发条
        if self.dock_edge in ["top", "bottom", "left", "right"]:
            # 检查小白条可见性设置
            trigger_bar_visible = self.get_setting("trigger_bar_visible", 1)  # 默认可见
            if trigger_bar_visible == 1:
                self.show_trigger_bar(self.dock_edge)
            else:
                # 如果设置为隐藏，则创建一个不可见的触发区域
                self.create_invisible_trigger_area(self.dock_edge)
        
        # 窗口隐藏后，切换回剪贴板界面
        QTimer.singleShot(400, lambda: self.switch_category("clipboard"))
        
        # 显示系统托盘图标
        if hasattr(self, 'tray_icon'):
            self.tray_icon.show()

    def _on_hide_animation_finished(self):
        """隐藏动画结束后的回调函数"""
        # 保持原生窗口标志，只添加 Tool 标志来隐藏任务栏图标
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
        self.show()
        
        # 断开动画结束信号连接，避免重复连接
        try:
            self.animation.finished.disconnect()
        except:
            pass

    def check_mouse_trigger(self):
        """检查鼠标位置并根据dock_edge触发相应的弹出动画"""
        if not self.is_hidden: return
        cursor_pos = QCursor.pos()
        screen_geometry = QGuiApplication.primaryScreen().availableGeometry()
        
        # 获取窗口吸附前的原始位置（存储在self.original_pos中）
        if hasattr(self, 'original_pos'):
            geo = self.original_pos
        else:
            geo = self.geometry()
        
        # 扩展检测范围，包括标题栏区域
        title_bar_height = 30  # 标题栏高度
        
        # 检查鼠标是否在触发条上
        if self.trigger_bar and self.trigger_bar.isVisible():
            trigger_rect = self.trigger_bar.geometry()
            if trigger_rect.contains(cursor_pos):
                self.animate_show()
                return
        
        # 根据dock_edge检查鼠标是否在相应的触发区域
        if self.dock_edge == "top":
            # 检查鼠标是否在屏幕顶部触发区域（与横向触发条大小一致：60x4）
            trigger_x = geo.x() + (geo.width() - 60) // 2
            trigger_y = 0
            if (trigger_x <= cursor_pos.x() < trigger_x + 60 and 
                trigger_y <= cursor_pos.y() < trigger_y + 4):
                self.animate_show()
        elif self.dock_edge == "bottom":
            # 检查鼠标是否在屏幕底部触发区域（与横向触发条大小一致：60x4）
            trigger_x = geo.x() + (geo.width() - 60) // 2
            trigger_y = screen_geometry.height() - 4  # 吸附到屏幕底部
            if (trigger_x <= cursor_pos.x() < trigger_x + 60 and 
                trigger_y <= cursor_pos.y() < trigger_y + 4):
                self.animate_show()
        elif self.dock_edge == "left":
            # 检查鼠标是否在左侧边缘触发区域（与竖向触发条大小一致：4x60）
            trigger_x = 0
            trigger_y = geo.y() + (geo.height() - 60) // 2
            if (trigger_x <= cursor_pos.x() < trigger_x + 4 and 
                trigger_y <= cursor_pos.y() < trigger_y + 60):
                self.animate_show()
        elif self.dock_edge == "right":
            # 检查鼠标是否在右侧边缘触发区域（与竖向触发条大小一致：4x60）
            trigger_x = screen_geometry.width() - 4
            trigger_y = geo.y() + (geo.height() - 60) // 2
            if (trigger_x <= cursor_pos.x() < trigger_x + 4 and 
                trigger_y <= cursor_pos.y() < trigger_y + 60):
                self.animate_show()

    def enterEvent(self, event):
        self.hide_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        # 如果窗口未固定，才启动隐藏计时器
        if not self.is_pinned:
            self.hide_timer.start()
        super().leaveEvent(event)

    def eventFilter(self, obj, event):
        """事件过滤器，用于处理触发器的鼠标事件"""
        # 检查是否是触发器的事件
        if obj == self.trigger_bar:
            # 鼠标进入触发器时显示窗口
            if event.type() == event.Type.Enter:
                if self.is_hidden:
                    self.animate_show()
                return True
            # 鼠标点击触发器时显示窗口
            elif event.type() == event.Type.MouseButtonPress:
                if self.is_hidden:
                    self.animate_show()
                return True
        
        return super().eventFilter(obj, event)

    def load_window_config(self):
        try:
            config_path = get_config_path()
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                w = config.get("width", 320)
                h = config.get("height", 450)
                x = config.get("x", None)
                y = config.get("y", None)
                self.resize(w, h)
                # 加载上次保存的吸附位置
                self.dock_edge = config.get("dock_edge", "top")
                
                # 加载UI缩放设置
                if "ui_scale" in config:
                    self.ui_scale = float(config["ui_scale"])
                
                # 加载窗口透明度设置
                if "window_opacity" in config:
                    window_opacity = float(config["window_opacity"])
                    self.setWindowOpacity(window_opacity)
                else:
                    self.setWindowOpacity(0.99)  # 默认99%，避免白边问题
                
                # 如果有保存的位置信息，则使用它
                if x is not None and y is not None:
                    self.move(x, y)
                    return True  # 表示已加载位置
        except FileNotFoundError:
            pass  # 第一次运行没有文件，用默认值
        return False  # 表示没有加载位置

    def load_display_settings(self):
        """加载显示设置"""
        try:
            # 从配置文件加载设置
            import json
            config_path = get_config_path()
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 加载字体大小
            self.font_size = config.get('font_size', 13)
                
            # 加载UI缩放
            self.ui_scale = config.get('ui_scale', 1.0)
            
            # 加载主题模式
            self.current_theme_mode = config.get('theme_mode', 'dark')
            
            # 加载吸附距离
            self.snap_distance = config.get('snap_distance', 10)
                
            # 应用设置
            self.apply_display_settings()
        except Exception as e:
            print(f"加载显示设置失败: {e}")
            # 使用默认值
            self.font_size = 13
            self.ui_scale = 1.0
            self.current_theme_mode = 'dark'
            self.snap_distance = 10
            self.apply_display_settings()
    
    def apply_display_settings(self):
        """应用显示设置"""
        # 应用字体大小到消息项
        self.update_message_font_size()
        
        # 应用UI缩放，但在初始化时不保存配置
        self.apply_ui_scale(save_config=False)
        
        # 应用主题
        self.apply_theme(self.current_theme_mode)
    
    def update_message_font_size(self):
        """更新消息项的字体大小"""
        colors = self.theme_colors.get(self.current_theme_mode, self.theme_colors['dark'])
        # 遍历所有消息项并更新字体大小
        if hasattr(self, 'message_layout'):
            for i in range(self.message_layout.count()):
                item = self.message_layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    # 如果是MessageWidget，更新字体大小
                    if hasattr(widget, 'content_label'):
                        font = widget.content_label.font()
                        font.setPointSize(self.font_size)
                        widget.content_label.setFont(font)
                        # 更新样式表中的字体大小
                        if hasattr(widget, 'content_type'):
                            if widget.content_type == "image":
                                widget.content_label.setStyleSheet(f"""
                                    QLabel {{
                                        color: {colors['accent_color']};
                                        font-size: {self.font_size}px;
                                        font-family: "Segoe UI", sans-serif;
                                        line-height: 1.4;
                                        font-style: italic;
                                    }}
                                """)
                            else:
                                widget.content_label.setStyleSheet(f"""
                                    QLabel {{
                                        color: {colors['text_color']};
                                        font-size: {self.font_size}px;
                                        font-family: "Segoe UI", sans-serif;
                                        line-height: 1.4;
                                    }}
                                """)
                    
                    # 如果是NoteWidget，更新字体大小
                    if hasattr(widget, 'title_label'):
                        font = widget.title_label.font()
                        font.setPointSize(self.font_size)
                        widget.title_label.setFont(font)
                    
                    if hasattr(widget, 'content_preview'):
                        font = widget.content_preview.font()
                        font.setPointSize(self.font_size)
                        widget.content_preview.setFont(font)
                    
                    # 更新时间标签的字体大小
                    if hasattr(widget, 'time_label'):
                        font = widget.time_label.font()
                        font.setPointSize(max(self.font_size - 2, 8))  # 时间标签稍小一些
                        widget.time_label.setFont(font)
                        # 更新样式表中的字体大小
                        widget.time_label.setStyleSheet(f"""
                            QLabel {{
                                color: #888888;
                                font-size: {max(self.font_size - 2, 8)}px;
                                font-family: "Segoe UI", sans-serif;
                            }}
                        """)
                    
                    # 更新收藏按钮的大小和图标
                    if hasattr(widget, 'favorite_btn'):
                        widget.favorite_btn.setFixedSize(int(24 * self.ui_scale), int(24 * self.ui_scale))
                        # 重新设置图标大小，明确指定图标尺寸
                        favorite_icon_size = int(16 * self.ui_scale)
                        if hasattr(widget, 'is_favorite') and widget.is_favorite:
                            widget.favorite_btn.setIcon(widget.qta.icon('fa5s.star', color='#FFD700'))
                        else:
                            widget.favorite_btn.setIcon(widget.qta.icon('fa5s.star', color='#CCCCCC'))
                        widget.favorite_btn.setIconSize(QSize(favorite_icon_size, favorite_icon_size))
    
    def apply_ui_scale(self, save_config=True):
        """应用UI缩放"""
        # 计算缩放后的窗口大小
        base_width = 315
        base_height = 380
        scaled_width = int(base_width * self.ui_scale)
        scaled_height = int(base_height * self.ui_scale)
        
        # 获取当前窗口大小
        current_width = self.width()
        current_height = self.height()
        
        # 只在缩放后的尺寸大于当前尺寸时才调整窗口大小
        # 这样确保窗口只能变大，不能变小
        new_width = max(current_width, scaled_width, 315)
        new_height = max(current_height, scaled_height, 380)
        
        # 应用新的窗口大小
        self.resize(new_width, new_height)
        self.setMinimumWidth(int(315 * self.ui_scale))
        
        # 应用缩放到UI元素
        self.apply_ui_element_scale()
        
        # 保存窗口配置，确保UI缩放设置也被保存
        # 但在初始化时不保存，避免属性不存在的错误
        if save_config and hasattr(self, 'dock_edge'):
            self.save_window_config()
    
    def apply_ui_element_scale(self):
        """应用UI缩放到UI元素和图标"""
        # 获取当前主题颜色
        colors = self.theme_colors.get(self.current_theme_mode, self.theme_colors['dark'])
        
        # 定义基础尺寸常量
        BASE_ICON_SIZE = 16
        BASE_BUTTON_WIDTH = 24
        BASE_BUTTON_HEIGHT = 24
        # 统一所有按钮大小为24x24
        BASE_CATEGORY_BUTTON_WIDTH = 24
        BASE_CATEGORY_BUTTON_HEIGHT = 24
        BASE_CATEGORY_ICON_SIZE = 16  # 调整分类按钮图标大小以适应更小的按钮
        BASE_SEARCH_HEIGHT = 24
        BASE_ADD_BUTTON_SIZE = 36
        BASE_ADD_ICON_SIZE = 20
        
        # 计算缩放后的尺寸
        icon_size = int(BASE_ICON_SIZE * self.ui_scale)
        button_width = int(BASE_BUTTON_WIDTH * self.ui_scale)
        button_height = int(BASE_BUTTON_HEIGHT * self.ui_scale)
        category_button_width = int(BASE_CATEGORY_BUTTON_WIDTH * self.ui_scale)
        category_button_height = int(BASE_CATEGORY_BUTTON_HEIGHT * self.ui_scale)
        category_icon_size = int(BASE_CATEGORY_ICON_SIZE * self.ui_scale)
        search_height = int(BASE_SEARCH_HEIGHT * self.ui_scale)
        add_button_size = int(BASE_ADD_BUTTON_SIZE * self.ui_scale)
        add_icon_size = int(BASE_ADD_ICON_SIZE * self.ui_scale)
        
        # 缩放工具栏按钮
        if hasattr(self, 'date_btn'):
            self.date_btn.setFixedSize(button_width, button_height)
            # 重新设置图标，保持原有状态
            date_icon = self.qta.icon('fa5s.calendar', color=colors['icon_color'])
            self.date_btn.setIcon(date_icon)
            self.date_btn.setIconSize(QSize(icon_size, icon_size))
            # 确保按钮样式正确
            self.date_btn.setStyleSheet(self.get_button_style("toolbar"))
        
        if hasattr(self, 'pin_btn'):
            self.pin_btn.setFixedSize(button_width, button_height)
            # 重新设置图标，保持原有状态
            pin_color = colors['icon_active_color'] if self.is_pinned else colors['icon_color']
            pin_icon = self.qta.icon('fa5s.thumbtack', color=pin_color)
            self.pin_btn.setIcon(pin_icon)
            self.pin_btn.setIconSize(QSize(icon_size, icon_size))
            # 确保按钮样式正确
            self.pin_btn.setStyleSheet(self.get_button_style("toolbar"))
        
        if hasattr(self, 'settings_btn'):
            self.settings_btn.setFixedSize(button_width, button_height)
            # 重新设置图标，保持原有状态
            settings_icon = self.qta.icon('fa5s.cog', color=colors['icon_color'])
            self.settings_btn.setIcon(settings_icon)
            self.settings_btn.setIconSize(QSize(icon_size, icon_size))
            # 确保按钮样式正确
            self.settings_btn.setStyleSheet(self.get_button_style("toolbar"))
        
        # 缩放分类按钮
        if hasattr(self, 'clipboard_btn'):
            self.clipboard_btn.setFixedSize(category_button_width, category_button_height)
            # 重新设置图标，保持原有状态
            clipboard_color = colors['icon_active_color'] if (hasattr(self, '_current_category') and self._current_category == "clipboard") else colors['icon_color']
            clipboard_icon = self.qta.icon('fa5s.clipboard', color=clipboard_color)
            self.clipboard_btn.setIcon(clipboard_icon)
            self.clipboard_btn.setIconSize(QSize(category_icon_size, category_icon_size))
            # 确保按钮样式正确
            self.clipboard_btn.setStyleSheet(self.get_button_style("category"))
        
        if hasattr(self, 'favorite_btn'):
            self.favorite_btn.setFixedSize(category_button_width, category_button_height)
            # 重新设置图标，保持原有状态
            favorite_color = colors['icon_active_color'] if (hasattr(self, '_current_category') and self._current_category == "favorite") else colors['icon_color']
            favorite_icon = self.qta.icon('fa5s.star', color=favorite_color)
            self.favorite_btn.setIcon(favorite_icon)
            self.favorite_btn.setIconSize(QSize(category_icon_size, category_icon_size))
            # 确保按钮样式正确
            self.favorite_btn.setStyleSheet(self.get_button_style("category"))
        
        if hasattr(self, 'image_btn'):
            self.image_btn.setFixedSize(category_button_width, category_button_height)
            # 重新设置图标，保持原有状态
            image_color = colors['icon_active_color'] if (hasattr(self, '_current_category') and self._current_category == "image") else colors['icon_color']
            image_icon = self.qta.icon('fa5s.image', color=image_color)
            self.image_btn.setIcon(image_icon)
            self.image_btn.setIconSize(QSize(category_icon_size, category_icon_size))
            # 确保按钮样式正确
            self.image_btn.setStyleSheet(self.get_button_style("category"))
        
        if hasattr(self, 'file_btn'):
            self.file_btn.setFixedSize(category_button_width, category_button_height)
            # 重新设置图标，保持原有状态
            file_color = colors['icon_active_color'] if (hasattr(self, '_current_category') and self._current_category == "file") else colors['icon_color']
            file_icon = self.qta.icon('fa5s.file', color=file_color)
            self.file_btn.setIcon(file_icon)
            self.file_btn.setIconSize(QSize(category_icon_size, category_icon_size))
            # 确保按钮样式正确
            self.file_btn.setStyleSheet(self.get_button_style("category"))
        
        if hasattr(self, 'notebook_btn'):
            self.notebook_btn.setFixedSize(category_button_width, category_button_height)
            # 重新设置图标，保持原有状态
            notebook_color = colors['icon_active_color'] if (hasattr(self, '_current_category') and self._current_category == "notebook") else colors['icon_color']
            notebook_icon = self.qta.icon('fa5s.book', color=notebook_color)
            self.notebook_btn.setIcon(notebook_icon)
            self.notebook_btn.setIconSize(QSize(category_icon_size, category_icon_size))
            # 确保按钮样式正确
            self.notebook_btn.setStyleSheet(self.get_button_style("category"))
        
        # 缩放搜索框
        if hasattr(self, 'search_input'):
            self.search_input.setFixedHeight(search_height)
            # 重新设置搜索框样式
            self.search_input.setStyleSheet(self.get_search_input_style())
        
        # 缩放底部搜索框
        if hasattr(self, 'search_box'):
            # 基于字体大小计算搜索框高度，确保文字完全显示
            # 对于中文文字，需要适当的垂直空间
            font_height = int(13 * self.ui_scale)  # 适中的字体高度计算值
            padding = int(6 * self.ui_scale)  # 减少上下内边距
            border = 2  # 边框宽度
            # 为中文文字提供适当的行高空间
            line_spacing = int(2 * self.ui_scale)
            scaled_height = font_height + (padding * 2) + border + line_spacing  # 总高度 = 字体高度 + 上下内边距 + 边框 + 行间距
            # 确保最小高度，特别是在小缩放比例时
            scaled_height = max(scaled_height, int(26 * self.ui_scale))
            self.search_box.setFixedHeight(scaled_height)
            # 清除之前的动作并重新添加，确保图标大小正确
            actions = self.search_box.actions()
            for action in actions:
                self.search_box.removeAction(action)
            # 重新添加搜索图标，确保图标大小随缩放调整
            search_icon_size = int(16 * self.ui_scale)
            search_icon = self.qta.icon('fa5s.search', color=colors['icon_color'])
            search_action = self.search_box.addAction(search_icon, QLineEdit.LeadingPosition)
            if search_action:
                search_action.setIcon(QIcon(search_icon.pixmap(search_icon_size, search_icon_size)))
            # 重新设置搜索框样式，确保字体大小根据搜索框高度动态调整
            self.search_box.setStyleSheet(self.get_search_input_style())
        
        # 缩放日期搜索框
        if hasattr(self, 'date_input'):
            # 基于字体大小计算搜索框高度，确保文字完全显示
            # 对于中文文字，需要适当的垂直空间
            font_height = int(13 * self.ui_scale)  # 适中的字体高度计算值
            padding = int(6 * self.ui_scale)  # 减少上下内边距
            border = 2  # 边框宽度
            # 为中文文字提供适当的行高空间
            line_spacing = int(2 * self.ui_scale)
            scaled_height = font_height + (padding * 2) + border + line_spacing  # 总高度 = 字体高度 + 上下内边距 + 边框 + 行间距
            # 确保最小高度，特别是在小缩放比例时
            scaled_height = max(scaled_height, int(26 * self.ui_scale))
            self.date_input.setFixedHeight(scaled_height)
            # 清除之前的动作并重新添加，确保图标大小正确
            actions = self.date_input.actions()
            for action in actions:
                self.date_input.removeAction(action)
            # 重新添加日历图标
            calendar_action = self.date_input.addAction(self.qta.icon('fa5s.calendar', color=colors['icon_color']), QLineEdit.LeadingPosition)
            if calendar_action:
                calendar_action.setIcon(QIcon(self.qta.icon('fa5s.calendar', color=colors['icon_color']).pixmap(icon_size, icon_size)))
            # 重新添加搜索图标
            self.date_search_action = self.date_input.addAction(self.qta.icon('fa5s.search', color=colors['icon_color']), QLineEdit.TrailingPosition)
            if self.date_search_action:
                self.date_search_action.setIcon(QIcon(self.qta.icon('fa5s.search', color=colors['icon_color']).pixmap(icon_size, icon_size)))
                # 重新连接信号
                self.date_search_action.triggered.connect(self.perform_date_search)
            # 重新设置搜索框样式，使用透明背景，确保字体大小根据输入框高度动态调整
            self.date_input.setStyleSheet(self.get_search_input_style(transparent=True))
        
        # 缩放添加笔记按钮
        if hasattr(self, 'add_note_btn'):
            self.add_note_btn.setFixedSize(add_button_size, add_button_size)
            # 重新设置图标
            add_icon = self.qta.icon('fa5s.plus', color='white')
            self.add_note_btn.setIcon(add_icon)
            self.add_note_btn.setIconSize(QSize(add_icon_size, add_icon_size))
            # 确保按钮样式正确
            self.add_note_btn.setStyleSheet(self.get_button_style("add"))
        
        # 更新样式表中的字体大小和图标大小
        self.update_ui_scale_styles()
        
        # 更新消息项中的收藏按钮大小
        self.update_message_font_size()
    
    def get_button_style(self, button_type):
        """获取按钮样式，根据类型和缩放比例"""
        colors = self.theme_colors.get(self.current_theme_mode, self.theme_colors['dark'])
        scaled_font_size = int(10 * self.ui_scale)
        scaled_border_radius = int(4 * self.ui_scale)
        scaled_padding = int(2 * self.ui_scale)
        
        if button_type == "toolbar":
            # 工具栏按钮应该是圆形的，所以border-radius应该是按钮宽度的一半
            toolbar_button_size = int(24 * self.ui_scale)
            toolbar_border_radius = int(toolbar_button_size / 2)
            return f"""
                QPushButton {{
                    background-color: transparent;
                    border: 1px solid {colors['toolbar_border']};
                    border-radius: {toolbar_border_radius}px;
                    padding: {scaled_padding}px;
                }}
                QPushButton:hover {{
                    background-color: {colors['toolbar_hover_bg']};
                    border: 1px solid {colors['toolbar_border']};
                }}
                QPushButton:pressed {{
                    background-color: {colors['toolbar_pressed_bg']};
                    border: 1px solid {colors['toolbar_border']};
                }}
            """
        elif button_type == "category":
            return f"""
                QPushButton {{
                    background-color: transparent;
                    border: none;
                    color: {colors['category_text']};
                    font-size: {scaled_font_size}px;
                    font-weight: bold;
                    text-align: center;
                    padding: {scaled_padding}px;
                }}
                QPushButton:hover {{
                    color: {colors['text_color']};
                    background-color: {colors['category_hover_bg']};
                }}
                QPushButton:pressed {{
                    color: {colors['category_checked_text']};
                    background-color: {colors['category_hover_bg']};
                }}
                QPushButton:checked {{
                    background-color: transparent;
                    color: {colors['category_text']};
                }}
            """
        elif button_type == "add":
            scaled_add_radius = int(18 * self.ui_scale)
            scaled_add_padding = int(5 * self.ui_scale)
            return f"""
                QPushButton {{
                    background-color: {colors['add_button_bg']};
                    border: none;
                    border-radius: {scaled_add_radius}px;
                    color: white;
                    font-size: {scaled_font_size}px;
                    font-weight: bold;
                    padding: {scaled_add_padding}px;
                }}
                QPushButton:hover {{
                    background-color: {colors['add_button_hover']};
                }}
                QPushButton:pressed {{
                    background-color: {colors['add_button_pressed']};
                }}
            """
        return ""
    
    def get_search_input_style(self, transparent=False):
        """获取搜索输入框样式，根据搜索框大小调整字体"""
        colors = self.theme_colors.get(self.current_theme_mode, self.theme_colors['dark'])
        # 根据搜索框实际高度计算字体大小，而不是UI缩放比例
        # 使用固定的基础字体大小，确保文字不会过大或过小
        base_font_size = 13  # 基础字体大小
        # 根据搜索框高度动态调整字体大小，但保持在合理范围内
        if hasattr(self, 'search_box') and self.search_box:
            box_height = self.search_box.height()
            # 字体大小为搜索框高度的40%，但限制在10-16px范围内
            dynamic_font_size = max(10, min(16, int(box_height * 0.4)))
        else:
            # 如果搜索框还未创建，使用UI缩放比例作为备用方案
            dynamic_font_size = int(12 * self.ui_scale)
        
        scaled_border_radius = int(6 * self.ui_scale)
        # 内边距也根据搜索框高度动态调整
        if hasattr(self, 'search_box') and self.search_box:
            box_height = self.search_box.height()
            dynamic_padding = max(4, min(8, int(box_height * 0.15)))
        else:
            dynamic_padding = int(6 * self.ui_scale)
        
        # 根据参数决定背景色和边框
        bg_color = "transparent" if transparent else colors['search_bg']
        border_style = "none" if transparent else f"1px solid {colors['search_border']}"
        focus_border = "none" if transparent else f"2px solid {colors['search_focus_border']}"
        
        return f"""
            QLineEdit {{
                border: {border_style};
                border-radius: {scaled_border_radius}px;
                padding: {dynamic_padding}px;
                padding-left: {int(dynamic_padding + 16 * self.ui_scale)}px;
                font-size: {dynamic_font_size}px;
                background-color: {bg_color};
                line-height: 1.2;
                color: {colors['text_color']};
            }}
            QLineEdit:focus {{
                border: {focus_border};
            }}
        """
    
    def update_ui_scale_styles(self):
        """更新样式表中的字体大小和图标大小"""
        # 计算缩放后的字体大小
        scaled_font_size = int(12 * self.ui_scale)
        scaled_small_font_size = int(10 * self.ui_scale)
        
        # 更新主样式表
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: #f5f5f5;
            }}
            #MainCard {{
                background-color: white;
                /* 移除自定义圆角和边框，使用Windows原生样式 */
            }}
            #CategoryButton {{
                background-color: transparent;
                border: none;
                color: #666666;
                font-size: {scaled_small_font_size}px;
                font-weight: bold;
                padding: {int(5 * self.ui_scale)}px;
                text-align: center;
                border-radius: {int(6 * self.ui_scale)}px;
            }}
            #CategoryButton:hover {{
                background-color: #e0e0e0;
            }}
            #CategoryButton:checked {{
                background-color: #0078d4;
                color: white;
            }}
            #ToolbarButton {{
                background-color: transparent;
                border: none;
                border-radius: {int(4 * self.ui_scale)}px;
                padding: {int(2 * self.ui_scale)}px;
            }}
            #ToolbarButton:hover {{
                background-color: rgba(0, 0, 0, 0.1);
            }}
            #SearchInput {{
                border: 1px solid #e0e0e0;
                border-radius: {int(16 * self.ui_scale)}px;
                padding: {int(5 * self.ui_scale)}px {int(12 * self.ui_scale)}px;
                font-size: {scaled_small_font_size}px;
                background-color: #f8f9fa;
            }}
            #SearchInput:focus {{
                border: 1px solid #0078d4;
                outline: none;
            }}
            #AddNoteButton {{
                background-color: #0078d4;
                border: none;
                border-radius: {int(18 * self.ui_scale)}px;
                color: white;
            }}
            #AddNoteButton:hover {{
                background-color: #106ebe;
            }}
            #AddNoteButton:pressed {{
                background-color: #005a9e;
            }}
            MessageWidget {{
                background-color: #f8f8ff;
                border-radius: {int(12 * self.ui_scale)}px;
                border: 1px solid #d0d0ff;
                margin: {int(5 * self.ui_scale)}px;
                padding: {int(10 * self.ui_scale)}px;
            }}
            MessageWidget:hover {{
                background-color: #f0f0ff;
            }}
            NoteWidget {{
                background-color: #f0f8ff;
                border-radius: {int(12 * self.ui_scale)}px;
                border: 1px solid #b0d0ff;
                margin: {int(5 * self.ui_scale)}px;
                padding: {int(10 * self.ui_scale)}px;
            }}
            NoteWidget:hover {{
                background-color: #e0f0ff;
            }}
        """)
    
    def apply_theme(self, theme_mode):
        """应用主题样式"""
        self.current_theme_mode = theme_mode
        colors = self.theme_colors.get(theme_mode, self.theme_colors['dark'])
        
        # 更新窗口样式
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {colors['window_bg']};
            }}
        """)
        
        # 更新自定义滚动条的主题
        if hasattr(self, 'custom_scrollbar'):
            self.custom_scrollbar.current_theme_mode = theme_mode
            self.custom_scrollbar.setup_style()
            # 更新滚动条按钮的图标颜色
            if hasattr(self.custom_scrollbar, 'top_button'):
                self.custom_scrollbar.top_button.setIcon(self.custom_scrollbar.qta.icon('fa5s.angle-up', color=colors['icon_color']))
            if hasattr(self.custom_scrollbar, 'bottom_button'):
                self.custom_scrollbar.bottom_button.setIcon(self.custom_scrollbar.qta.icon('fa5s.angle-down', color=colors['icon_color']))
        
        # 更新主窗口样式
        if hasattr(self, 'main_widget'):
            self.main_widget.setStyleSheet(f"""
                #MainCard {{
                    background-color: {colors['main_bg']};
                }}
            """)
        
        # 更新分类标签栏样式
        if hasattr(self, 'category_widget'):
            self.category_widget.setStyleSheet(f"""
                #CategoryWidget {{
                    background-color: {colors['main_bg']};
                    border-bottom: 1px solid {colors['border_color']};
                }}
            """)
        
        # 更新滚动区域样式
        if hasattr(self, 'scroll_area'):
            self.scroll_area.setStyleSheet(f"""
                QScrollArea {{
                    border: none;
                    background-color: transparent;
                    border-bottom-left-radius: 12px;
                    border-bottom-right-radius: 12px;
                    padding-right: 5px;
                }}
                QScrollBar:vertical {{
                    background-color: {colors['scrollbar_bg']};
                    width: 10px;
                    border-radius: 5px;
                    margin-top: 0px;
                    margin-bottom: 0px;
                }}
                QScrollBar::handle:vertical {{
                    background-color: {colors['scrollbar_handle']};
                    border-radius: 5px;
                    min-height: 20px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background-color: {colors['scrollbar_handle_hover']};
                }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    height: 0px;
                }}
            """)
        
        # 更新消息容器样式
        if hasattr(self, 'message_container'):
            self.message_container.setStyleSheet(f"""
                #MessageContainer {{
                    background-color: transparent;
                    margin-right: 0px;
                }}
            """)
        
        # 更新搜索框样式
        if hasattr(self, 'search_box'):
            self.search_box.setStyleSheet(self.get_search_input_style())
        
        # 更新日期输入框样式
        if hasattr(self, 'date_input'):
            self.date_input.setStyleSheet(self.get_search_input_style(transparent=True))
        
        # 更新工具栏按钮样式和图标颜色
        if hasattr(self, 'date_btn'):
            self.date_btn.setStyleSheet(self.get_button_style("toolbar"))
            self.date_btn.setIcon(self.qta.icon('fa5s.calendar', color=colors['icon_color']))
        if hasattr(self, 'pin_btn'):
            self.pin_btn.setStyleSheet(self.get_button_style("toolbar"))
            self.pin_btn.setIcon(self.qta.icon('fa5s.thumbtack', color=colors['icon_color']))
        if hasattr(self, 'settings_btn'):
            self.settings_btn.setStyleSheet(self.get_button_style("toolbar"))
            self.settings_btn.setIcon(self.qta.icon('fa5s.cog', color=colors['icon_color']))
        
        # 更新分类按钮样式和图标颜色
        if hasattr(self, 'clipboard_btn'):
            self.clipboard_btn.setStyleSheet(self.get_button_style("category"))
            if self.clipboard_btn.isChecked():
                self.clipboard_btn.setIcon(self.qta.icon('fa5s.clipboard', color=colors['icon_active_color']))
            else:
                self.clipboard_btn.setIcon(self.qta.icon('fa5s.clipboard', color=colors['icon_color']))
        if hasattr(self, 'image_btn'):
            self.image_btn.setStyleSheet(self.get_button_style("category"))
            if self.image_btn.isChecked():
                self.image_btn.setIcon(self.qta.icon('fa5s.image', color=colors['icon_active_color']))
            else:
                self.image_btn.setIcon(self.qta.icon('fa5s.image', color=colors['icon_color']))
        if hasattr(self, 'file_btn'):
            self.file_btn.setStyleSheet(self.get_button_style("category"))
            if self.file_btn.isChecked():
                self.file_btn.setIcon(self.qta.icon('fa5s.file', color=colors['icon_active_color']))
            else:
                self.file_btn.setIcon(self.qta.icon('fa5s.file', color=colors['icon_color']))
        if hasattr(self, 'favorite_btn'):
            self.favorite_btn.setStyleSheet(self.get_button_style("category"))
            if self.favorite_btn.isChecked():
                self.favorite_btn.setIcon(self.qta.icon('fa5s.star', color=colors['icon_active_color']))
            else:
                self.favorite_btn.setIcon(self.qta.icon('fa5s.star', color=colors['icon_color']))
        if hasattr(self, 'notebook_btn'):
            self.notebook_btn.setStyleSheet(self.get_button_style("category"))
            if self.notebook_btn.isChecked():
                self.notebook_btn.setIcon(self.qta.icon('fa5s.book', color=colors['icon_active_color']))
            else:
                self.notebook_btn.setIcon(self.qta.icon('fa5s.book', color=colors['icon_color']))
        
        # 更新搜索框图标颜色
        if hasattr(self, 'search_box'):
            search_icon = self.qta.icon('fa5s.search', color=colors['icon_color'])
            for action in self.search_box.actions():
                action.setIcon(search_icon)
        
        # 更新日期输入框图标颜色
        if hasattr(self, 'date_input'):
            date_icon = self.qta.icon('fa5s.calendar', color=colors['icon_color'])
            for action in self.date_input.actions():
                action.setIcon(date_icon)
            if hasattr(self, 'date_search_action'):
                self.date_search_action.setIcon(self.qta.icon('fa5s.search', color=colors['icon_color']))
        
        # 更新添加笔记按钮样式
        if hasattr(self, 'add_note_btn'):
            self.add_note_btn.setStyleSheet(self.get_button_style("add"))
        
        # 更新所有消息卡片样式
        self.update_message_widgets_theme(colors)
        
        # 更新日期搜索悬浮框样式
        if hasattr(self, 'date_search_widget'):
            self.date_search_widget.setStyleSheet(f"""
                QWidget#DateSearchWidget {{
                    background-color: {colors['window_bg']};
                    border-radius: 18px;
                    border: 1px solid {colors['border_color']};
                }}
            """)
        
        # 更新底部工具栏样式
        if hasattr(self, 'bottom_toolbar'):
            self.bottom_toolbar.setStyleSheet(f"""
                #BottomToolbar {{
                    background-color: {colors['main_bg']};
                    border-top: 1px solid {colors['border_color']};
                }}
            """)
        
        # 更新标题栏颜色
        self.set_title_bar_white()
    
    def update_message_widgets_theme(self, colors):
        """更新所有消息小部件的主题样式"""
        if hasattr(self, 'message_layout'):
            for i in range(self.message_layout.count()):
                widget = self.message_layout.itemAt(i).widget()
                if widget and hasattr(widget, 'setStyleSheet'):
                    if isinstance(widget, MessageWidget):
                        widget.setStyleSheet(f"""
                            MessageWidget {{
                                background-color: {colors['card_bg']};
                                border-radius: 12px;
                                border: 1px solid {colors['border_color']};
                                margin: 5px;
                                padding: 10px;
                            }}
                            MessageWidget:hover {{
                                background-color: {colors['card_hover_bg']};
                            }}
                        """)
                        # 更新内容标签颜色
                        if hasattr(widget, 'content_label'):
                            widget.content_label.setStyleSheet(f"""
                                QLabel {{
                                    color: {colors['text_color']};
                                    font-size: {self.font_size}px;
                                    font-family: "Segoe UI", sans-serif;
                                    line-height: 1.4;
                                }}
                            """)
                        # 更新时间标签颜色
                        if hasattr(widget, 'time_label'):
                            widget.time_label.setStyleSheet(f"""
                                QLabel {{
                                    color: {colors['secondary_text']};
                                    font-size: {max(self.font_size - 2, 8)}px;
                                    font-family: "Segoe UI", sans-serif;
                                }}
                            """)
                    elif isinstance(widget, NoteWidget):
                        widget.setStyleSheet(f"""
                            NoteWidget {{
                                background-color: {colors['card_bg']};
                                border-radius: 12px;
                                border: 1px solid {colors['border_color']};
                                margin: 5px;
                                padding: 10px;
                            }}
                            NoteWidget:hover {{
                                background-color: {colors['card_hover_bg']};
                            }}
                        """)
                        # 更新标题标签颜色
                        if hasattr(widget, 'title_label'):
                            widget.title_label.setStyleSheet(f"""
                                QLabel {{
                                    color: {colors['text_color']};
                                    font-size: {self.font_size + 1}px;
                                    font-weight: bold;
                                }}
                            """)
                        # 更新内容预览颜色
                        if hasattr(widget, 'content_preview'):
                            widget.content_preview.setStyleSheet(f"""
                                QLabel {{
                                    color: {colors['secondary_text']};
                                    font-size: {self.font_size - 1}px;
                                }}
                            """)
                        # 更新时间标签颜色
                        if hasattr(widget, 'time_label'):
                            widget.time_label.setStyleSheet(f"""
                                QLabel {{
                                    color: {colors['secondary_text']};
                                    font-size: {max(self.font_size - 2, 8)}px;
                                }}
                            """)

    def save_window_config(self):
        config_path = get_config_path()
        # 先读取现有配置
        config = {}
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except:
            # 如果文件不存在或读取失败，使用空配置
            pass
        
        # 只更新窗口相关的配置，保留其他配置（如device_code, auth_token等）
        config["width"] = self.width()
        config["height"] = self.height()
        config["x"] = self.x()
        config["y"] = self.y()
        # 检查dock_edge属性是否存在，避免初始化时的错误
        if hasattr(self, 'dock_edge'):
            config["dock_edge"] = self.dock_edge  # 保存当前吸附位置
        config["ui_scale"] = self.ui_scale  # 保存UI缩放设置
        config["window_opacity"] = self.windowOpacity()  # 保存窗口透明度设置
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)

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
    
    def init_trigger_bar(self):
        """初始化白色小条悬浮窗作为触发器"""
        self.trigger_bar = QWidget()
        self.trigger_bar.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.trigger_bar.setAttribute(Qt.WA_ShowWithoutActivating)
        
        # 从设置中加载小白条配置
        self.update_trigger_bar_settings()
        
        self.trigger_bar.hide()  # 初始隐藏
        
        # 为触发器安装事件过滤器，以便捕获鼠标事件
        self.trigger_bar.installEventFilter(self)
    
    def init_system_tray(self):
        """初始化系统托盘图标"""
        self.tray_icon = QSystemTrayIcon(self)
        
        # 使用软件图标作为托盘图标
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "assets", "Clippot.ico")
            if os.path.exists(icon_path):
                self.tray_icon.setIcon(QIcon(icon_path))
            else:
                # 如果找不到图标文件，使用qtawesome创建图标
                icon = self.qta.icon('fa5s.clipboard', color='#4A90E2')
                self.tray_icon.setIcon(icon)
        except Exception:
            # 如果无法加载图标，使用默认图标
            self.tray_icon.setIcon(QIcon.fromTheme("edit-paste"))
        
        # 创建托盘菜单
        tray_menu = QMenu()
        
        # 显示窗口动作
        show_text = self.language_manager.get_text("show_window")
        if show_text == "show_window":
            show_text = "显示窗口"
        show_action = QAction(show_text, self)
        show_action.triggered.connect(self.animate_show)
        tray_menu.addAction(show_action)
        
        tray_menu.addSeparator()
        
        # 退出动作
        quit_text = self.language_manager.get_text("quit")
        if quit_text == "quit":
            quit_text = "退出"
        quit_action = QAction(quit_text, self)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        
        # 双击托盘图标显示窗口
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        
        # 初始隐藏托盘图标（窗口显示时）
        self.tray_icon.hide()
    
    def on_tray_icon_activated(self, reason):
        """托盘图标被激活时的处理"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.animate_show()
    
    def quit_application(self):
        """退出应用程序"""
        self.tray_icon.hide()
        self.close()
        QApplication.quit()
    
    def update_trigger_bar_settings(self):
        """更新小白条设置"""
        if not self.trigger_bar:
            return
            
        # 获取小白条设置
        trigger_bar_width = self.get_setting("trigger_bar_width", 4)
        trigger_bar_height = self.get_setting("trigger_bar_height", 60)
        trigger_bar_color = self.get_setting("trigger_bar_color", "#ffffffc8")
        trigger_bar_visible = self.get_setting("trigger_bar_visible", 1)  # 默认可见
        
        # 处理颜色格式
        if len(trigger_bar_color) == 9:  # #RRGGBBAA格式
            r = int(trigger_bar_color[1:3], 16)
            g = int(trigger_bar_color[3:5], 16)
            b = int(trigger_bar_color[5:7], 16)
            a = int(trigger_bar_color[7:9], 16)
            color_str = f"rgba({r}, {g}, {b}, {a})"
        elif len(trigger_bar_color) == 7:  # #RRGGBB格式
            r = int(trigger_bar_color[1:3], 16)
            g = int(trigger_bar_color[3:5], 16)
            b = int(trigger_bar_color[5:7], 16)
            color_str = f"rgba({r}, {g}, {b}, 200)"
        else:
            color_str = "rgba(255, 255, 255, 200)"
        
        # 应用样式
        self.trigger_bar.setStyleSheet(f"""
            QWidget {{
                background-color: {color_str};
                border-radius: 3px;
            }}
        """)
        
        # 保存尺寸到实例变量，供show_trigger_bar使用
        self.trigger_bar_width = trigger_bar_width
        self.trigger_bar_height = trigger_bar_height
        
        # 根据设置决定是否显示小白条
        if trigger_bar_visible == 1:
            # 如果设置为可见，且当前窗口隐藏，则显示小白条
            if not self.isVisible():
                self.show_trigger_bar(self.dock_edge)
        else:
            # 如果设置为隐藏，则隐藏小白条
            self.trigger_bar.hide()

    def show_trigger_bar(self, position):
        """显示触发条在指定位置（跟随窗口位置）"""
        if not self.trigger_bar:
            return
            
        screen_geometry = QGuiApplication.primaryScreen().availableGeometry()
        
        # 获取窗口隐藏前的原始位置
        if hasattr(self, 'original_pos'):
            geo = self.original_pos
        else:
            geo = self.geometry()
        
        # 确保有尺寸设置
        if not hasattr(self, 'trigger_bar_width'):
            self.trigger_bar_width = self.get_setting("trigger_bar_width", 4)
        if not hasattr(self, 'trigger_bar_height'):
            self.trigger_bar_height = self.get_setting("trigger_bar_height", 60)
            
        if position == "left":
            # 左侧显示竖向触发条
            self.trigger_bar.setFixedSize(self.trigger_bar_width, self.trigger_bar_height)
            self.trigger_bar.move(0, geo.y() + (geo.height() - self.trigger_bar_height) // 2)
        elif position == "right":
            # 右侧显示竖向触发条
            self.trigger_bar.setFixedSize(self.trigger_bar_width, self.trigger_bar_height)
            self.trigger_bar.move(screen_geometry.width() - self.trigger_bar_width, 
                                 geo.y() + (geo.height() - self.trigger_bar_height) // 2)
        elif position == "top":
            # 顶部显示横向触发条
            self.trigger_bar.setFixedSize(self.trigger_bar_height, self.trigger_bar_width)
            self.trigger_bar.move(geo.x() + (geo.width() - self.trigger_bar_height) // 2, 0)
        elif position == "bottom":
            # 底部显示横向触发条，吸附到屏幕底部
            self.trigger_bar.setFixedSize(self.trigger_bar_height, self.trigger_bar_width)
            self.trigger_bar.move(geo.x() + (geo.width() - self.trigger_bar_height) // 2, 
                                 screen_geometry.height() - self.trigger_bar_width)  # 吸附到屏幕底部
            
        self.trigger_bar.show()
        self.trigger_bar.raise_()

    def hide_trigger_bar(self):
        """隐藏触发条"""
        if self.trigger_bar:
            self.trigger_bar.hide()
    
    def create_invisible_trigger_area(self, position):
        """创建不可见的触发区域，确保即使小白条隐藏，触发范围仍然有效"""
        if not self.trigger_bar:
            return
            
        # 获取窗口隐藏前的原始位置
        if hasattr(self, 'original_pos'):
            geo = self.original_pos
        else:
            geo = self.geometry()
        
        # 确保有尺寸设置
        if not hasattr(self, 'trigger_bar_width'):
            self.trigger_bar_width = self.get_setting("trigger_bar_width", 4)
        if not hasattr(self, 'trigger_bar_height'):
            self.trigger_bar_height = self.get_setting("trigger_bar_height", 60)
        
        # 设置完全透明的样式，但仍然保持触发区域
        self.trigger_bar.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
            }
        """)
        
        screen_geometry = QGuiApplication.primaryScreen().availableGeometry()
            
        if position == "left":
            # 左侧显示竖向触发条
            self.trigger_bar.setFixedSize(self.trigger_bar_width, self.trigger_bar_height)
            self.trigger_bar.move(0, geo.y() + (geo.height() - self.trigger_bar_height) // 2)
        elif position == "right":
            # 右侧显示竖向触发条
            self.trigger_bar.setFixedSize(self.trigger_bar_width, self.trigger_bar_height)
            self.trigger_bar.move(screen_geometry.width() - self.trigger_bar_width, 
                                 geo.y() + (geo.height() - self.trigger_bar_height) // 2)
        elif position == "top":
            # 顶部显示横向触发条
            self.trigger_bar.setFixedSize(self.trigger_bar_height, self.trigger_bar_width)
            self.trigger_bar.move(geo.x() + (geo.width() - self.trigger_bar_height) // 2, 0)
        elif position == "bottom":
            # 底部显示横向触发条，吸附到屏幕底部
            self.trigger_bar.setFixedSize(self.trigger_bar_height, self.trigger_bar_width)
            self.trigger_bar.move(geo.x() + (geo.width() - self.trigger_bar_height) // 2, 
                                 screen_geometry.height() - self.trigger_bar_width)  # 吸附到屏幕底部
            
        # 显示透明触发区域
        self.trigger_bar.show()
        self.trigger_bar.raise_()

    def set_title_bar_white(self):
        """根据主题设置标题栏颜色"""
        if sys.platform == 'win32':
            try:
                # Windows API 常量
                DWMWA_CAPTION_COLOR = 35
                DWMWA_TEXT_COLOR = 36
                
                # 获取窗口句柄
                hwnd = int(self.winId())
                
                # 获取当前主题的颜色
                colors = self.theme_colors.get(self.current_theme_mode, self.theme_colors['dark'])
                
                # 将十六进制颜色转换为Windows COLORREF格式（AABBGGRR）
                def hex_to_colorref(hex_color):
                    hex_color = hex_color.lstrip('#')
                    # 转换为BGR格式
                    r = int(hex_color[0:2], 16)
                    g = int(hex_color[2:4], 16)
                    b = int(hex_color[4:6], 16)
                    return (b << 16) | (g << 8) | r
                
                # 设置标题栏背景色
                caption_color = hex_to_colorref(colors['window_bg'])
                text_color = hex_to_colorref(colors['text_color'])
                
                # 使用 DwmSetWindowAttribute 设置标题栏颜色
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 
                    DWMWA_CAPTION_COLOR, 
                    ctypes.byref(ctypes.c_int(caption_color)), 
                    ctypes.sizeof(ctypes.c_int)
                )
                
                # 设置标题栏文字颜色
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 
                    DWMWA_TEXT_COLOR, 
                    ctypes.byref(ctypes.c_int(text_color)), 
                    ctypes.sizeof(ctypes.c_int)
                )
            except Exception as e:
                print(f"设置标题栏颜色失败: {e}")

    def apply_edge_snapping(self):
        """应用边缘吸附功能（支持上下左右）"""
        screen_geo = QGuiApplication.primaryScreen().availableGeometry()
        sw, sh = screen_geo.width(), screen_geo.height()
        x, y, w, h = self.x(), self.y(), self.width(), self.height()
        
        dist_top = y
        dist_bottom = sh - (y + h)
        dist_left = x
        dist_right = sw - (x + w)
        
        min_dist = min(dist_top, dist_bottom, dist_left, dist_right)
        
        if min_dist > 100: return

        if min_dist == dist_top:
            self.dock_edge = "top"
            self.move(x, 0) # 【修改】距顶 0 (原来是30)
            
        elif min_dist == dist_bottom:
            self.dock_edge = "bottom"
            self.move(x, sh - h - 30) # 距底 30
            
        elif min_dist == dist_left:
            self.dock_edge = "left"
            self.move(0, y) # 【修改】距左 0 (原来是30)
            
        elif min_dist == dist_right:
            self.dock_edge = "right"
            self.move(sw - w, y) # 【修改】距右 0 (原来是30)
            
        # 保存吸附位置配置
        self.save_window_config()

    def update_all_message_displays(self):
        """更新所有消息小部件的文本显示，使其适应当前窗口宽度"""
        # 只在窗口宽度变化时更新，避免不必要的更新
        current_width = self.width()
        if hasattr(self, '_last_width') and self._last_width == current_width:
            return
            
        self._last_width = current_width
        
        # 计算滚动区域的可用宽度
        available_width = self.scroll_area.width() - 18  # 15px滚动条 + 3px边距
        
        if hasattr(self, 'message_layout'):
            for i in range(self.message_layout.count()):
                item = self.message_layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    # 检查是否是MessageWidget或NoteWidget实例
                    if isinstance(widget, MessageWidget):
                        widget.update_text_display()
                        # 更新最大宽度约束，确保不超过滚动区域
                        widget.setMaximumWidth(max(200, available_width))
                    elif isinstance(widget, NoteWidget):
                        # 更新笔记小部件的最大宽度约束
                        widget.setMaximumWidth(max(200, available_width))

    def resizeEvent(self, event):
        """窗口大小变化时保存配置并更新按钮位置和文本显示"""
        super().resizeEvent(event)
        self.save_window_config()  # 保存窗口大小
        # 自定义滚动条会自动处理按钮位置更新
        
        # 更新悬浮加号按钮位置（如果存在）
        if hasattr(self, 'add_note_btn'):
            # 计算动态位置，避免与日期筛选悬浮框重叠
            # 检查日期筛选悬浮框是否可见
            if hasattr(self, 'date_search_widget') and self.date_search_widget.isVisible():
                # 如果日期筛选悬浮框可见，将加号按钮上移，避免遮挡
                # 日期筛选框高度约为36 * ui_scale，再加上一些间距
                offset_y = int(36 * self.ui_scale) + 20  # 20px额外间距
                self.add_note_btn.move(20, self.height() - 120 - offset_y)
            else:
                # 默认位置
                self.add_note_btn.move(20, self.height() - 120)
        
        # 使用防抖机制更新所有消息小部件的文本显示
        if hasattr(self, 'resize_timer'):
            self.resize_timer.stop()
        else:
            self.resize_timer = QTimer()
            self.resize_timer.setSingleShot(True)
            self.resize_timer.timeout.connect(self.update_all_message_displays)
        
        self.resize_timer.start(100)  # 100毫秒后执行，避免频繁更新
        
        # 如果日期搜索悬浮框可见，重新调整其大小和位置
        if hasattr(self, 'date_search_widget') and self.date_search_widget.isVisible():
            # 计算悬浮框位置和大小 - 占满窗口左边，留出右侧滚动条距离
            window_width = self.width()
            # 估算滚动条宽度，通常为15-20px
            scrollbar_width = 20
            # 设置悬浮框宽度为窗口宽度减去滚动条宽度和边距
            widget_width = window_width - scrollbar_width - 10  # 左右各留5px边距
            self.date_search_widget.resize(widget_width, int(36 * self.ui_scale))
            
            # 设置悬浮框位置，在底部工具栏上方
            btn_geometry = self.date_btn.geometry()
            widget_pos = self.date_btn.parentWidget().mapTo(self, btn_geometry.topLeft())
            
            # 悬浮框在日期按钮上方，左边对齐，留5px边距
            x = 5
            y = widget_pos.y() - self.date_search_widget.height() - 5  # 5px的间距
            
            self.date_search_widget.move(x, y)
    
    def on_scroll_value_changed(self, value):
        """滚动值变化时的处理"""
        # 这个方法可以用来处理滚动时的其他逻辑
        pass
        
    def nativeEvent(self, eventType, message):
        """监听 Windows 窗口移动结束事件"""
        try:
            # 仅在 Windows 平台处理
            if sys.platform == 'win32':
                # 直接获取消息 ID
                msg = ctypes.wintypes.MSG.from_address(int(message))
                
                # 0x0232 是 WM_EXITSIZEMOVE - 窗口移动/调整大小结束
                if msg.message == 0x0232:
                    self.is_moving = False  # 结束移动/调整大小状态
                    self.apply_edge_snapping()
                    # 保存窗口位置
                    self.save_window_config()
                
                # 0x0214 是 WM_SIZING - 窗口正在调整大小
                elif msg.message == 0x0214:
                    self.is_moving = True  # 开始调整大小状态
                    
                # 0x0216 是 WM_MOVING - 窗口正在移动
                elif msg.message == 0x0216:
                    self.is_moving = True  # 开始移动状态
                    
        except Exception as e:
            pass
            
        return super().nativeEvent(eventType, message)
    
    def showEvent(self, event):
        """窗口显示时确保消息布局正确"""
        super().showEvent(event)
        # 应用主题样式（确保启动时正确应用主题）
        self.apply_theme(self.current_theme_mode)
        # 延迟一点时间确保窗口完全显示后再更新布局
        QTimer.singleShot(100, self.update_all_message_displays)