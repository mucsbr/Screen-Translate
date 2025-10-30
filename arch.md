# PC端实时屏幕翻译工具：技术实现方案

## 1. 项目概述

本项目旨在开发一款PC桌面应用，能够实时捕捉用户在屏幕上指定区域的字幕（支持英、日、韩等语言），通过OCR技术识别文字，调用OpenAI格式的翻译API将其翻译成中文，并将结果显示在用户指定的另一个屏幕区域。最终实现源语言字幕与翻译字幕并行显示的“双语字幕”效果。

### 核心特性

*   **跨平台**：支持 Windows 和 macOS。
*   **高自由度**：用户可自定义字幕抓取区域和翻译显示区域。
*   **可配置性**：用户可选源语言，并配置自己的OpenAI格式API密钥（API Key）和服务器地址（Endpoint）。
*   **实时性**：以较低延迟持续进行“抓取-识别-翻译-显示”的循环。
*   **性能优化**：避免重复翻译相同内容，并在后台线程执行耗时操作，防止UI卡顿。

## 2. 核心功能模块

整个应用可以分解为以下几个核心模块：

1.  **主控模块 (Main Control)**
    *   提供一个简单的UI界面或系统托盘图标，用于启动/停止翻译、打开设置。
    *   管理配置信息（API Key, Endpoint, 源语言等）。

2.  **区域选择模块 (Region Selector)**
    *   当用户触发选择时，显示一个半透明的全屏遮罩。
    *   允许用户通过鼠标拖拽画出一个矩形，记录该矩形的坐标和尺寸。
    *   分别用于设置“源字幕区域”和“翻译显示区域”。

3.  **翻译引擎模块 (Translation Engine)**
    *   这是应用的核心后台服务，在一个独立的线程中运行。
    *   **循环控制器**：按照设定的时间间隔（如800ms）重复执行任务。
    *   **屏幕捕捉器 (Screen Capturer)**：抓取“源字幕区域”的屏幕图像。
    *   **OCR处理器 (OCR Processor)**：将抓取到的图像转换为文本字符串。
    *   **翻译协调器 (Translation Coordinator)**：调用外部API，将识别出的文本发送进行翻译。

4.  **显示模块 (Display Overlay)**
    *   创建一个无边框、背景透明的悬浮窗口。
    *   该窗口的位置和大小由用户设置的“翻译显示区域”决定。
    *   实时接收翻译引擎传来的结果，并更新显示的文本。

## 3. 技术选型

为了实现跨平台和满足功能需求，推荐以下技术栈：

*   **编程语言**: **Python 3**
    *   拥有丰富的第三方库，生态成熟，开发效率高。
*   **GUI框架**: **PyQt6 / PySide6**
    *   强大的跨平台GUI库，能轻松创建现代化的UI，并且对创建无边框、透明的悬浮窗口有完美的支持。
*   **屏幕截图**: **mss**
    *   性能极高，跨平台支持良好，是实时截图的首选。
*   **OCR引擎**: **EasyOCR**
    *   基于Python，安装简单，支持包括英文、日文、韩文在内的80多种语言，识别效果优秀。
*   **API通信**: **requests**
    *   业界标准的HTTP请求库，用于与OpenAI格式的API进行交互。
*   **应用打包**: **PyInstaller**
    *   可将Python脚本打包成Windows (.exe) 和 macOS (.app) 的独立可执行文件。

## 4. 实现流程与伪代码

下面我们用伪代码来详细描述每个关键环节的实现逻辑。

### 主应用 `MainApp`

```python
class MainApp:
    def __init__(self):
        # 初始化UI窗口或系统托盘
        self.ui = create_main_window()
        self.config = load_config() # 加载API Key, 语言等配置

        # 定义源区域和目标区域变量
        self.source_rect = None
        self.target_rect = None

        # 初始化翻译引擎和显示窗口
        self.display_overlay = DisplayOverlay()
        self.translation_engine = TranslationEngine(self.config)

        # 绑定UI事件
        self.ui.button_select_source.on_click = self.select_source_region
        self.ui.button_select_target.on_click = self.select_target_region
        self.ui.button_start_stop.on_click = self.toggle_translation

    def select_source_region(self):
        # 启动区域选择器，并将选择结果保存
        selector = RegionSelector("请选择要翻译的字幕区域")
        self.source_rect = selector.get_selection()
        print(f"源区域已选择: {self.source_rect}")

    def select_target_region(self):
        selector = RegionSelector("请选择翻译内容的显示区域")
        self.target_rect = selector.get_selection()
        print(f"目标区域已选择: {self.target_rect}")
        # 根据选择的区域，设置显示窗口的位置和大小
        self.display_overlay.set_geometry(self.target_rect)

    def toggle_translation(self):
        if self.translation_engine.is_running():
            self.translation_engine.stop()
            self.display_overlay.hide()
            self.ui.button_start_stop.set_text("启动")
        else:
            if self.source_rect and self.target_rect:
                self.translation_engine.start(self.source_rect, self.on_translation_received)
                self.display_overlay.show()
                self.ui.button_start_stop.set_text("停止")
            else:
                show_error("请先选择源区域和目标区域！")

    def on_translation_received(self, translated_text):
        # 这是一个回调函数，当引擎获得新翻译时被调用
        self.display_overlay.update_text(translated_text)

```

### 区域选择器 `RegionSelector`

```python
# 使用PyQt实现
class RegionSelector(QWidget):
    def __init__(self, prompt_text):
        super().__init__()
        # 1. 设置窗口为全屏、无边框、半透明
        self.setWindowState(Qt.WindowFullScreen)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 0.3);")

        # 2. 监听鼠标事件
        self.begin_pos = None
        self.end_pos = None
        self.selected_rect = None

    def mousePressEvent(self, event):
        self.begin_pos = event.pos()

    def mouseMoveEvent(self, event):
        self.end_pos = event.pos()
        self.update() # 触发重绘，实时显示选择框

    def mouseReleaseEvent(self, event):
        self.selected_rect = QRect(self.begin_pos, self.end_pos).normalized()
        self.close() # 选择完成，关闭窗口

    def paintEvent(self, event):
        # 在鼠标拖拽时，绘制一个醒目的矩形框
        if self.begin_pos and self.end_pos:
            painter = QPainter(self)
            painter.setPen(QPen(Qt.red, 2))
            painter.drawRect(QRect(self.begin_pos, self.end_pos))

    def get_selection(self):
        # 显示窗口并等待其关闭，然后返回结果
        self.show()
        # (此处需要一个事件循环来等待窗口关闭)
        return self.selected_rect # 返回QRect对象
```

### 翻译引擎 `TranslationEngine` (核心)

```python
# 这个类应该在单独的线程中运行
class TranslationEngine(Thread):
    def __init__(self, config):
        self.config = config
        self.running = False
        self.source_rect = None
        self.callback = None
        self.last_recognized_text = ""

        # 初始化OCR阅读器，指定语言
        self.ocr_reader = easyocr.Reader(['en', 'ja', 'ko']) # 根据用户配置初始化

    def run(self):
        # 线程的主循环
        while self.running:
            # 1. 屏幕捕捉
            image = capture_screen_area(self.source_rect)

            # 2. OCR识别
            # 将numpy图像数组传入
            ocr_results = self.ocr_reader.readtext(image)
            current_text = " ".join([result[1] for result in ocr_results])

            # 3. 检查文本是否有变化，避免重复翻译
            if current_text and current_text != self.last_recognized_text:
                self.last_recognized_text = current_text

                # 4. 调用翻译API
                translated_text = self.translate_text(current_text)

                # 5. 通过回调函数将结果发送给主线程
                if translated_text and self.callback:
                    self.callback(translated_text)
            
            # 6. 等待一个时间间隔
            time.sleep(0.8) # 800毫秒

    def start(self, source_rect, callback):
        self.source_rect = source_rect
        self.callback = callback
        self.running = True
        super().start() # 启动线程

    def stop(self):
        self.running = False

    def translate_text(self, text):
        # 使用requests库与OpenAI格式的API通信
        try:
            response = requests.post(
                self.config.api_endpoint,
                headers={"Authorization": f"Bearer {self.config.api_key}"},
                json={
                    "model": "gpt-3.5-turbo", # or other model
                    "messages": [
                        {"role": "system", "content": "You are a translator. Translate the following text to Chinese."},
                        {"role": "user", "content": text}
                    ]
                }
            )
            response.raise_for_status() # 如果请求失败则抛出异常
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            print(f"翻译失败: {e}")
            return "翻译错误"
```

### 显示覆盖层 `DisplayOverlay`

```python
# 同样使用PyQt实现
class DisplayOverlay(QWidget):
    def __init__(self):
        super().__init__()
        # 1. 设置窗口为无边框、背景透明、总在最前
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool # Tool类型窗口通常不会出现在任务栏
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 2. 创建一个用于显示文本的QLabel
        self.label = QLabel("...", self)
        self.label.setStyleSheet("color: white; font-size: 20px; background-color: rgba(0, 0, 0, 0.5);")
        self.label.setAlignment(Qt.AlignCenter)

        # 3. 使用布局管理器
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

    def update_text(self, text):
        self.label.setText(text)

    def set_geometry(self, rect):
        self.setGeometry(rect)
```

## 5. 关键实现细节与优化

*   **权限问题**：在macOS上，屏幕录制需要用户在“系统偏好设置” -> “隐私与安全性” -> “屏幕录制”中手动授权。应用需要引导用户完成此操作。
*   **性能优化**：
    1.  **OCR优化**：`EasyOCR`在初始化时会加载模型，这是一个耗时操作，应在程序启动时就完成。
    2.  **缓存**：`last_recognized_text`的检查是简单的缓存机制，避免了对完全相同的字幕图片进行重复的OCR和翻译请求，极大节省了资源。
    3.  **异步处理**：将整个翻译引擎放在独立线程中是必须的，否则UI会完全冻结。
*   **打包**：使用PyInstaller打包时，需要确保`EasyOCR`的模型文件和`Tesseract`（如果使用）的可执行文件被正确地包含进最终的应用包中。

## 6. 项目路线图

1.  **第一阶段：核心功能实现**
    *   搭建Python + PyQt基本环境。
    *   实现可靠的跨平台屏幕区域截图功能。
    *   集成EasyOCR，并测试其对目标语言的识别准确率。
    *   编写调用OpenAI API的翻译函数。

2.  **第二阶段：整合与串联**
    *   实现区域选择器和显示覆盖层的UI。
    *   将所有功能整合到`TranslationEngine`线程中。
    *   建立主线程UI与后台引擎之间的通信（通过回调或信号/槽机制）。

3.  **第三阶段：完善与优化**
    *   创建设置界面，允许用户配置API、语言等。
    *   优化UI/UX，添加系统托盘图标等。
    *   处理各种异常情况（如网络错误、API限流、OCR识别失败等）。
    *   进行性能测试和内存泄漏检查。

4.  **第四阶段：打包与分发**
    *   编写打包脚本（如`.spec`文件）。
    *   分别在Windows和macOS上进行打包测试。
    *   为macOS应用进行代码签名和公证，以避免安全警告。

---