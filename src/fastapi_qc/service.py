"""
内涵质控核心服务（仅核心能力）：
1) 严格按 2.26 需求沟通入参执行
2) 合并形式质控 + 内涵质控为统一 violations
3) 输出严格对齐目标出参
"""

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, Generator, List, Optional, Tuple

from .constants import DOC_HINTS, LEVEL_LABELS
from .heuristic_engine import HeuristicRuleEngine
from .schemas import QualityControlRequest, QualityControlResponse, ViolationOut
from .qa_config import get_qa_config


def _safe_json(text: str) -> Dict[str, Any]:
    raw = text.strip()
    if raw.startswith("```json"):
        raw = raw[7:]
    if raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()
    try:
        return json.loads(raw)
    except Exception:
        # 尝试从输出中提取第一个JSON对象
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            return json.loads(raw[start:end + 1])
        raise


class MedicalQualityControlService:
    def __init__(
        self,
        llm_client: Any = None,
        default_max_workers: int = 4,
        plugin_modules: Optional[List[str]] = None,
    ):
        self.llm_client = llm_client
        self.default_max_workers = default_max_workers
        self.heuristic_engine = HeuristicRuleEngine()
        self.plugin_modules = plugin_modules or []
        self.plugin_status = self.heuristic_engine.load_plugins(self.plugin_modules)
        self.qa_config = get_qa_config()

    def check(self, request: QualityControlRequest) -> QualityControlResponse:
        response, _ = self._check_internal(request)
        return response

    def check_with_debug(self, request: QualityControlRequest) -> Tuple[QualityControlResponse, Dict[str, Any]]:
        return self._check_internal(request)

    def check_stream(self, request: QualityControlRequest) -> Generator[Dict[str, Any], None, None]:
        """逐规则执行并 yield 进度事件，最后 yield complete 事件含完整结果。"""
        llm_rules = request.qc_rules.llmRules[: request.options.maxLlmRules]
        tables = request.get_emr_tables()
        mode = self._resolve_mode(request.options.llmMode)
        total = len(llm_rules)

        # 形式质控违规直接收集
        existing_violations = [
            self._normalize_existing_violation(item.model_dump())
            for item in request.qc_rules.violations
        ]

        yield {"event": "start", "total": total, "existing": len(existing_violations),
               "mode": mode, "visitId": request.visitList.visit_id}

        llm_violations: List[ViolationOut] = []
        max_workers = max(1, min(request.options.maxWorkers or self.default_max_workers, 16))

        if mode == "live" and total > 0:
            # 并发执行，每完成一条立即 yield
            futures: Dict[Any, Dict[str, Any]] = {}
            executor = ThreadPoolExecutor(max_workers=max_workers)
            try:
                for rule in llm_rules:
                    f = executor.submit(
                        self._evaluate_single_rule_live,
                        rule.model_dump(), tables,
                        request.options.llmRetry,
                        request.options.fallbackToHeuristic,
                        request.options.maxContextRecordsPerTable,
                        request.options.maxContextCharsPerField,
                        request.options.enableSuggestionRefine,
                    )
                    futures[f] = rule.model_dump()

                done_count = 0
                for future in as_completed(futures):
                    rule_data = futures[future]
                    done_count += 1
                    try:
                        verdict = future.result()
                    except Exception as exc:
                        verdict = {"violated": False, "_engine": "live_error", "_error": str(exc)}

                    violated = verdict.get("violated", False)
                    violation_out = None
                    if violated:
                        v = self._build_violation(rule_data, verdict)
                        llm_violations.append(v)
                        violation_out = v.model_dump()

                    yield {
                        "event": "rule_done",
                        "done": done_count,
                        "total": total,
                        "progress": int(done_count / total * 90),
                        "ruleKey": rule_data.get("ruleKey", ""),
                        "ruleName": rule_data.get("ruleName", ""),
                        "violated": violated,
                        "engine": verdict.get("_engine", "live"),
                        "violation": violation_out,
                    }
            finally:
                executor.shutdown(wait=False)
        else:
            # mock/heuristic 模式
            for i, rule in enumerate(llm_rules):
                verdict = self._evaluate_rule_heuristic(rule.model_dump(), tables)
                violated = verdict.get("violated", False)
                violation_out = None
                if violated:
                    v = self._build_violation(rule.model_dump(), verdict)
                    llm_violations.append(v)
                    violation_out = v.model_dump()
                yield {
                    "event": "rule_done",
                    "done": i + 1,
                    "total": total,
                    "progress": int((i + 1) / max(total, 1) * 90),
                    "ruleKey": rule.ruleKey,
                    "ruleName": rule.ruleName,
                    "violated": violated,
                    "engine": "heuristic",
                    "violation": violation_out,
                }

        all_violations = existing_violations + llm_violations
        total_deduct = round(sum(v.deductScore for v in all_violations), 2)
        qc_status = "TO_RECTIFY" if all_violations else "COMPLETED"
        quality_score = max(0.0, 100.0 - total_deduct)

        result = QualityControlResponse(
            visitId=request.visitList.visit_id,
            recordId=request.visitList.record_id,
            qcType=request.options.qcType,
            qcStatus=qc_status,
            totalDeductScore=total_deduct,
            qcGrade=self._score_to_grade(quality_score),
            defectCount=len(all_violations),
            violations=all_violations,
        )
        yield {"event": "complete", "progress": 100, "result": result.model_dump()}

    def _check_internal(self, request: QualityControlRequest) -> Tuple[QualityControlResponse, Dict[str, Any]]:
        start_ts = time.perf_counter()
        llm_stats_before = self._llm_debug_snapshot()
        existing_violations = [
            self._normalize_existing_violation(item.model_dump())
            for item in request.qc_rules.violations
        ]

        llm_violations, llm_debug = self._evaluate_llm_violations(request)
        all_violations = existing_violations + llm_violations

        total_deduct = round(sum(v.deductScore for v in all_violations), 2)
        qc_status = "TO_RECTIFY" if all_violations else "COMPLETED"
        quality_score = max(0.0, 100.0 - total_deduct)

        response = QualityControlResponse(
            visitId=request.visitList.visit_id,
            recordId=request.visitList.record_id,
            qcType=request.options.qcType,
            qcStatus=qc_status,
            totalDeductScore=total_deduct,
            qcGrade=self._score_to_grade(quality_score),
            defectCount=len(all_violations),
            violations=all_violations,
        )
        llm_stats_after = self._llm_debug_snapshot()
        debug = {
            "elapsedMs": round((time.perf_counter() - start_ts) * 1000.0, 2),
            "execution": llm_debug,
            "llmClientDelta": self._diff_llm_stats(llm_stats_before, llm_stats_after),
            "pluginStatus": self.plugin_status,
            "qaConfig": self.qa_config.to_dict(),
        }
        return response, debug

    def _evaluate_llm_violations(self, request: QualityControlRequest) -> Tuple[List[ViolationOut], Dict[str, Any]]:
        llm_rules = request.qc_rules.llmRules[: request.options.maxLlmRules]
        tables = request.get_emr_tables()
        mode = self._resolve_mode(request.options.llmMode)
        max_workers = max(1, min(request.options.maxWorkers or self.default_max_workers, 16))
        rule_debug: Dict[str, Any] = {
            "mode": mode,
            "llmRulesInput": len(request.qc_rules.llmRules),
            "llmRulesEvaluated": len(llm_rules),
            "maxWorkers": max_workers,
        }

        if mode == "live":
            verdicts, live_debug = self._evaluate_rules_live(
                rules=[rule.model_dump() for rule in llm_rules],
                tables=tables,
                retries=request.options.llmRetry,
                max_workers=max_workers,
                fallback=request.options.fallbackToHeuristic,
                max_records=request.options.maxContextRecordsPerTable,
                max_chars=request.options.maxContextCharsPerField,
                refine_suggestion=request.options.enableSuggestionRefine,
            )
            rule_debug.update(live_debug)
        else:
            verdicts = [
                self._evaluate_rule_heuristic(rule.model_dump(), tables)
                for rule in llm_rules
            ]
            rule_debug.update({
                "heuristicRules": len(llm_rules),
                "liveRules": 0,
                "notApplicableRules": 0,
                "heuristicFallbackRules": 0,
                "liveErrorRules": 0,
            })

        violations: List[ViolationOut] = []
        for rule, verdict in zip(llm_rules, verdicts):
            if not verdict.get("violated"):
                continue
            violations.append(self._build_violation(rule.model_dump(), verdict))
        rule_debug["llmViolationCount"] = len(violations)
        return violations, rule_debug

    def _evaluate_rules_live(
        self,
        rules: List[Dict[str, Any]],
        tables: Dict[str, List[Dict[str, Any]]],
        retries: int,
        max_workers: int,
        fallback: bool,
        max_records: int,
        max_chars: int,
        refine_suggestion: bool,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        verdicts: List[Optional[Dict[str, Any]]] = [None] * len(rules)
        errors: List[Tuple[int, Exception]] = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {
                executor.submit(
                    self._evaluate_single_rule_live,
                    rule,
                    tables,
                    retries,
                    fallback,
                    max_records,
                    max_chars,
                    refine_suggestion,
                ): idx
                for idx, rule in enumerate(rules)
            }
            for future in as_completed(future_map):
                idx = future_map[future]
                try:
                    verdicts[idx] = future.result()
                except Exception as exc:
                    errors.append((idx, exc))
                    verdicts[idx] = {"violated": False, "_engine": "live_error", "_error": str(exc)}

        if errors:
            # 记录错误但不中断整个请求，已在 verdicts 中标记为 live_error
            pass

        finalized = [item or {"violated": False} for item in verdicts]
        debug = self._summarize_live_verdicts(finalized)
        return finalized, debug

    def _evaluate_single_rule_live(
        self,
        rule: Dict[str, Any],
        tables: Dict[str, List[Dict[str, Any]]],
        retries: int,
        fallback: bool,
        max_records: int,
        max_chars: int,
        refine_suggestion: bool,
    ) -> Dict[str, Any]:
        context = self._build_rule_context(rule, tables, max_records, max_chars)

        # 如果规则需要的表没有传入，跳过规则
        if context.get("_not_applicable"):
            return {"violated": False, "_engine": "not_applicable", "_reason": context.get("reason", "")}

        last_error: Optional[Exception] = None
        for attempt in range(retries + 1):
            try:
                stage1_prompt = self._build_stage1_prompt(rule, context)
                raw = self.llm_client.call(stage1_prompt)
                parsed = _safe_json(raw)
                violated = bool(parsed.get("violated", False))
                result = {
                    "violated": violated,
                    "description": parsed.get("description", ""),
                    "itemInfo": parsed.get("itemInfo", ""),
                    "_engine": "live",
                }
                if violated and refine_suggestion:
                    suggestion = self._generate_suggestion(rule, context, result)
                    if suggestion:
                        result["suggestion"] = suggestion
                elif violated:
                    result["suggestion"] = parsed.get("suggestion", "")
                return result
            except Exception as exc:
                last_error = exc
                if attempt < retries:
                    time.sleep(min(2 ** attempt, 2))
                    continue

        if fallback:
            result = self._evaluate_rule_heuristic(rule, tables)
            result["_engine"] = "heuristic_fallback"
            return result
        raise RuntimeError(f"rule={rule.get('ruleKey')} LLM执行失败: {last_error}") from last_error

    def _evaluate_rule_heuristic(self, rule: Dict[str, Any], tables: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        hint_context = self._get_rule_hint_context(rule, tables)
        return self.heuristic_engine.evaluate(rule.get("ruleKey", ""), tables, hint_context)

    def _build_stage1_prompt(self, rule: Dict[str, Any], context: Dict[str, Any]) -> str:
        rule_json = json.dumps(rule, ensure_ascii=False)
        context_json = json.dumps(context, ensure_ascii=False)
        output_schema = rule.get("expectedOutputSchema") or {
            "violated": "bool",
            "description": "string（说明违规的具体内容，引用病历原文）",
            "itemInfo": "string（命中的具体位置或记录条目）",
            "suggestion": "string（针对本患者的具体整改建议，20-100字）",
        }
        custom_template = (rule.get("promptTemplate") or "").strip()
        if custom_template:
            try:
                return custom_template.format(
                    rule_json=rule_json,
                    context_json=context_json,
                    output_schema_json=json.dumps(output_schema, ensure_ascii=False),
                )
            except Exception:
                pass

        # 符合 Qwen3.5-35B 最佳实践：简洁明确的 Prompt，末尾明确输出格式
        return (
            "你是医疗质控专家，判断病历是否违反质控规则。\n\n"
            "【质控规则】\n"
            f"{rule_json}\n\n"
            "【病历上下文】\n"
            f"{context_json}\n\n"
            "【判断要求】\n"
            "1. 判断是否违反规则：violated=true（存在缺陷）或 violated=false（无缺陷）\n"
            "2. description：引用病历原文说明违规点\n"
            "3. itemInfo：说明具体位置（如：第1条记录、首次病程记录）\n"
            "4. suggestion：针对本患者给出具体整改建议（20-100字）\n\n"
            "请仅输出 JSON 格式，不输出其他文字：\n"
            f"{json.dumps(output_schema, ensure_ascii=False)}\n"
        )

    def _generate_suggestion(
        self,
        rule: Dict[str, Any],
        context: Dict[str, Any],
        verdict: Dict[str, Any],
    ) -> str:
        prompt = (
            "你是医疗病历整改专家。请生成一条针对当前患者的整改建议。\n"
            "要求：20-120字，必须可执行，避免空泛套话。\n"
            f"规则: {json.dumps(rule, ensure_ascii=False)}\n"
            f"判定: {json.dumps(verdict, ensure_ascii=False)}\n"
            f"病历上下文: {json.dumps(context, ensure_ascii=False)}\n"
            "只输出建议正文。"
        )
        try:
            return self.llm_client.call(prompt).strip()
        except Exception:
            return ""

    def _build_rule_context(
        self,
        rule: Dict[str, Any],
        tables: Dict[str, List[Dict[str, Any]]],
        max_records: int,
        max_chars: int,
    ) -> Dict[str, Any]:
        source_keys = list(rule.get("sourceDocKeys", []))
        if not source_keys:
            _, inferred_table, _, _ = self._infer_doc_hint(rule.get("ruleKey", ""))
            source_keys = [inferred_table]

        # 检查规则需要的表是否存在（是否传入）
        # 如果表不存在（key不在tables中），说明没有传入，标记为not_applicable
        table_exists = any(table_key in tables for table_key in source_keys)
        if not table_exists:
            return {"_not_applicable": True, "sourceDocKeys": source_keys, "reason": "required_tables_not_provided"}

        context_tables: Dict[str, List[Dict[str, Any]]] = {}
        for table_key in source_keys:
            records = tables.get(table_key, [])
            context_tables[table_key] = self._compress_records(records, max_records=max_records, max_chars=max_chars)

        return {
            "sourceDocKeys": source_keys,
            "records": context_tables,
        }

    def _compress_records(
        self,
        records: List[Dict[str, Any]],
        max_records: int,
        max_chars: int,
    ) -> List[Dict[str, Any]]:
        clipped = records[:max_records]
        result: List[Dict[str, Any]] = []
        for row in clipped:
            new_row = {}
            for key, value in row.items():
                if isinstance(value, str) and len(value) > max_chars:
                    new_row[key] = value[:max_chars] + "...(truncated)"
                else:
                    new_row[key] = value
            result.append(new_row)
        return result

    def _build_violation(self, rule_data: Dict[str, Any], verdict: Dict[str, Any]) -> ViolationOut:
        doc_name, array_key, col_name, secondary_path = self._infer_doc_hint(rule_data.get("ruleKey", ""))
        level = rule_data.get("ruleLevel", "normal")
        item_info = verdict.get("itemInfo") or "命中内涵质控规则"
        description = verdict.get("description") or rule_data.get("ruleDesc") or rule_data.get("ruleName", "")
        suggestion = verdict.get("suggestion") or self._build_general_suggestion(
            rule_name=rule_data.get("ruleName", ""),
            secondary_path=secondary_path,
            description=description,
        )

        deduct_score = float(rule_data.get("deductScore", 1.0))
        if deduct_score <= 0:
            deduct_score = 1.0

        return ViolationOut(
            deductScore=deduct_score,
            docName=verdict.get("docName") or doc_name,
            colName=verdict.get("colName") or col_name,
            levelLabel=LEVEL_LABELS.get(level, "一般"),
            secondaryPath=verdict.get("secondaryPath") or secondary_path,
            level=level,
            ruleName=rule_data.get("ruleName", ""),
            description=description,
            arrayKey=verdict.get("arrayKey") or array_key,
            arrayIndex=int(verdict.get("arrayIndex", 0)),
            itemInfo=item_info,
            ruleKey=rule_data.get("ruleKey", ""),
            suggestion=suggestion,
        )

    def _normalize_existing_violation(self, item: Dict[str, Any]) -> ViolationOut:
        col_name = item.get("colName", "")
        if col_name == "diagnosis_other":
            col_name = "diagnosis_code"
        doc_name = item.get("docName", "")
        if doc_name == "住院病案首页":
            doc_name = "病案首页"

        # 形式质控 suggestion：优先使用原有值，否则用通用模板
        suggestion = item.get("suggestion") or self._build_general_suggestion(
            rule_name=item.get("ruleName", ""),
            secondary_path=item.get("secondaryPath", ""),
            description=item.get("description", ""),
        )

        return ViolationOut(
            deductScore=float(item.get("deductScore", 0.0)),
            docName=doc_name,
            colName=col_name,
            levelLabel=item.get("levelLabel", LEVEL_LABELS.get(item.get("level", "normal"), "一般")),
            secondaryPath=item.get("secondaryPath", ""),
            level=item.get("level", "normal"),
            ruleName=item.get("ruleName", ""),
            description=item.get("description", ""),
            arrayKey=item.get("arrayKey", ""),
            arrayIndex=int(item.get("arrayIndex", 0)),
            itemInfo=item.get("itemInfo", ""),
            ruleKey=item.get("ruleKey", ""),
            suggestion=suggestion,
        )

    def _resolve_mode(self, mode: str) -> str:
        picked = (mode or "auto").lower().strip()
        if picked not in ("auto", "live", "mock"):
            picked = "auto"
        if picked == "auto":
            picked = "live" if self.llm_client else "mock"
        if picked == "live" and not self.llm_client:
            raise RuntimeError("live模式不可用：模型客户端未初始化，请检查 .env / 配置 / 依赖")
        return picked

    def _get_rule_hint_context(self, rule: Dict[str, Any], tables: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        homepage = tables.get("emr_qc_inpatient_homepage", [])
        department = ""
        if homepage:
            department = homepage[0].get("admit_dept", "") or homepage[0].get("discharge_dept", "")
        rule_key = rule.get("ruleKey", "")
        parts = rule_key.split("_")
        doc_type = parts[1] if len(parts) >= 3 else ""
        return {"department": department, "doc_type": doc_type}

    def _infer_doc_hint(self, rule_key: str) -> Tuple[str, str, str, str]:
        parts = rule_key.split("_")
        if len(parts) >= 3 and parts[1] in DOC_HINTS:
            return DOC_HINTS[parts[1]]
        return ("病历文书", "emr_qc_admission_record", "content", "病历内容")

    def _score_to_grade(self, score: float) -> str:
        if score >= 90:
            return "甲"
        if score >= 75:
            return "乙"
        if score >= 60:
            return "丙"
        return "丁"

    def _build_general_suggestion(self, rule_name: str, secondary_path: str, description: str) -> str:
        path_hint = secondary_path or "相关文书字段"
        core = rule_name or description or "该质控项"
        return f"建议完善{path_hint}记录并补齐关键要素，重点整改：{core}。"

    def _summarize_live_verdicts(self, verdicts: List[Dict[str, Any]]) -> Dict[str, Any]:
        summary = {
            "liveRules": 0,
            "heuristicRules": 0,
            "notApplicableRules": 0,
            "heuristicFallbackRules": 0,
            "liveErrorRules": 0,
        }
        for verdict in verdicts:
            engine = (verdict.get("_engine") or "").strip()
            if engine == "live":
                summary["liveRules"] += 1
            elif engine == "not_applicable":
                summary["notApplicableRules"] += 1
            elif engine == "heuristic_fallback":
                summary["heuristicFallbackRules"] += 1
            elif engine == "live_error":
                summary["liveErrorRules"] += 1
            else:
                summary["heuristicRules"] += 1
        return summary

    def _llm_debug_snapshot(self) -> Dict[str, Any]:
        if not self.llm_client:
            return {}
        snapshot = getattr(self.llm_client, "debug_snapshot", None)
        if callable(snapshot):
            try:
                data = snapshot()
                if isinstance(data, dict):
                    return data
            except Exception:
                return {}
        return {}

    def _diff_llm_stats(self, before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
        if not after:
            return {"enabled": False}
        delta = {
            "enabled": True,
            "client": after.get("client", ""),
            "transport": after.get("transport", ""),
            "call_total_delta": int(after.get("call_total", 0)) - int(before.get("call_total", 0)),
            "call_success_delta": int(after.get("call_success", 0)) - int(before.get("call_success", 0)),
            "call_error_delta": int(after.get("call_error", 0)) - int(before.get("call_error", 0)),
            "latency_ms_total_delta": round(
                float(after.get("latency_ms_total", 0.0)) - float(before.get("latency_ms_total", 0.0)), 2
            ),
            "last_error": after.get("last_error", ""),
        }
        return delta


def create_service_from_env() -> MedicalQualityControlService:
    """从环境变量创建服务实例"""
    llm_client: Optional[Any] = None

    # 从环境变量读取配置
    client_type = os.getenv("LLM_CLIENT_TYPE", "modelscope")
    max_workers = int(os.getenv("MAX_WORKERS", "2"))
    plugin_modules_str = os.getenv("PLUGIN_MODULES", "fastapi_qc.plugins.cardiology_plugin")
    plugin_modules = [m.strip() for m in plugin_modules_str.split(",") if m.strip()]

    try:
        if client_type == "modelscope":
            from llm_client import ModelScopeClient
            llm_client = ModelScopeClient(
                api_key=os.getenv("MODELSCOPE_API_KEY", ""),
                model=os.getenv("MODELSCOPE_MODEL", "Qwen/Qwen3.5-35B-A3B"),
                base_url=os.getenv("MODELSCOPE_BASE_URL", "https://api-inference.modelscope.cn/v1"),
                temperature=float(os.getenv("MODELSCOPE_TEMPERATURE", "0.1")),
                max_tokens=int(os.getenv("MODELSCOPE_MAX_TOKENS", "32768")),
                timeout=int(os.getenv("MODELSCOPE_TIMEOUT", "90")),
                top_p=float(os.getenv("MODELSCOPE_TOP_P", "0.8")),
            )
        elif client_type == "openai":
            from llm_client import OpenAIClient
            llm_client = OpenAIClient(
                api_key=os.getenv("OPENAI_API_KEY", ""),
                model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
                base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.1")),
                max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "2000")),
            )
        elif client_type == "local":
            from llm_client import LocalModelClient
            llm_client = LocalModelClient(
                base_url=os.getenv("LOCAL_BASE_URL", "http://localhost:8000"),
                model=os.getenv("LOCAL_MODEL", "qwen-30b"),
                temperature=float(os.getenv("LOCAL_TEMPERATURE", "0.1")),
                max_tokens=int(os.getenv("LOCAL_MAX_TOKENS", "2000")),
            )
    except Exception as exc:
        print(f"Warning: Failed to create LLM client: {exc}")
        llm_client = None

    return MedicalQualityControlService(
        llm_client=llm_client,
        default_max_workers=max_workers,
        plugin_modules=plugin_modules,
    )
