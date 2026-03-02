"""
启发式规则引擎（支持插件）：
- 内置规则
- 外部插件 register(engine) 动态扩展
"""

import importlib
import json
from typing import Any, Callable, Dict, List, Optional


RuleHandler = Callable[[Dict[str, List[Dict[str, Any]]]], Dict[str, Any]]


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


class HeuristicRuleEngine:
    def __init__(self):
        self._handlers: Dict[str, List[Dict[str, Any]]] = {}
        self._register_builtin_handlers()

    def register_handler(
        self,
        rule_key: str,
        handler: RuleHandler,
        plugin: str = "builtin",
        departments: Optional[List[str]] = None,
        doc_types: Optional[List[str]] = None,
    ) -> None:
        self._handlers.setdefault(rule_key, []).append(
            {
                "handler": handler,
                "plugin": plugin,
                "departments": [item.strip() for item in (departments or []) if item.strip()],
                "doc_types": [item.strip() for item in (doc_types or []) if item.strip()],
            }
        )

    def load_plugins(self, modules: List[str]) -> Dict[str, Any]:
        result = {"loaded": [], "failed": []}
        for module_name in modules:
            try:
                module = importlib.import_module(module_name)
                if not hasattr(module, "register"):
                    result["failed"].append({"module": module_name, "error": "missing register(engine)"})
                    continue
                module.register(self)
                result["loaded"].append(module_name)
            except Exception as exc:
                result["failed"].append({"module": module_name, "error": str(exc)})
        return result

    def evaluate(
        self,
        rule_key: str,
        tables: Dict[str, List[Dict[str, Any]]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        candidates = self._handlers.get(rule_key, [])
        if not candidates:
            return {"violated": False}
        ctx = context or {}
        for item in candidates:
            if not self._handler_match(item, ctx):
                continue
            result = item["handler"](tables)
            result["_plugin"] = item["plugin"]
            return result
        return {"violated": False}

    def _handler_match(self, handler_meta: Dict[str, Any], context: Dict[str, Any]) -> bool:
        departments = handler_meta.get("departments", [])
        doc_types = handler_meta.get("doc_types", [])
        if not departments and not doc_types:
            return True
        dept = (context.get("department") or "").strip()
        doc_type = (context.get("doc_type") or "").strip()
        if departments and dept not in departments:
            return False
        if doc_types and doc_type not in doc_types:
            return False
        return True

    def _register_builtin_handlers(self) -> None:
        self.register_handler("LLM_RYJL_609", self._check_609)
        self.register_handler("LLM_RYJL_611", self._check_611)
        self.register_handler("LLM_SCBCJL_625", self._check_625)
        self.register_handler("LLM_RYJL_631", self._check_631)
        self.register_handler("LLM_RYJL_614", self._check_614)
        self.register_handler("LLM_RYJL_608", self._check_608)
        self.register_handler("LLM_SCBCJL_621", self._check_621)
        self.register_handler("LLM_RYJL_628", self._check_628)

    def _check_609(self, tables: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        records = tables.get("emr_qc_admission_record", [])
        text = _safe_text(records[0].get("history_present_illness", "")) if records else ""
        needed = ["食欲", "大小便", "精神", "体力", "睡眠"]
        missing = [item for item in needed if item not in text]
        if len(missing) >= 3:
            return {
                "violated": True,
                "description": "检查病史中是否描述了患者的一般情况，包括食欲、大小便、精神、体力、睡眠等",
                "itemInfo": "现病史缺少一般情况描述",
                "docName": "入院记录",
                "colName": "history_present_illness",
                "secondaryPath": "现病史",
                "arrayKey": "emr_qc_admission_record",
                "arrayIndex": 0,
            }
        return {"violated": False}

    def _check_611(self, tables: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        records = tables.get("emr_qc_admission_record", [])
        text = _safe_text(records[0].get("history_past", "")) if records else ""
        needed = ["传染病史", "预防接种", "手术史", "外伤史", "输血史"]
        missing = [item for item in needed if item not in text]
        if len(missing) >= 2:
            return {
                "violated": True,
                "description": "检查既往史是否包含患者过去的健康和疾病情况",
                "itemInfo": "既往史缺少传染病史、手术史、外伤史、输血史等",
                "docName": "入院记录",
                "colName": "history_past",
                "secondaryPath": "既往史",
                "arrayKey": "emr_qc_admission_record",
                "arrayIndex": 0,
            }
        return {"violated": False}

    def _check_625(self, tables: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        plan = ""
        for record in tables.get("emr_qc_course_record", []):
            if "首次病程" in _safe_text(record.get("record_type", "")):
                plan = _safe_text(record.get("treatment_plan", ""))
                break
        if plan and all(word not in plan for word in ("注意", "风险", "防范", "监测")):
            return {
                "violated": True,
                "description": "检查诊疗计划中是否记录了注意事项和防范措施",
                "itemInfo": "诊疗计划缺少注意事项和防范措施",
                "docName": "首次病程记录",
                "colName": "treatment_plan",
                "secondaryPath": "诊疗计划",
                "arrayKey": "emr_qc_course_record",
                "arrayIndex": 0,
            }
        return {"violated": False}

    def _check_631(self, tables: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        comm = tables.get("emr_qc_communication_record", [])
        difficult = tables.get("emr_qc_difficult_case_discussion", [])
        has_critical_notice = any("病危" in _safe_text(item.get("record_type", "")) for item in comm)
        if has_critical_notice and not difficult:
            return {
                "violated": True,
                "description": "检查疑难病例是否有讨论记录",
                "itemInfo": "患者病情危重（有病危通知），但缺失疑难病例讨论记录",
                "docName": "疑难病例讨论记录",
                "colName": "discussion_content",
                "secondaryPath": "病例讨论",
                "arrayKey": "emr_qc_difficult_case_discussion",
                "arrayIndex": 0,
            }
        return {"violated": False}

    def _check_614(self, tables: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        records = tables.get("emr_qc_admission_record", [])
        text = _safe_text(records[0].get("specialty_exam", "")) if records else ""
        if text and ("冠脉" not in text and "扩张型" not in text):
            return {
                "violated": True,
                "description": "检查体格检查中鉴别诊断体征的记录完整性",
                "itemInfo": "缺少冠心病、扩张型心肌病鉴别诊断的特异性体征描述",
                "docName": "入院记录",
                "colName": "specialty_exam",
                "secondaryPath": "专科检查",
                "arrayKey": "emr_qc_admission_record",
                "arrayIndex": 0,
            }
        return {"violated": False}

    def _check_608(self, tables: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        records = tables.get("emr_qc_admission_record", [])
        text = _safe_text(records[0].get("auxiliary_exam", "")) if records else ""
        if text and ("冠脉造影" not in text and "EF" not in text and "射血分数" not in text):
            return {
                "violated": True,
                "description": "检查是否缺少对鉴别诊断有重要意义的阳性或阴性资料",
                "itemInfo": "缺少冠脉造影、心脏超声详细数据等鉴别诊断依据",
                "docName": "入院记录",
                "colName": "auxiliary_exam",
                "secondaryPath": "辅助检查",
                "arrayKey": "emr_qc_admission_record",
                "arrayIndex": 0,
            }
        return {"violated": False}

    def _check_621(self, tables: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        text = ""
        for record in tables.get("emr_qc_course_record", []):
            if "首次病程" in _safe_text(record.get("record_type", "")):
                text = _safe_text(record.get("diagnosis_discussion", ""))
                break
        if text and (len(text) < 40 or "并发症" not in text):
            return {
                "violated": True,
                "description": "检查首次病程记录中是否全面分析讨论了诊断和并发症",
                "itemInfo": "诊断讨论内容过于简单，未全面分析并发症",
                "docName": "首次病程记录",
                "colName": "diagnosis_discussion",
                "secondaryPath": "诊断讨论",
                "arrayKey": "emr_qc_course_record",
                "arrayIndex": 0,
            }
        return {"violated": False}

    def _check_628(self, tables: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        daily_records = [
            item for item in tables.get("emr_qc_course_record", [])
            if "日常" in _safe_text(item.get("record_type", ""))
        ]
        if not daily_records:
            return {"violated": False}
        text = _safe_text(daily_records[0].get("content", ""))
        if text and all(word not in text for word in ("分析", "评估", "判断", "趋势")):
            return {
                "violated": True,
                "description": "检查日常查房记录中病情演变的分析",
                "itemInfo": "日常病程记录缺少病情演变的深入分析",
                "docName": "日常病程记录",
                "colName": "content",
                "secondaryPath": "病程记录",
                "arrayKey": "emr_qc_course_record",
                "arrayIndex": 1,
            }
        return {"violated": False}
