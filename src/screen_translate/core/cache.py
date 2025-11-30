"""Translation text cache to avoid duplicate OCR/translation."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class CacheEntry:
    text: str
    timestamp: float


class TranslationCache:
    """Store last translated text to prevent duplicate translations."""

    def __init__(self, ttl_seconds: float = 5.0) -> None:
        self._ttl = ttl_seconds
        self._entry: Optional[CacheEntry] = None
        self._mode = "ocr"  # "ocr" or "audio"

    def set_mode(self, mode: str) -> None:
        """Set cache mode for optimal behavior."""
        if mode not in ["ocr", "audio"]:
            raise ValueError("Mode must be 'ocr' or 'audio'")
        self._mode = mode

    def should_translate(self, text: str) -> bool:
        import re
        normalized = text.strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        if not normalized:
            return False

        current_time = time.monotonic()
        if self._entry is None:
            self._entry = CacheEntry(text=normalized, timestamp=current_time)
            return True

        # Audio mode: 更严格的缓存策略
        if self._mode == "audio":
            time_diff = current_time - self._entry.timestamp

            # 首先检查是否完全相同（避免重复）
            if normalized == self._entry.text and time_diff < 5.0:
                return False

            # 检查是否是同一句话的不同版本（语法、用词差异）
            if self._is_same_sentence_variation(normalized, self._entry.text):
                # 如果变化不大且时间间隔短，跳过
                if time_diff < 8.0:  # 8秒内认为是同一句话
                    return False

            # 对于音频模式，时间间隔是最重要的因素
            # 如果时间间隔太短，即使文本不同也跳过（避免快速连续的误识别）
            if time_diff < 1.5:
                return False

        # OCR mode: original logic
        if (
            normalized != self._entry.text
            or current_time - self._entry.timestamp > self._ttl
        ):
            self._entry = CacheEntry(text=normalized, timestamp=current_time)
            return True

        return False

    def _is_same_sentence_variation(self, new_text: str, old_text: str) -> bool:
        """检测是否是同一句话的不同识别版本（语序、用词差异）"""
        if not old_text or not new_text:
            return False

        # 简单的相似度检查
        similarity = self._calculate_similarity(new_text, old_text)
        if similarity < 0.6:  # 相似度太低，不是同一句话
            return False

        # 检查长度差异
        len_ratio = max(len(new_text), len(old_text)) / min(len(new_text), len(old_text))
        if len_ratio > 2.0:  # 长度差异太大，不是同一句话
            return False

        # 检查是否有共同的词根
        words_new = set(new_text.lower().split())
        words_old = set(old_text.lower().split())

        if not words_new or not words_old:
            return False

        common_words = words_new & words_old
        overlap_ratio = len(common_words) / max(len(words_new), len(words_old))

        # 如果有60%以上的词重叠，认为是同一句话
        return overlap_ratio > 0.6

    def _is_continuous_speech_update(self, new_text: str, old_text: str) -> bool:
        """检测是否是连续的语音识别更新（Vosk PartialResult特性）"""
        if not old_text:
            return False

        # 检查是否包含旧文本（典型的PartialResult模式）
        if old_text in new_text:
            # 检查新文本是否主要是在旧文本基础上的扩展
            overlap_ratio = len(old_text) / len(new_text) if len(new_text) > 0 else 0
            return overlap_ratio > 0.6  # 60%以上是旧文本内容

        # 检查是否有很高的文本相似度（编辑距离小的修改）
        similarity = self._calculate_similarity(new_text, old_text)
        return similarity > 0.7

    @staticmethod
    def _calculate_similarity(text1: str, text2: str) -> float:
        """Calculate text similarity ratio (0-1)."""
        if not text1 or not text2:
            return 0.0

        # Simple Levenshtein-like similarity for short texts
        len1, len2 = len(text1), len(text2)
        if len1 == 0:
            return 0.0
        if len2 == 0:
            return 0.0

        # Check for common prefix/suffix
        common_chars = 0
        min_len = min(len1, len2)
        for i in range(min_len):
            if text1[i] == text2[i]:
                common_chars += 1
            else:
                break

        # Simple similarity based on common prefix
        similarity = common_chars / max(len1, len2)
        return similarity

    @staticmethod
    def _is_minor_addition(new_text: str, old_text: str) -> bool:
        """Check if new_text is just a minor addition to old_text."""
        if not old_text:
            return False

        # Check if old_text is prefix of new_text
        if new_text.startswith(old_text):
            addition = new_text[len(old_text):].strip()
            # If addition is very short (<= 10 chars), consider it minor
            return len(addition) <= 10

        # Check if old_text is suffix of new_text
        if new_text.endswith(old_text):
            addition = new_text[:-len(old_text)].strip()
            return len(addition) <= 10

        return False
