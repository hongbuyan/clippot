# word_segmenter.py
"""
中文分词工具模块
使用 jieba 库进行中文分词，支持多种分词模式
"""

import re
from typing import List, Tuple, Optional

# 尝试导入 jieba，如果未安装则使用简单分词
try:
    import jieba
    import jieba.posseg as pseg
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False
    print("Warning: jieba not installed. Using simple word segmentation.")


class WordSegmenter:
    """中文分词器"""
    
    def __init__(self):
        self.jieba_available = JIEBA_AVAILABLE
        
    def segment(self, text: str, mode: str = 'default') -> List[str]:
        """
        对文本进行分词
        
        Args:
            text: 待分词的文本
            mode: 分词模式
                - 'default': 精确模式
                - 'full': 全模式
                - 'search': 搜索引擎模式
                
        Returns:
            分词结果列表
        """
        if not text or not text.strip():
            return []
            
        text = text.strip()
        
        if self.jieba_available:
            try:
                if mode == 'full':
                    # 全模式，把句子中所有可以成词的词语都扫描出来
                    words = list(jieba.cut(text, cut_all=True))
                elif mode == 'search':
                    # 搜索引擎模式，在精确模式基础上对长词再次切分
                    words = list(jieba.cut_for_search(text))
                else:
                    # 默认精确模式，适合文本分析
                    words = list(jieba.cut(text, cut_all=False))
                
                # 过滤空字符串和纯空白字符
                words = [w.strip() for w in words if w.strip()]
                return words
            except Exception as e:
                print(f"Jieba segmentation error: {e}")
                return self._simple_segment(text)
        else:
            return self._simple_segment(text)
    
    def segment_with_pos(self, text: str) -> List[Tuple[str, str]]:
        """
        分词并返回词性标注
        
        Args:
            text: 待分词的文本
            
        Returns:
            [(词语, 词性), ...] 的列表
        """
        if not text or not text.strip():
            return []
            
        text = text.strip()
        
        if self.jieba_available:
            try:
                words_pos = list(pseg.cut(text))
                # 过滤空字符串
                return [(w.word.strip(), w.flag) for w in words_pos if w.word.strip()]
            except Exception as e:
                print(f"Jieba posseg error: {e}")
                return self._simple_segment_with_pos(text)
        else:
            return self._simple_segment_with_pos(text)
    
    def _simple_segment(self, text: str) -> List[str]:
        """
        简单分词方法（当 jieba 不可用时使用）
        按中英文、数字、标点进行基础分割
        """
        # 匹配中文字符、英文单词、数字
        pattern = r'[\u4e00-\u9fff]+|[a-zA-Z]+|\d+|[^\w\s]'
        words = re.findall(pattern, text)
        return [w.strip() for w in words if w.strip()]
    
    def _simple_segment_with_pos(self, text: str) -> List[Tuple[str, str]]:
        """
        简单分词并标注词性（当 jieba 不可用时使用）
        """
        words = self._simple_segment(text)
        result = []
        for word in words:
            if re.match(r'^[\u4e00-\u9fff]+$', word):
                pos = 'n'  # 中文默认为名词
            elif re.match(r'^[a-zA-Z]+$', word):
                pos = 'eng'  # 英文
            elif re.match(r'^\d+$', word):
                pos = 'm'  # 数字
            else:
                pos = 'x'  # 其他
            result.append((word, pos))
        return result
    
    def get_word_frequency(self, text: str) -> dict:
        """
        获取词频统计
        
        Args:
            text: 待分析的文本
            
        Returns:
            {词语: 出现次数} 的字典
        """
        words = self.segment(text)
        freq = {}
        for word in words:
            if len(word) > 1:  # 忽略单字，只统计词语
                freq[word] = freq.get(word, 0) + 1
        return freq
    
    def extract_keywords(self, text: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """
        提取关键词（需要 jieba.analyse）
        
        Args:
            text: 待分析的文本
            top_k: 返回前 k 个关键词
            
        Returns:
            [(关键词, 权重), ...] 的列表
        """
        if not self.jieba_available:
            # 如果 jieba 不可用，使用简单的词频统计
            freq = self.get_word_frequency(text)
            sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
            # 归一化权重
            if sorted_words:
                max_count = sorted_words[0][1]
                return [(word, count/max_count) for word, count in sorted_words[:top_k]]
            return []
        
        try:
            import jieba.analyse
            keywords = jieba.analyse.extract_tags(text, topK=top_k, withWeight=True)
            return keywords
        except Exception as e:
            print(f"Keyword extraction error: {e}")
            return []
    
    def format_segmentation_result(self, words: List[str], separator: str = ' / ') -> str:
        """
        格式化分词结果
        
        Args:
            words: 分词列表
            separator: 分隔符
            
        Returns:
            格式化后的字符串
        """
        return separator.join(words)


# 全局分词器实例
segmenter = WordSegmenter()


def segment_text(text: str, mode: str = 'default') -> List[str]:
    """便捷函数：对文本进行分词"""
    return segmenter.segment(text, mode)


def format_words(words: List[str], separator: str = ' / ') -> str:
    """便捷函数：格式化分词结果"""
    return segmenter.format_segmentation_result(words, separator)
