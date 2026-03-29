# category.py
from datetime import datetime
import sqlite3
from .backend import ClipboardBackend

class CategoryManager:
    """分类管理器，用于处理不同类型的内容"""
    
    def __init__(self, backend):
        self.backend = backend
        self.current_category = "clipboard"  # 默认显示剪贴板内容
        self.show_all = False  # 默认只显示前500条
        
    def set_category(self, category):
        """设置当前分类"""
        self.current_category = category
        # 通知backend当前分类
        self.backend._current_category = category
        
    def set_show_all(self, show_all):
        """设置是否显示全部记录"""
        self.show_all = show_all
        
    def get_category_data(self, limit=50):
        """根据当前分类获取数据"""
        # 如果show_all为True，使用一个非常大的limit
        actual_limit = 999999 if self.show_all else 500
        if self.current_category == "clipboard":
            return self.backend.get_history(actual_limit)
        elif self.current_category == "favorite":
            return self.backend.get_favorites(actual_limit)
        elif self.current_category == "image":
            return self.backend.get_images(actual_limit)
        elif self.current_category == "file":
            return self.backend.get_files(actual_limit)
        elif self.current_category == "notebook":
            return self.backend.get_notebook(actual_limit)  # 添加记事本类别支持
        else:
            return []
    
    def get_total_count(self):
        """获取当前分类的总记录数"""
        return self.backend.get_total_count()
    
    def save_content(self, text, content_type=None):
        """保存内容，自动检测类型并标记"""
        # 如果没有指定类型，自动检测
        if content_type is None:
            content_type = self._detect_content_type(text)
        return self.backend.save_content_with_type(text, content_type)
    
    def _detect_content_type(self, text):
        """检测内容类型"""
        import os
        import re
        
        # 检查是否是新的图片引用格式
        if text.startswith('IMG_REF:'):
            return "image"
            
        # 检查是否是图片base64编码
        if text.startswith('data:image/') and ';base64,' in text:
            return "image"
            
        # 检查是否是图片路径
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico']
        if any(text.lower().endswith(ext) for ext in image_extensions):
            return "image"
        
        # 检查是否是文件路径
        # Windows路径: C:\path\to\file 或 \\server\share\file
        # Unix路径: /path/to/file 或 ~/path/to/file
        # 支持混合路径: B:/path/to/file
        if (len(text) < 260 and  # Windows路径长度限制
            (os.path.sep in text or 
             '/' in text or  # 添加对Unix风格路径分隔符的支持
             ('~' in text and '/' in text) or
             (len(text) > 2 and text[1] == ':' and text[2] == '\\'))):
            # 检查是否有文件扩展名
            if '.' in os.path.basename(text):
                return "file"
            
        # 默认为文本类型
        return "text"
    
    def toggle_favorite(self, index):
        """切换收藏状态"""
        return self.backend.toggle_favorite(index)
    
    def delete_item(self, index):
        """删除指定索引的项目"""
        return self.backend.delete_item(index)
    
    def batch_delete_by_time(self, time_range):
        """根据时间范围批量删除记录
        
        Args:
            time_range: 时间范围，可选值: 'today', '7days', '30days', 'all'
        
        Returns:
            int: 删除的记录数量
        """
        return self.backend.batch_delete_by_time(time_range)
    
    def save_note(self, note_data):
        """保存笔记数据到数据库"""
        return self.backend.save_note(note_data)