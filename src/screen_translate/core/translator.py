"""Translation coordinator using OpenAI-compatible APIs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Callable

import requests

from ..config.schemas import ApiConfig


@dataclass
class TranslationResult:
    """Container for translated text."""

    text: str


class Translator:
    """Call external translation API using OpenAI-compatible schema."""

    def __init__(self, api_config: ApiConfig, logger: Optional[Callable[[str], None]] = None) -> None:
        self._api_config = api_config
        self._logger = logger

    def _log(self, message: str) -> None:
        """Log message if logger is set."""
        if self._logger:
            self._logger(message)

    def translate(self, text: str) -> Optional[TranslationResult]:
        self._log(f"准备翻译文本: {text[:50]}{'...' if len(text) > 50 else ''}")

        system_prompt = self._api_config.system_prompt or "You are a translator. Translate the text to Chinese."
        self._log(f"使用系统提示: {system_prompt[:50]}{'...' if len(system_prompt) > 50 else ''}")
        prefix = '''你是一个专业的简体中文母语译者，需将文本流畅地翻译为简体中文。
## 翻译规则
1. 仅输出译文内容，禁止解释或添加任何额外内容（如\"以下是翻译：\"、\"译文如下：\"等）
2. 返回的译文必须和原文保持完全相同的段落数量和格式
3. 如果文本包含HTML标签，请在翻译后考虑标签应放在译文的哪个位置，同时保持译文的流畅性
4. 对于无需翻译的内容（如专有名词、代码等），请保留原文。
需要翻译的内容如下：
'''

        payload = {
            "model": self._api_config.model,
            "messages": [
                # {"role": "system", "content": system_prompt},
                {"role": "user", "content": prefix + text},
            ],
            "temperature": 0.2,
            "stream": False,
        }

        self._log(f"请求模型: {self._api_config.model}")
        self._log(f"API端点: {self._api_config.endpoint}")
        self._log("响应模式: 非流式 (stream=False)")

        headers = {"Content-Type": "application/json"}
        if self._api_config.api_key:
            headers["Authorization"] = f"Bearer {self._api_config.api_key}"
            self._log("已设置API密钥")
        else:
            self._log("警告：未设置API密钥")

        self._log("正在发送API请求...")
        try:
            response = requests.post(self._api_config.endpoint, json=payload, headers=headers, timeout=15)
            self._log(f"API响应状态码: {response.status_code}")

            response.raise_for_status()
            data = response.json()

            self._log("正在解析API响应...")
            content = data["choices"][0]["message"]["content"]
            self._log(f"API返回内容: {content[:50]}{'...' if len(content) > 50 else ''}")

            return TranslationResult(text=content.strip())
        except Exception as e:
            self._log(f"API请求失败: {str(e)}")
            raise
