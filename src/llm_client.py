"""
内涵质控系统 - LLM客户端
支持多种LLM后端（OpenAI、Qwen、本地模型等）
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Iterator, List, Union
import os
import requests
import json
import time
try:
    from openai import OpenAI
except Exception:
    OpenAI = None


class BaseLLMClient(ABC):
    """LLM客户端基类"""

    @abstractmethod
    def call(self, prompt: str, **kwargs) -> str:
        """
        调用LLM

        Args:
            prompt: 输入prompt
            **kwargs: 其他参数

        Returns:
            LLM响应文本
        """
        pass

    def debug_snapshot(self) -> Dict[str, Any]:
        return {}


class OpenAIClient(BaseLLMClient):
    """OpenAI API客户端"""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-3.5-turbo",
        base_url: str = "https://api.openai.com/v1",
        temperature: float = 0.1,
        max_tokens: int = 2000
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens

    def call(self, prompt: str, **kwargs) -> str:
        """调用OpenAI API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": kwargs.get("model", self.model),
            "messages": [
                {"role": "system", "content": "你是一个专业的医疗质控专家。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens)
        }

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=data,
            timeout=60
        )

        response.raise_for_status()
        result = response.json()

        return result["choices"][0]["message"]["content"]


class QwenClient(BaseLLMClient):
    """通义千问客户端（阿里云）"""

    def __init__(
        self,
        api_key: str,
        model: str = "qwen-turbo",
        base_url: str = "https://dashscope.aliyuncs.com/api/v1",
        temperature: float = 0.1,
        max_tokens: int = 2000
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens

    def call(self, prompt: str, **kwargs) -> str:
        """调用通义千问API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": kwargs.get("model", self.model),
            "input": {
                "messages": [
                    {"role": "system", "content": "你是一个专业的医疗质控专家。"},
                    {"role": "user", "content": prompt}
                ]
            },
            "parameters": {
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "result_format": "message"
            }
        }

        response = requests.post(
            f"{self.base_url}/services/aigc/text-generation/generation",
            headers=headers,
            json=data,
            timeout=60
        )

        response.raise_for_status()
        result = response.json()

        return result["output"]["choices"][0]["message"]["content"]


class LocalModelClient(BaseLLMClient):
    """本地模型客户端（支持vLLM、Ollama等）"""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        model: str = "qwen-30b",
        temperature: float = 0.1,
        max_tokens: int = 2000
    ):
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def call(self, prompt: str, **kwargs) -> str:
        """调用本地模型API（vLLM格式）"""
        headers = {
            "Content-Type": "application/json"
        }

        data = {
            "model": kwargs.get("model", self.model),
            "messages": [
                {"role": "system", "content": "你是一个专业的医疗质控专家。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens)
        }

        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=120
        )

        response.raise_for_status()
        result = response.json()

        return result["choices"][0]["message"]["content"]


class OllamaClient(BaseLLMClient):
    """Ollama客户端（本地运行）"""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen:30b",
        temperature: float = 0.1
    ):
        self.base_url = base_url
        self.model = model
        self.temperature = temperature

    def call(self, prompt: str, **kwargs) -> str:
        """调用Ollama API"""
        data = {
            "model": kwargs.get("model", self.model),
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", self.temperature)
            }
        }

        response = requests.post(
            f"{self.base_url}/api/generate",
            json=data,
            timeout=120
        )

        response.raise_for_status()
        result = response.json()

        return result["response"]


class ModelScopeClient(BaseLLMClient):
    """ModelScope API客户端（使用OpenAI SDK）"""

    def __init__(
        self,
        api_key: str,
        model: str = "Qwen/Qwen3.5-35B-A3B",
        base_url: str = "https://api-inference.modelscope.cn/v1",
        temperature: float = 0.1,
        max_tokens: int = 32768,
        timeout: int = 90,
    ):
        self.api_key = os.getenv("MODELSCOPE_API_KEY", api_key)
        self.model = os.getenv("MODELSCOPE_MODEL", model)
        self.base_url = os.getenv("MODELSCOPE_BASE_URL", base_url)
        self.temperature = float(os.getenv("MODELSCOPE_TEMPERATURE", str(temperature)))
        self.max_tokens = int(os.getenv("MODELSCOPE_MAX_TOKENS", str(max_tokens)))
        self.timeout = int(os.getenv("MODELSCOPE_TIMEOUT", str(timeout)))
        self.client = None
        if OpenAI is not None:
            self.client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
            )
        self.transport = "openai_sdk" if self.client is not None else "http_requests"
        self._stats: Dict[str, Any] = {
            "client": "modelscope",
            "transport": self.transport,
            "call_total": 0,
            "call_success": 0,
            "call_error": 0,
            "latency_ms_total": 0.0,
            "last_error": "",
        }

    def call(self, prompt: str, **kwargs) -> str:
        """调用ModelScope（非流式）"""
        start = time.perf_counter()
        self._stats["call_total"] += 1
        messages = kwargs.get("messages") or [
            {"role": "system", "content": "你是一个专业的医疗质控专家。"},
            {"role": "user", "content": prompt}
        ]
        try:
            if self.client is not None:
                response = self.client.chat.completions.create(
                    model=kwargs.get("model", self.model),
                    messages=messages,
                    temperature=kwargs.get("temperature", self.temperature),
                    max_tokens=kwargs.get("max_tokens", self.max_tokens),
                    stream=False,
                )
                content = response.choices[0].message.content
                text = self._extract_text_content(content)
                self._stats["call_success"] += 1
                return text

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": kwargs.get("model", self.model),
                "messages": messages,
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "stream": False,
            }
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            text = self._extract_text_content(content)
            self._stats["call_success"] += 1
            return text
        except Exception as exc:
            self._stats["call_error"] += 1
            self._stats["last_error"] = str(exc)
            raise
        finally:
            self._stats["latency_ms_total"] += (time.perf_counter() - start) * 1000.0

    def stream(self, prompt: str, **kwargs) -> Iterator[str]:
        """调用ModelScope（流式）"""
        if self.client is None:
            raise RuntimeError("未安装 openai 包，当前环境不支持ModelScope SDK流式")
        messages = kwargs.get("messages") or [
            {"role": "system", "content": "你是一个专业的医疗质控专家。"},
            {"role": "user", "content": prompt}
        ]
        response = self.client.chat.completions.create(
            model=kwargs.get("model", self.model),
            messages=messages,
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            stream=True,
        )
        for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    def _extract_text_content(self, content: Union[str, List[Dict[str, Any]], None]) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
                else:
                    parts.append(str(item))
            return "".join(parts)
        return str(content)

    def debug_snapshot(self) -> Dict[str, Any]:
        snapshot = dict(self._stats)
        total = int(snapshot.get("call_total", 0))
        latency_total = float(snapshot.get("latency_ms_total", 0.0))
        snapshot["avg_latency_ms"] = round(latency_total / total, 2) if total > 0 else 0.0
        return snapshot


class LLMClientFactory:
    """LLM客户端工厂"""

    @staticmethod
    def create_client(
        client_type: str,
        config: Dict[str, Any]
    ) -> BaseLLMClient:
        """
        创建LLM客户端

        Args:
            client_type: 客户端类型（openai/qwen/local/ollama/modelscope）
            config: 配置参数

        Returns:
            LLM客户端实例
        """
        if client_type == "openai":
            return OpenAIClient(**config)
        elif client_type == "qwen":
            return QwenClient(**config)
        elif client_type == "local":
            return LocalModelClient(**config)
        elif client_type == "ollama":
            return OllamaClient(**config)
        elif client_type == "modelscope":
            return ModelScopeClient(**config)
        else:
            raise ValueError(f"Unsupported client type: {client_type}")


# 配置示例
EXAMPLE_CONFIGS = {
    "openai": {
        "api_key": "sk-xxx",
        "model": "gpt-3.5-turbo",
        "temperature": 0.1,
        "max_tokens": 2000
    },
    "qwen": {
        "api_key": "sk-xxx",
        "model": "qwen-turbo",
        "temperature": 0.1,
        "max_tokens": 2000
    },
    "local": {
        "base_url": "http://localhost:8000",
        "model": "qwen-30b",
        "temperature": 0.1,
        "max_tokens": 2000
    },
    "ollama": {
        "base_url": "http://localhost:11434",
        "model": "qwen:30b",
        "temperature": 0.1
    },
    "modelscope": {
        "api_key": "ms-xxx",
        "model": "Qwen/Qwen3.5-35B-A3B",
        "base_url": "https://api-inference.modelscope.cn/v1",
        "temperature": 0.1,
        "max_tokens": 2000
    }
}


if __name__ == "__main__":
    # 测试代码
    # 使用Ollama客户端（需要先启动Ollama服务）
    try:
        client = LLMClientFactory.create_client("ollama", {
            "base_url": "http://localhost:11434",
            "model": "qwen:7b",
            "temperature": 0.1
        })

        prompt = """请判断以下病历是否完整：
患者：张三，男，45岁
主诉：腹痛3天
现病史：患者3天前无明显诱因出现腹痛...

请输出JSON格式：
{
    "violated": true/false,
    "description": "描述",
    "confidence": 0.95
}
"""

        response = client.call(prompt)
        print("Response:", response)

    except Exception as e:
        print(f"Error: {e}")
        print("请确保Ollama服务已启动，并且已下载相应模型")
