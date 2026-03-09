"""
FastAPI 质控接口快速可视化验证页（Gradio）—— 流式实时版 + 医疗问答助手

功能：
1. 质控测试：支持流式/非流式切换
2. 医疗问答助手：流式对话

启动:
    python web_fastapi_verify.py
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

import gradio as gr
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).parent
SAMPLE_FILE = ROOT / "2.26需求沟通" / "入参接口入参报文样例"
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# 加载环境变量
load_dotenv(ROOT / ".env")

# 导入 LLM 客户端用于问答
try:
    from llm_client import ModelScopeClient
    qa_client: Optional[ModelScopeClient] = ModelScopeClient(
        api_key=os.getenv("MODELSCOPE_API_KEY", ""),
        model=os.getenv("MODELSCOPE_MODEL", "Qwen/Qwen3.5-35B-A3B"),
        base_url=os.getenv("MODELSCOPE_BASE_URL", "https://api-inference.modelscope.cn/v1"),
        temperature=float(os.getenv("MODELSCOPE_TEMPERATURE", "0.7")),
        max_tokens=int(os.getenv("MODELSCOPE_MAX_TOKENS", "2048")),
        timeout=int(os.getenv("MODELSCOPE_TIMEOUT", "90")),
        top_p=float(os.getenv("MODELSCOPE_TOP_P", "0.9")),
    )
except Exception as e:
    print(f"Warning: Failed to create QA client: {e}")
    qa_client = None


def load_sample() -> str:
    if not SAMPLE_FILE.exists():
        return "{}"
    return SAMPLE_FILE.read_text(encoding="utf-8")


def _stream_url(base_url: str, use_stream: bool = True) -> str:
    """
    根据 use_stream 参数决定是否转换为流式接口

    Args:
        base_url: 基础 URL
        use_stream: 是否使用流式接口

    Returns:
        转换后的 URL
    """
    url = base_url.strip().rstrip("/")

    if not use_stream:
        # 非流式：使用 /check/debug 接口
        for suffix in ("/stream", "/debug", ""):
            if url.endswith(f"/check{suffix}"):
                return url[: -len(f"/check{suffix}")] + "/check/debug"
        return url + "/debug"

    # 流式：把 /check 或 /check/debug 统一换成 /check/stream
    for suffix in ("/debug", ""):
        if url.endswith(f"/check{suffix}"):
            return url[: -len(f"/check{suffix}")] + "/check/stream"
    return url + "/stream"


def _format_violations_md(violations: List[Dict[str, Any]]) -> str:
    if not violations:
        return "**无缺陷**"
    lines = ["| # | 文书 | 规则 | 等级 | 扣分 | 整改建议 |",
             "|---|------|------|------|:----:|----------|"]
    for i, v in enumerate(violations, 1):
        rn = v.get("ruleName", "")
        rn_short = rn[:22] + "…" if len(rn) > 22 else rn
        sg = v.get("suggestion", "")
        sg_short = sg[:45] + "…" if len(sg) > 45 else sg
        lines.append(
            f"| {i} | {v.get('docName','')} | {rn_short} | "
            f"{v.get('levelLabel','')} | **{v.get('deductScore',0)}** | {sg_short} |"
        )
    return "\n".join(lines)


def _grade_badge(grade: str) -> str:
    color = {"甲": "#16a34a", "乙": "#ca8a04", "丙": "#ea580c", "丁": "#dc2626"}.get(grade, "#6b7280")
    return f'<span style="background:{color};color:#fff;padding:2px 10px;border-radius:4px;font-weight:bold">{grade}</span>'


def run_non_stream(
    api_url: str,
    llm_mode: str,
    max_rules: int,
    payload_text: str,
) -> Tuple[str, str, str]:
    """非流式执行质控"""
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        return f"入参 JSON 解析失败: {exc}", "", ""

    payload.setdefault("options", {})
    payload["options"]["llmMode"] = llm_mode
    payload["options"]["maxLlmRules"] = int(max_rules)
    payload["options"]["fallbackToHeuristic"] = False

    target_url = _stream_url(api_url, use_stream=False)

    try:
        # 增加超时时间，并使用连接超时和读取超时分离
        # 连接超时：10秒（快速失败）
        # 读取超时：1800秒（30分钟，支持大量规则）
        resp = requests.post(target_url, json=payload, timeout=(10, 1800))
        resp.raise_for_status()
        data = resp.json()

        result = data.get("result", {})
        debug = data.get("debug", {})

        score = 100 - float(result.get("totalDeductScore", 0))
        grade = result.get("qcGrade", "")
        all_violations = result.get("violations", [])

        summary_lines = [
            "## 质控完成（非流式）",
            "",
            f"| 项目 | 值 |",
            f"|------|-----|",
            f"| 患者ID | `{result.get('patientId','')}` |",
            f"| 记录ID | `{result.get('recordId','')}` |",
            f"| 质控类型 | {result.get('qcType','')} |",
            f"| 状态 | **{result.get('qcStatus','')}** |",
            f"| 等级 | {_grade_badge(grade)} |",
            f"| 质量分 | **{score:.1f}** / 100 |",
            f"| 总扣分 | {result.get('totalDeductScore',0)} |",
            f"| 缺陷数 | **{result.get('defectCount',0)}** |",
            f"| 执行时间 | {debug.get('elapsedMs', 0)} ms |",
            f"| 执行模式 | {debug.get('execution', {}).get('mode', '')} |",
        ]

        return (
            "\n".join(summary_lines),
            json.dumps(result, ensure_ascii=False, indent=2),
            _format_violations_md(all_violations),
        )

    except requests.exceptions.ConnectionError:
        return "连接失败：FastAPI 服务未启动，请先运行 `uvicorn fastapi_app:app --port 8000`", "", ""
    except Exception as exc:
        return f"请求失败: {exc}", "", ""


def run_qc_check(
    api_url: str,
    llm_mode: str,
    max_rules: int,
    payload_text: str,
    use_stream: bool = True,
) -> Generator[Tuple[str, str, str], None, None]:
    """
    执行质控（支持流式/非流式切换）

    Args:
        api_url: API 地址
        llm_mode: LLM 模式
        max_rules: 最大规则数
        payload_text: 入参 JSON
        use_stream: 是否使用流式接口
    """
    # 如果不使用流式，直接调用非流式函数
    if not use_stream:
        result = run_non_stream(api_url, llm_mode, max_rules, payload_text)
        yield result
        return

    # 以下是流式逻辑
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        yield f"入参 JSON 解析失败: {exc}", "", ""
        return

    payload.setdefault("options", {})
    payload["options"]["llmMode"] = llm_mode
    payload["options"]["maxLlmRules"] = int(max_rules)
    payload["options"]["fallbackToHeuristic"] = False

    target_url = _stream_url(api_url, use_stream=True)

    # 状态变量
    done = 0
    total = 0
    violations_live: List[Dict[str, Any]] = []
    log_lines: List[str] = []

    def _progress_bar(d: int, t: int) -> str:
        if t == 0:
            return ""
        pct = int(d / t * 100)
        filled = int(pct / 5)
        bar = "█" * filled + "░" * (20 - filled)
        return f"`[{bar}] {pct}%  {d}/{t}`"

    try:
        with requests.post(target_url, json=payload, stream=True, timeout=(10, 600)) as resp:
            resp.raise_for_status()
            for raw_line in resp.iter_lines():
                if not raw_line:
                    continue
                try:
                    event = json.loads(raw_line)
                except Exception:
                    continue

                ev = event.get("event", "")

                if ev == "start":
                    total = event.get("total", 0)
                    existing = event.get("existing", 0)
                    mode = event.get("mode", llm_mode)
                    log_lines = [
                        f"## 质控执行中…（流式）",
                        f"- 患者ID: `{event.get('patientId','')}`",
                        f"- 模式: `{mode}`",
                        f"- 形式质控违规: **{existing}** 条",
                        f"- LLM规则总数: **{total}** 条",
                        "",
                        _progress_bar(0, total),
                    ]
                    yield "\n".join(log_lines), "", ""

                elif ev == "rule_done":
                    done = event.get("done", done)
                    total = event.get("total", total)
                    rule_key = event.get("ruleKey", "")
                    rule_name = event.get("ruleName", "")[:28]
                    violated = event.get("violated", False)
                    engine = event.get("engine", "")
                    icon = "🔴" if violated else "🟢"

                    log_lines.append(
                        f"{icon} `[{done}/{total}]` **{rule_key}** {rule_name}"
                        + (f"  ← *{engine}*" if engine not in ("live", "") else "")
                    )
                    # 更新进度条（替换最后一行进度条）
                    for i in range(len(log_lines) - 1, -1, -1):
                        if log_lines[i].startswith("`["):
                            log_lines[i] = _progress_bar(done, total)
                            break
                    else:
                        log_lines.append(_progress_bar(done, total))

                    if violated and event.get("violation"):
                        violations_live.append(event["violation"])

                    yield "\n".join(log_lines), "", _format_violations_md(violations_live)

                elif ev == "complete":
                    result = event.get("result", {})
                    score = 100 - float(result.get("totalDeductScore", 0))
                    grade = result.get("qcGrade", "")
                    all_violations = result.get("violations", [])

                    summary_lines = [
                        "## 质控完成（流式）",
                        "",
                        f"| 项目 | 值 |",
                        f"|------|-----|",
                        f"| 患者ID | `{result.get('patientId','')}` |",
                        f"| 记录ID | `{result.get('recordId','')}` |",
                        f"| 质控类型 | {result.get('qcType','')} |",
                        f"| 状态 | **{result.get('qcStatus','')}** |",
                        f"| 等级 | {_grade_badge(grade)} |",
                        f"| 质量分 | **{score:.1f}** / 100 |",
                        f"| 总扣分 | {result.get('totalDeductScore',0)} |",
                        f"| 缺陷数 | **{result.get('defectCount',0)}** |",
                    ]

                    yield (
                        "\n".join(summary_lines),
                        json.dumps(result, ensure_ascii=False, indent=2),
                        _format_violations_md(all_violations),
                    )

    except requests.exceptions.ConnectionError:
        yield "连接失败：FastAPI 服务未启动，请先运行 `uvicorn fastapi_app:app --port 8000`", "", ""
    except Exception as exc:
        yield f"请求失败: {exc}", "", ""


def medical_qa_stream(
    message: str,
    history: list,
    system_prompt: str,
    temperature: float,
    max_tokens: int,
    use_api: bool = True,
    api_url: str = "http://127.0.0.1:8000"
) -> Generator[str, None, None]:
    """
    医疗问答流式响应

    Args:
        message: 用户消息
        history: 对话历史
        system_prompt: 系统提示词
        temperature: 温度参数
        max_tokens: 最大生成长度
        use_api: 是否使用 FastAPI 接口（True）或直接调用客户端（False）
        api_url: FastAPI 地址
    """
    # 构建消息历史
    messages = [{"role": "system", "content": system_prompt}]

    for user_msg, assistant_msg in history:
        messages.append({"role": "user", "content": user_msg})
        if assistant_msg:
            messages.append({"role": "assistant", "content": assistant_msg})

    messages.append({"role": "user", "content": message})

    if use_api:
        # 使用 FastAPI 统一接口（推荐，性能优化）
        try:
            response = requests.post(
                f"{api_url}/api/v1/qa/chat",
                json={
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": True,  # 启用流式输出
                },
                stream=True,
                timeout=(5, 120)
            )
            response.raise_for_status()

            response_text = ""
            for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
                if chunk:
                    response_text += chunk
                    yield response_text

        except requests.exceptions.ConnectionError:
            yield "错误：FastAPI 服务未启动，请先运行 `uvicorn fastapi_app:app --port 8000`"
        except Exception as e:
            yield f"错误：{str(e)}"
    else:
        # 直接调用客户端（备用方案）
        if not qa_client:
            yield "错误：问答客户端未初始化，请检查 .env 配置中的 MODELSCOPE_API_KEY"
            return

        try:
            response_text = ""
            for chunk in qa_client.stream(
                prompt="",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            ):
                response_text += chunk
                yield response_text

        except Exception as e:
            yield f"错误：{str(e)}"


CSS = """
:root {
  --bg1: #f7f3ea; --bg2: #e9efe6;
  --ink: #263238; --accent: #0f766e;
}
.gradio-container {
  font-family: "Noto Serif SC", "FangSong", serif !important;
  color: var(--ink);
  background: linear-gradient(135deg, var(--bg1), var(--bg2));
}
#title-card {
  border: 1px solid rgba(15,118,110,0.35); border-radius: 14px;
  background: rgba(255,255,255,0.72); backdrop-filter: blur(4px);
  padding: 14px 18px;
}
"""


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="医疗内涵质控验证台", css=CSS) as demo:
        gr.HTML("""
<div id="title-card">
  <h2 style="margin:0;color:#0f766e;">医疗内涵质控 FastAPI 验证台 + 问答助手</h2>
  <p style="margin:6px 0 0;font-size:0.9em;">
    质控测试（流式/非流式切换） + 医疗问答助手 &nbsp;|&nbsp;
    FastAPI: <code>uvicorn fastapi_app:app --port 8000</code> &nbsp;|&nbsp;
    <a href="http://127.0.0.1:8000/docs" target="_blank">接口文档</a>
  </p>
</div>
        """)

        with gr.Tabs():
            # Tab 1: 质控测试
            with gr.Tab("质控测试"):
                with gr.Row():
                    api_url = gr.Textbox(
                        label="FastAPI 地址",
                        value="http://127.0.0.1:8000/api/v1/qc/check",
                        scale=3,
                    )
                    llm_mode = gr.Dropdown(
                        label="LLM模式", choices=["live", "mock"], value="live", scale=1,
                    )
                    max_rules = gr.Slider(
                        label="最大规则数", minimum=1, maximum=300, value=20, step=1, scale=2,
                    )

                with gr.Row():
                    use_stream_checkbox = gr.Checkbox(
                        label="启用流式输出",
                        value=True,
                        info="勾选后使用流式接口（/check/stream），取消勾选使用非流式接口（/check/debug）"
                    )

                with gr.Row():
                    with gr.Column(scale=1):
                        payload_input = gr.TextArea(label="入参 JSON", lines=28)
                        with gr.Row():
                            load_btn = gr.Button("加载样例", variant="secondary")
                            run_btn = gr.Button("执行质控", variant="primary")

                    with gr.Column(scale=1):
                        with gr.Tabs():
                            with gr.Tab("实时进度 / 结果摘要"):
                                summary_md = gr.Markdown(value="*等待执行…*")
                            with gr.Tab("缺陷列表"):
                                violations_md = gr.Markdown(value="*等待执行…*")
                            with gr.Tab("完整出参 JSON"):
                                raw_json = gr.TextArea(label="完整出参", lines=26)

                gr.Markdown("""
                **使用说明：**
                - 勾选"启用流式输出"可以看到实时进度（推荐）
                - 取消勾选则使用非流式接口，一次性返回完整结果
                - 可以对比两种模式的输出是否一致
                """)

                load_btn.click(fn=load_sample, outputs=payload_input)
                run_btn.click(
                    fn=run_qc_check,
                    inputs=[api_url, llm_mode, max_rules, payload_input, use_stream_checkbox],
                    outputs=[summary_md, raw_json, violations_md],
                )

            # Tab 2: 医疗问答助手
            with gr.Tab("医疗问答助手"):
                gr.Markdown("### 医疗与质控问答助手")
                gr.Markdown("支持医疗知识问答、质控规则咨询等")

                with gr.Row():
                    qa_api_url = gr.Textbox(
                        label="FastAPI 地址",
                        value="http://127.0.0.1:8000",
                        scale=2,
                    )
                    qa_use_api = gr.Checkbox(
                        label="使用 FastAPI 接口",
                        value=True,
                        scale=1,
                        info="推荐：性能优化，连接复用"
                    )

                with gr.Row():
                    with gr.Column(scale=3):
                        chatbot = gr.Chatbot(
                            label="对话历史",
                            height=500,
                            show_copy_button=True
                        )

                        with gr.Row():
                            qa_input = gr.Textbox(
                                label="输入问题",
                                placeholder="请输入您的医疗或质控相关问题...",
                                lines=2,
                                scale=4
                            )
                            qa_submit_btn = gr.Button("发送", variant="primary", scale=1)

                        with gr.Row():
                            qa_clear_btn = gr.Button("清空对话")
                            qa_retry_btn = gr.Button("重新生成")

                    with gr.Column(scale=1):
                        gr.Markdown("### 参数设置")

                        qa_system_prompt = gr.Textbox(
                            label="系统提示词",
                            value="你是一位专业的医疗质控专家，精通医疗知识和质控规则。请用专业、准确、易懂的方式回答问题。",
                            lines=4
                        )

                        qa_temperature = gr.Slider(
                            label="Temperature",
                            minimum=0.0,
                            maximum=1.0,
                            value=0.7,
                            step=0.1,
                            info="控制回答的随机性"
                        )

                        qa_max_tokens = gr.Slider(
                            label="Max Tokens",
                            minimum=512,
                            maximum=4096,
                            value=2048,
                            step=256,
                            info="最大生成长度"
                        )

                        gr.Markdown("""
                        **快速测试问题：**
                        - 什么是医疗内涵质控？
                        - 病历首页必填项有哪些？
                        - 如何判断病程记录是否完整？
                        - 质控规则的扣分标准是什么？
                        """)

                # 问答交互
                def user_submit(message, history):
                    return "", history + [[message, None]]

                def bot_response(history, system_prompt, temperature, max_tokens, use_api, api_url):
                    if not history or history[-1][1] is not None:
                        return history

                    user_message = history[-1][0]
                    history[-1][1] = ""

                    for response in medical_qa_stream(
                        user_message,
                        history[:-1],
                        system_prompt,
                        temperature,
                        max_tokens,
                        use_api,
                        api_url
                    ):
                        history[-1][1] = response
                        yield history

                qa_input.submit(
                    fn=user_submit,
                    inputs=[qa_input, chatbot],
                    outputs=[qa_input, chatbot],
                    queue=False
                ).then(
                    fn=bot_response,
                    inputs=[chatbot, qa_system_prompt, qa_temperature, qa_max_tokens, qa_use_api, qa_api_url],
                    outputs=chatbot
                )

                qa_submit_btn.click(
                    fn=user_submit,
                    inputs=[qa_input, chatbot],
                    outputs=[qa_input, chatbot],
                    queue=False
                ).then(
                    fn=bot_response,
                    inputs=[chatbot, qa_system_prompt, qa_temperature, qa_max_tokens, qa_use_api, qa_api_url],
                    outputs=chatbot
                )

                qa_clear_btn.click(
                    fn=lambda: [],
                    outputs=chatbot
                )

                qa_retry_btn.click(
                    fn=lambda h: h[:-1] if h else h,
                    inputs=chatbot,
                    outputs=chatbot
                ).then(
                    fn=bot_response,
                    inputs=[chatbot, qa_system_prompt, qa_temperature, qa_max_tokens, qa_use_api, qa_api_url],
                    outputs=chatbot
                )

    return demo


if __name__ == "__main__":
    demo = build_ui()
    demo.queue()  # 启用队列以支持流式输出
    demo.launch(server_name="0.0.0.0", server_port=7861, show_error=True)
