# Screen Translate 项目

## 环境准备

```bash
# 安装运行依赖（推荐使用 uv）
uv pip install -e .
# 或使用 pip
pip install -e .

# 安装开发/测试依赖
uv pip install -e .[dev]
# 或使用 pip
pip install -e .[dev]
```

## 快速开始

```bash
# 启动桌面应用
python -m screen_translate.app

# 运行单元测试
pytest
```

## 依赖说明
- Python >= 3.11
- PySide6、EasyOCR、mss、numpy、requests 等核心库
- 开发/测试：pytest、pytest-qt、pytest-mock、ruff、mypy

## 使用说明

### 配置翻译服务
点击“设置”按钮，在弹出的对话框中填入：
- **Endpoint**：OpenAI 兼容接口地址（如：https://api.openai.com/v1/chat/completions）
- **API Key**：你的 API Key（可选，留空则不发送 Authorization）
- **Model**：模型名称（如：gpt-3.5-turbo、gpt-4）
- **System Prompt**：系统提示词（可选，默认“You are a translator. Translate the text to Chinese.”）

配置会自动保存到 `~/.screen_translate/config.json` 并在下次启动时加载。

**注意**：若在翻译过程中修改设置，需要重新点击“开始/停止”以使新配置生效。

### 基本流程
1. 点击“设置”，输入你的翻译服务配置并保存
2. 点击“选择字幕区域”，在当前屏幕上拖拽选择需要识别的字幕区域
3. 点击“选择显示区域”，选择翻译结果要显示的位置
4. 点击“开始/停止”控制翻译循环

## 已知限制
- macOS 首次运行需要在“系统设置 → 隐私与安全性 → 屏幕录制”手动授权应用。
- OCR/翻译尚未做性能优化，建议在资源充足的环境下使用。
