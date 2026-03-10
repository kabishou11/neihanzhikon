# 医疗内涵质控系统 FastAPI

基于 30B 大模型的医疗病历内涵质控系统，支持形式质控与 LLM 规则质控合并输出，提供 FastAPI 接口、Gradio 界面与流式实时验证。

## 核心特性

- **严格对齐需求**：入参/出参完全遵循 2.26 需求沟通定义
- **真流式执行**：逐规则实时推送进度，支持 30B 模型长时间执行
- **并发优化**：多线程并发执行 LLM 规则，提升吞吐量
- **智能回退**：LLM 失败时可选启发式规则兜底
- **插件扩展**：支持按科室/文书类型动态加载规则插件
- **双界面支持**：
  - **FastAPI**：RESTful API 接口，支持流式/非流式
  - **Gradio**：可视化界面，质控测试 + 医疗问答助手
- **质量保障**：集成 quality_assurance.yaml 配置，支持置信度、重试、超时等参数

## 快速开始

### 1. 安装依赖

```bash
# Windows
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`：

```bash
cp .env.example .env
```

编辑 `.env`，填入必要配置：

```bash
# LLM 客户端类型
LLM_CLIENT_TYPE=modelscope

# ModelScope API Key（必填）
MODELSCOPE_API_KEY=ms-your-api-key-here

# 可选：覆盖默认值
MODELSCOPE_MODEL=Qwen/Qwen3.5-35B-A3B
MODELSCOPE_MAX_TOKENS=32768
MODELSCOPE_TIMEOUT=90

# 并发线程数
MAX_WORKERS=2
```

**支持的 LLM 后端：**
- `modelscope` - ModelScope API（推荐）
- `openai` - OpenAI API
- `local` - 本地模型（vLLM）

### 3. 启动服务

**方式一：FastAPI 后端服务**
```bash
# 启动 FastAPI 服务
uvicorn fastapi_app:app --host 0.0.0.0 --port 8000

# 访问接口文档
# http://localhost:8000/docs
```

**方式二：Gradio 可视化界面（推荐）**
```bash
# 启动 Gradio 验证台
python web_fastapi_verify.py

# 访问界面
# http://localhost:7861
```

**Gradio 界面功能：**
- ✅ **质控测试**：支持流式/非流式切换，实时对比输出
- ✅ **医疗问答助手**：流式对话，支持医疗知识和质控规则咨询
- ✅ **参数调节**：Temperature、Max Tokens 等
- ✅ **快速测试**：内置示例问题和测试数据

## 接口说明

### POST /api/v1/qc/check

执行质控（同步接口）

**请求体：**
```json
{
  "visitList": {
    "visit_id": "P2026TEST002",
    "record_id": "06b0442c0ffe11f1af39902e16e9744b"
  },
  "qc_rules": {
    "totalDeductScore": 11.0,
    "llmRules": [...],
    "violations": [...]
  },
  "options": {
    "llmMode": "live",
    "maxLlmRules": 20
  },
  "emr_qc_admission_record": [...],
  "emr_qc_course_record": [...]
}
```

**响应体：**
```json
{
  "visitId": "P2026TEST002",
  "recordId": "06b0442c0ffe11f1af39902e16e9744b",
  "qcType": "TERMINAL",
  "qcStatus": "TO_RECTIFY",
  "totalDeductScore": 19.0,
  "qcGrade": "乙",
  "defectCount": 10,
  "violations": [...]
}
```

### POST /api/v1/qc/check/stream

流式执行质控（推荐）

返回 JSON Lines 格式，每完成一条规则立即推送：

```json
{"event":"start","total":20,"existing":3,"mode":"live","visitId":"P2026TEST002"}
{"event":"rule_done","done":1,"total":20,"progress":4,"ruleKey":"LLM_RYJL_609","violated":true,"engine":"live","violation":{...}}
{"event":"rule_done","done":2,"total":20,"progress":9,"ruleKey":"LLM_RYJL_611","violated":false,"engine":"live"}
...
{"event":"complete","progress":100,"result":{...}}
```

### POST /api/v1/qc/check/debug

执行质控（含调试信息）

返回标准结果 + 调试统计（LLM 调用次数、耗时、执行路径等）

## 配置参数

### RuntimeOptions

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `llmMode` | string | `"auto"` | `live`（真实调用模型）/ `mock`（启发式规则）/ `auto`（自动选择） |
| `maxLlmRules` | int | `200` | 最大执行 LLM 规则数（建议验证时设为 5-20，生产时设为全量） |
| `maxWorkers` | int | 从 `.env` 读取 | 并发线程数（30B 模型建议 2-3） |
| `llmRetry` | int | `0` | LLM 失败重试次数（30B 模型建议 0，避免超时叠加） |
| `fallbackToHeuristic` | bool | `false` | LLM 失败时是否回退启发式规则 |
| `maxContextRecordsPerTable` | int | `6` | 每个病历表最多传入 LLM 的记录数 |
| `maxContextCharsPerField` | int | `800` | 单字段文本最大长度（超出截断） |
| `enableSuggestionRefine` | bool | `true` | 是否二阶段生成整改建议（仅对违规项） |

## 项目结构

```
neihanzhikon/
├── fastapi_app.py              # FastAPI 主应用
├── web_fastapi_verify.py       # Gradio 流式验证台
├── requirements.txt            # Python 依赖
├── .env.example                # 环境变量模板
├── .env                        # 环境变量配置（不入库）
├── config/
│   └── quality_assurance.yaml # 质量保障配置（默认值）
├── src/
│   ├── llm_client.py          # LLM 客户端（ModelScope/OpenAI/Local）
│   └── fastapi_qc/
│       ├── service.py         # 质控核心服务
│       ├── schemas.py         # 请求/响应模型
│       ├── constants.py       # 常量定义
│       ├── heuristic_engine.py # 启发式规则引擎
│       └── plugins/           # 规则插件（按科室/文书扩展）
└── venv/                      # Python 虚拟环境
```

## 技术栈

- **FastAPI** - 高性能异步 Web 框架
- **Gradio** - 快速构建 ML 应用界面
- **Pydantic** - 数据验证与序列化
- **ThreadPoolExecutor** - 并发执行 LLM 规则
- **ModelScope API** - 30B 大模型推理

## 开发说明

### 添加新规则

1. **启发式规则**（不调用 LLM）：

```python
# src/fastapi_qc/heuristic_engine.py
def _check_custom_rule(self, tables):
    records = tables.get("emr_qc_admission_record", [])
    if not records:
        return {"violated": False}
    # 自定义逻辑
    return {"violated": True, "description": "...", "itemInfo": "..."}

# 注册
self.register_handler("LLM_CUSTOM_001", self._check_custom_rule)
```

2. **科室专属规则插件**：

```python
# src/fastapi_qc/plugins/cardiology_plugin.py
def register(engine):
    def check_cardiology_628(tables):
        # 心内科专属逻辑
        return {"violated": True, ...}

    engine.register_handler(
        "LLM_RYJL_628",
        check_cardiology_628,
        plugin="cardiology",
        departments=["心内科"],
    )
```

### 自定义 Prompt 模板

在入参 `llmRules` 中指定 `promptTemplate`：

```json
{
  "ruleKey": "LLM_CUSTOM_001",
  "promptTemplate": "你是医疗质控专家。规则：{rule_json}\n病历：{context_json}\n输出：{output_schema_json}"
}
```

## 常见问题

**Q: 执行超时怎么办？**

A: 降低 `maxLlmRules`（建议 5-20），或增加 `config.yaml` 中的 `timeout`（默认 90 秒）。

**Q: 如何确认真实调用了模型？**

A: 使用 `/api/v1/qc/check/debug` 接口，查看返回的 `debug.llmClientDelta.call_total_delta` 是否 > 0。

**Q: 流式接口卡住不动？**

A: 检查 FastAPI 服务是否启动，或尝试降低 `maxLlmRules` 到 5 条快速验证。

**Q: 如何切换到本地模型？**

A: 修改 `config.yaml` 中 `client_type` 为 `local`，并配置 vLLM 服务地址。

## License

MIT

## 作者

kabishou11 (woicyou@gmail.com)
