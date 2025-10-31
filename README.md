# Screen Translate 项目

支持两种翻译模式：
- **OCR模式**：识别屏幕文字进行翻译
- **音频模式**：通过麦克风/系统音频进行语音转录翻译

## 环境准备

### 基础环境

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

### macOS M系列芯片特殊安装步骤（音频功能必需）

如果您需要使用**音频转录功能**，在安装PyAudio前请执行以下步骤：

```bash
# 1. 安装 portaudio
brew install portaudio

# 2. 链接 portaudio
brew link portaudio

# 3. 获取 portaudio 安装路径（记录此路径）
brew --prefix portaudio
# 例如输出：/opt/homebrew

# 4. 创建 .pydistutils.cfg 配置文件
nano $HOME/.pydistutils.cfg
# 或者使用 vim/code 等编辑器

# 5. 添加以下内容（替换 <PATH> 为步骤3的输出路径）
[build_ext]
include_dirs=<PATH>/include/
library_dirs=<PATH>/lib/

# 例如：
# [build_ext]
# include_dirs=/opt/homebrew/include/
# library_dirs=/opt/homebrew/lib/

# 6. 保存并退出编辑器，然后安装 pyaudio
pip install pyaudio
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
- PySide6（GUI框架）
- EasyOCR、mss（OCR模式依赖）
- **PyAudio、Vosk（音频模式依赖）**
- **OpenAI Whisper、PyTorch（推荐音频方案）**
- numpy、requests、loguru、pydantic
- 开发/测试：pytest、pytest-qt、pytest-mock、ruff、mypy

## 使用说明

### 配置翻译服务
点击"设置"按钮，在弹出的对话框中填入：
- **Endpoint**：OpenAI 兼容接口地址（如：https://api.openai.com/v1/chat/completions）
- **API Key**：你的 API Key（可选，留空则不发送 Authorization）
- **Model**：模型名称（如：gpt-3.5-turbo、gpt-4）
- **System Prompt**：系统提示词（可选，默认"You are a translator. Translate the text to Chinese."）

配置会自动保存到 `~/.screen_translate/config.json` 并在下次启动时加载。

**注意**：若在翻译过程中修改设置，需要重新点击"开始/停止"以使新配置生效。

### 音频转录模式使用（macOS）

音频模式支持两种语音识别引擎：

#### 推荐方案：Whisper（更准确，兼容性更好）
- **优势**：识别准确度更高，M1/M2芯片完全兼容
- **支持语言**：英语、中文、日语、韩语（支持多语言混合）
- **模型选择**：从Tiny（最快）到Large（最准确）5种模型可选

#### 备选方案：Vosk（轻量级，适合纯英文）
- **优势**：资源占用小，适合纯英文环境
- **限制**：M1/M2芯片存在兼容性问题，可能需要Rosetta模式

### 第一步：安装 BlackHole 虚拟音频驱动

BlackHole 是一个 macOS 虚拟音频设备，可以将系统音频同时路由到多个输出设备。

```bash
# 安装 BlackHole 2ch 版本
brew install blackhole-2ch
```

### 第二步：配置 BlackHole 多输出设备

为了既能将音频发送给 Screen Translate 进行识别，又能通过耳机监听声音，需要创建多输出设备：

1. **打开音频 MIDI 设置**：
   - 系统设置 → 隐私与安全性 → 完全磁盘访问权限
   - 将"音频 MIDI 设置"添加到允许列表（/Applications/Utilities/Audio MIDI Setup.app）

2. **创建多输出设备**：
   - 打开"音频 MIDI 设置"应用
   - 点击左下角 "+" 按钮 → 选择"创建多输出设备"
   - 在右侧设置中勾选：
     - **BlackHole 2ch**（用于音频捕获）
     - **您的耳机/扬声器**（用于声音监听）
   - 取消勾选"主设备"选项，让 BlackHole 作为主时钟源

3. **设置系统音频输出**：
   - 打开 **系统设置** → **声音** → **输出**
   - 选择刚刚创建的 **多输出设备**
   - 调节音量到合适水平

### 第三步：Whisper 模式（推荐）
Whisper模型会自动下载，无需手动安装。首次使用时会根据选择的模型大小自动下载对应文件。

### 第四步：Vosk 模式（备选）
1. 访问 [Vosk 模型下载页](https://alphacephei.com/vosk/models)
2. 推荐下载 `vosk-model-small-en-us-0.15`（英文小型模型，约 50MB）
3. 解压到项目目录的 `models` 文件夹中
4. 最终路径类似：`models/vosk-model-small-en-us-0.15/`

**⚠️ 故障排除**：
如果在加载模型时遇到 `segmentation fault` 错误，这是由于 M1/M2 芯片兼容性问题导致的。请尝试以下解决方案：

**方案一（推荐）**：使用 Rosetta 模式运行
```bash
arch -x86_64 python -m screen_translate.app
```

**方案二**：降级 Vosk 版本
```bash
pip uninstall vosk
pip install vosk==0.3.42
```

**方案三**：使用不同的模型版本
- 尝试 `vosk-model-small-en-us-0.22`
- 或下载其他架构的模型

### 第五步：配置音频设备
1. 启动应用程序，点击"设置"
2. 切换到"音频设置"标签页
3. 勾选"启用音频输入模式"
4. **选择语音识别引擎**：推荐选择"Whisper"
5. **选择物理输出设备**：选择您要监听的应用程序（如浏览器、视频播放器等）
6. **选择虚拟输入设备**：选择 "BlackHole 2ch"（标记为★的设备）
7. 如选择Whisper，可选择模型大小（推荐Base或Small）
8. 如选择Vosk，确认模型路径正确
9. 点击"确定"保存设置

### 第六步：开始翻译
- 启动应用后，音频模式会自动开始录音
- **Whisper模式**：识别所有音频内容（包括语音和音乐）
- **Vosk模式**：识别所有音频内容（包括语音和噪音）
- 识别到的语音将自动翻译为中文并显示在目标区域
- 点击"开始/停止"控制翻译循环

**注意**：
- 确保您有麦克风访问权限（系统会提示授权）
- 使用多输出设备时，可以同时听到声音并进行转录
- 语音识别需要清晰的声音，建议在安静环境下使用

### OCR模式使用（原有功能）
1. 点击"设置"，输入您的翻译服务配置并保存
2. 点击"选择字幕区域"，在当前屏幕上拖拽选择需要识别的字幕区域
3. 点击"选择显示区域"，选择翻译结果要显示的位置
4. 点击"开始/停止"控制翻译循环

## 已知限制
- macOS 首次运行需要在"系统设置 → 隐私与安全性 → 屏幕录制"手动授权应用。
- OCR/翻译尚未做性能优化，建议在资源充足的环境下使用。
- **音频模式仅支持 macOS**，需要手动安装 BlackHole 虚拟音频驱动。
- 音频模式需要麦克风访问权限，首次使用时会提示授权。
- 语音识别准确率取决于音频质量和模型，建议使用清晰的英语语音。
- **Vosk在M1/M2芯片兼容性问题**：在加载模型时可能出现 segmentation fault，建议使用Whisper替代。

## 💡 BlackHole 使用技巧

### 为什么需要多输出设备？
- **单设备问题**：如果只选择 BlackHole 作为输出，系统会静音，您听不到声音
- **多设备优势**：同时将音频路由到 BlackHole（供应用识别）和耳机（供您监听）

### 音频流程图
```
应用程序音频 → 多输出设备 → [BlackHole 2ch + 您的耳机]
                         ↓
                    Screen Translate 识别
                         ↓
                     翻译并显示文本
```

### 常见问题解决
1. **听不到声音**：确认多输出设备中包含您的耳机/扬声器
2. **识别不到音频**：确认多输出设备中包含 BlackHole 2ch
3. **音频延迟**：这是正常现象，Whisper 需要3秒缓冲时间
4. **权限问题**：给与"音频 MIDI 设置"完全磁盘访问权限
