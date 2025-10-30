"""预下载 EasyOCR 模型文件，避免首次运行时卡顿。"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import easyocr
except ImportError:
    print("错误: EasyOCR 未安装。请先运行: pip install easyocr")
    sys.exit(1)


def download_models(languages: list[str] | None = None) -> None:
    """下载 EasyOCR 模型文件。"""
    if languages is None:
        languages = ["ja", "en", "ko"]

    print(f"开始下载 EasyOCR 模型，语言: {', '.join(languages)}")
    print("这可能需要几分钟时间，取决于你的网络连接...")
    print()

    project_root = Path(__file__).parent.parent.parent
    model_dir = project_root / ".easyocr_models"
    model_dir.mkdir(exist_ok=True)

    print(f"模型将保存到: {model_dir}")
    print()

    for lang in languages:
        print(f"正在下载 {lang} 语言模型...")
        try:
            reader = easyocr.Reader(
                [lang],
                model_storage_directory=str(model_dir),
                download_enabled=True,
                detector=True,
                recognizer=True
            )
            print(f"✓ {lang} 语言模型下载完成")
        except Exception as e:
            print(f"✗ {lang} 语言模型下载失败: {e}")
            return

    print()
    print("=" * 60)
    print("所有模型下载完成！")
    print(f"模型位置: {model_dir}")
    print("=" * 60)


def main() -> None:
    """主函数。"""
    import argparse

    parser = argparse.ArgumentParser(description="预下载 EasyOCR 模型文件")
    parser.add_argument(
        "--languages",
        nargs="+",
        default=["ja", "en"],
        help="要下载的语言代码 (例如: ja en ko)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="下载所有支持的语言"
    )

    args = parser.parse_args()

    if args.all:
        languages = ["af", "az", "bs", "cs", "da", "de", "en", "es", "et", "fr", "ga", "hr",
                    "hu", "id", "is", "it", "ja", "ko", "lt", "lv", "mi", "ms", "mt", "nl",
                    "no", "oc", "pl", "pt", "ro", "sk", "sl", "sq", "sv", "th", "tr", "ug",
                    "vi", "zh"]
        print("警告: 下载所有语言模型需要大量磁盘空间和长时间等待！")
        response = input("确定要继续吗？(y/N): ")
        if response.lower() != "y":
            print("已取消")
            return
    else:
        languages = args.languages

    download_models(languages)