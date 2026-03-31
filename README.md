# Clippot v1.01 ✂️

一个功能强大的剪贴板管理工具，支持加密存储、多语言、暗黑模式等功能。

## ✨ 更新日志

### v1.01 (2026-03-31)
**新增功能：**
- ✅ **最小化自动隐藏** - 点击最小化按钮时，窗口自动隐藏到系统托盘，不再占用任务栏
- ✅ **右键选取文字** - 剪贴板历史项右键菜单新增"选取文字"功能，支持选择部分文字进行复制

**优化改进：**
- 改进窗口管理逻辑
- 优化用户体验

## 功能特性

- 剪贴板历史记录管理
- 记事本功能
- 加密存储（使用 Fernet 对称加密）
- 多语言支持（中文/英文）
- 暗黑/明亮主题
- 窗口透明度调节
- 开机自启动
- 系统托盘图标
- **最小化自动隐藏到托盘** (v1.01新增)
- **右键选取文字功能** (v1.01新增)

## 运行要求

- Python 3.8+
- PySide6
- cryptography
- qtawesome

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行

```bash
python main.py
```

## 打包

```bash
pyinstaller --noconfirm --onefile --windowed --name "Clippot" --icon "src\ui\assets\Clippot.ico" --add-data "src\ui\assets;src\ui\assets" --add-data "src\locales;src\locales" --hidden-import "PySide6" --hidden-import "cryptography" --hidden-import "qtawesome" --hidden-import "sqlite3" main.py
```

## 安全说明

**重要：** 在部署前，请务必修改 `main.py` 中的 `FIXED_SALT` 变量为您自己的随机盐值。

```python
# 将此行修改为您自己的随机字符串
FIXED_SALT = b'YOUR_SECRET_SALT_HERE_PLEASE_REPLACE_WITH_YOUR_OWN_RANDOM_STRING'
```

建议使用 32 字节以上的随机字符串作为盐值。

## 文件结构

```
Clippot/
├── main.py              # 主程序入口
├── requirements.txt     # 依赖列表
├── releases/            # 可执行文件目录
│   └── Clippot_v1.01.exe # v1.01可执行文件
├── src/
│   ├── core/
│   │   ├── backend.py   # 后端逻辑
│   │   └── category.py  # 分类管理
│   ├── ui/
│   │   ├── ui.py        # 主界面
│   │   ├── settings.py  # 设置界面
│   │   ├── text_editor.py # 记事本编辑器
│   │   ├── text_viewer_dialog.py # 文字查看器 (v1.01新增)
│   │   ├── word_segment_dialog.py # 分词对话框 (v1.01新增)
│   │   ├── welcome_dialog.py # 欢迎对话框
│   │   ├── assets/      # 图标资源
│   │   └── locales/     # 语言文件
│   └── utils/
│       └── word_segmenter.py # 分词工具 (v1.01新增)
```

## 许可证

MIT License
