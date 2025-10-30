# EasyOCR 模型预下载指南

## 问题
每次启动应用时，EasyOCR 都会重新下载模型文件，导致启动缓慢。

## 解决方案

### 1. 自动缓存机制
应用现在会自动将模型保存到项目根目录的 `.easyocr_models` 文件夹中，第二次启动时将使用已缓存的模型，避免重复下载。

### 2. 手动预下载（推荐）
为了避免首次启动时的长时间等待，你可以预先下载模型：

```bash
python -m screen_translate.download_models
```

这将下载日语和英语模型（最常用的组合）。

### 自定义语言
```bash
python -m screen_translate.download_models --languages ja en ko
```

### 下载所有语言（不推荐）
```bash
python -m screen_translate.download_models --all
```
⚠️ 这需要大量磁盘空间和长时间等待！

## 模型位置
所有模型都保存在项目根目录的 `.easyocr_models` 文件夹中：
```
/path/to/Screen-Translate/
├── .easyocr_models/
│   ├── craft_mlt_25k.pth
│   ├── craft_mlt_25k.pth.tar
│   ├── japanese_gtdb.pth
│   └── ...
└── ...
```

## 手动清理
如果需要重新下载模型，只需删除 `.easyocr_models` 文件夹：
```bash
rm -rf .easyocr_models
```