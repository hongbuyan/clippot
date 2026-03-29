# text_editor.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QToolBar, QComboBox, QFontComboBox, QDialog, QLineEdit, QTextEdit, QApplication
from PySide6.QtCore import Qt, Signal, QMimeData, QTranslator, QLibraryInfo
from PySide6.QtGui import QFont, QIcon, QColor, QTextCharFormat, QTextDocumentFragment, QTextCursor, QTextDocument, QTextFormat
from datetime import datetime
import sys
import ctypes

# Windows API 导入，用于设置标题栏颜色
if sys.platform == 'win32':
    import ctypes
    from ctypes import wintypes

# 导入QScintilla
try:
    from Qsci import QsciScintilla, QsciLexerPython, QsciLexerJavaScript, QsciLexerHTML, QsciLexerCPP, QsciLexerSQL
    QSCINTILLA_AVAILABLE = True
except ImportError:
    QSCINTILLA_AVAILABLE = False
    print("QScintilla not available. Using QTextEdit as fallback.")

# 全局CleanTextEdit类定义，用于粘贴格式清洗
# ==============================================================================
# 替换原来的 CleanTextEdit 类
# ==============================================================================

class CleanTextEdit(QTextEdit):
    def __init__(self, language_manager=None, parent=None):
        super().__init__(parent)
        self.language_manager = language_manager
        self.setAcceptRichText(True)
        self.paste_clean_mode = True
        
        # 设置上下文菜单
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
    def setPasteCleanMode(self, enabled):
        """设置粘贴清洗模式"""
        self.paste_clean_mode = enabled
        
    def show_context_menu(self, position):
        """显示自定义上下文菜单"""
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QAction
        
        menu = self.createStandardContextMenu()
        
        # 找到粘贴动作并替换它
        actions = menu.actions()
        for action in actions:
            if action.text().startswith("Paste") or action.text().startswith("粘贴"):
                menu.removeAction(action)
                break
        
        # 添加自定义粘贴动作
        paste_action = QAction("粘贴" if self.language_manager and hasattr(self.language_manager, 'current_language') and self.language_manager.current_language == 'zh' else "Paste", self)
        paste_action.triggered.connect(self.paste)
        menu.insertAction(actions[0] if actions else None, paste_action)
        
        menu.exec(self.mapToGlobal(position))
        
    def keyPressEvent(self, event):
        """重写键盘事件，捕获Ctrl+V快捷键"""
        from PySide6.QtGui import QKeySequence
        from PySide6.QtCore import Qt
        
        # 检查是否是Ctrl+V粘贴快捷键
        if event.matches(QKeySequence.Paste):
            self.paste()  # 调用我们重写的paste方法
            event.accept()
        else:
            super().keyPressEvent(event)
        
    def paste(self):
        """重写粘贴方法，执行智能清洗"""
        from PySide6.QtWidgets import QApplication
        
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()
        
        if mime_data.hasHtml():
            html_content = mime_data.html()
            # 执行清洗
            cleaned_fragment = self.sanitize_rich_text(html_content, strict_mode=self.paste_clean_mode)
            cursor = self.textCursor()
            
            # 记录插入前的位置
            insert_pos = cursor.position()
            
            # 插入清洗后的内容
            cursor.insertFragment(cleaned_fragment)
            
            # 如果是严格模式，确保所有文本都使用默认颜色
            if self.paste_clean_mode:
                # 选择刚刚插入的内容
                cursor.setPosition(insert_pos)
                cursor.setPosition(self.textCursor().position(), QTextCursor.KeepAnchor)
                char_fmt = cursor.charFormat()
                char_fmt.setForeground(QColor("#000000"))
                cursor.mergeCharFormat(char_fmt)
        elif mime_data.hasText():
            self.insertPlainText(mime_data.text())

    def sanitize_rich_text(self, html, strict_mode):
        """
        智能清洗核心逻辑
        :param strict_mode: 
            True (开启清洗): 仅保留文字内容和基本字形（字体、大小），去除所有颜色、背景、边框。
            False (关闭清洗): 保留字体、大小和颜色，去除其他所有格式（背景、边框等）。
        """
        from PySide6.QtGui import QTextDocument, QTextCursor, QTextFrameFormat
        import re  # 必须引入 re 模块
        
        # ==========================================
        # 1. 字符串级暴力清洗 (The Silver Bullet)
        # 在 Qt 解析之前，直接从 HTML 源码中删掉背景和边框样式
        # ==========================================
        
        # 去除 CSS 背景相关属性 (background, background-color)
        html = re.sub(r'background(-color)?\s*:[^;"]+;?', '', html, flags=re.IGNORECASE)
        # 去除 HTML bgcolor 属性
        html = re.sub(r'bgcolor="[^"]+"', '', html, flags=re.IGNORECASE)
        
        # 去除 CSS 边框相关属性 (border, border-width, border-style, etc.)
        # 这是解决"黑色方框"最有效的手段
        html = re.sub(r'border(-[a-zA-Z]+)?\s*:[^;"]+;?', '', html, flags=re.IGNORECASE)
        
        # 去除可能导致边框效果的阴影
        html = re.sub(r'box-shadow\s*:[^;"]+;?', '', html, flags=re.IGNORECASE)
        
        # 根据模式决定是否去除颜色
        if strict_mode:
            # 开启清洗模式：去除所有颜色相关属性，但保留字体大小
            html = re.sub(r'color\s*:\s*[^;"]+;?', '', html, flags=re.IGNORECASE)
            html = re.sub(r'text-decoration\s*:\s*[^;"]+;?', '', html, flags=re.IGNORECASE)
            html = re.sub(r'font-weight\s*:\s*[^;"]+;?', '', html, flags=re.IGNORECASE)
            html = re.sub(r'font-style\s*:\s*[^;"]+;?', '', html, flags=re.IGNORECASE)
            # 去除HTML中的颜色属性，但保留字体大小属性
            html = re.sub(r'text="[^"]*"', '', html, flags=re.IGNORECASE)
            html = re.sub(r'color="[^"]*"', '', html, flags=re.IGNORECASE)
            # 去除style属性中的color
            html = re.sub(r'style="[^"]*color\s*:\s*[^;"]+;?[^"]*"', '', html, flags=re.IGNORECASE)
        else:
            # 关闭清洗模式：保留颜色、字体大小，但去除其他装饰性属性
            html = re.sub(r'text-decoration\s*:\s*[^;"]+;?', '', html, flags=re.IGNORECASE)
            # 保留font-weight和font-style以支持粗体和斜体，也保留font-size

        # ==========================================
        # 2. Qt 对象级清洗
        # ==========================================
        temp_doc = QTextDocument()
        temp_doc.setHtml(html)
        
        # A. 递归清洗所有框架 (Frame) 和 表格 (Table)
        def clean_frame_recursive(frame):
            fmt = frame.frameFormat()
            
            # 强制去除边框和背景刷子
            fmt.setBorder(0)
            fmt.setBorderBrush(Qt.NoBrush)  # 关键：边框颜色设为透明
            fmt.setBorderStyle(QTextFrameFormat.BorderStyle_None) # 关键：边框样式设为无
            fmt.setBackground(Qt.NoBrush)   # 关键：背景设为透明
            fmt.setPadding(0)
            fmt.setMargin(0)
            # 移除不支持的LengthVariable属性
            # fmt.setWidth(QTextFrameFormat.LengthVariable)  # 确保宽度可变
            # fmt.setHeight(QTextFrameFormat.LengthVariable)  # 确保高度可变
            
            frame.setFrameFormat(fmt)
            
            for child_frame in frame.childFrames():
                clean_frame_recursive(child_frame)

        clean_frame_recursive(temp_doc.rootFrame())
        
        # A1. 额外清洗所有表格
        all_tables = temp_doc.allFormats()
        for fmt in all_tables:
            if fmt.isTableFormat():
                fmt.setBackground(Qt.NoBrush)
                fmt.setBorder(0)
                fmt.setCellPadding(0)
                fmt.setCellSpacing(0)
                fmt.setBorderBrush(Qt.NoBrush)
                fmt.setBorderStyle(QTextFrameFormat.BorderStyle_None)

        # B. 遍历内容清洗段落 (Block) 和 文字 (Char)
        cursor = QTextCursor(temp_doc)
        cursor.movePosition(QTextCursor.Start)
        
        # B1. 先进行一次全局背景和边框清洗
        cursor.select(QTextCursor.Document)
        doc_fmt = cursor.charFormat()
        doc_fmt.clearBackground()
        # 只在严格模式下清除前景色（文字颜色）
        if strict_mode:
            doc_fmt.clearForeground()
        cursor.setCharFormat(doc_fmt)
        
        block_fmt = cursor.blockFormat()
        block_fmt.clearBackground()
        cursor.setBlockFormat(block_fmt)
        
        cursor.movePosition(QTextCursor.Start)
        
        while True:
            # --- 清洗段落背景 ---
            # 确保文字后面不会有灰色的长条
            block_fmt = cursor.blockFormat()
            block_fmt.setBackground(Qt.NoBrush)
            block_fmt.clearBackground()
            block_fmt.setLeftMargin(0)
            block_fmt.setRightMargin(0)
            block_fmt.setTopMargin(0)
            block_fmt.setBottomMargin(0)
            block_fmt.setTextIndent(0)
            cursor.setBlockFormat(block_fmt)
            
            # --- 清洗文字属性 ---
            cursor.select(QTextCursor.BlockUnderCursor)
            if cursor.hasSelection():
                it = cursor.block().begin()
                while not it.atEnd():
                    fragment = it.fragment()
                    if fragment.isValid():
                        frag_cursor = QTextCursor(temp_doc)
                        frag_cursor.setPosition(fragment.position())
                        frag_cursor.setPosition(fragment.position() + fragment.length(), QTextCursor.KeepAnchor)
                        
                        char_fmt = frag_cursor.charFormat()
                        
                        if strict_mode:
                            # 【开启清洗】：只保留字体和大小，去除所有颜色和其他格式
                            # 保存字体族和字体大小
                            font_family = char_fmt.fontFamily()
                            font_size = char_fmt.fontPointSize()
                            
                            # 重置所有格式
                            char_fmt.clearForeground()
                            char_fmt.clearBackground()
                            char_fmt.clearProperty(QTextFormat.FontWeight)
                            char_fmt.clearProperty(QTextFormat.FontItalic)
                            char_fmt.clearProperty(QTextFormat.TextUnderlineStyle)
                            # PySide6中没有TextStrikeOut属性，使用setFontStrikeOut(False)代替
                            char_fmt.setFontStrikeOut(False)
                            
                            # 恢复字体和大小
                            if font_family:
                                char_fmt.setFontFamily(font_family)
                            if font_size > 0:
                                char_fmt.setFontPointSize(font_size)
                            
                            # 设置为默认文本颜色（黑色）
                            char_fmt.setForeground(QColor("#000000"))
                        else:
                            # 【关闭清洗】：保留字体、大小和颜色，去除其他格式
                            # 保留字体族、字体大小和颜色
                            font_family = char_fmt.fontFamily()
                            font_size = char_fmt.fontPointSize()
                            text_color = char_fmt.foreground()
                            
                            # 重置除字体、大小和颜色外的所有格式
                            char_fmt.clearBackground()
                            char_fmt.clearProperty(QTextFormat.TextUnderlineStyle)
                            # PySide6中没有TextStrikeOut属性，使用setFontStrikeOut(False)代替
                            char_fmt.setFontStrikeOut(False)
                            
                            # 恢复字体、大小和颜色
                            if font_family:
                                char_fmt.setFontFamily(font_family)
                            if font_size > 0:
                                char_fmt.setFontPointSize(font_size)
                            if text_color.style() != Qt.NoBrush:
                                char_fmt.setForeground(text_color)
                        
                        frag_cursor.setCharFormat(char_fmt)
                    it += 1
            
            if not cursor.movePosition(QTextCursor.NextBlock):
                break
                
        # 如果是严格模式，再进行一次全局颜色重置，确保没有遗漏
        if strict_mode:
            cursor.select(QTextCursor.Document)
            char_fmt = cursor.charFormat()
            char_fmt.setForeground(QColor("#000000"))
            char_fmt.clearBackground()
            cursor.mergeCharFormat(char_fmt)
            
            # 再次清洗所有框架和表格
            clean_frame_recursive(temp_doc.rootFrame())
            
            # 清洗所有图像
            all_formats = temp_doc.allFormats()
            for fmt in all_formats:
                if fmt.isImageFormat():
                    # 去除图像的边框
                    fmt.clearProperty(QTextFormat.TextOutline)
                    fmt.clearBackground()
                
        # 最后再进行一次全局清洗，确保没有任何边框和背景
        cursor.select(QTextCursor.Document)
        final_char_fmt = cursor.charFormat()
        final_char_fmt.clearBackground()
        # 只在严格模式下设置前景色为黑色
        if strict_mode:
            final_char_fmt.setForeground(QColor("#000000"))
        cursor.setCharFormat(final_char_fmt)
        
        cursor.movePosition(QTextCursor.Start)
        while True:
            block_fmt = cursor.blockFormat()
            block_fmt.clearBackground()
            block_fmt.setLeftMargin(0)
            block_fmt.setRightMargin(0)
            block_fmt.setTopMargin(0)
            block_fmt.setBottomMargin(0)
            cursor.setBlockFormat(block_fmt)
            
            if not cursor.movePosition(QTextCursor.NextBlock):
                break
                
        return QTextDocumentFragment(temp_doc)

class AdvancedTextEditor(QWidget):
    """基于QScintilla的高级文本编辑器"""
    
    # 定义信号
    textChanged = Signal()
    saveRequested = Signal()
    
    def __init__(self, language_manager=None, parent=None):
        super().__init__(parent)
        self.language_manager = language_manager
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI组件"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 顶部布局，包含工具栏（左对齐）
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        # 工具栏
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.toolbar.setStyleSheet("""
            QToolBar {
                border: none;
                background: #F8F8F8;
                border-bottom: 1px solid #E0E0E0;
                spacing: 8px;
                padding: 8px;
            }
            QToolButton {
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                background-color: white;
                padding: 4px;
            }
            QToolButton:hover {
                background-color: #F0F0F0;
            }
            QToolButton:checked {
                background-color: #E6F3FF;
            }
            QComboBox {
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                padding: 2px 6px;
                min-width: 80px;
                background-color: white;
            }
            QComboBox:hover {
                border-color: #AAAAAA;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #666666;
            }
        """)
        self.setup_toolbar()
        top_layout.addWidget(self.toolbar)
        
        main_layout.addLayout(top_layout)
        
        # 编辑器
        if QSCINTILLA_AVAILABLE:
            self.editor = QsciScintilla()
            self.setup_scintilla_editor()
            # 设置无边框
            self.editor.setFrameStyle(0)
            self.editor.setLineWidth(0)
        else:
            # 回退到QTextEdit
            from PySide6.QtWidgets import QTextEdit
            from PySide6.QtGui import QTextDocument, QTextCursor
            
            # 【注意】这里直接使用全局定义的 CleanTextEdit，不要在这里重新定义类！
            self.editor = CleanTextEdit(self.language_manager)
            # 设置无边框
            self.editor.setFrameStyle(0)
            self.editor.setLineWidth(0)
        
        main_layout.addWidget(self.editor)
        
        # 连接信号
        if QSCINTILLA_AVAILABLE:
            self.editor.textChanged.connect(self.textChanged.emit)
        else:
            self.editor.textChanged.connect(self.textChanged.emit)
    
    def setup_toolbar(self):
        """设置工具栏 - 左侧为格式化按钮，右侧为下拉框组件"""
        
        # === 左侧：格式化按钮组 ===
        
        # 粗体按钮
        self.bold_button = QPushButton()
        self.bold_button.setText("B")
        self.bold_button.setToolTip(self.language_manager.get_text("tooltip_bold"))
        self.bold_button.setFixedSize(24, 24)
        self.bold_button.setStyleSheet("""
            QPushButton {
                font-weight: bold;
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                background-color: white;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
            }
            QPushButton:checked {
                background-color: #E6F3FF;
            }
        """)
        self.bold_button.setCheckable(True)
        self.bold_button.clicked.connect(self.toggle_bold)
        self.toolbar.addWidget(self.bold_button)
        
        # 斜体按钮
        self.italic_button = QPushButton()
        self.italic_button.setText("I")
        self.italic_button.setToolTip(self.language_manager.get_text("tooltip_italic"))
        self.italic_button.setFixedSize(24, 24)
        self.italic_button.setStyleSheet("""
            QPushButton {
                font-style: italic;
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                background-color: white;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
            }
            QPushButton:checked {
                background-color: #E6F3FF;
            }
        """)
        self.italic_button.setCheckable(True)
        self.italic_button.clicked.connect(self.toggle_italic)
        self.toolbar.addWidget(self.italic_button)
        
        # 下划线按钮
        self.underline_button = QPushButton()
        self.underline_button.setText("U")
        self.underline_button.setToolTip(self.language_manager.get_text("tooltip_underline"))
        self.underline_button.setFixedSize(24, 24)
        self.underline_button.setStyleSheet("""
            QPushButton {
                text-decoration: underline;
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                background-color: white;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
            }
            QPushButton:checked {
                background-color: #E6F3FF;
            }
        """)
        self.underline_button.setCheckable(True)
        self.underline_button.clicked.connect(self.toggle_underline)
        self.toolbar.addWidget(self.underline_button)
        
        # 粘贴模式切换按钮
        self.paste_mode_button = QPushButton()
        self.paste_mode_button.setText("P")
        self.paste_mode_button.setToolTip(self.language_manager.get_text("tooltip_paste_mode"))
        self.paste_mode_button.setFixedSize(24, 24)
        self.paste_mode_button.setStyleSheet("""
            QPushButton {
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                background-color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
            }
            QPushButton:checked {
                background-color: #E6F3FF;
            }
        """)
        self.paste_mode_button.setCheckable(True)
        self.paste_mode_button.setChecked(True)  # 默认为清洗模式
        self.paste_mode_button.clicked.connect(self.toggle_paste_mode)
        self.toolbar.addWidget(self.paste_mode_button)
        
        # 分隔符
        self.toolbar.addSeparator()
        
        # 文本颜色按钮
        self.color_button = QPushButton()
        self.color_button.setText("A")
        self.color_button.setToolTip(self.language_manager.get_text("tooltip_text_color"))
        self.color_button.setFixedSize(24, 24)
        self.color_button.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: white;
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        self.color_button.clicked.connect(self.choose_text_color)
        self.toolbar.addWidget(self.color_button)
        
        # 背景颜色按钮
        self.bg_color_button = QPushButton()
        self.bg_color_button.setText("A")
        self.bg_color_button.setToolTip(self.language_manager.get_text("tooltip_bg_color"))
        self.bg_color_button.setFixedSize(24, 24)
        self.bg_color_button.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #333333;
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                border-color: #AAAAAA;
            }
        """)
        self.bg_color_button.clicked.connect(self.choose_bg_color)
        self.toolbar.addWidget(self.bg_color_button)
        
        # 分隔符
        self.toolbar.addSeparator()
        
        # 行号切换 (开关按钮)
        self.line_numbers_button = QPushButton(self.language_manager.get_text("btn_line_numbers"))
        self.line_numbers_button.setToolTip(self.language_manager.get_text("tooltip_line_numbers"))
        self.line_numbers_button.setCheckable(True)
        self.line_numbers_button.setChecked(True)
        self.line_numbers_button.clicked.connect(self.toggle_line_numbers)
        self.line_numbers_button.setStyleSheet("""
            QPushButton {
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                padding: 2px 6px;
                background-color: white;
            }
            QPushButton:hover { border-color: #AAAAAA; }
            QPushButton:checked { background-color: #E6F3FF; }
        """)
        self.toolbar.addWidget(self.line_numbers_button)
        

        
        # 添加弹性空间，将右侧组件推到工具栏末尾
        from PySide6.QtWidgets import QSizePolicy
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred))
        self.toolbar.addWidget(spacer)
        
        # === 右侧：下拉框组件组 ===
        
        # 2. 语言选择 (带下拉框)
        self.language_combo = QComboBox()
        self.language_combo.addItems([
            self.language_manager.get_text("lang_plain_text"),
            self.language_manager.get_text("lang_python"),
            self.language_manager.get_text("lang_javascript"),
            self.language_manager.get_text("lang_html"),
            self.language_manager.get_text("lang_cpp"),
            self.language_manager.get_text("lang_sql")
        ])
        self.language_combo.setCurrentText(self.language_manager.get_text("lang_plain_text"))
        self.language_combo.setToolTip(self.language_manager.get_text("tooltip_language_mode"))
        self.language_combo.currentTextChanged.connect(self.change_language)
        self.toolbar.addWidget(self.language_combo)
        
        # 3. 字体选择 (带下拉框)
        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(QFont("Consolas"))
        self.font_combo.setToolTip(self.language_manager.get_text("tooltip_font"))
        self.font_combo.currentFontChanged.connect(self.change_font)
        # 设置固定宽度和高度，确保与按钮大小一致
        self.font_combo.setFixedWidth(120)  # 减小宽度以匹配按钮
        self.font_combo.setFixedHeight(24)  # 设置与按钮一致的高度
        self.toolbar.addWidget(self.font_combo)
        
        # 4. 字体大小 (带下拉框)
        self.size_combo = QComboBox()
        self.size_combo.addItems(["8", "9", "10", "11", "12", "14", "16", "18", "20", "24", "28", "32", "36", "48"])
        self.size_combo.setCurrentText("12")
        self.size_combo.setToolTip(self.language_manager.get_text("tooltip_font_size"))
        self.size_combo.setFixedWidth(60) # 固定宽度更美观
        self.size_combo.setFixedHeight(24)  # 设置与按钮一致的高度
        self.size_combo.currentTextChanged.connect(self.change_font_size)
        self.toolbar.addWidget(self.size_combo)
        
        # 分隔符
        self.toolbar.addSeparator()
        
        # 语言选择
        self.language_combo = QComboBox()
        self.language_combo.addItems([
            self.language_manager.get_text("lang_plain_text"),
            self.language_manager.get_text("lang_python"),
            self.language_manager.get_text("lang_javascript"),
            self.language_manager.get_text("lang_html"),
            self.language_manager.get_text("lang_cpp"),
            self.language_manager.get_text("lang_sql")
        ])
        self.language_combo.setCurrentText(self.language_manager.get_text("lang_plain_text"))
        self.language_combo.currentTextChanged.connect(self.change_language)
        self.toolbar.addWidget(self.language_combo)
        
        # 行号切换
        self.line_numbers_button = QPushButton(self.language_manager.get_text("btn_line_numbers"))
        self.line_numbers_button.setToolTip(self.language_manager.get_text("tooltip_line_numbers"))
        self.line_numbers_button.setCheckable(True)
        self.line_numbers_button.setChecked(True)
        self.line_numbers_button.clicked.connect(self.toggle_line_numbers)
        self.line_numbers_button.setStyleSheet("""
            QPushButton {
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                padding: 2px 6px;
                background-color: white;
            }
            QPushButton:checked {
                background-color: #e6f3ff;
            }
        """)
        self.toolbar.addWidget(self.line_numbers_button)
        
        # 自动换行切换
        self.word_wrap_button = QPushButton()
        self.word_wrap_button.setText(self.language_manager.get_text("btn_word_wrap"))
        self.word_wrap_button.setToolTip(self.language_manager.get_text("tooltip_word_wrap"))
        self.word_wrap_button.setCheckable(True)
        self.word_wrap_button.clicked.connect(self.toggle_word_wrap)
        self.word_wrap_button.setStyleSheet("""
            QPushButton {
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                padding: 2px 6px;
                background-color: white;
            }
            QPushButton:checked {
                background-color: #e6f3ff;
            }
        """)
        self.toolbar.addWidget(self.word_wrap_button)
    
    def setup_scintilla_editor(self):
        """设置QScintilla编辑器"""
        # 设置字体
        font = QFont("Consolas", 12)
        self.editor.setFont(font)
        
        # 设置行号显示
        self.editor.setMarginType(0, self.editor.NumberMargin)
        self.editor.setMarginWidth(0, 40)
        self.editor.setMarginLineNumbers(0, True)
        
        # 设置当前行高亮
        self.editor.setCaretLineVisible(True)
        self.editor.setCaretLineBackgroundColor(QColor("#e6f3ff"))
        
        # 设置自动缩进
        self.editor.setAutoIndent(True)
        self.editor.setIndentationGuides(True)
        self.editor.setIndentationsUseTabs(False)
        self.editor.setIndentationWidth(4)
        
        # 设置括号匹配
        self.editor.setBracesMatching(True)
        self.editor.setMatchedBraceBackgroundColor(QColor("#c0c0c0"))
        self.editor.setMatchedBraceForegroundColor(QColor("#0000ff"))
        
        # 设置自动补全
        self.editor.setAutoCompletionSource(self.editor.AcsAll)
        self.editor.setAutoCompletionThreshold(1)
        
        # 设置代码折叠
        self.editor.setFolding(self.editor.PlainFoldStyle)
        
        # 设置边缘（用于显示换行等）
        self.editor.setEdgeMode(self.editor.EdgeLine)
        self.editor.setEdgeColumn(80)
        self.editor.setEdgeColor(QColor("#cccccc"))
        
        # 设置选择颜色
        self.editor.setSelectionBackgroundColor(QColor("#3399ff"))
        
        # 设置默认语言为纯文本
        self.change_language(self.language_manager.get_text("lang_plain_text"))
    
    def change_font(self, font):
        """更改字体"""
        if QSCINTILLA_AVAILABLE:
            self.editor.setFont(font)
        else:
            cursor = self.editor.textCursor()
            if cursor.hasSelection():
                # 如果有选中文本，只对选中文本应用字体
                fmt = cursor.charFormat()
                fmt.setFontFamily(font.family())
                cursor.mergeCharFormat(fmt)
                self.editor.setTextCursor(cursor)
            else:
                # 如果没有选中文本，设置默认字体
                self.editor.setFontFamily(font.family())
    
    def change_font_size(self, size):
        """更改字体大小"""
        if QSCINTILLA_AVAILABLE:
            font = self.editor.font()
            font.setPointSize(int(size))
            self.editor.setFont(font)
        else:
            cursor = self.editor.textCursor()
            if cursor.hasSelection():
                # 如果有选中文本，只对选中文本应用字体大小
                fmt = cursor.charFormat()
                fmt.setFontPointSize(float(size))
                cursor.mergeCharFormat(fmt)
                self.editor.setTextCursor(cursor)
            else:
                # 如果没有选中文本，设置默认字体大小
                self.editor.setFontPointSize(float(size))
    
    def change_language(self, language):
        """更改语言模式"""
        if not QSCINTILLA_AVAILABLE:
            return
            
        # 移除当前词法分析器
        self.editor.setLexer(None)
        
        # 根据选择的语言设置词法分析器
        # 处理多语言的语言名称
        lang_plain_text = self.language_manager.get_text("lang_plain_text")
        lang_python = self.language_manager.get_text("lang_python")
        lang_javascript = self.language_manager.get_text("lang_javascript")
        lang_html = self.language_manager.get_text("lang_html")
        lang_cpp = self.language_manager.get_text("lang_cpp")
        lang_sql = self.language_manager.get_text("lang_sql")
        
        if language == lang_python or language == "Python":
            lexer = QsciLexerPython()
        elif language == lang_javascript or language == "JavaScript":
            lexer = QsciLexerJavaScript()
        elif language == lang_html or language == "HTML":
            lexer = QsciLexerHTML()
        elif language == lang_cpp or language == "C++":
            lexer = QsciLexerCPP()
        elif language == lang_sql or language == "SQL":
            lexer = QsciLexerSQL()
        else:
            lexer = None
        
        if lexer:
            # 设置字体
            font = QFont("Consolas", 12)
            lexer.setFont(font)
            self.editor.setLexer(lexer)
    
    def toggle_line_numbers(self, checked):
        """切换行号显示"""
        if QSCINTILLA_AVAILABLE:
            self.editor.setMarginLineNumbers(0, checked)
            if checked:
                self.editor.setMarginWidth(0, 40)
            else:
                self.editor.setMarginWidth(0, 0)
    
    def toggle_word_wrap(self, checked):
        """切换自动换行"""
        if QSCINTILLA_AVAILABLE:
            if checked:
                self.editor.setWrapMode(self.editor.WrapWord)
            else:
                self.editor.setWrapMode(self.editor.WrapNone)
    
    def set_text(self, text):
        """设置文本内容"""
        if QSCINTILLA_AVAILABLE:
            self.editor.setText(text)
        else:
            self.editor.setPlainText(text)
    
    def set_html(self, html):
        """设置HTML内容（仅QTextEdit支持）"""
        if not QSCINTILLA_AVAILABLE:
            self.editor.setHtml(html)
    
    def get_text(self):
        """获取文本内容"""
        if QSCINTILLA_AVAILABLE:
            return self.editor.text()
        else:
            # 如果是富文本编辑器，返回纯文本内容
            return self.editor.toPlainText()
    
    def get_html(self):
        """获取HTML格式内容（仅QTextEdit支持）"""
        if not QSCINTILLA_AVAILABLE:
            return self.editor.toHtml()
        return None
    
    def set_readonly(self, readonly):
        """设置只读模式"""
        if QSCINTILLA_AVAILABLE:
            self.editor.setReadOnly(readonly)
        else:
            self.editor.setReadOnly(readonly)
    
    def append_text(self, text):
        """追加文本"""
        if QSCINTILLA_AVAILABLE:
            self.editor.append(text)
        else:
            self.editor.append(text)
    
    def get_selected_text(self):
        """获取选中的文本"""
        if QSCINTILLA_AVAILABLE:
            return self.editor.selectedText()
        else:
            return self.editor.textCursor().selectedText()
    
    def replace_selected_text(self, text):
        """替换选中的文本"""
        if QSCINTILLA_AVAILABLE:
            self.editor.replaceSelectedText(text)
        else:
            cursor = self.editor.textCursor()
            cursor.insertText(text)
    
    def find_text(self, text, case_sensitive=False, whole_word=False, regex=False):
        """查找文本"""
        if not QSCINTILLA_AVAILABLE:
            return False
            
        flags = 0
        if case_sensitive:
            flags |= self.editor.FindMatchCase
        if whole_word:
            flags |= self.editor.FindWholeWord
        if regex:
            flags |= self.editor.FindRegExp
            
        return self.editor.findFirst(text, False, flags, False, False)
    
    def replace_text(self, find_text, replace_text, case_sensitive=False, whole_word=False, regex=False):
        """替换文本"""
        if not QSCINTILLA_AVAILABLE:
            return False
            
        if self.find_text(find_text, case_sensitive, whole_word, regex):
            self.replace_selected_text(replace_text)
            return True
        return False
    
    def replace_all_text(self, find_text, replace_text, case_sensitive=False, whole_word=False, regex=False):
        """替换所有文本"""
        if not QSCINTILLA_AVAILABLE:
            return False
            
        count = 0
        self.editor.setCursorPosition(0, 0)
        while self.replace_text(find_text, replace_text, case_sensitive, whole_word, regex):
            count += 1
        return count
    
    def choose_text_color(self):
        """选择文本颜色"""
        from PySide6.QtWidgets import QColorDialog
        
        # 设置颜色对话框的父窗口和位置
        color_dialog = QColorDialog(self)
        color_dialog.setWindowTitle(self.language_manager.get_text("dialog_select_text_color"))
        
        # 获取当前文本颜色
        current_color = self.editor.textColor() if not QSCINTILLA_AVAILABLE else self.editor.color()
        color_dialog.setCurrentColor(current_color)
        
        # 显示对话框并获取颜色
        if color_dialog.exec() == QColorDialog.Accepted:
            color = color_dialog.selectedColor()
            if color.isValid():
                if QSCINTILLA_AVAILABLE:
                    self.editor.setColor(color)
                else:
                    self.editor.setTextColor(color)
                
                # 更新按钮颜色
                self.color_button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {color.name()};
                        color: white;
                        border: 1px solid #CCCCCC;
                        border-radius: 3px;
                        font-weight: bold;
                    }}
                """)
    
    def choose_bg_color(self):
        """选择背景颜色"""
        from PySide6.QtWidgets import QColorDialog
        
        # 设置颜色对话框的父窗口和位置
        color_dialog = QColorDialog(self)
        color_dialog.setWindowTitle(self.language_manager.get_text("dialog_select_bg_color"))
        
        # 获取当前背景颜色
        if QSCINTILLA_AVAILABLE:
            current_color = self.editor.paper()  # 获取背景色
        else:
            # QTextEdit没有直接获取背景色的方法，使用默认白色
            current_color = QColor("#FFFFFF")
        
        color_dialog.setCurrentColor(current_color)
        
        # 显示对话框并获取颜色
        if color_dialog.exec() == QColorDialog.Accepted:
            color = color_dialog.selectedColor()
            if color.isValid():
                if QSCINTILLA_AVAILABLE:
                    self.editor.setPaper(color)
                else:
                    self.editor.setTextBackgroundColor(color)
                
                # 更新按钮颜色
                self.bg_color_button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {color.name()};
                        color: {'black' if color.lightness() > 128 else 'white'};
                        border: 1px solid #CCCCCC;
                        border-radius: 3px;
                        font-weight: bold;
                    }}
                """)
    
    def toggle_bold(self, checked):
        """切换粗体"""
        if QSCINTILLA_AVAILABLE:
            font = self.editor.font()
            font.setBold(checked)
            self.editor.setFont(font)
        else:
            cursor = self.editor.textCursor()
            if cursor.hasSelection():
                # 如果有选中文本，只对选中文本应用格式
                fmt = cursor.charFormat()
                fmt.setFontWeight(QFont.Bold if checked else QFont.Normal)
                cursor.mergeCharFormat(fmt)
                self.editor.setTextCursor(cursor)
            else:
                # 如果没有选中文本，设置默认格式
                fmt = cursor.charFormat()
                fmt.setFontWeight(QFont.Bold if checked else QFont.Normal)
                cursor.setCharFormat(fmt)
                self.editor.setTextCursor(cursor)
    
    def toggle_italic(self, checked):
        """切换斜体"""
        if QSCINTILLA_AVAILABLE:
            font = self.editor.font()
            font.setItalic(checked)
            self.editor.setFont(font)
        else:
            cursor = self.editor.textCursor()
            if cursor.hasSelection():
                # 如果有选中文本，只对选中文本应用格式
                fmt = cursor.charFormat()
                fmt.setFontItalic(checked)
                cursor.mergeCharFormat(fmt)
                self.editor.setTextCursor(cursor)
            else:
                # 如果没有选中文本，设置默认格式
                fmt = cursor.charFormat()
                fmt.setFontItalic(checked)
                cursor.setCharFormat(fmt)
                self.editor.setTextCursor(cursor)
    
    def toggle_underline(self, checked):
        """切换下划线"""
        if QSCINTILLA_AVAILABLE:
            font = self.editor.font()
            font.setUnderline(checked)
            self.editor.setFont(font)
        else:
            cursor = self.editor.textCursor()
            if cursor.hasSelection():
                # 如果有选中文本，只对选中文本应用格式
                fmt = cursor.charFormat()
                fmt.setFontUnderline(checked)
                cursor.mergeCharFormat(fmt)
                self.editor.setTextCursor(cursor)
            else:
                # 如果没有选中文本，设置默认格式
                fmt = cursor.charFormat()
                fmt.setFontUnderline(checked)
                cursor.setCharFormat(fmt)
                self.editor.setTextCursor(cursor)
    
    def toggle_paste_mode(self, checked):
        """切换粘贴模式"""
        if not QSCINTILLA_AVAILABLE:
            # 更新编辑器的粘贴模式
            self.editor.setPasteCleanMode(checked)
            
            # 更新按钮提示文本
            if checked:
                self.paste_mode_button.setToolTip(self.language_manager.get_text("paste_mode_strict"))
            else:
                self.paste_mode_button.setToolTip(self.language_manager.get_text("paste_mode_loose"))


class NoteEditWindow(QDialog):
    """独立的笔记编辑窗口"""
    
    def __init__(self, note_data=None, language_manager=None, parent=None):
        super().__init__(parent)
        self.note_data = note_data or {}
        self.language_manager = language_manager
        self.setWindowTitle(self.language_manager.get_text("edit_note") if note_data else self.language_manager.get_text("new_note"))
        self.resize(700, 600)  # 使用resize而不是setFixedSize，允许调整大小
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMaximizeButtonHint)  # 只保留最大化和关闭按钮
        
        # 导入qtawesome
        import qtawesome as qta
        self.qta = qta
        
        # 设置Windows原生标题栏为白色
        self.set_title_bar_white()
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI组件"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
        main_layout.setSpacing(0)  # 移除默认间距，使用自定义间距
        
        # 创建独立的工具栏，放在最顶部
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.toolbar.setStyleSheet("""
            QToolBar {
                border: none;
                background: #F8F8F8;
                border-bottom: 1px solid #E0E0E0;
                spacing: 8px;
                padding: 8px;
                margin: 0px;
            }
            QToolButton {
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                background-color: white;
                padding: 4px;
            }
            QToolButton:hover {
                background-color: #F0F0F0;
            }
            QToolButton:checked {
                background-color: #E6F3FF;
            }
            QComboBox {
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                padding: 2px 6px;
                min-width: 80px;
                background-color: white;
            }
            QComboBox:hover {
                border-color: #AAAAAA;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #666666;
            }
        """)
        self.setup_toolbar()
        main_layout.addWidget(self.toolbar)  # 将工具栏添加到主布局的最顶部
        
        # 内容区域
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(30, 20, 30, 30)
        content_layout.setSpacing(0)
        
        # 标题区域 - 左对齐，无装饰框体
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText(self.language_manager.get_text("placeholder_no_title"))
        self.title_edit.setText(self.note_data.get("title", ""))
        self.title_edit.setFrame(False)  # 移除边框
        self.title_edit.setStyleSheet("""
            QLineEdit {
                font-size: 24px;
                font-weight: bold;
                color: #333333;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
            QLineEdit:focus {
                border: none;
                background: transparent;
            }
        """)
        content_layout.addWidget(self.title_edit)
        
        # 添加标题与信息栏之间的间距
        content_layout.addSpacing(10)
        
        # 时间与字数信息栏 - 左对齐，小号浅灰色
        info_layout = QHBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(8)
        
        # 时间标签
        current_time = self.note_data.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.time_label = QLabel(current_time)
        self.time_label.setStyleSheet("""
            QLabel {
                color: #999999;
                font-size: 12px;
                font-family: "Segoe UI", sans-serif;
            }
        """)
        info_layout.addWidget(self.time_label)
        
        # 分隔符
        separator = QLabel("|")
        separator.setStyleSheet("""
            QLabel {
                color: #CCCCCC;
                font-size: 12px;
            }
        """)
        info_layout.addWidget(separator)
        
        # 字数统计
        self.word_count_label = QLabel(f"0 {self.language_manager.get_text('word_count')}")
        self.word_count_label.setStyleSheet("""
            QLabel {
                color: #999999;
                font-size: 12px;
                font-family: "Segoe UI", sans-serif;
            }
        """)
        info_layout.addWidget(self.word_count_label)
        
        info_layout.addStretch()
        content_layout.addLayout(info_layout)
        
        # 添加信息栏与内容区域之间的间距
        content_layout.addSpacing(20)
        
        # 内容区域 - 使用CleanTextEdit类
        self.content_edit = CleanTextEdit(self.language_manager)
        self.content_edit.setAcceptRichText(True)  # 启用富文本编辑
        # 设置无边框
        self.content_edit.setFrameStyle(0)
        self.content_edit.setLineWidth(0)
        
        # 初始化粘贴清洗模式状态（与按钮状态同步）
        self.content_edit.setPasteCleanMode(True)  # 默认开启清洗模式
        
        # 如果有笔记数据，需要从数据库获取内容
        if self.note_data.get("id"):
            content = self.get_note_content(self.note_data["id"])
            self.content_edit.setPlainText(content)
            
            # 如果有HTML内容，也设置
            html_content = self.get_note_html_content(self.note_data["id"])
            if html_content:
                self.content_edit.setHtml(html_content)
        else:
            self.content_edit.setPlainText(self.note_data.get("content", ""))
        
        # 连接文本变化信号以更新字数统计
        self.content_edit.textChanged.connect(self.update_word_count)
        
        # 连接光标位置变化信号，用于更新工具栏状态
        self.content_edit.cursorPositionChanged.connect(self.update_toolbar_state)
        
        # 初始更新字数统计
        self.update_word_count()
        
        content_layout.addWidget(self.content_edit)
        
        # 添加内容区域与按钮之间的间距
        content_layout.addSpacing(20)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 取消按钮
        cancel_btn = QPushButton(self.language_manager.get_text("cancel"))
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.close)  # 改为close而不是reject
        cancel_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #F5F5F5;
                border: 1px solid #DDDDDD;
                border-radius: 6px;
                font-size: 14px;
                color: #666666;
            }
            QPushButton:hover {
                background-color: #EEEEEE;
            }
        """)
        button_layout.addWidget(cancel_btn)
        
        # 保存按钮
        save_btn = QPushButton(self.language_manager.get_text("save"))
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self.save_note)
        save_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #357ABD;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                color: white;
            }
            QPushButton:hover {
                background-color: #2968A8;
            }
        """)
        button_layout.addWidget(save_btn)
        
        content_layout.addLayout(button_layout)
        main_layout.addWidget(content_widget)
        
        # 设置整体样式
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
                margin: 0px;
                padding: 0px;
            }
        """)
        
        # 设置标题输入框焦点
        self.title_edit.setFocus()
    
    def setup_toolbar(self):
        """设置工具栏 - 左侧为格式化按钮，右侧为下拉框组件"""
        
        # === 左侧：格式化按钮组 ===
        
        # 粗体按钮
        self.bold_button = QPushButton()
        self.bold_button.setText("B")
        self.bold_button.setToolTip(self.language_manager.get_text("tooltip_bold"))
        self.bold_button.setFixedSize(24, 24)
        self.bold_button.setStyleSheet("""
            QPushButton {
                font-weight: bold;
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                background-color: white;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
            }
            QPushButton:checked {
                background-color: #E6F3FF;
            }
        """)
        self.bold_button.setCheckable(True)
        self.bold_button.clicked.connect(self.toggle_bold)
        self.toolbar.addWidget(self.bold_button)
        
        # 斜体按钮
        self.italic_button = QPushButton()
        self.italic_button.setText("I")
        self.italic_button.setToolTip(self.language_manager.get_text("tooltip_italic"))
        self.italic_button.setFixedSize(24, 24)
        self.italic_button.setStyleSheet("""
            QPushButton {
                font-style: italic;
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                background-color: white;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
            }
            QPushButton:checked {
                background-color: #E6F3FF;
            }
        """)
        self.italic_button.setCheckable(True)
        self.italic_button.clicked.connect(self.toggle_italic)
        self.toolbar.addWidget(self.italic_button)
        
        # 下划线按钮
        self.underline_button = QPushButton()
        self.underline_button.setText("U")
        self.underline_button.setToolTip(self.language_manager.get_text("tooltip_underline"))
        self.underline_button.setFixedSize(24, 24)
        self.underline_button.setStyleSheet("""
            QPushButton {
                text-decoration: underline;
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                background-color: white;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
            }
            QPushButton:checked {
                background-color: #E6F3FF;
            }
        """)
        self.underline_button.setCheckable(True)
        self.underline_button.clicked.connect(self.toggle_underline)
        self.toolbar.addWidget(self.underline_button)
        
        # 粘贴模式切换按钮
        self.paste_mode_button = QPushButton()
        self.paste_mode_button.setText("P")
        self.paste_mode_button.setToolTip(self.language_manager.get_text("tooltip_paste_mode"))
        self.paste_mode_button.setFixedSize(24, 24)
        self.paste_mode_button.setStyleSheet("""
            QPushButton {
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                background-color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
            }
            QPushButton:checked {
                background-color: #E6F3FF;
            }
        """)
        self.paste_mode_button.setCheckable(True)
        self.paste_mode_button.setChecked(True)  # 默认为清洗模式
        self.paste_mode_button.clicked.connect(self.toggle_paste_mode)
        self.toolbar.addWidget(self.paste_mode_button)
        
        # 分隔符
        self.toolbar.addSeparator()
        
        # 文本颜色按钮
        self.color_button = QPushButton()
        self.color_button.setText("A")
        self.color_button.setToolTip(self.language_manager.get_text("tooltip_text_color"))
        self.color_button.setFixedSize(24, 24)
        self.color_button.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: white;
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        self.color_button.clicked.connect(self.choose_text_color)
        self.toolbar.addWidget(self.color_button)
        
        # 背景颜色按钮
        self.bg_color_button = QPushButton()
        self.bg_color_button.setText("A")
        self.bg_color_button.setToolTip(self.language_manager.get_text("tooltip_bg_color"))
        self.bg_color_button.setFixedSize(24, 24)
        self.bg_color_button.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #333333;
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                border-color: #AAAAAA;
            }
        """)
        self.bg_color_button.clicked.connect(self.choose_bg_color)
        self.toolbar.addWidget(self.bg_color_button)
        
        # 分隔符
        self.toolbar.addSeparator()
        
        # 行号切换 (开关按钮)
        # 注意：行号按钮是在content_edit中创建的，这里不需要重复创建
        # self.line_numbers_button.setText(self.language_manager.get_text("btn_line_numbers"))
        # self.line_numbers_button.setToolTip(self.language_manager.get_text("tooltip_line_numbers"))
        # self.line_numbers_button.setCheckable(True)
        # self.line_numbers_button.setChecked(True)
        # self.line_numbers_button.clicked.connect(self.toggle_line_numbers)
        # self.line_numbers_button.setStyleSheet("""
        #     QPushButton {
        #         border: 1px solid #CCCCCC;
        #         border-radius: 3px;
        #         padding: 2px 6px;
        #         background-color: white;
        #     }
        #     QPushButton:hover { border-color: #AAAAAA; }
        #     QPushButton:checked { background-color: #E6F3FF; }
        # """)
        # self.toolbar.addWidget(self.line_numbers_button)
        
        # 自动换行切换 (开关按钮)
        self.word_wrap_button = QPushButton(self.language_manager.get_text("btn_word_wrap"))
        self.word_wrap_button.setToolTip(self.language_manager.get_text("tooltip_word_wrap"))
        self.word_wrap_button.setCheckable(True)
        self.word_wrap_button.clicked.connect(self.toggle_word_wrap)
        self.word_wrap_button.setStyleSheet("""
            QPushButton {
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                padding: 2px 6px;
                background-color: white;
            }
            QPushButton:hover { border-color: #AAAAAA; }
            QPushButton:checked { background-color: #E6F3FF; }
        """)
        self.toolbar.addWidget(self.word_wrap_button)
        
        # 添加弹性空间，将右侧组件推到工具栏末尾
        from PySide6.QtWidgets import QSizePolicy
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred))
        self.toolbar.addWidget(spacer)
        
        # === 右侧：下拉框组件组 ===
        
        # 2. 语言选择 (带下拉框)
        self.language_combo = QComboBox()
        self.language_combo.addItems([
            self.language_manager.get_text("lang_plain_text"),
            self.language_manager.get_text("lang_python"),
            self.language_manager.get_text("lang_javascript"),
            self.language_manager.get_text("lang_html"),
            self.language_manager.get_text("lang_cpp"),
            self.language_manager.get_text("lang_sql")
        ])
        self.language_combo.setCurrentText(self.language_manager.get_text("lang_plain_text"))
        self.language_combo.setToolTip(self.language_manager.get_text("tooltip_language_mode"))
        self.language_combo.currentTextChanged.connect(self.change_language)
        self.toolbar.addWidget(self.language_combo)
        
        # 3. 字体选择 (带下拉框)
        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(QFont("Consolas"))
        self.font_combo.setToolTip(self.language_manager.get_text("tooltip_font"))
        self.font_combo.currentFontChanged.connect(self.change_font)
        # 设置固定宽度和高度，确保与按钮大小一致
        self.font_combo.setFixedWidth(150)
        self.font_combo.setFixedHeight(24)  # 设置与按钮一致的高度
        self.toolbar.addWidget(self.font_combo)
        
        # 4. 字体大小 (带下拉框)
        self.size_combo = QComboBox()
        self.size_combo.addItems(["8", "9", "10", "11", "12", "14", "16", "18", "20", "24", "28", "32", "36", "48"])
        self.size_combo.setCurrentText("12")
        self.size_combo.setToolTip(self.language_manager.get_text("tooltip_font_size"))
        self.size_combo.setFixedWidth(60) # 固定宽度更美观
        self.size_combo.setFixedHeight(24)  # 设置与按钮一致的高度
        self.size_combo.currentTextChanged.connect(self.change_font_size)
        self.toolbar.addWidget(self.size_combo)
    
    def change_font(self, font):
        """更改字体"""
        fmt = QTextCharFormat()
        fmt.setFontFamily(font.family())
        self.content_edit.mergeCurrentCharFormat(fmt)
        self.content_edit.setFocus()  # 重要：操作完后把焦点还给编辑框
    
    def change_font_size(self, size):
        """更改字体大小"""
        fmt = QTextCharFormat()
        fmt.setFontPointSize(float(size))
        self.content_edit.mergeCurrentCharFormat(fmt)
        self.content_edit.setFocus()
    
    def choose_text_color(self):
        """选择文本颜色"""
        from PySide6.QtWidgets import QColorDialog
        
        color = QColorDialog.getColor(self.content_edit.textColor(), self, self.language_manager.get_text("dialog_select_text_color"))
        
        if color.isValid():
            fmt = QTextCharFormat()
            fmt.setForeground(color)
            self.content_edit.mergeCurrentCharFormat(fmt)
            self.content_edit.setFocus()
            
            # 更新按钮图标颜色反馈
            self.color_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color.name()};
                    color: white;
                    border: 1px solid #CCCCCC;
                    border-radius: 3px;
                    font-weight: bold;
                }}
            """)
    
    def choose_bg_color(self):
        """选择背景颜色"""
        from PySide6.QtWidgets import QColorDialog
        
        # 获取当前背景色 (QTextCharFormat)
        current_fmt = self.content_edit.currentCharFormat()
        current_bg = current_fmt.background().color()
        
        color = QColorDialog.getColor(current_bg, self, self.language_manager.get_text("dialog_select_bg_color"))
        
        if color.isValid():
            fmt = QTextCharFormat()
            fmt.setBackground(color)
            self.content_edit.mergeCurrentCharFormat(fmt)
            self.content_edit.setFocus()
            
            # 更新按钮样式
            self.bg_color_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color.name()};
                    color: {'black' if color.lightness() > 128 else 'white'};
                    border: 1px solid #CCCCCC;
                    border-radius: 3px;
                    font-weight: bold;
                }}
            """)
    
    def toggle_bold(self, checked):
        """切换粗体"""
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Bold if checked else QFont.Normal)
        self.content_edit.mergeCurrentCharFormat(fmt)
        self.content_edit.setFocus()
    
    def toggle_italic(self, checked):
        """切换斜体"""
        fmt = QTextCharFormat()
        fmt.setFontItalic(checked)
        self.content_edit.mergeCurrentCharFormat(fmt)
        self.content_edit.setFocus()
    
    def toggle_underline(self, checked):
        """切换下划线"""
        fmt = QTextCharFormat()
        fmt.setFontUnderline(checked)
        self.content_edit.mergeCurrentCharFormat(fmt)
        self.content_edit.setFocus()
    
    def toggle_paste_mode(self, checked):
        """切换粘贴模式"""
        # 更新编辑器的粘贴模式
        self.content_edit.setPasteCleanMode(checked)
        
        # 更新按钮提示文本
        if checked:
            self.paste_mode_button.setToolTip("粘贴模式：仅保留字体和大小（去除颜色、背景等）")
        else:
            self.paste_mode_button.setToolTip("粘贴模式：保留字体、大小和颜色（去除背景等）")
    
    def change_language(self, language):
        """更改语言模式"""
        # 由于使用QTextEdit而不是QScintilla，此方法暂时为空
        # 可以在未来添加语法高亮功能
        
        # 处理多语言的语言名称
        lang_plain_text = self.language_manager.get_text("lang_plain_text")
        lang_python = self.language_manager.get_text("lang_python")
        lang_javascript = self.language_manager.get_text("lang_javascript")
        lang_html = self.language_manager.get_text("lang_html")
        lang_cpp = self.language_manager.get_text("lang_cpp")
        lang_sql = self.language_manager.get_text("lang_sql")
        
        # 将多语言名称映射到标准名称
        if language == lang_plain_text:
            language = "Plain Text"
        elif language == lang_python:
            language = "Python"
        elif language == lang_javascript:
            language = "JavaScript"
        elif language == lang_html:
            language = "HTML"
        elif language == lang_cpp:
            language = "C++"
        elif language == lang_sql:
            language = "SQL"
        
        # 在这里可以添加语法高亮功能
        pass
    
    def toggle_line_numbers(self, checked):
        """切换行号显示"""
        if checked:
            # 启用行号显示
            self.setup_line_numbers()
        else:
            # 禁用行号显示
            self.remove_line_numbers()
    
    def setup_line_numbers(self):
        """设置行号显示"""
        # 检查是否已经有行号区域
        if hasattr(self, 'line_number_area'):
            return
            
        from PySide6.QtWidgets import QWidget
        from PySide6.QtGui import QPainter, QColor
        from PySide6.QtCore import QRect, QSize, Qt
        
        class LineNumberArea(QWidget):
            def __init__(self, editor):
                super().__init__(editor)
                self.editor = editor
                
            def sizeHint(self):
                return QSize(self.editor.line_number_area_width(), 0)
                
            def paintEvent(self, event):
                self.editor.line_number_area_paint_event(event)
        
        # 创建行号区域
        self.line_number_area = LineNumberArea(self.content_edit)
        
        # 添加方法到content_edit
        def line_number_area_width():
            # 计算行号区域的宽度
            digits = 1
            max_value = max(1, self.content_edit.document().blockCount())
            while max_value >= 10:
                max_value /= 10
                digits += 1
            space = 3 + self.content_edit.fontMetrics().horizontalAdvance('9') * digits
            return space
            
        def update_line_number_area():
            # 更新行号区域
            self.content_edit.setViewportMargins(self.content_edit.line_number_area_width(), 0, 0, 0)
            if hasattr(self, 'line_number_area'):
                # 更新行号区域的大小和位置
                cr = self.content_edit.contentsRect()
                self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), 
                                                       self.content_edit.line_number_area_width(), cr.height()))
                # 触发重绘
                self.line_number_area.update()
                    
        def resizeEvent(event):
            # 处理大小变化事件
            cr = self.content_edit.contentsRect()
            self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), 
                                                   self.content_edit.line_number_area_width(), cr.height()))
            # 调用原始的resizeEvent
            QTextEdit.resizeEvent(self.content_edit, event)
            
        def line_number_area_paint_event(event):
            # 绘制行号
            painter = QPainter(self.line_number_area)
            painter.fillRect(event.rect(), QColor('#F8F8F8'))
            
            # 获取可见区域
            block = self.content_edit.document().begin()
            block_number = 0
            
            # 获取滚动条位置
            scrollbar = self.content_edit.verticalScrollBar()
            scroll_value = scrollbar.value()
            
            # 计算可见区域的起始和结束位置
            top = scroll_value
            bottom = top + self.content_edit.viewport().height()
            
            # 遍历所有文本块
            while block.isValid():
                block_layout = block.layout()
                if block_layout:
                    # 获取文本块的位置
                    block_position = block_layout.position()
                    block_height = block_layout.boundingRect().height()
                    
                    # 检查文本块是否在可见区域内
                    if block_position.y() + block_height >= top and block_position.y() <= bottom:
                        number = str(block_number + 1)
                        painter.setPen(QColor('#666666'))
                        painter.drawText(0, int(block_position.y()), self.line_number_area.width(), 
                                       self.content_edit.fontMetrics().height(),
                                       Qt.AlignRight, number)
                
                block = block.next()
                block_number += 1
        
        # 将方法添加到content_edit
        self.content_edit.line_number_area_width = line_number_area_width
        self.content_edit.update_line_number_area = update_line_number_area
        self.content_edit.line_number_area_paint_event = line_number_area_paint_event
        
        # 保存原始resizeEvent
        original_resize_event = self.content_edit.resizeEvent
        self.content_edit.resizeEvent = resizeEvent
        
        # 连接信号 - 只使用document的contentsChanged信号
        self.content_edit.document().contentsChanged.connect(self.content_edit.update_line_number_area)
        
        # 连接滚动条信号以在滚动时更新行号
        self.content_edit.verticalScrollBar().valueChanged.connect(self.content_edit.update_line_number_area)
        
        # 使用定时器定期更新行号区域
        from PySide6.QtCore import QTimer
        self.line_number_update_timer = QTimer(self)
        self.line_number_update_timer.timeout.connect(self.content_edit.update_line_number_area)
        self.line_number_update_timer.start(100)  # 每100毫秒更新一次
        
        # 初始化行号区域
        self.content_edit.update_line_number_area()
    
    def remove_line_numbers(self):
        """移除行号显示"""
        if hasattr(self, 'line_number_area'):
            # 停止定时器
            if hasattr(self, 'line_number_update_timer'):
                self.line_number_update_timer.stop()
                self.line_number_update_timer.deleteLater()
                delattr(self, 'line_number_update_timer')
                
            # 断开信号连接
            try:
                self.content_edit.document().contentsChanged.disconnect(self.content_edit.update_line_number_area)
            except:
                pass
                
            try:
                self.content_edit.verticalScrollBar().valueChanged.disconnect(self.content_edit.update_line_number_area)
            except:
                pass
                
            # 移除行号区域
            self.line_number_area.deleteLater()
            delattr(self, 'line_number_area')
            
            # 重置视口边距
            self.content_edit.setViewportMargins(0, 0, 0, 0)
            
            # 恢复原始resizeEvent
            if hasattr(self.content_edit, '_original_resize_event'):
                self.content_edit.resizeEvent = self.content_edit._original_resize_event
    
    def toggle_word_wrap(self, checked):
        """切换自动换行"""
        self.content_edit.setLineWrapMode(QTextEdit.WidgetWidth if checked else QTextEdit.NoWrap)
    
    def update_word_count(self):
        """更新字数统计"""
        content = self.content_edit.toPlainText()
        # 统计中文字符和英文单词
        import re
        # 中文字符
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', content)
        # 英文单词
        english_words = re.findall(r'\b[a-zA-Z]+\b', content)
        
        total_count = len(chinese_chars) + len(english_words)
        self.word_count_label.setText(f"{total_count} {self.language_manager.get_text('word_count')}")
    
    def update_toolbar_state(self):
        """根据当前光标处的格式，更新工具栏按钮状态"""
        # 获取当前格式
        fmt = self.content_edit.currentCharFormat()
        
        # 1. 更新字体
        self.font_combo.blockSignals(True)
        self.font_combo.setCurrentFont(fmt.font())
        self.font_combo.blockSignals(False)
        
        # 2. 更新字号
        self.size_combo.blockSignals(True)
        self.size_combo.setCurrentText(str(int(fmt.fontPointSize())))
        self.size_combo.blockSignals(False)
        
        # 3. 更新按钮状态
        self.bold_button.blockSignals(True)
        self.bold_button.setChecked(fmt.fontWeight() == QFont.Bold)
        self.bold_button.blockSignals(False)
        
        self.italic_button.blockSignals(True)
        self.italic_button.setChecked(fmt.fontItalic())
        self.italic_button.blockSignals(False)
        
        self.underline_button.blockSignals(True)
        self.underline_button.setChecked(fmt.fontUnderline())
        self.underline_button.blockSignals(False)
        
    def get_note_content(self, note_id):
        """从数据库获取笔记内容"""
        try:
            # 获取父窗口的backend
            parent = self.parent()
            if hasattr(parent, 'backend'):
                backend = parent.backend
                # 获取笔记数据
                notes = backend.get_notes()
                for note in notes:
                    if note.get("id") == note_id:
                        # 同时保存 favorite 状态到 note_data
                        self.note_data["favorite"] = note.get("favorite", False)
                        self.note_data["is_favorite"] = note.get("favorite", False)
                        return note.get("text", "")
            return ""
        except Exception as e:
            print(f"获取笔记内容失败: {e}")
            return ""
    
    def get_note_html_content(self, note_id):
        """从数据库获取笔记HTML内容"""
        try:
            # 获取父窗口的backend
            parent = self.parent()
            if hasattr(parent, 'backend'):
                backend = parent.backend
                # 获取笔记数据
                notes = backend.get_notes()
                for note in notes:
                    if note.get("id") == note_id:
                        # 同时保存 favorite 状态到 note_data
                        self.note_data["favorite"] = note.get("favorite", False)
                        self.note_data["is_favorite"] = note.get("favorite", False)
                        return note.get("html_content", "")
            return ""
        except Exception as e:
            print(f"获取笔记HTML内容失败: {e}")
            return ""
            
    def save_note(self):
        """保存笔记"""
        title = self.title_edit.text().strip()
        content = self.content_edit.toPlainText().strip()
        
        # 获取HTML格式的内容
        html_content = self.content_edit.toHtml()
        
        if not title:
            self.show_notification("请输入笔记标题", error=True)
            return
            
        # 更新笔记数据
        if self.note_data.get("id"):
            # 更新现有笔记，保留原有的 favorite 状态
            self.note_data["title"] = title
            self.note_data["content"] = content
            self.note_data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # 保存HTML内容
            self.note_data["html_content"] = html_content
            # 确保保留原有的 is_favorite 状态
            if "is_favorite" not in self.note_data:
                self.note_data["is_favorite"] = False
            
            # 调用backend的update_note方法
            parent = self.parent()
            if hasattr(parent, 'backend'):
                parent.backend.update_note(self.note_data)
        else:
            # 创建新笔记
            self.note_data = {
                "title": title,
                "content": content,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "is_favorite": False,
                "html_content": html_content
            }
            
            # 调用backend的save_note方法
            parent = self.parent()
            if hasattr(parent, 'backend'):
                parent.backend.save_note(self.note_data)
            
        # 显示保存成功的通知，但不关闭窗口
        self.show_notification("保存成功")
        
    def show_notification(self, message, error=False):
        """显示通知消息"""
        # 创建通知标签
        notification = QLabel(message)
        notification.setStyleSheet(f"""
            QLabel {{
                padding: 8px 12px;
                background-color: {'#FF4444' if error else '#4CAF50'};
                color: white;
                border-radius: 12px;
                font-size: 12px;
                font-weight: bold;
            }}
        """)
        
        # 设置位置（顶部居中显示）
        notification.setParent(self)
        
        # 计算位置 - 窗口顶部中心
        notification_size = notification.sizeHint()
        notification.move(
            (self.width() - notification_size.width()) // 2,
            50  # 距离顶部50像素
        )
        
        # 设置固定大小，防止自动调整
        notification.setFixedSize(notification_size)
        notification.show()
        
        # 2秒后自动隐藏
        from PySide6.QtCore import QTimer
        QTimer.singleShot(2000, notification.deleteLater)
    
    def set_title_bar_white(self):
        """设置Windows原生标题栏为白色"""
        if sys.platform == 'win32':
            try:
                # Windows API 常量
                DWMWA_CAPTION_COLOR = 35
                DWMWA_TEXT_COLOR = 36
                
                # 获取窗口句柄
                hwnd = int(self.winId())
                
                # 设置标题栏背景色为白色
                caption_color = 0x00FFFFFF  # 白色 (AABBGGRR 格式)
                text_color = 0x00000000     # 黑色文字 (AABBGGRR 格式)
                
                # 使用 DwmSetWindowAttribute 设置标题栏颜色
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 
                    DWMWA_CAPTION_COLOR, 
                    ctypes.byref(ctypes.c_int(caption_color)), 
                    ctypes.sizeof(ctypes.c_int)
                )
                
                # 设置标题栏文字颜色为黑色
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 
                    DWMWA_TEXT_COLOR, 
                    ctypes.byref(ctypes.c_int(text_color)), 
                    ctypes.sizeof(ctypes.c_int)
                )
            except Exception as e:
                print(f"设置标题栏颜色失败: {e}")
    
    def showEvent(self, event):
        """窗口显示时确保标题栏颜色正确"""
        super().showEvent(event)
        # 延迟一点时间确保窗口完全显示后再设置标题栏颜色
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self.set_title_bar_white)
    
    def update_ui_language(self):
        """更新界面语言"""
        # 更新窗口标题
        self.setWindowTitle(self.language_manager.get_text("edit_note") if self.note_data else self.language_manager.get_text("new_note"))
        
        # 更新标题占位符
        self.title_edit.setPlaceholderText(self.language_manager.get_text("placeholder_no_title"))
        
        # 更新字数统计
        self.update_word_count()
        
        # 更新工具栏按钮文本和提示
        self.bold_button.setToolTip(self.language_manager.get_text("tooltip_bold"))
        self.italic_button.setToolTip(self.language_manager.get_text("tooltip_italic"))
        self.underline_button.setToolTip(self.language_manager.get_text("tooltip_underline"))
        self.paste_mode_button.setToolTip(self.language_manager.get_text("tooltip_paste_mode"))
        self.color_button.setToolTip(self.language_manager.get_text("tooltip_text_color"))
        self.bg_color_button.setToolTip(self.language_manager.get_text("tooltip_bg_color"))
        
        # 更新content_edit中的按钮文本和提示
        self.content_edit.line_numbers_button.setText(self.language_manager.get_text("btn_line_numbers"))
        self.content_edit.line_numbers_button.setToolTip(self.language_manager.get_text("tooltip_line_numbers"))
        self.content_edit.word_wrap_button.setText(self.language_manager.get_text("btn_word_wrap"))
        self.content_edit.word_wrap_button.setToolTip(self.language_manager.get_text("tooltip_word_wrap"))
        self.content_edit.language_combo.setToolTip(self.language_manager.get_text("tooltip_language_mode"))
        self.content_edit.font_combo.setToolTip(self.language_manager.get_text("tooltip_font"))
        self.content_edit.size_combo.setToolTip(self.language_manager.get_text("tooltip_font_size"))
        
        # 更新语言下拉框选项
        current_language = self.content_edit.language_combo.currentText()
        self.content_edit.language_combo.clear()
        self.content_edit.language_combo.addItems([
            self.language_manager.get_text("lang_plain_text"),
            self.language_manager.get_text("lang_python"),
            self.language_manager.get_text("lang_javascript"),
            self.language_manager.get_text("lang_html"),
            self.language_manager.get_text("lang_cpp"),
            self.language_manager.get_text("lang_sql")
        ])
        
        # 尝试恢复之前选择的语言
        if current_language in [
            self.language_manager.get_text("lang_plain_text"),
            self.language_manager.get_text("lang_python"),
            self.language_manager.get_text("lang_javascript"),
            self.language_manager.get_text("lang_html"),
            self.language_manager.get_text("lang_cpp"),
            self.language_manager.get_text("lang_sql")
        ]:
            self.content_edit.language_combo.setCurrentText(current_language)
        else:
            self.content_edit.language_combo.setCurrentText(self.language_manager.get_text("lang_plain_text"))
