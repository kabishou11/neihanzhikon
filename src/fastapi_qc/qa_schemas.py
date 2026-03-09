"""
医疗问答接口数据模型
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class Message(BaseModel):
    """对话消息"""
    role: str = Field(..., description="角色：system/user/assistant")
    content: str = Field(..., description="消息内容")


class QARequest(BaseModel):
    """
    问答请求

    支持流式和非流式两种模式：
    - stream=false: 返回完整JSON响应（包含统计信息和上下文分析）
    - stream=true: 返回实时文本流（适合用户交互场景）
    """
    messages: List[Message] = Field(
        ...,
        description="对话历史数组，包含system/user/assistant角色的消息。支持多轮对话上下文记忆。"
    )
    stream: Optional[bool] = Field(
        False,
        description="是否启用流式输出。false=完整响应（含统计），true=实时文本流"
    )
    temperature: Optional[float] = Field(
        0.7,
        ge=0.0,
        le=1.0,
        description="温度参数，控制输出随机性。0=确定性，1=最随机"
    )
    max_tokens: Optional[int] = Field(
        2048,
        ge=1,
        le=4096,
        description="最大生成token数"
    )
    top_p: Optional[float] = Field(
        0.9,
        ge=0.0,
        le=1.0,
        description="核采样参数，控制输出多样性"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "messages": [
                    {"role": "system", "content": "你是一位专业的医疗质控专家。"},
                    {"role": "user", "content": "什么是医疗内涵质控？"}
                ],
                "stream": False,
                "temperature": 0.7,
                "max_tokens": 2048,
                "top_p": 0.9
            }
        }


class QAResponse(BaseModel):
    """问答响应"""
    content: str = Field(..., description="回答内容")
    model: str = Field(..., description="使用的模型")
    usage: Optional[dict] = Field(None, description="Token 使用统计")
    context: Optional[dict] = Field(None, description="上下文信息")

    class Config:
        json_schema_extra = {
            "example": {
                "content": "医疗内涵质控是指对医疗服务的内在质量进行评价和控制...",
                "model": "Qwen/Qwen3.5-35B-A3B",
                "usage": {
                    "prompt_tokens": 50,
                    "completion_tokens": 100,
                    "total_tokens": 150,
                    "elapsed_ms": 1234.56
                },
                "context": {
                    "message_count": 3,
                    "conversation_turns": 1,
                    "has_system_prompt": True,
                    "context_length": 150
                }
            }
        }
