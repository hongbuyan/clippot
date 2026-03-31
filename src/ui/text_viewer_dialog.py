# text_viewer_dialog.py
"""文字选取窗口 - 非模态对话框，用于显示和选取剪贴板内容"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QPushButton, QLabel, QWidget, QApplication
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor, QPalette
import sys


class TextViewerDialog(QDialog):
    """文字选取窗口 - 非模态，支持主题切换"""
    
    def __init__(self, text, theme_mode='dark', language_manager=None, parent=None):
        super().__init__(parent)
        self.text = text
        self.theme_mode = theme_mode
        self.language_manager = language_manager
        self.setup_ui()
        self.apply_theme()
        
    def setup_ui(self):
        """设置UI"""
        # 设置窗口属性 - 非模态
        self.setWindowModality(Qt.NonModal)
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowCloseButtonHint |
            Qt.WindowTitleHint
        )
        
        # 设置窗口标题
        if self.language_manager:
            try:
                title = self.language_manager.get_text("text_viewer_title")
            except:
                title = "选取文字"
        else:
            title = "选取文字"
        self.setWindowTitle(title)
        
        # 设置窗口大小
        self.resize(500, 400)
        self.setMinimumSize(400, 300)
        
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)
        
        # 创建文本编辑区域
        self.text_edit = QTextEdit(self)
        self.text_edit.setPlainText(self.text)
        self.text_edit.setReadOnly(False)
        self.text_edit.setLineWrapMode(QTextEdit.WidgetWidth)
        
        # 设置字体
        font = QFont("Microsoft YaHei", 11)
        self.text_edit.setFont(font)
        
        main_layout.addWidget(self.text_edit)
        
        # 创建底部按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # 添加弹性空间
        button_layout.addStretch()
        
        # 全选按钮
        self.select_all_btn = QPushButton(self)
        if self.language_manager:
            try:
                self.select_all_btn.setText(self.language_manager.get_text("select_all"))
            except:
                self.select_all_btn.setText("全选")
        else:
            self.select_all_btn.setText("全选")
        self.select_all_btn.setFixedWidth(80)
        self.select_all_btn.setCursor(Qt.PointingHandCursor)
        self.select_all_btn.clicked.connect(self.text_edit.selectAll)
        button_layout.addWidget(self.select_all_btn)
        
        # 复制按钮
        self.copy_btn = QPushButton(self)
        if self.language_manager:
            try:
                self.copy_btn.setText(self.language_manager.get_text("copy"))
            except:
                self.copy_btn.setText("复制")
        else:
            self.copy_btn.setText("复制")
        self.copy_btn.setFixedWidth(80)
        self.copy_btn.setCursor(Qt.PointingHandCursor)
        self.copy_btn.clicked.connect(self.copy_selected_text)
        button_layout.addWidget(self.copy_btn)
        
        # 关闭按钮
        self.close_btn = QPushButton(self)
        if self.language_manager:
            try:
                self.close_btn.setText(self.language_manager.get_text("close"))
            except:
                self.close_btn.setText("关闭")
        else:
            self.close_btn.setText("关闭")
        self.close_btn.setFixedWidth(80)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.clicked.connect(self.close)
        button_layout.addWidget(self.close_btn)
        
        main_layout.addLayout(button_layout)
        
        # 创建状态标签
        self.status_label = QLabel(self)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setVisible(False)
        main_layout.addWidget(self.status_label)
        
    def apply_theme(self):
        """应用主题样式"""
        if self.theme_mode == 'dark':
            self._apply_dark_theme()
        else:
            self._apply_light_theme()
            
    def _apply_dark_theme(self):
        """应用深色主题"""
        # 窗口背景色
        bg_color = "#2b2b2b"
        text_color = "#e0e0e0"
        border_color = "#404040"
        button_bg = "#3d3d3d"
        button_hover = "#4d4d4d"
        text_edit_bg = "#1e1e1e"
        text_edit_border = "#505050"
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
            }}
            QTextEdit {{
                background-color: {text_edit_bg};
                color: {text_color};
                border: 1px solid {text_edit_border};
                border-radius: 6px;
                padding: 8px;
                selection-background-color: #4a90d9;
                selection-color: #ffffff;
            }}
            QPushButton {{
                background-color: {button_bg};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {button_hover};
                border-color: #606060;
            }}
            QPushButton:pressed {{
                background-color: #555555;
            }}
            QLabel {{
                color: {text_color};
                font-size: 12px;
            }}
        """)
        
    def _apply_light_theme(self):
        """应用浅色主题"""
        # 窗口背景色
        bg_color = "#f5f5f5"
        text_color = "#333333"
        border_color = "#d0d0d0"
        button_bg = "#ffffff"
        button_hover = "#f0f0f0"
        text_edit_bg = "#ffffff"
        text_edit_border = "#c0c0c0"
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
            }}
            QTextEdit {{
                background-color: {text_edit_bg};
                color: {text_color};
                border: 1px solid {text_edit_border};
                border-radius: 6px;
                padding: 8px;
                selection-background-color: #0078d4;
                selection-color: #ffffff;
            }}
            QPushButton {{
                background-color: {button_bg};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {button_hover};
                border-color: #b0b0b0;
            }}
            QPushButton:pressed {{
                background-color: #e0e0e0;
            }}
            QLabel {{
                color: {text_color};
                font-size: 12px;
            }}
        """)
        
    def copy_selected_text(self):
        """复制选中的文本到剪贴板"""
        selected_text = self.text_edit.textCursor().selectedText()
        if selected_text:
            clipboard = QApplication.clipboard()
            clipboard.setText(selected_text)
            try:
                status_msg = self.language_manager.get_text("copied") if self.language_manager else "已复制到剪贴板"
            except:
                status_msg = "已复制到剪贴板"
            self.show_status(status_msg)
        else:
            try:
                status_msg = self.language_manager.get_text("select_text_first") if self.language_manager else "请先选择文字"
            except:
                status_msg = "请先选择文字"
            self.show_status(status_msg)
            
    def show_status(self, message):
        """显示状态消息"""
        self.status_label.setText(message)
        self.status_label.setVisible(True)
        # 2秒后隐藏
        QTimer.singleShot(2000, lambda: self.status_label.setVisible(False))
        
    def update_theme(self, theme_mode):
        """更新主题"""
        self.theme_mode = theme_mode
        self.apply_theme()
        
    def get_theme(self):
        """获取当前主题"""
        return self.theme_mode
