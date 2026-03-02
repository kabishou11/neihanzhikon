"""
FastAPI 质控常量定义
"""

from typing import Dict, Tuple


LEVEL_LABELS: Dict[str, str] = {
    "minor": "轻微",
    "normal": "一般",
    "major": "严重",
    "critical": "致命",
    "serious": "严重",
}


DOC_HINTS: Dict[str, Tuple[str, str, str, str]] = {
    "RYJL":     ("入院记录",       "emr_qc_admission_record",          "history_present_illness", "入院记录"),
    "SCBCJL":   ("首次病程记录",   "emr_qc_course_record",             "diagnosis_discussion",    "首次病程"),
    "RCBCJL":   ("日常病程记录",   "emr_qc_course_record",             "content",                 "日常病程"),
    "MZJLCZ":   ("门诊初诊记录",   "emr_qc_outpatient_record",         "content",                 "门诊初诊"),
    "MZJLFZ":   ("门诊复诊记录",   "emr_qc_outpatient_record",         "content",                 "门诊复诊"),
    "SYJL":     ("手术记录",       "emr_qc_surgery_record",            "content",                 "手术记录"),
    "MAZJL":    ("麻醉记录",       "emr_qc_anesthesia_record",         "content",                 "麻醉记录"),
    "HZJL":     ("会诊记录",       "emr_qc_consultation_record",       "opinion",                 "会诊记录"),
    "SSJL":     ("手术记录",       "emr_qc_surgery_record",            "content",                 "手术记录"),
    "SAQC":     ("手术安全核查",   "emr_qc_surgery_safety",            "content",                 "手术安全"),
    "BLJL":     ("病理记录",       "emr_qc_pathology_detail",          "content",                 "病理记录"),
    "SWJL":     ("死亡记录",       "emr_qc_death_record",              "content",                 "死亡记录"),
    "SWDTJL":   ("死亡讨论",       "emr_qc_death_discussion_detail",   "content",                 "死亡讨论"),
    "NJJL":     ("护理记录",       "emr_qc_nursing_record",            "content",                 "护理记录"),
    "JJJL":     ("急诊记录",       "emr_qc_emergency_record",          "content",                 "急诊记录"),
}
