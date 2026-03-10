"""
FastAPI 请求/响应模型
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PatientRef(BaseModel):
    record_id: str = Field(..., description="质控记录唯一ID")
    visit_id: str = Field(..., description="患者唯一ID")


class LLMRule(BaseModel):
    ruleId: str = Field(..., description="规则ID")
    ruleKey: str = Field(..., description="规则编码")
    ruleName: str = Field(..., description="规则名称")
    ruleDesc: str = Field("", description="规则描述")
    ruleCategory: str = Field("", description="规则类别")
    ruleLevel: str = Field("normal", description="规则等级")
    deductScore: float = Field(1.0, description="违规扣分")
    execType: str = Field("LLM", description="执行类型")
    # 预留：规则扩展字段（后续规则平台可直接透传）
    version: str = Field("v1", description="规则版本")
    promptTemplate: str = Field("", description="自定义Prompt模板（可选）")
    expectedOutputSchema: Dict[str, Any] = Field(default_factory=dict, description="期望输出JSON结构")
    sourceDocKeys: List[str] = Field(default_factory=list, description="指定检索的病历表key")
    checkItems: List[str] = Field(default_factory=list, description="规则检查项")
    customParams: Dict[str, Any] = Field(default_factory=dict, description="规则自定义参数")

    class Config:
        extra = "allow"


class ExistingViolation(BaseModel):
    deductScore: float = Field(..., description="扣分")
    colName: str = Field("", description="字段名")
    level: str = Field("normal", description="等级")
    description: str = Field("", description="描述")
    arrayKey: str = Field("", description="来源数组key")
    itemInfo: str = Field("", description="命中项信息")
    ruleKey: str = Field(..., description="规则编码")
    docName: str = Field("", description="文书名称")
    levelLabel: str = Field("", description="等级标签")
    secondaryPath: str = Field("", description="二级路径")
    ruleName: str = Field("", description="规则名称")
    arrayIndex: int = Field(0, description="数组索引")
    execType: str = Field("ENGINE", description="执行类型")
    suggestion: Optional[str] = Field(None, description="整改建议")

    class Config:
        extra = "allow"


class QCRules(BaseModel):
    totalDeductScore: float = Field(0.0, description="形式质控总扣分")
    llmRules: List[LLMRule] = Field(default_factory=list, description="待执行LLM规则列表")
    violations: List[ExistingViolation] = Field(default_factory=list, description="形式质控已命中违规")

    class Config:
        extra = "allow"


class RuntimeOptions(BaseModel):
    qcType: str = Field("TERMINAL", description="质控类型")
    llmMode: str = Field("auto", description="auto/live/mock")
    maxLlmRules: int = Field(200, ge=1, le=5000, description="最大执行LLM规则数")
    strictMode: bool = Field(True, description="严格模式：遇到关键字段缺失直接返回400")
    llmRetry: int = Field(0, ge=0, le=5, description="live模式下LLM失败重试次数（30B模型建议0）")
    maxWorkers: int = Field(4, ge=1, le=16, description="live模式并发规则执行线程数")
    fallbackToHeuristic: bool = Field(False, description="live失败时回退启发式规则")
    maxContextRecordsPerTable: int = Field(6, ge=1, le=100, description="每个表最多传入LLM的记录数")
    maxContextCharsPerField: int = Field(800, ge=100, le=5000, description="单字段文本最大长度")
    enableSuggestionRefine: bool = Field(True, description="二阶段建议生成：仅对命中规则调用")


class QualityControlRequest(BaseModel):
    visitList: PatientRef
    qc_rules: QCRules
    options: RuntimeOptions = Field(default_factory=RuntimeOptions)

    # 常见病历表（可继续扩展，extra=allow 仍支持其他 emr_qc_* 字段）
    emr_qc_admission_record: List[Dict[str, Any]] = Field(default_factory=list)
    emr_qc_anesthesia_record: List[Dict[str, Any]] = Field(default_factory=list)
    emr_qc_blood_transfusion: List[Dict[str, Any]] = Field(default_factory=list)
    emr_qc_communication_record: List[Dict[str, Any]] = Field(default_factory=list)
    emr_qc_consent_form: List[Dict[str, Any]] = Field(default_factory=list)
    emr_qc_consultation_record: List[Dict[str, Any]] = Field(default_factory=list)
    emr_qc_course_record: List[Dict[str, Any]] = Field(default_factory=list)
    emr_qc_death_discussion_detail: List[Dict[str, Any]] = Field(default_factory=list)
    emr_qc_death_record: List[Dict[str, Any]] = Field(default_factory=list)
    emr_qc_difficult_case_discussion: List[Dict[str, Any]] = Field(default_factory=list)
    emr_qc_discharge_record: List[Dict[str, Any]] = Field(default_factory=list)
    emr_qc_emergency_record: List[Dict[str, Any]] = Field(default_factory=list)
    emr_qc_handover_record: List[Dict[str, Any]] = Field(default_factory=list)
    emr_qc_inpatient_homepage: List[Dict[str, Any]] = Field(default_factory=list)
    emr_qc_medical_report: List[Dict[str, Any]] = Field(default_factory=list)
    emr_qc_nursing_record: List[Dict[str, Any]] = Field(default_factory=list)
    emr_qc_nursing_special: List[Dict[str, Any]] = Field(default_factory=list)
    emr_qc_order_record: List[Dict[str, Any]] = Field(default_factory=list)
    emr_qc_outpatient_homepage: List[Dict[str, Any]] = Field(default_factory=list)
    emr_qc_outpatient_record: List[Dict[str, Any]] = Field(default_factory=list)
    emr_qc_outpatient_surgery: List[Dict[str, Any]] = Field(default_factory=list)
    emr_qc_pathology_detail: List[Dict[str, Any]] = Field(default_factory=list)
    emr_qc_refusal_record: List[Dict[str, Any]] = Field(default_factory=list)
    emr_qc_special_exam_report: List[Dict[str, Any]] = Field(default_factory=list)
    emr_qc_surgery_record: List[Dict[str, Any]] = Field(default_factory=list)
    emr_qc_surgery_safety: List[Dict[str, Any]] = Field(default_factory=list)

    class Config:
        extra = "allow"

    def get_emr_tables(self) -> Dict[str, List[Dict[str, Any]]]:
        payload = self.model_dump(exclude={"visitList", "qc_rules", "options"}, exclude_none=True)
        return {
            key: value for key, value in payload.items()
            if key.startswith("emr_qc_") and isinstance(value, list)
        }


class ViolationOut(BaseModel):
    deductScore: float
    docName: str
    colName: str
    levelLabel: str
    secondaryPath: str
    level: str
    ruleName: str
    description: str
    arrayKey: str
    arrayIndex: int
    itemInfo: str
    ruleKey: str
    suggestion: str


class QualityControlResponse(BaseModel):
    visitId: str
    recordId: str
    qcType: str
    qcStatus: str
    totalDeductScore: float
    qcGrade: str
    defectCount: int
    violations: List[ViolationOut]


class QualityControlDebugResponse(BaseModel):
    result: QualityControlResponse
    debug: Dict[str, Any]
