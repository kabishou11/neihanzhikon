"""
医疗内涵质控 FastAPI 服务

启动:
    uvicorn fastapi_app:app --host 0.0.0.0 --port 8000 --reload
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Generator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

ROOT = Path(__file__).parent
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def _load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_env_file(ROOT / ".env")

from fastapi_qc import (
    QualityControlRequest,
    QualityControlResponse,
    QualityControlDebugResponse,
    create_service_from_config,
)


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

service = create_service_from_config(str(ROOT / "config" / "config.yaml"))


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
            if not payload.patientList.patient_id or not payload.patientList.record_id:
                raise HTTPException(status_code=400, detail="patientList.patient_id/record_id 不能为空")
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
            if not payload.patientList.patient_id or not payload.patientList.record_id:
                raise HTTPException(status_code=400, detail="patientList.patient_id/record_id 不能为空")
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "fastapi_app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
