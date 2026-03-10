"""
医疗内涵质控 FastAPI 服务

启动:
    uvicorn fastapi_app:app --host 0.0.0.0 --port 8000 --reload
"""

import json
import os
import sys
from pathlib import Path
from typing import Generator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

ROOT = Path(__file__).parent
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# 加载环境变量
load_dotenv(ROOT / ".env")

from fastapi_qc import (
    QualityControlRequest,
    QualityControlResponse,
    QualityControlDebugResponse,
    create_service_from_env,
    QARequest,
    QAResponse,
)
from fastapi_qc.qa_service import get_qa_service


app = FastAPI(
    title="医疗内涵质控 API",
    description=(
        "接收形式质控+病历数据，执行内涵质控并输出统一缺陷结果。"
        "支持 mock/live 两种 LLM 执行模式。"
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

service = create_service_from_env()
qa_service = get_qa_service()


@app.get("/api/v1/health", summary="健康检查")
def health() -> dict:
    return {"status": "ok", "service": "medical-qc-fastapi"}


@app.post(
    "/api/v1/qc/check",
    response_model=QualityControlResponse,
    summary="执行质控",
    description=(
        "核心接口：入参为 2.26 需求沟通定义的完整报文，"
        "出参为最终质控缺陷结果集合。"
    ),
)
def check_quality(payload: QualityControlRequest) -> QualityControlResponse:
    try:
        if payload.options.strictMode:
            if not payload.visitList.visit_id or not payload.visitList.record_id:
                raise HTTPException(status_code=400, detail="visitList.visit_id/record_id 不能为空")
        return service.check(payload)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"质控执行失败: {exc}") from exc


@app.post(
    "/api/v1/qc/check/debug",
    response_model=QualityControlDebugResponse,
    summary="执行质控（含调试信息）",
    description=(
        "返回 result(标准出参) + debug(模型调用统计、执行路径)。"
        "用于确认 live 是否真实调用模型。"
    ),
)
def check_quality_debug(payload: QualityControlRequest) -> QualityControlDebugResponse:
    try:
        if payload.options.strictMode:
            if not payload.visitList.visit_id or not payload.visitList.record_id:
                raise HTTPException(status_code=400, detail="visitList.visit_id/record_id 不能为空")
        result, debug = service.check_with_debug(payload)
        return QualityControlDebugResponse(result=result, debug=debug)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"质控执行失败: {exc}") from exc


@app.post(
    "/api/v1/qc/check/stream",
    summary="流式执行质控（JSON Lines）",
    description="每完成一条LLM规则立即推送结果，最后推送完整汇总。用于前端实时展示进度。",
)
def check_quality_stream(payload: QualityControlRequest) -> StreamingResponse:
    def event_stream() -> Generator[str, None, None]:
        for event in service.check_stream(payload):
            yield json.dumps(event, ensure_ascii=False) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@app.get("/api/v1/qc/template", summary="获取入参模板")
def payload_template() -> dict:
    sample_file = ROOT / "2.26需求沟通" / "入参接口入参报文样例"
    if not sample_file.exists():
        return {"message": "sample not found"}
    with open(sample_file, "r", encoding="utf-8") as file:
        return json.loads(file.read())


# ==================== 医疗问答接口 ====================

@app.post(
    "/api/v1/qa/chat",
    summary="医疗问答（统一接口）",
    description=(
        "医疗知识和质控规则问答，支持多轮对话上下文记忆。\n\n"
        "## 参数说明\n\n"
        "**stream参数（重要）**：\n"
        "- `stream=false`（默认）：返回完整JSON响应，包含回答内容、模型信息、性能统计和上下文分析\n"
        "- `stream=true`：返回实时文本流，适合用户交互场景，减少首字延迟\n\n"
        "**历史对话记忆**：\n"
        "- 通过messages数组传递完整对话历史\n"
        "- 支持system/user/assistant三种角色\n"
        "- 前端维护上下文，后端无状态处理\n\n"
        "## 调用示例\n\n"
        "**非流式调用**（获取完整响应和统计信息）：\n"
        "```json\n"
        "{\n"
        "  \"messages\": [\n"
        "    {\"role\": \"system\", \"content\": \"你是医疗质控专家\"},\n"
        "    {\"role\": \"user\", \"content\": \"什么是内涵质控？\"}\n"
        "  ],\n"
        "  \"stream\": false,\n"
        "  \"temperature\": 0.7,\n"
        "  \"max_tokens\": 2048\n"
        "}\n"
        "```\n\n"
        "**流式调用**（实时返回文本）：\n"
        "```json\n"
        "{\n"
        "  \"messages\": [\n"
        "    {\"role\": \"system\", \"content\": \"你是医疗质控专家\"},\n"
        "    {\"role\": \"user\", \"content\": \"什么是内涵质控？\"}\n"
        "  ],\n"
        "  \"stream\": true,\n"
        "  \"temperature\": 0.7,\n"
        "  \"max_tokens\": 2048\n"
        "}\n"
        "```\n\n"
        "**多轮对话**（带上下文）：\n"
        "```json\n"
        "{\n"
        "  \"messages\": [\n"
        "    {\"role\": \"system\", \"content\": \"你是医疗质控专家\"},\n"
        "    {\"role\": \"user\", \"content\": \"什么是内涵质控？\"},\n"
        "    {\"role\": \"assistant\", \"content\": \"内涵质控是...\"},\n"
        "    {\"role\": \"user\", \"content\": \"它与形式质控有什么区别？\"}\n"
        "  ],\n"
        "  \"stream\": false\n"
        "}\n"
        "```\n\n"
        "## 性能优化\n"
        "- 单例模式复用LLM连接\n"
        "- 连接池减少握手开销\n"
        "- 流式传输降低首字延迟\n"
        "- 最小化序列化开销"
    ),
)
def qa_chat(request: QARequest):
    """
    医疗问答统一接口

    特性：
    - 多轮对话上下文记忆（通过messages数组）
    - 流式/非流式输出切换（stream参数）
    - 医疗知识咨询、质控规则解释
    - 上下文分析（message_count、conversation_turns等）

    设计原则：
    - 前端维护对话历史，后端无状态处理
    - 每次请求携带完整上下文（system + 历史对话 + 当前问题）
    - 单例模式复用LLM连接，减少初始化开销

    示例：
    ```json
    {
      "messages": [
        {"role": "system", "content": "你是医疗质控专家"},
        {"role": "user", "content": "什么是内涵质控？"},
        {"role": "assistant", "content": "内涵质控是..."},
        {"role": "user", "content": "它与形式质控有什么区别？"}
      ],
      "stream": true,
      "temperature": 0.7,
      "max_tokens": 2048
    }
    ```
    """
    try:
        # 转换消息格式
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

        # 根据stream参数决定返回类型
        if request.stream:
            # 流式输出
            def event_stream() -> Generator[str, None, None]:
                try:
                    for chunk in qa_service.chat_stream(
                        messages=messages,
                        temperature=request.temperature,
                        max_tokens=request.max_tokens,
                        top_p=request.top_p,
                    ):
                        yield chunk

                except RuntimeError as exc:
                    yield f"\n\n[错误] {str(exc)}"
                except Exception as exc:
                    yield f"\n\n[错误] 问答失败: {exc}"

            return StreamingResponse(
                event_stream(),
                media_type="text/plain; charset=utf-8"
            )
        else:
            # 非流式输出（返回完整响应 + 统计信息）
            result = qa_service.chat(
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                top_p=request.top_p,
            )

            return QAResponse(**result)

    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"问答失败: {exc}") from exc



if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "fastapi_app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
