# word_segment_dialog.py
"""
拆词结果展示对话框
用于展示中文分词结果并提供复制功能
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLabel, QTextEdit, QComboBox, QGroupBox, QApplication,
                               QMessageBox, QSplitter, QWidget, QScrollArea, QFrame,
                               QSizePolicy, QGridLayout, QTabWidget, QTableWidget,
                               QTableWidgetItem, QHeaderView)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QClipboard

import sys
import os

# 添加项目根目录到路径
if __name__ != '__main__':
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.utils.word_segmenter import segmenter, segment_text, format_words


class WordSegmentDialog(QDialog):
    """拆词结果展示对话框"""
    
    def __init__(self, text: str, language_manager=None, parent=None):
        super().__init__(parent)
        self.original_text = text
        self.language_manager = language_manager
        self.segmented_words = []
        self.words_with_pos = []
        
        self.setWindowTitle(self.get_text("word_segment_title", "拆词结果"))
        self.resize(700, 550)
        self.setMinimumSize(500, 400)
        
        # 设置窗口标志
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)
        
        self.setup_ui()
        self.perform_segmentation()
    
    def get_text(self, key: str, default: str = "") -> str:
        """获取多语言文本"""
        if self.language_manager and hasattr(self.language_manager, 'get_text'):
            return self.language_manager.get_text(key)
        return default
    
    def setup_ui(self):
        """设置UI界面"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 标题
        title_label = QLabel(self.get_text("word_segment_title", "🔤 文本拆词分析"))
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #333333;
                padding-bottom: 10px;
            }
        """)
        main_layout.addWidget(title_label)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background-color: #fafafa;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                padding: 8px 16px;
                margin-right: 4px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background-color: #357ABD;
                color: white;
            }
            QTabBar::tab:hover:!selected {
                background-color: #e0e0e0;
            }
        """)
        
        # 标签页1：分词结果
        self.result_tab = QWidget()
        self.setup_result_tab()
        self.tab_widget.addTab(self.result_tab, self.get_text("tab_segment_result", "分词结果"))
        
        # 标签页2：原文对比
        self.compare_tab = QWidget()
        self.setup_compare_tab()
        self.tab_widget.addTab(self.compare_tab, self.get_text("tab_original", "原文对比"))
        
        # 标签页3：词频统计
        self.freq_tab = QWidget()
        self.setup_freq_tab()
        self.tab_widget.addTab(self.freq_tab, self.get_text("tab_word_freq", "词频统计"))
        
        main_layout.addWidget(self.tab_widget)
        
        # 控制区域
        control_layout = QHBoxLayout()
        
        # 分词模式选择
        mode_label = QLabel(self.get_text("label_segment_mode", "分词模式："))
        mode_label.setStyleSheet("font-size: 13px; color: #666666;")
        control_layout.addWidget(mode_label)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            self.get_text("mode_default", "精确模式（推荐）"),
            self.get_text("mode_full", "全模式"),
            self.get_text("mode_search", "搜索引擎模式")
        ])
        self.mode_combo.setFixedWidth(180)
        self.mode_combo.setStyleSheet("""
            QComboBox {
                padding: 6px 10px;
                border: 1px solid #cccccc;
                border-radius: 4px;
                background-color: white;
                font-size: 13px;
            }
            QComboBox:hover {
                border-color: #999999;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
        """)
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        control_layout.addWidget(self.mode_combo)
        
        control_layout.addStretch()
        
        # 分隔符选择
        sep_label = QLabel(self.get_text("label_separator", "分隔符："))
        sep_label.setStyleSheet("font-size: 13px; color: #666666;")
        control_layout.addWidget(sep_label)
        
        self.sep_combo = QComboBox()
        self.sep_combo.setEditable(True)
        self.sep_combo.addItems([" / ", " | ", "  ", "\n", ", "])
        self.sep_combo.setCurrentText(" / ")
        self.sep_combo.setFixedWidth(80)
        self.sep_combo.setStyleSheet("""
            QComboBox {
                padding: 6px 10px;
                border: 1px solid #cccccc;
                border-radius: 4px;
                background-color: white;
                font-size: 13px;
            }
            QComboBox:hover {
                border-color: #999999;
            }
        """)
        self.sep_combo.currentTextChanged.connect(self.update_display)
        control_layout.addWidget(self.sep_combo)
        
        main_layout.addLayout(control_layout)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 复制结果按钮
        self.copy_btn = QPushButton(self.get_text("btn_copy_result", "📋 复制分词结果"))
        self.copy_btn.setCursor(Qt.PointingHandCursor)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 20px;
                background-color: #357ABD;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2968A8;
            }
            QPushButton:pressed {
                background-color: #1e4d7a;
            }
        """)
        self.copy_btn.clicked.connect(self.copy_result)
        button_layout.addWidget(self.copy_btn)
        
        # 复制原文按钮
        self.copy_original_btn = QPushButton(self.get_text("btn_copy_original", "复制原文"))
        self.copy_original_btn.setCursor(Qt.PointingHandCursor)
        self.copy_original_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 20px;
                background-color: #f0f0f0;
                color: #333333;
                border: 1px solid #cccccc;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        self.copy_original_btn.clicked.connect(self.copy_original)
        button_layout.addWidget(self.copy_original_btn)
        
        # 关闭按钮
        close_btn = QPushButton(self.get_text("btn_close", "关闭"))
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 20px;
                background-color: #f5f5f5;
                color: #666666;
                border: 1px solid #dddddd;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #eeeeee;
            }
        """)
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        
        main_layout.addLayout(button_layout)
        
        # 状态栏
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #999999;
                padding-top: 5px;
            }
        """)
        main_layout.addWidget(self.status_label)
        
        # 设置整体样式
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
        """)
    
    def setup_result_tab(self):
        """设置分词结果标签页"""
        layout = QVBoxLayout(self.result_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # 结果显示区域
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 12px;
                background-color: #ffffff;
                font-size: 14px;
                line-height: 1.6;
            }
        """)
        self.result_text.setPlaceholderText(self.get_text("placeholder_segmenting", "正在分词..."))
        layout.addWidget(self.result_text)
        
        # 统计信息
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #666666;
                padding: 5px;
            }
        """)
        layout.addWidget(self.stats_label)
    
    def setup_compare_tab(self):
        """设置原文对比标签页"""
        layout = QVBoxLayout(self.compare_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 使用分割器
        splitter = QSplitter(Qt.Vertical)
        
        # 原文区域
        original_group = QGroupBox(self.get_text("label_original_text", "原文"))
        original_layout = QVBoxLayout(original_group)
        self.original_text_edit = QTextEdit()
        self.original_text_edit.setReadOnly(True)
        self.original_text_edit.setText(self.original_text)
        self.original_text_edit.setStyleSheet("""
            QTextEdit {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 10px;
                background-color: #f9f9f9;
                font-size: 14px;
            }
        """)
        original_layout.addWidget(self.original_text_edit)
        splitter.addWidget(original_group)
        
        # 分词结果区域
        result_group = QGroupBox(self.get_text("label_segmented_text", "分词结果"))
        result_layout = QVBoxLayout(result_group)
        self.compare_result_text = QTextEdit()
        self.compare_result_text.setReadOnly(True)
        self.compare_result_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 10px;
                background-color: #f9f9f9;
                font-size: 14px;
            }
        """)
        result_layout.addWidget(self.compare_result_text)
        splitter.addWidget(result_group)
        
        # 设置分割比例
        splitter.setSizes([200, 200])
        layout.addWidget(splitter)
    
    def setup_freq_tab(self):
        """设置词频统计标签页"""
        layout = QVBoxLayout(self.freq_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 词频表格
        self.freq_table = QTableWidget()
        self.freq_table.setColumnCount(3)
        self.freq_table.setHorizontalHeaderLabels([
            self.get_text("header_word", "词语"),
            self.get_text("header_count", "出现次数"),
            self.get_text("header_percentage", "占比")
        ])
        self.freq_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.freq_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.freq_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.freq_table.setColumnWidth(1, 100)
        self.freq_table.setColumnWidth(2, 100)
        self.freq_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                background-color: #ffffff;
                gridline-color: #e0e0e0;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #e0e0e0;
                font-weight: bold;
                color: #333333;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTableWidget::item:selected {
                background-color: #e6f3ff;
                color: #333333;
            }
        """)
        self.freq_table.setAlternatingRowColors(True)
        layout.addWidget(self.freq_table)
        
        # 统计摘要
        self.freq_summary_label = QLabel("")
        self.freq_summary_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #666666;
                padding: 10px 5px;
            }
        """)
        layout.addWidget(self.freq_summary_label)
    
    def perform_segmentation(self):
        """执行分词"""
        if not self.original_text or not self.original_text.strip():
            self.show_error(self.get_text("error_empty_text", "文本内容为空，无法进行分词"))
            return
        
        try:
            # 获取分词模式
            mode_map = {0: 'default', 1: 'full', 2: 'search'}
            mode = mode_map.get(self.mode_combo.currentIndex(), 'default')
            
            # 执行分词
            self.segmented_words = segmenter.segment(self.original_text, mode)
            self.words_with_pos = segmenter.segment_with_pos(self.original_text)
            
            # 更新显示
            self.update_display()
            self.update_freq_table()
            
            # 更新状态
            word_count = len(self.segmented_words)
            char_count = len(self.original_text)
            self.status_label.setText(
                self.get_text("status_segmented", "共分词 {0} 个，原文字符数：{1}").format(word_count, char_count)
            )
            
        except Exception as e:
            self.show_error(self.get_text("error_segment_failed", "分词失败：{0}").format(str(e)))
    
    def update_display(self):
        """更新分词结果显示"""
        if not self.segmented_words:
            return
        
        separator = self.sep_combo.currentText()
        # 处理换行符
        if separator == "\\n":
            separator = "\n"
        
        # 格式化结果
        formatted_result = separator.join(self.segmented_words)
        
        # 更新结果标签页
        self.result_text.setText(formatted_result)
        
        # 更新对比标签页
        self.compare_result_text.setText(formatted_result)
        
        # 更新统计
        word_count = len(self.segmented_words)
        unique_count = len(set(self.segmented_words))
        self.stats_label.setText(
            self.get_text("stats_words", "词语总数：{0} | 不重复词语：{1}").format(word_count, unique_count)
        )
    
    def update_freq_table(self):
        """更新词频统计表格"""
        if not self.segmented_words:
            return
        
        # 统计词频
        freq_dict = {}
        for word in self.segmented_words:
            if len(word) > 1:  # 只统计长度大于1的词
                freq_dict[word] = freq_dict.get(word, 0) + 1
        
        # 排序
        sorted_freq = sorted(freq_dict.items(), key=lambda x: x[1], reverse=True)
        
        # 更新表格
        self.freq_table.setRowCount(len(sorted_freq))
        total_words = len(self.segmented_words)
        
        for row, (word, count) in enumerate(sorted_freq):
            # 词语
            word_item = QTableWidgetItem(word)
            word_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.freq_table.setItem(row, 0, word_item)
            
            # 次数
            count_item = QTableWidgetItem(str(count))
            count_item.setTextAlignment(Qt.AlignCenter)
            self.freq_table.setItem(row, 1, count_item)
            
            # 占比
            percentage = (count / total_words) * 100 if total_words > 0 else 0
            percentage_item = QTableWidgetItem(f"{percentage:.1f}%")
            percentage_item.setTextAlignment(Qt.AlignCenter)
            self.freq_table.setItem(row, 2, percentage_item)
        
        # 更新摘要
        unique_words = len(sorted_freq)
        self.freq_summary_label.setText(
            self.get_text("freq_summary", "共 {0} 个不同的词语（长度≥2），总词语数：{1}").format(unique_words, total_words)
        )
    
    def on_mode_changed(self, index):
        """分词模式改变时重新分词"""
        self.perform_segmentation()
    
    def copy_result(self):
        """复制分词结果到剪贴板"""
        if not self.segmented_words:
            self.show_notification(self.get_text("notify_no_content", "没有可复制的内容"), error=True)
            return
        
        separator = self.sep_combo.currentText()
        if separator == "\\n":
            separator = "\n"
        
        result = separator.join(self.segmented_words)
        
        clipboard = QApplication.clipboard()
        clipboard.setText(result)
        
        self.show_notification(self.get_text("notify_copied", "分词结果已复制到剪贴板"))
    
    def copy_original(self):
        """复制原文到剪贴板"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.original_text)
        self.show_notification(self.get_text("notify_original_copied", "原文已复制到剪贴板"))
    
    def show_notification(self, message: str, error: bool = False):
        """显示通知"""
        # 临时改变按钮文本作为反馈
        original_text = self.copy_btn.text()
        self.copy_btn.setText(message)
        
        if error:
            self.copy_btn.setStyleSheet("""
                QPushButton {
                    padding: 10px 20px;
                    background-color: #ff4444;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 14px;
                }
            """)
        
        # 2秒后恢复
        QTimer.singleShot(2000, lambda: self.restore_button(original_text))
    
    def restore_button(self, original_text: str):
        """恢复按钮状态"""
        self.copy_btn.setText(original_text)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 20px;
                background-color: #357ABD;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2968A8;
            }
            QPushButton:pressed {
                background-color: #1e4d7a;
            }
        """)
    
    def show_error(self, message: str):
        """显示错误信息"""
        QMessageBox.warning(self, self.get_text("title_error", "错误"), message)


# 便捷函数
def show_word_segment_dialog(text: str, language_manager=None, parent=None):
    """
    显示拆词对话框
    
    Args:
        text: 待分词的文本
        language_manager: 语言管理器
        parent: 父窗口
    """
    if not text or not text.strip():
        QMessageBox.information(
            parent,
            language_manager.get_text("title_info", "提示") if language_manager else "提示",
            language_manager.get_text("msg_empty_clipboard", "粘贴板内容为空") if language_manager else "粘贴板内容为空"
        )
        return
    
    dialog = WordSegmentDialog(text, language_manager, parent)
    dialog.exec()


# 测试代码
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 测试文本
    test_text = """自然语言处理是人工智能领域的一个重要方向。
    它研究能实现人与计算机之间用自然语言进行有效通信的各种理论和方法。
    Natural Language Processing is a branch of artificial intelligence."""
    
    dialog = WordSegmentDialog(test_text)
    dialog.show()
    sys.exit(app.exec())
