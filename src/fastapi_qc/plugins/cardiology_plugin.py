"""
示例插件：心内科规则增强
"""

import json
from typing import Any, Dict, List


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def register(engine) -> None:
    engine.register_handler(
        rule_key="LLM_RYJL_628",
        handler=_check_628_cardiology,
        plugin="cardiology_plugin",
        departments=["心内科"],
    )


def _check_628_cardiology(tables: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    daily_records = [
        item for item in tables.get("emr_qc_course_record", [])
        if "日常" in _safe_text(item.get("record_type", ""))
    ]
    if not daily_records:
        return {"violated": False}
    text = _safe_text(daily_records[0].get("content", ""))
    keywords = ["分析", "评估", "判断", "趋势", "心功能", "容量管理", "肾功能"]
    if text and not any(word in text for word in keywords):
        return {
            "violated": True,
            "description": "心内科病程记录应包含病情演变分析及心肾相关评估",
            "itemInfo": "日常病程记录缺少心功能/肾功能联合分析",
            "docName": "日常病程记录",
            "colName": "content",
            "secondaryPath": "病程记录",
            "arrayKey": "emr_qc_course_record",
            "arrayIndex": 1,
        }
    return {"violated": False}
