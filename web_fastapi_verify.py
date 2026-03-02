"""
FastAPI 质控接口快速可视化验证页（Gradio）—— 流式实时版

启动:
    python web_fastapi_verify.py
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, Generator, List, Tuple

import gradio as gr
import requests

ROOT = Path(__file__).parent
SAMPLE_FILE = ROOT / "2.26需求沟通" / "入参接口入参报文样例"
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

STREAM_URL_SUFFIX = "/stream"


def load_sample() -> str:
    if not SAMPLE_FILE.exists():
        return "{}"
    return SAMPLE_FILE.read_text(encoding="utf-8")


def _stream_url(base_url: str) -> str:
    url = base_url.strip().rstrip("/")
    # 把 /check 或 /check/debug 统一换成 /check/stream
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


def run_stream(
    api_url: str,
    llm_mode: str,
    max_rules: int,
    payload_text: str,
) -> Generator[Tuple[str, str, str], None, None]:
    """Gradio generator：消费 /check/stream，每收到一条事件就 yield 更新 UI。"""

    # 解析入参
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        yield f"入参 JSON 解析失败: {exc}", "", ""
        return

    payload.setdefault("options", {})
    payload["options"]["llmMode"] = llm_mode
    payload["options"]["maxLlmRules"] = int(max_rules)
    payload["options"]["fallbackToHeuristic"] = False

    target_url = _stream_url(api_url)

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
                        f"## 质控执行中…",
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
                        "## 质控完成",
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
  <h2 style="margin:0;color:#0f766e;">医疗内涵质控 FastAPI 验证台</h2>
  <p style="margin:6px 0 0;font-size:0.9em;">
    流式实时展示每条规则执行结果 &nbsp;|&nbsp;
    FastAPI: <code>uvicorn fastapi_app:app --port 8000</code> &nbsp;|&nbsp;
    <a href="http://127.0.0.1:8000/docs" target="_blank">接口文档</a>
  </p>
</div>
        """)

        with gr.Row():
            api_url = gr.Textbox(
                label="FastAPI 地址（自动转为 /stream 接口）",
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
            with gr.Column(scale=1):
                payload_input = gr.TextArea(label="入参 JSON", lines=28)
                with gr.Row():
                    load_btn = gr.Button("加载样例", variant="secondary")
                    run_btn = gr.Button("执行质控（流式）", variant="primary")

            with gr.Column(scale=1):
                with gr.Tabs():
                    with gr.Tab("实时进度 / 结果摘要"):
                        summary_md = gr.Markdown(value="*等待执行…*")
                    with gr.Tab("缺陷列表"):
                        violations_md = gr.Markdown(value="*等待执行…*")
                    with gr.Tab("完整出参 JSON"):
                        raw_json = gr.TextArea(label="完整出参", lines=26)

        load_btn.click(fn=load_sample, outputs=payload_input)
        run_btn.click(
            fn=run_stream,
            inputs=[api_url, llm_mode, max_rules, payload_input],
            outputs=[summary_md, raw_json, violations_md],
        )

    return demo


if __name__ == "__main__":
    build_ui().launch(server_name="0.0.0.0", server_port=7861, show_error=True)
