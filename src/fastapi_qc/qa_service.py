"""
医疗问答服务 - 优化版
实现连接池、缓存等性能优化
"""

import os
import time
from typing import Dict, Any, Optional, Iterator
from functools import lru_cache

from llm_client import ModelScopeClient


class QAService:
    """医疗问答服务（单例模式，连接复用）"""

    _instance: Optional['QAService'] = None
    _client: Optional[ModelScopeClient] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None:
            self._initialize_client()

    def _initialize_client(self):
        """初始化 LLM 客户端（复用连接）"""
        try:
            self._client = ModelScopeClient(
                api_key=os.getenv("MODELSCOPE_API_KEY", ""),
                model=os.getenv("MODELSCOPE_MODEL", "Qwen/Qwen3.5-35B-A3B"),
                base_url=os.getenv("MODELSCOPE_BASE_URL", "https://api-inference.modelscope.cn/v1"),
                temperature=float(os.getenv("MODELSCOPE_TEMPERATURE", "0.7")),
                max_tokens=int(os.getenv("MODELSCOPE_MAX_TOKENS", "2048")),
                timeout=int(os.getenv("MODELSCOPE_TIMEOUT", "90")),
                top_p=float(os.getenv("MODELSCOPE_TOP_P", "0.9")),
            )
        except Exception as e:
            print(f"Warning: Failed to initialize QA client: {e}")
            self._client = None

    @property
    def client(self) -> Optional[ModelScopeClient]:
        """获取客户端实例"""
        return self._client

    def chat(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 0.9,
    ) -> Dict[str, Any]:
        """
        非流式问答

        Args:
            messages: 对话消息列表
            temperature: 温度参数
            max_tokens: 最大生成长度
            top_p: Top-p 采样

        Returns:
            包含回答内容、统计信息和上下文信息的字典
        """
        if not self._client:
            raise RuntimeError("QA 客户端未初始化，请检查 .env 配置")

        start_time = time.perf_counter()

        # 分析上下文
        context_info = self._analyze_context(messages)

        try:
            # 调用 LLM
            response = self._client.call(
                prompt="",  # 使用 messages 参数
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
            )

            elapsed_ms = (time.perf_counter() - start_time) * 1000

            return {
                "content": response,
                "model": self._client.model,
                "usage": {
                    "elapsed_ms": round(elapsed_ms, 2),
                },
                "context": context_info,
            }
        except Exception as e:
            raise RuntimeError(f"问答调用失败: {str(e)}")

    def _analyze_context(self, messages: list) -> Dict[str, Any]:
        """
        分析上下文信息

        Args:
            messages: 对话消息列表

        Returns:
            上下文分析结果
        """
        # 统计消息数量
        message_count = len(messages)

        # 统计对话轮次（user 消息数量）
        conversation_turns = sum(1 for msg in messages if msg.get("role") == "user")

        # 检查是否有系统提示词
        has_system_prompt = any(msg.get("role") == "system" for msg in messages)

        # 计算上下文长度（字符数）
        context_length = sum(len(msg.get("content", "")) for msg in messages)

        # 获取最近的对话历史（最后3轮）
        recent_history = []
        user_count = 0
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_count += 1
                if user_count > 3:
                    break
            recent_history.insert(0, {
                "role": msg.get("role"),
                "content_preview": msg.get("content", "")[:50] + "..." if len(msg.get("content", "")) > 50 else msg.get("content", "")
            })

        return {
            "message_count": message_count,
            "conversation_turns": conversation_turns,
            "has_system_prompt": has_system_prompt,
            "context_length": context_length,
            "recent_history": recent_history,
        }


    def chat_stream(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 0.9,
    ) -> Iterator[str]:
        """
        流式问答

        Args:
            messages: 对话消息列表
            temperature: 温度参数
            max_tokens: 最大生成长度
            top_p: Top-p 采样

        Yields:
            生成的文本片段
        """
        if not self._client:
            raise RuntimeError("QA 客户端未初始化，请检查 .env 配置")

        try:
            # 流式调用
            for chunk in self._client.stream(
                prompt="",  # 使用 messages 参数
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
            ):
                yield chunk
        except Exception as e:
            raise RuntimeError(f"流式问答调用失败: {str(e)}")


# 全局单例实例
_qa_service: Optional[QAService] = None


def get_qa_service() -> QAService:
    """获取 QA 服务单例"""
    global _qa_service
    if _qa_service is None:
        _qa_service = QAService()
    return _qa_service
