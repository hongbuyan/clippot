# backend.py
import sqlite3
import base64
import os
import sys
import json
import glob
from datetime import datetime
from cryptography.fernet import Fernet

MAX_VOLUME_SIZE = 5 * 1024 * 1024  # 5MB

def get_app_dir():
    """获取应用程序目录（支持打包后路径）"""
    if getattr(sys, 'frozen', False):
        # 打包后：exe所在目录
        return os.path.dirname(sys.executable)
    else:
        # 开发环境：项目根目录
        return os.path.join(os.path.dirname(__file__), '..', '..')

class ClipboardBackend:
    def __init__(self, key):
        app_dir = get_app_dir()
        self.data_dir = os.path.join(app_dir, 'data')
        self.db_base_name = 'clipboard_history'
        self.config_file = os.path.join(app_dir, 'config.json')
        
        if isinstance(key, str):
            self.key = key.encode()
        else:
            self.key = key
            
        self.cipher = Fernet(self.key)
        self._init_all_volumes()

    def _get_db_name(self, volume_num=None):
        """获取指定卷的数据库文件名"""
        if volume_num is None:
            volume_num = self._get_current_volume()
        return os.path.join(self.data_dir, f'{self.db_base_name}_vol{volume_num}.db')
    
    def _get_current_volume(self):
        """获取当前卷号"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get('current_volume', 1)
        except:
            pass
        return 1
    
    def _set_current_volume(self, volume_num):
        """设置当前卷号"""
        try:
            config = {}
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            config['current_volume'] = volume_num
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"设置当前卷号失败: {e}")
    
    def _get_all_volumes(self):
        """获取所有卷文件列表"""
        pattern = os.path.join(self.data_dir, f'{self.db_base_name}_vol*.db')
        volumes = sorted(glob.glob(pattern))
        if not volumes:
            return [self._get_db_name(1)]
        return volumes
    
    def _get_volume_size(self, volume_num=None):
        """获取指定卷的文件大小"""
        db_path = self._get_db_name(volume_num)
        if os.path.exists(db_path):
            return os.path.getsize(db_path)
        return 0
    
    def _should_create_new_volume(self):
        """检查是否需要创建新卷"""
        current_size = self._get_volume_size()
        return current_size >= MAX_VOLUME_SIZE
    
    def _create_new_volume(self):
        """创建新卷"""
        current_vol = self._get_current_volume()
        new_vol = current_vol + 1
        new_db_path = self._get_db_name(new_vol)
        self._init_volume(new_db_path)
        self._set_current_volume(new_vol)
        print(f"创建新卷: vol{new_vol}")
        return new_vol
    
    def _init_volume(self, db_path):
        """初始化单个卷的数据库"""
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS history
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      content BLOB, 
                      timestamp TEXT,
                      favorite INTEGER DEFAULT 0,
                      content_type TEXT DEFAULT "text")''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS notes
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      title TEXT,
                      content BLOB,
                      created_at TEXT,
                      updated_at TEXT,
                      favorite INTEGER DEFAULT 0)''')
        
        c.execute("PRAGMA table_info(history)")
        columns = [column[1] for column in c.fetchall()]
        if 'favorite' not in columns:
            c.execute("ALTER TABLE history ADD COLUMN favorite INTEGER DEFAULT 0")
        if 'content_type' not in columns:
            c.execute("ALTER TABLE history ADD COLUMN content_type TEXT DEFAULT 'text'")
            
        conn.commit()
        conn.close()

    def _init_all_volumes(self):
        """初始化所有卷"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        
        volumes = self._get_all_volumes()
        for vol_path in volumes:
            self._init_volume(vol_path)
        
        if not volumes:
            self._init_volume(self._get_db_name(1))

    def _get_last_record_from_all_volumes(self):
        """从所有卷中获取最后一条记录"""
        volumes = self._get_all_volumes()
        for vol_path in reversed(volumes):
            try:
                conn = sqlite3.connect(vol_path)
                c = conn.cursor()
                c.execute("SELECT content FROM history ORDER BY id DESC LIMIT 1")
                row = c.fetchone()
                conn.close()
                if row:
                    return row[0]
            except:
                pass
        return None

    def save_content(self, text):
        """保存内容，如果重复则跳过"""
        if not text or not text.strip(): 
            return False
        
        # 检查是否需要创建新卷
        if self._should_create_new_volume():
            self._create_new_volume()
        
        db_name = self._get_db_name()
        
        # 简单查重：对比最后一条记录
        last_content = self._get_last_record_from_all_volumes()
        if last_content:
            try:
                last_text = self.cipher.decrypt(last_content).decode()
                if last_text == text:
                    return False
            except:
                pass

        encrypted = self.cipher.encrypt(text.encode())
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        conn = sqlite3.connect(db_name)
        c = conn.cursor()
        
        c.execute("PRAGMA table_info(history)")
        columns = [column[1] for column in c.fetchall()]
        has_favorite = 'favorite' in columns
        has_content_type = 'content_type' in columns
        
        if has_favorite and has_content_type:
            c.execute("INSERT INTO history (content, timestamp, favorite, content_type) VALUES (?, ?, ?, ?)", 
                     (encrypted, timestamp, 0, "text"))
        elif has_favorite:
            c.execute("INSERT INTO history (content, timestamp, favorite) VALUES (?, ?, ?)", 
                     (encrypted, timestamp, 0))
        else:
            c.execute("INSERT INTO history (content, timestamp) VALUES (?, ?)", 
                     (encrypted, timestamp))
            
        conn.commit()
        conn.close()
        
        self._check_and_enforce_limits()
        
        return True
    
    def save_content_with_type(self, text, content_type="text"):
        """保存内容并标记类型，如果重复则跳过"""
        if not text or not text.strip(): 
            return False
        
        # 检查是否需要创建新卷
        if self._should_create_new_volume():
            self._create_new_volume()
        
        db_name = self._get_db_name()
        
        # 简单查重：对比最后一条记录
        last_content = self._get_last_record_from_all_volumes()
        if last_content:
            try:
                last_text = self.cipher.decrypt(last_content).decode()
                if last_text == text:
                    return False
            except:
                pass

        encrypted = self.cipher.encrypt(text.encode())
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        conn = sqlite3.connect(db_name)
        c = conn.cursor()
        
        c.execute("PRAGMA table_info(history)")
        columns = [column[1] for column in c.fetchall()]
        has_favorite = 'favorite' in columns
        has_content_type = 'content_type' in columns
        
        if not has_content_type:
            c.execute("ALTER TABLE history ADD COLUMN content_type TEXT DEFAULT 'text'")
            has_content_type = True
        
        if has_favorite and has_content_type:
            c.execute("INSERT INTO history (content, timestamp, favorite, content_type) VALUES (?, ?, ?, ?)", 
                     (encrypted, timestamp, 0, content_type))
        elif has_favorite:
            c.execute("INSERT INTO history (content, timestamp, favorite) VALUES (?, ?, ?)", 
                     (encrypted, timestamp, 0))
        else:
            c.execute("INSERT INTO history (content, timestamp) VALUES (?, ?)", 
                     (encrypted, timestamp))
            
        conn.commit()
        conn.close()
        
        self._check_and_enforce_limits()
        
        return True

    def get_total_count(self):
        """获取历史记录总数（所有卷）"""
        total = 0
        volumes = self._get_all_volumes()
        for vol_path in volumes:
            try:
                conn = sqlite3.connect(vol_path)
                c = conn.cursor()
                c.execute("SELECT COUNT(*) FROM history")
                total += c.fetchone()[0]
                conn.close()
            except:
                pass
        return total

    def get_history(self, limit=50):
        """获取最近的历史记录（从所有卷中获取）"""
        results = []
        volumes = self._get_all_volumes()
        
        # 从最新的卷开始读取
        for vol_path in reversed(volumes):
            if len(results) >= limit:
                break
                
            try:
                conn = sqlite3.connect(vol_path)
                c = conn.cursor()
                
                c.execute("PRAGMA table_info(history)")
                columns = [column[1] for column in c.fetchall()]
                has_favorite = 'favorite' in columns
                has_content_type = 'content_type' in columns
                
                if not has_content_type:
                    c.execute("ALTER TABLE history ADD COLUMN content_type TEXT DEFAULT 'text'")
                    has_content_type = True
                
                remaining = limit - len(results)
                
                if has_favorite and has_content_type:
                    c.execute("SELECT content, timestamp, favorite, content_type FROM history ORDER BY id DESC LIMIT ?", (remaining,))
                elif has_favorite:
                    c.execute("SELECT content, timestamp, favorite FROM history ORDER BY id DESC LIMIT ?", (remaining,))
                else:
                    c.execute("SELECT content, timestamp FROM history ORDER BY id DESC LIMIT ?", (remaining,))
                    
                rows = c.fetchall()
                conn.close()

                for row in rows:
                    try:
                        decrypted = self.cipher.decrypt(row[0]).decode()
                        if has_favorite and has_content_type:
                            results.append({
                                "text": decrypted, 
                                "time": row[1],
                                "favorite": bool(row[2]),
                                "content_type": row[3],
                                "preview": decrypted.replace('\n', ' ')[:40]
                            })
                        elif has_favorite:
                            results.append({
                                "text": decrypted, 
                                "time": row[1],
                                "favorite": bool(row[2]),
                                "content_type": "text",
                                "preview": decrypted.replace('\n', ' ')[:40]
                            })
                        else:
                            results.append({
                                "text": decrypted, 
                                "time": row[1],
                                "favorite": False,
                                "content_type": "text",
                                "preview": decrypted.replace('\n', ' ')[:40]
                            })
                    except Exception as e:
                        print(f"解密失败: {e}")
                        results.append({"text": "", "time": row[1], "favorite": False, "content_type": "text", "preview": "[解密失败]"})
                        
            except Exception as e:
                print(f"读取卷 {vol_path} 失败: {e}")
        
        return results
    
    def save_note(self, note_data):
        """保存笔记数据到数据库"""
        try:
            conn = sqlite3.connect(self._get_db_name())
            c = conn.cursor()
            
            # 获取笔记数据
            title = note_data.get("title", "")
            content = note_data.get("content", "")
            html_content = note_data.get("html_content", "")
            created_at = note_data.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            updated_at = note_data.get("updated_at", created_at)
            favorite = note_data.get("is_favorite", False)
            
            # 加密内容
            encrypted_content = self.cipher.encrypt(content.encode())
            
            # 检查是否有html_content列
            c.execute("PRAGMA table_info(notes)")
            columns = [column[1] for column in c.fetchall()]
            has_html_content = 'html_content' in columns
            
            # 如果没有html_content列，则添加
            if not has_html_content:
                c.execute("ALTER TABLE notes ADD COLUMN html_content BLOB")
                has_html_content = True
            
            # 加密HTML内容（如果有）
            encrypted_html = None
            if html_content:
                encrypted_html = self.cipher.encrypt(html_content.encode())
            
            # 插入笔记记录
            if has_html_content:
                c.execute(
                    "INSERT INTO notes (title, content, html_content, created_at, updated_at, favorite) VALUES (?, ?, ?, ?, ?, ?)",
                    (title, encrypted_content, encrypted_html, created_at, updated_at, 1 if favorite else 0)
                )
            else:
                c.execute(
                    "INSERT INTO notes (title, content, created_at, updated_at, favorite) VALUES (?, ?, ?, ?, ?)",
                    (title, encrypted_content, created_at, updated_at, 1 if favorite else 0)
                )
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"保存笔记失败: {e}")
            return False
    
    def update_note(self, note_data):
        """更新笔记数据到数据库"""
        try:
            note_id = note_data.get("id")
            if not note_id:
                print("更新笔记失败: 缺少笔记ID")
                return False
                
            conn = sqlite3.connect(self._get_db_name())
            c = conn.cursor()
            
            # 获取笔记数据
            title = note_data.get("title", "")
            content = note_data.get("content", "")
            html_content = note_data.get("html_content", "")
            updated_at = note_data.get("updated_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            # 同时检查 favorite 和 is_favorite 字段，确保兼容性
            favorite = note_data.get("is_favorite", note_data.get("favorite", False))
            
            # 加密内容
            encrypted_content = self.cipher.encrypt(content.encode())
            
            # 检查是否有html_content列
            c.execute("PRAGMA table_info(notes)")
            columns = [column[1] for column in c.fetchall()]
            has_html_content = 'html_content' in columns
            
            # 如果没有html_content列，则添加
            if not has_html_content:
                c.execute("ALTER TABLE notes ADD COLUMN html_content BLOB")
                has_html_content = True
            
            # 加密HTML内容（如果有）
            encrypted_html = None
            if html_content:
                encrypted_html = self.cipher.encrypt(html_content.encode())
            
            # 更新笔记记录
            if has_html_content:
                c.execute(
                    "UPDATE notes SET title = ?, content = ?, html_content = ?, updated_at = ?, favorite = ? WHERE id = ?",
                    (title, encrypted_content, encrypted_html, updated_at, 1 if favorite else 0, note_id)
                )
            else:
                c.execute(
                    "UPDATE notes SET title = ?, content = ?, updated_at = ?, favorite = ? WHERE id = ?",
                    (title, encrypted_content, updated_at, 1 if favorite else 0, note_id)
                )
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"更新笔记失败: {e}")
            return False
    
    def toggle_note_favorite(self, note_id):
        """切换笔记的收藏状态"""
        try:
            conn = sqlite3.connect(self._get_db_name())
            c = conn.cursor()
            
            # 获取当前收藏状态
            c.execute("SELECT favorite FROM notes WHERE id = ?", (note_id,))
            result = c.fetchone()
            
            if result:
                current_favorite = result[0]
                new_favorite = 0 if current_favorite else 1
                
                # 更新收藏状态
                c.execute("UPDATE notes SET favorite = ? WHERE id = ?", (new_favorite, note_id))
                conn.commit()
                conn.close()
                return True
            else:
                print(f"未找到ID为 {note_id} 的笔记")
                conn.close()
                return False
                
        except Exception as e:
            print(f"切换笔记收藏状态失败: {e}")
            return False
    
    def get_notes(self):
        """获取所有笔记数据"""
        try:
            conn = sqlite3.connect(self._get_db_name())
            c = conn.cursor()
            
            # 检查是否有html_content列
            c.execute("PRAGMA table_info(notes)")
            columns = [column[1] for column in c.fetchall()]
            has_html_content = 'html_content' in columns
            
            # 查询所有笔记，置顶的笔记排在前面
            if has_html_content:
                c.execute("SELECT id, title, content, html_content, created_at, updated_at, favorite FROM notes ORDER BY favorite DESC, id DESC")
            else:
                c.execute("SELECT id, title, content, created_at, updated_at, favorite FROM notes ORDER BY favorite DESC, id DESC")
            
            notes = []
            
            for row in c.fetchall():
                try:
                    # 解密内容
                    decrypted = self.cipher.decrypt(row[2]).decode('utf-8')
                    note_data = {
                        "id": row[0],
                        "title": row[1],
                        "text": decrypted,
                        "created_at": row[3] if not has_html_content else row[4],
                        "updated_at": row[4] if not has_html_content else row[5],
                        "favorite": bool(row[5] if not has_html_content else row[6])
                    }
                    
                    # 如果有HTML内容，也解密并添加
                    if has_html_content and row[3]:
                        try:
                            html_decrypted = self.cipher.decrypt(row[3]).decode('utf-8')
                            note_data["html_content"] = html_decrypted
                        except:
                            pass
                    
                    notes.append(note_data)
                except Exception as e:
                    print(f"解密笔记失败: {e}")
                    # 创建基本笔记数据
                    note_data = {
                        "id": row[0],
                        "title": row[1],
                        "text": "[解密失败]",
                        "created_at": row[3] if not has_html_content else row[4],
                        "updated_at": row[4] if not has_html_content else row[5],
                        "favorite": bool(row[5] if not has_html_content else row[6])
                    }
                    notes.append(note_data)
            
            conn.close()
            return notes
            
        except Exception as e:
            print(f"获取笔记失败: {e}")
            return []
    
    def toggle_favorite(self, item_index):
        """切换指定项目的收藏状态"""
        # 获取当前分类
        current_category = getattr(self, '_current_category', 'clipboard')
        
        conn = sqlite3.connect(self._get_db_name())
        c = conn.cursor()
        
        # 检查是否有favorite列
        c.execute("PRAGMA table_info(history)")
        columns = [column[1] for column in c.fetchall()]
        has_favorite = 'favorite' in columns
        
        if not has_favorite:
            # 如果没有favorite列，添加它
            c.execute("ALTER TABLE history ADD COLUMN favorite INTEGER DEFAULT 0")
            
        # 根据当前分类获取指定索引项的ID和当前收藏状态
        if current_category == 'clipboard':
            c.execute("SELECT COUNT(*) FROM history")
            total_count = c.fetchone()[0]
            if item_index >= total_count or item_index < 0:
                conn.close()
                return False
            c.execute("SELECT id, favorite FROM history ORDER BY id DESC LIMIT 1 OFFSET ?", (item_index,))
        elif current_category == 'favorite':
            c.execute("SELECT COUNT(*) FROM history WHERE favorite = 1")
            total_count = c.fetchone()[0]
            if item_index >= total_count or item_index < 0:
                conn.close()
                return False
            c.execute("SELECT id, favorite FROM history WHERE favorite = 1 ORDER BY id DESC LIMIT 1 OFFSET ?", (item_index,))
        elif current_category == 'image':
            c.execute("SELECT COUNT(*) FROM history WHERE content_type = 'image'")
            total_count = c.fetchone()[0]
            if item_index >= total_count or item_index < 0:
                conn.close()
                return False
            c.execute("SELECT id, favorite FROM history WHERE content_type = 'image' ORDER BY id DESC LIMIT 1 OFFSET ?", (item_index,))
        elif current_category == 'file':
            c.execute("SELECT COUNT(*) FROM history WHERE content_type = 'file'")
            total_count = c.fetchone()[0]
            if item_index >= total_count or item_index < 0:
                conn.close()
                return False
            c.execute("SELECT id, favorite FROM history WHERE content_type = 'file' ORDER BY id DESC LIMIT 1 OFFSET ?", (item_index,))
        else:
            c.execute("SELECT COUNT(*) FROM history")
            total_count = c.fetchone()[0]
            if item_index >= total_count or item_index < 0:
                conn.close()
                return False
            c.execute("SELECT id, favorite FROM history ORDER BY id DESC LIMIT 1 OFFSET ?", (item_index,))
            
        result = c.fetchone()
        
        if result:
            item_id, current_favorite = result
            new_favorite = 0 if current_favorite else 1
            c.execute("UPDATE history SET favorite = ? WHERE id = ?", (new_favorite, item_id))
            conn.commit()
            conn.close()
            return True
        
        conn.close()
        return False
    
    def get_favorites(self, limit=50):
        """获取收藏的内容"""
        conn = sqlite3.connect(self._get_db_name())
        c = conn.cursor()
        
        # 检查是否有favorite列和content_type列
        c.execute("PRAGMA table_info(history)")
        columns = [column[1] for column in c.fetchall()]
        has_favorite = 'favorite' in columns
        has_content_type = 'content_type' in columns
        
        # 检查并添加content_type列（如果不存在）
        if not has_content_type:
            c.execute("ALTER TABLE history ADD COLUMN content_type TEXT DEFAULT 'text'")
            has_content_type = True
        
        if not has_favorite:
            conn.close()
            return []
            
        if has_content_type:
            c.execute("SELECT content, timestamp, favorite, content_type FROM history WHERE favorite = 1 ORDER BY id DESC LIMIT ?", (limit,))
        else:
            c.execute("SELECT content, timestamp, favorite FROM history WHERE favorite = 1 ORDER BY id DESC LIMIT ?", (limit,))
            
        rows = c.fetchall()
        conn.close()

        results = []
        for row in rows:
            try:
                decrypted = self.cipher.decrypt(row[0]).decode()
                if has_content_type:
                    results.append({
                        "text": decrypted, 
                        "time": row[1],
                        "favorite": bool(row[2]),
                        "content_type": row[3],
                        "preview": decrypted.replace('\n', ' ')[:40] # 预览前40字
                    })
                else:
                    results.append({
                        "text": decrypted, 
                        "time": row[1],
                        "favorite": bool(row[2]),
                        "content_type": "text",  # 默认为文本类型
                        "preview": decrypted.replace('\n', ' ')[:40] # 预览前40字
                    })
            except Exception as e:
                print(f"解密失败: {e}")
                if has_content_type:
                    results.append({"text": "", "time": row[1], "favorite": False, "content_type": "text", "preview": "[解密失败]"})
                else:
                    results.append({"text": "", "time": row[1], "favorite": False, "content_type": "text", "preview": "[解密失败]"})
        return results
    
    def get_images(self, limit=50):
        """获取图片类型的内容"""
        conn = sqlite3.connect(self._get_db_name())
        c = conn.cursor()
        
        # 检查是否有content_type列
        c.execute("PRAGMA table_info(history)")
        columns = [column[1] for column in c.fetchall()]
        has_content_type = 'content_type' in columns
        
        # 检查并添加content_type列（如果不存在）
        if not has_content_type:
            c.execute("ALTER TABLE history ADD COLUMN content_type TEXT DEFAULT 'text'")
            has_content_type = True
        
        c.execute("SELECT content, timestamp, favorite, content_type FROM history WHERE content_type = 'image' ORDER BY id DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        conn.close()

        results = []
        for row in rows:
            try:
                decrypted = self.cipher.decrypt(row[0]).decode()
                results.append({
                    "text": decrypted, 
                    "time": row[1],
                    "favorite": bool(row[2]),
                    "content_type": row[3],
                    "preview": decrypted.replace('\n', ' ')[:40] # 预览前40字
                })
            except Exception as e:
                print(f"解密失败: {e}")
                results.append({"text": "", "time": row[1], "favorite": False, "content_type": "image", "preview": "[解密失败]"})
        return results
    
    def get_files(self, limit=50):
        """获取文件类型的内容"""
        conn = sqlite3.connect(self._get_db_name())
        c = conn.cursor()
        
        # 检查是否有content_type列
        c.execute("PRAGMA table_info(history)")
        columns = [column[1] for column in c.fetchall()]
        has_content_type = 'content_type' in columns
        
        # 检查并添加content_type列（如果不存在）
        if not has_content_type:
            c.execute("ALTER TABLE history ADD COLUMN content_type TEXT DEFAULT 'text'")
            has_content_type = True
        
        c.execute("SELECT content, timestamp, favorite, content_type FROM history WHERE content_type = 'file' ORDER BY id DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        conn.close()

        results = []
        for row in rows:
            try:
                decrypted = self.cipher.decrypt(row[0]).decode()
                results.append({
                    "text": decrypted, 
                    "time": row[1],
                    "favorite": bool(row[2]),
                    "content_type": row[3],
                    "preview": decrypted.replace('\n', ' ')[:40] # 预览前40字
                })
            except Exception as e:
                print(f"解密失败: {e}")
                results.append({"text": "", "time": row[1], "favorite": False, "content_type": "file", "preview": "[解密失败]"})
        return results
    
    def get_notebook(self, limit=50):
        """获取记事本类型的内容"""
        conn = sqlite3.connect(self._get_db_name())
        c = conn.cursor()
        
        # 从notes表获取数据，置顶的笔记排在前面
        c.execute("SELECT id, title, content, created_at, updated_at, favorite FROM notes ORDER BY favorite DESC, id DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        conn.close()

        results = []
        for row in rows:
            note_id, title, encrypted_content, created_at, updated_at, favorite = row
            try:
                # 解密内容
                if encrypted_content:
                    content = self.cipher.decrypt(encrypted_content).decode()
                else:
                    content = ""
                
                # 创建预览文本
                preview = content.replace('\n', ' ')[:40] if content else ""
                
                results.append({
                    "id": note_id,
                    "title": title,
                    "text": content,
                    "time": created_at,
                    "updated_at": updated_at,
                    "favorite": bool(favorite),
                    "content_type": "note",
                    "preview": preview
                })
            except Exception as e:
                print(f"解密笔记失败: {e}")
                results.append({
                    "id": note_id,
                    "title": title,
                    "text": "",
                    "time": created_at,
                    "updated_at": updated_at,
                    "favorite": False,
                    "content_type": "note",
                    "preview": "[解密失败]"
                })
        return results
    
    def delete_item(self, index):
        """删除指定索引的项目"""
        try:
            conn = sqlite3.connect(self._get_db_name())
            c = conn.cursor()
            
            # 获取当前分类的数据总数
            current_category = getattr(self, '_current_category', 'clipboard')
            
            if current_category == 'clipboard':
                c.execute("SELECT COUNT(*) FROM history")
            elif current_category == 'favorite':
                c.execute("SELECT COUNT(*) FROM history WHERE favorite = 1")
            elif current_category == 'image':
                c.execute("SELECT COUNT(*) FROM history WHERE content_type = 'image'")
            elif current_category == 'file':
                c.execute("SELECT COUNT(*) FROM history WHERE content_type = 'file'")
            elif current_category == 'notebook':
                c.execute("SELECT COUNT(*) FROM notes")
            else:
                c.execute("SELECT COUNT(*) FROM history")
                
            total_count = c.fetchone()[0]
            
            # 确保索引有效
            if index >= total_count or index < 0:
                conn.close()
                return False
            
            # 获取要删除的记录ID
            if current_category == 'clipboard':
                c.execute("SELECT id FROM history ORDER BY id DESC LIMIT 1 OFFSET ?", (index,))
            elif current_category == 'favorite':
                c.execute("SELECT id FROM history WHERE favorite = 1 ORDER BY id DESC LIMIT 1 OFFSET ?", (index,))
            elif current_category == 'image':
                c.execute("SELECT id FROM history WHERE content_type = 'image' ORDER BY id DESC LIMIT 1 OFFSET ?", (index,))
            elif current_category == 'file':
                c.execute("SELECT id FROM history WHERE content_type = 'file' ORDER BY id DESC LIMIT 1 OFFSET ?", (index,))
            elif current_category == 'notebook':
                c.execute("SELECT id FROM notes ORDER BY id DESC LIMIT 1 OFFSET ?", (index,))
            else:
                c.execute("SELECT id FROM history ORDER BY id DESC LIMIT 1 OFFSET ?", (index,))
                
            result = c.fetchone()
            if not result:
                conn.close()
                return False
                
            record_id = result[0]
            
            # 删除记录
            if current_category == 'notebook':
                c.execute("DELETE FROM notes WHERE id = ?", (record_id,))
            else:
                c.execute("DELETE FROM history WHERE id = ?", (record_id,))
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"删除记录时出错: {e}")
            return False
    
    def batch_delete_by_time(self, time_range):
        """根据时间范围批量删除记录
        
        Args:
            time_range: 时间范围，可选值: 'today', '7days', '30days', 'all'
        
        Returns:
            int: 删除的记录数量
        """
        try:
            import datetime
            
            conn = sqlite3.connect(self._get_db_name())
            c = conn.cursor()
            
            current_category = getattr(self, '_current_category', 'clipboard')
            
            # 确定时间列名
            if current_category == 'notebook':
                time_column = 'created_at'
            else:
                time_column = 'timestamp'
            
            # 计算时间条件
            time_condition = ""
            params = ()
            
            if time_range == 'today':
                today = datetime.datetime.now().date()
                time_condition = f"AND DATE({time_column}) = ?"
                params = (today,)
            elif time_range == '7days':
                seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)
                time_condition = f"AND {time_column} >= ?"
                params = (seven_days_ago,)
            elif time_range == '30days':
                thirty_days_ago = datetime.datetime.now() - datetime.timedelta(days=30)
                time_condition = f"AND {time_column} >= ?"
                params = (thirty_days_ago,)
            elif time_range == 'all':
                time_condition = ""
                params = ()
            else:
                conn.close()
                return 0
            
            # 根据当前分类执行删除
            if current_category == 'notebook':
                if time_range == 'all':
                    c.execute("DELETE FROM notes")
                else:
                    c.execute(f"DELETE FROM notes WHERE 1=1 {time_condition}", params)
            else:
                base_query = "DELETE FROM history WHERE 1=1"
                
                if current_category == 'favorite':
                    base_query += " AND favorite = 1"
                elif current_category == 'image':
                    base_query += " AND content_type = 'image'"
                elif current_category == 'file':
                    base_query += " AND content_type = 'file'"
                
                c.execute(f"{base_query} {time_condition}", params)
            
            deleted_count = c.rowcount
            conn.commit()
            conn.close()
            
            return deleted_count
            
        except Exception as e:
            print(f"批量删除记录时出错: {e}")
            return 0
    
    def _get_setting(self, key, default=None):
        """从配置文件获取值"""
        try:
            import json
            config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config.json')
            
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
            
            return default
        except Exception as e:
            print(f"获取设置时出错: {e}")
            return default
    
    def _check_and_enforce_limits(self):
        """检查并强制执行内容限制"""
        try:
            conn = sqlite3.connect(self._get_db_name())
            c = conn.cursor()
            
            # 获取当前记录总数
            c.execute("SELECT COUNT(*) FROM history")
            total_count = c.fetchone()[0]
            
            # 检查条数限制
            limit_enabled = self._get_setting("content_limit_enabled", 1)
            if limit_enabled == 1:
                limit = self._get_setting("content_limit", 2000)
                if total_count > limit:
                    # 删除最旧的记录
                    to_delete = total_count - limit
                    c.execute("DELETE FROM history WHERE id IN (SELECT id FROM history ORDER BY id ASC LIMIT ?)", (to_delete,))
                    print(f"已删除 {to_delete} 条最旧的历史记录以符合条数限制")
            
            # 检查大小限制
            size_enabled = self._get_setting("content_size_enabled", 0)
            if size_enabled == 1:
                size_limit_gb = self._get_setting("content_size_limit", 5)
                size_limit_bytes = size_limit_gb * 1024 * 1024 * 1024
                
                # 获取数据库文件大小
                db_size = os.path.getsize(self._get_db_name())
                
                if db_size > size_limit_bytes:
                    # 计算需要删除的记录数（按比例）
                    excess_ratio = db_size / size_limit_bytes
                    # 删除最旧的记录直到大小符合要求
                    while db_size > size_limit_bytes:
                        c.execute("SELECT COUNT(*) FROM history")
                        current_count = c.fetchone()[0]
                        if current_count == 0:
                            break
                        
                        # 每次删除10%的记录
                        to_delete = max(1, int(current_count * 0.1))
                        c.execute("DELETE FROM history WHERE id IN (SELECT id FROM history ORDER BY id ASC LIMIT ?)", (to_delete,))
                        conn.commit()
                        db_size = os.path.getsize(self._get_db_name())
                        print(f"已删除 {to_delete} 条最旧的历史记录以符合大小限制")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"检查并执行限制时出错: {e}")
    
    def search_content(self, query, limit=50, content_type_filter=None):
        """搜索内容"""
        if not query or not query.strip():
            return []
            
        conn = sqlite3.connect(self._get_db_name())
        c = conn.cursor()
        
        # 检查是否有favorite列和content_type列
        c.execute("PRAGMA table_info(history)")
        columns = [column[1] for column in c.fetchall()]
        has_favorite = 'favorite' in columns
        has_content_type = 'content_type' in columns
        
        # 检查并添加content_type列（如果不存在）
        if not has_content_type:
            c.execute("ALTER TABLE history ADD COLUMN content_type TEXT DEFAULT 'text'")
            has_content_type = True
        
        # 搜索所有记录，解密后匹配查询文本
        if has_favorite and has_content_type:
            c.execute("SELECT content, timestamp, favorite, content_type FROM history ORDER BY id DESC")
        elif has_favorite:
            c.execute("SELECT content, timestamp, favorite FROM history ORDER BY id DESC")
        else:
            c.execute("SELECT content, timestamp FROM history ORDER BY id DESC")
            
        rows = c.fetchall()
        conn.close()

        results = []
        query_lower = query.lower()
        
        for row in rows:
            try:
                decrypted = self.cipher.decrypt(row[0]).decode()
                
                # 获取内容类型
                if has_content_type:
                    row_content_type = row[3]
                else:
                    # 如果数据库没有content_type列，使用默认值
                    row_content_type = "text"
                
                # 如果有内容类型过滤器，检查是否匹配
                if content_type_filter and row_content_type != content_type_filter:
                    continue
                
                # 检查是否包含查询文本（不区分大小写）
                if query_lower in decrypted.lower():
                    if has_favorite and has_content_type:
                        results.append({
                            "text": decrypted, 
                            "time": row[1],
                            "favorite": bool(row[2]),
                            "content_type": row_content_type,
                            "preview": decrypted.replace('\n', ' ')[:40] # 预览前40字
                        })
                    elif has_favorite:
                        results.append({
                            "text": decrypted, 
                            "time": row[1],
                            "favorite": bool(row[2]),
                            "content_type": row_content_type,
                            "preview": decrypted.replace('\n', ' ')[:40] # 预览前40字
                        })
                    else:
                        results.append({
                            "text": decrypted, 
                            "time": row[1],
                            "favorite": False,  # 默认未收藏
                            "content_type": row_content_type,
                            "preview": decrypted.replace('\n', ' ')[:40] # 预览前40字
                        })
                        
                # 限制结果数量
                if len(results) >= limit:
                    break
                    
            except Exception as e:
                print(f"解密失败: {e}")
                # 跳过解密失败的记录
                
        return results
    
    def search_notes(self, query, limit=50):
        """搜索笔记内容"""
        if not query or not query.strip():
            return []
            
        conn = sqlite3.connect(self._get_db_name())
        c = conn.cursor()
        
        # 检查是否有html_content列
        c.execute("PRAGMA table_info(notes)")
        columns = [column[1] for column in c.fetchall()]
        has_html_content = 'html_content' in columns
        
        # 搜索所有笔记记录
        if has_html_content:
            c.execute("SELECT id, title, content, html_content, created_at, updated_at, favorite FROM notes ORDER BY id DESC")
        else:
            c.execute("SELECT id, title, content, created_at, updated_at, favorite FROM notes ORDER BY id DESC")
            
        rows = c.fetchall()
        conn.close()

        results = []
        query_lower = query.lower()
        
        for row in rows:
            try:
                # 解密内容
                decrypted = self.cipher.decrypt(row[2]).decode()
                
                # 检查标题或内容是否包含查询文本（不区分大小写）
                title_match = query_lower in row[1].lower()
                content_match = query_lower in decrypted.lower()
                
                # 如果有HTML内容，也检查HTML内容
                html_match = False
                if has_html_content and row[3]:
                    try:
                        html_decrypted = self.cipher.decrypt(row[3]).decode()
                        html_match = query_lower in html_decrypted.lower()
                    except:
                        pass
                
                if title_match or content_match or html_match:
                    note_data = {
                        "id": row[0],
                        "title": row[1],
                        "text": decrypted,
                        "created_at": row[3] if not has_html_content else row[4],
                        "updated_at": row[4] if not has_html_content else row[5],
                        "favorite": bool(row[5] if not has_html_content else row[6]),
                        "content_type": "note",  # 标记为笔记类型
                        "preview": decrypted.replace('\n', ' ')[:40]  # 预览前40字
                    }
                    
                    # 如果有HTML内容，也添加到结果中
                    if has_html_content and row[3]:
                        try:
                            html_decrypted = self.cipher.decrypt(row[3]).decode()
                            note_data["html_content"] = html_decrypted
                        except:
                            pass
                    
                    results.append(note_data)
                        
                # 限制结果数量
                if len(results) >= limit:
                    break
                    
            except Exception as e:
                print(f"解密笔记失败: {e}")
                # 跳过解密失败的记录
                
        return results
    
    def search_by_date(self, year, month=None, day=None, limit=50, content_type_filter=None):
        """按日期搜索内容"""
        conn = sqlite3.connect(self._get_db_name())
        c = conn.cursor()
        
        # 检查是否有favorite列和content_type列
        c.execute("PRAGMA table_info(history)")
        columns = [column[1] for column in c.fetchall()]
        has_favorite = 'favorite' in columns
        has_content_type = 'content_type' in columns
        
        # 检查并添加content_type列（如果不存在）
        if not has_content_type:
            c.execute("ALTER TABLE history ADD COLUMN content_type TEXT DEFAULT 'text'")
            has_content_type = True
        
        # 构建日期查询条件
        date_pattern = f"{year:04d}"
        if month is not None:
            date_pattern += f"-{month:02d}"
        if day is not None:
            date_pattern += f"-{day:02d}"
        
        # 搜索所有记录，解密后匹配日期
        if has_favorite and has_content_type:
            c.execute("SELECT content, timestamp, favorite, content_type FROM history ORDER BY id DESC")
        elif has_favorite:
            c.execute("SELECT content, timestamp, favorite FROM history ORDER BY id DESC")
        else:
            c.execute("SELECT content, timestamp FROM history ORDER BY id DESC")
            
        rows = c.fetchall()
        conn.close()

        results = []
        
        for row in rows:
            try:
                decrypted = self.cipher.decrypt(row[0]).decode()
                
                # 获取内容类型
                if has_content_type:
                    row_content_type = row[3]
                else:
                    # 如果数据库没有content_type列，使用默认值
                    row_content_type = "text"
                
                # 如果有内容类型过滤器，检查是否匹配
                if content_type_filter and row_content_type != content_type_filter:
                    continue
                
                # 检查时间戳是否匹配日期模式
                timestamp = row[1]
                # 时间戳格式通常是 "2023-12-19 14:30:25"
                if timestamp.startswith(date_pattern):
                    if has_favorite and has_content_type:
                        results.append({
                            "text": decrypted, 
                            "time": row[1],
                            "favorite": bool(row[2]),
                            "content_type": row_content_type,
                            "preview": decrypted.replace('\n', ' ')[:40] # 预览前40字
                        })
                    elif has_favorite:
                        results.append({
                            "text": decrypted, 
                            "time": row[1],
                            "favorite": bool(row[2]),
                            "content_type": row_content_type,
                            "preview": decrypted.replace('\n', ' ')[:40] # 预览前40字
                        })
                    else:
                        results.append({
                            "text": decrypted, 
                            "time": row[1],
                            "favorite": False,  # 默认未收藏
                            "content_type": row_content_type,
                            "preview": decrypted.replace('\n', ' ')[:40] # 预览前40字
                        })
                        
                # 限制结果数量
                if len(results) >= limit:
                    break
                    
            except Exception as e:
                print(f"解密失败: {e}")
                # 跳过解密失败的记录
                
        return results