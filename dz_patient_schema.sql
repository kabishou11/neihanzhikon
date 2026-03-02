CREATE TABLE `dz_consent` (
  `id` varchar(32) NOT NULL COMMENT '主键ID，无横杠UUID',
  `patient_id` varchar(32) NOT NULL COMMENT '患者ID，关联 dz_patient.id',
  `consent_type` varchar(50) NOT NULL COMMENT '同意书类型（SURGERY/TRANSFUSION/ANESTHESIA/SPECIAL_TREATMENT/OTHER 等）',
  `target_procedure` varchar(255) DEFAULT NULL COMMENT '对应手术/操作/治疗名称',
  `sign_time` varchar(32) DEFAULT NULL COMMENT '签署时间',
  `patient_signed` varchar(1) NOT NULL DEFAULT '0' COMMENT '患者是否签字（1是，0否）',
  `patient_sign_name` varchar(100) DEFAULT NULL COMMENT '患者签字姓名',
  `family_signed` varchar(1) NOT NULL DEFAULT '0' COMMENT '家属是否签字（1是，0否）',
  `family_sign_name` varchar(100) DEFAULT NULL COMMENT '家属签字姓名',
  `doctor_id` varchar(64) DEFAULT NULL COMMENT '沟通医生ID',
  `doctor_name` varchar(100) DEFAULT NULL COMMENT '沟通医生姓名',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_consent_patient_type` (`patient_id`,`consent_type`,`sign_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='知情同意书表';

CREATE TABLE `dz_death` (
  `id` varchar(32) NOT NULL COMMENT '主键ID，无横杠UUID',
  `patient_id` varchar(32) NOT NULL COMMENT '患者ID，关联 dz_patient.id',
  `death_time` varchar(32) DEFAULT NULL COMMENT '死亡时间',
  `immediate_cause` varchar(255) DEFAULT NULL COMMENT '直接死亡原因',
  `underlying_cause` varchar(255) DEFAULT NULL COMMENT '根本死亡原因',
  `death_place` varchar(100) DEFAULT NULL COMMENT '死亡地点',
  `autopsy_flag` varchar(1) NOT NULL DEFAULT '0' COMMENT '是否尸检（1是，0否）',
  `death_record_done` varchar(1) NOT NULL DEFAULT '0' COMMENT '死亡记录是否完成',
  `death_cert_done` varchar(1) NOT NULL DEFAULT '0' COMMENT '死亡医学证明/推断书是否完成',
  `discussion_done` varchar(1) NOT NULL DEFAULT '0' COMMENT '死亡病例讨论是否完成',
  `discussion_time` varchar(32) DEFAULT NULL COMMENT '死亡病例讨论时间',
  `discussion_host_title` varchar(50) DEFAULT NULL COMMENT '讨论主持人职称',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_death_patient` (`patient_id`),
  KEY `idx_death_time` (`death_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='死亡及死亡讨论结构化信息表';

CREATE TABLE `dz_diagnosis` (
  `id` varchar(32) NOT NULL COMMENT '主键ID，无横杠UUID',
  `patient_id` varchar(32) NOT NULL COMMENT '患者ID，关联 dz_patient.id',
  `diag_type` varchar(30) NOT NULL COMMENT '诊断类型（ADMISSION/FINAL/DISCHARGE/COMPLICATION/TCM 等）',
  `diag_seq` varchar(10) NOT NULL DEFAULT '1' COMMENT '同一类型下排序号（1为主诊断）',
  `icd_code` varchar(50) DEFAULT NULL COMMENT 'ICD 编码',
  `diag_name` varchar(255) NOT NULL COMMENT '诊断名称',
  `is_primary` varchar(1) NOT NULL DEFAULT '0' COMMENT '是否主诊断（1是，0否）',
  `diag_time` varchar(32) DEFAULT NULL COMMENT '诊断时间',
  `tcm_syndrome` varchar(255) DEFAULT NULL COMMENT '中医证候（如有）',
  `comment` varchar(500) DEFAULT NULL COMMENT '备注',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_diag_patient` (`patient_id`,`diag_type`,`diag_seq`),
  KEY `idx_diag_code` (`icd_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='诊断表';

CREATE TABLE `dz_document` (
  `id` varchar(32) NOT NULL COMMENT '主键ID，无横杠UUID',
  `patient_id` varchar(32) NOT NULL COMMENT '患者ID，关联 dz_patient.id',
  `doc_type` varchar(50) NOT NULL COMMENT '文书类型（ADMISSION/FIRST_COURSE/SUPERIOR_FIRST/DAILY_COURSE/STAGE_SUMMARY/TRANSFER_IN/TRANSFER_OUT/CONSULTATION/OP_NOTE/ANES_NOTE/DISCHARGE_RECORD/DEATH_RECORD/DEATH_DISCUSSION/TRANSFUSION_RECORD/EMERGENCY_RECORD/SHIFT_RECORD 等）',
  `doc_title` varchar(255) DEFAULT NULL COMMENT '文书标题',
  `doc_status` varchar(20) DEFAULT NULL COMMENT '文书状态（DRAFT/SUBMITTED/SIGNED 等）',
  `doc_source` varchar(20) DEFAULT NULL COMMENT '来源（DOCTOR/NURSE/SYSTEM）',
  `author_id` varchar(64) DEFAULT NULL COMMENT '书写医生/护士ID',
  `author_name` varchar(100) DEFAULT NULL COMMENT '书写医生/护士姓名',
  `title_time` varchar(32) DEFAULT NULL COMMENT '文书标题时间',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '文书创建时间',
  `first_sign_time` varchar(32) DEFAULT NULL COMMENT '首次签名时间',
  `last_sign_time` varchar(32) DEFAULT NULL COMMENT '最近签名时间',
  `main_sign_level` varchar(50) DEFAULT NULL COMMENT '最高级别签名（RESIDENT/ATTENDING/CHIEF 等）',
  `special_char_flag` varchar(10) DEFAULT NULL COMMENT '是否存在特殊字符/占位符（是/否）',
  `typo_flag` varchar(10) DEFAULT NULL COMMENT '是否存在错别字（是/否）',
  `printed_flag` varchar(1) NOT NULL DEFAULT '0' COMMENT '是否已打印归档（1是，0否）',
  `remark` varchar(500) DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`id`),
  KEY `idx_doc_patient_type` (`patient_id`,`doc_type`,`title_time`),
  KEY `idx_doc_patient_sign` (`patient_id`,`first_sign_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='电子病历文书主表';


CREATE TABLE `dz_document_section` (
  `id` varchar(32) NOT NULL COMMENT '主键ID，无横杠UUID',
  `document_id` varchar(32) NOT NULL COMMENT '文书ID，关联 dz_document.id',
  `section_code` varchar(50) NOT NULL COMMENT '分段代码（CHIEF_COMPLAINT/PRESENT_ILLNESS/PAST_HISTORY/PERSONAL_HISTORY/FAMILY_HISTORY/OB_MENSTRUAL/BIRTH_HISTORY/FEEDING_HISTORY/PHYSICAL_EXAM/SPECIAL_EXAM/DIAGNOSIS/DIAGNOSIS_BASIS/DIFFERENTIAL_DIAGNOSIS/TREATMENT_PLAN/CURRENT_STATUS/PLAN/TRANSFER_REASON/TRANSFER_PLAN/CONSULT_REASON/CONSULT_OPINION/RESCUE_PROCESS/DEATH_CAUSE 等）',
  `section_name` varchar(100) DEFAULT NULL COMMENT '分段名称（中文显示用）',
  `content` longtext COMMENT '分段文本内容',
  `content_length` varchar(10) DEFAULT NULL COMMENT '内容字数（预处理冗余，便于规则校验）',
  `special_char_flag` varchar(10) DEFAULT NULL COMMENT '是否含特殊字符（是/否）',
  `typo_flag` varchar(10) DEFAULT NULL COMMENT '是否含错别字（是/否）',
  `structured_json` text COMMENT '结构化信息JSON（如评分、量表、体征结构化值等）',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_section_doc` (`document_id`,`section_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='电子病历文书分段内容表';


CREATE TABLE `dz_exam_report` (
  `id` varchar(32) NOT NULL COMMENT '主键ID，无横杠UUID',
  `patient_id` varchar(32) NOT NULL COMMENT '患者ID，关联 dz_patient.id',
  `exam_type` varchar(50) NOT NULL COMMENT '检查类别（CT/MRI/US/XRAY/PATHOLOGY/NUCLEAR/ENDOSCOPY 等）',
  `exam_item_code` varchar(64) DEFAULT NULL COMMENT '检查项目代码',
  `exam_item_name` varchar(255) NOT NULL COMMENT '检查项目名称',
  `exam_time` varchar(32) DEFAULT NULL COMMENT '检查时间',
  `report_time` varchar(32) DEFAULT NULL COMMENT '报告时间',
  `report_doctor_id` varchar(64) DEFAULT NULL COMMENT '报告医生ID',
  `report_doctor_name` varchar(100) DEFAULT NULL COMMENT '报告医生姓名',
  `description` text COMMENT '检查所见/描述',
  `impression` text COMMENT '印象/诊断意见',
  `conclusion` text COMMENT '结论（可选的简要字段）',
  `hospital_name` varchar(255) DEFAULT NULL COMMENT '检查医院名称（外院检查时使用）',
  `remark` varchar(500) DEFAULT NULL COMMENT '备注',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_exam_patient_type` (`patient_id`,`exam_type`,`exam_time`),
  KEY `idx_exam_item` (`exam_item_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='检查报告表';


CREATE TABLE `dz_home_page` (
  `id` varchar(32) NOT NULL COMMENT '主键ID，无横杠UUID',
  `patient_id` varchar(32) NOT NULL COMMENT '患者ID，关联 dz_patient.id',
  `id_card` varchar(32) DEFAULT NULL COMMENT '身份证号（首页记载）',
  `name` varchar(100) DEFAULT NULL COMMENT '姓名（首页）',
  `gender_code` varchar(1) DEFAULT NULL COMMENT '性别（首页）',
  `birth_date` varchar(10) DEFAULT NULL COMMENT '出生日期（首页）yyyy-MM-dd',
  `admission_date` varchar(32) DEFAULT NULL COMMENT '入院日期（首页）',
  `discharge_date` varchar(32) DEFAULT NULL COMMENT '出院日期（首页）',
  `marital_status` varchar(20) DEFAULT NULL COMMENT '婚姻状况（首页）',
  `occupation` varchar(100) DEFAULT NULL COMMENT '职业（首页）',
  `native_place` varchar(255) DEFAULT NULL COMMENT '籍贯/出生地',
  `residence` varchar(255) DEFAULT NULL COMMENT '常住地址',
  `contact_name` varchar(100) DEFAULT NULL COMMENT '联系人（首页）',
  `contact_phone` varchar(50) DEFAULT NULL COMMENT '联系人电话（首页）',
  `contact_relation` varchar(50) DEFAULT NULL COMMENT '与联系人关系（首页）',
  `leave_type` varchar(50) DEFAULT NULL COMMENT '离院方式（首页）',
  `discharge_dept` varchar(100) DEFAULT NULL COMMENT '出院科室（首页）',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_home_patient` (`patient_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='病案首页信息表';


CREATE TABLE `dz_lab_result` (
  `id` varchar(32) NOT NULL COMMENT '主键ID，无横杠UUID',
  `patient_id` varchar(32) NOT NULL COMMENT '患者ID，关联 dz_patient.id',
  `sample_no` varchar(64) DEFAULT NULL COMMENT '标本号/样本号',
  `test_item_code` varchar(64) NOT NULL COMMENT '检验项目代码',
  `test_item_name` varchar(255) NOT NULL COMMENT '检验项目名称',
  `test_time` varchar(32) DEFAULT NULL COMMENT '检验采样/检测时间',
  `report_time` varchar(32) DEFAULT NULL COMMENT '报告时间',
  `result_value` varchar(100) DEFAULT NULL COMMENT '结果值（文本形式）',
  `result_numeric` varchar(30) DEFAULT NULL COMMENT '结果值（数值形式，若可解析）',
  `result_unit` varchar(50) DEFAULT NULL COMMENT '单位',
  `ref_low` varchar(30) DEFAULT NULL COMMENT '参考下限',
  `ref_high` varchar(30) DEFAULT NULL COMMENT '参考上限',
  `abnormal_flag` varchar(10) DEFAULT NULL COMMENT '异常标记（L/H/LL/HH 等）',
  `lab_dept` varchar(100) DEFAULT NULL COMMENT '检验科室',
  `remark` varchar(500) DEFAULT NULL COMMENT '备注',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_lab_patient_item` (`patient_id`,`test_item_code`),
  KEY `idx_lab_patient_time` (`patient_id`,`report_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='检验结果表';


CREATE TABLE `dz_operation` (
  `id` varchar(32) NOT NULL COMMENT '主键ID，无横杠UUID',
  `patient_id` varchar(32) NOT NULL COMMENT '患者ID，关联 dz_patient.id',
  `operation_no` varchar(50) DEFAULT NULL COMMENT '手术序号',
  `operation_date` varchar(32) DEFAULT NULL COMMENT '手术开始时间',
  `operation_end` varchar(32) DEFAULT NULL COMMENT '手术结束时间',
  `operation_name` varchar(255) NOT NULL COMMENT '手术名称',
  `operation_code` varchar(50) DEFAULT NULL COMMENT '手术编码（ICD-9-CM 等）',
  `surgeon_id` varchar(64) DEFAULT NULL COMMENT '术者ID',
  `surgeon_name` varchar(100) DEFAULT NULL COMMENT '术者姓名',
  `assistant1_id` varchar(64) DEFAULT NULL COMMENT '一助ID',
  `assistant1_name` varchar(100) DEFAULT NULL COMMENT '一助姓名',
  `assistant2_id` varchar(64) DEFAULT NULL COMMENT '二助ID',
  `assistant2_name` varchar(100) DEFAULT NULL COMMENT '二助姓名',
  `anesthesia_method` varchar(100) DEFAULT NULL COMMENT '麻醉方式',
  `wound_grade` varchar(20) DEFAULT NULL COMMENT '切口等级',
  `healing_grade` varchar(20) DEFAULT NULL COMMENT '切口愈合等级',
  `blood_loss` varchar(20) DEFAULT NULL COMMENT '术中出血量(ml)',
  `transfusion_volume` varchar(20) DEFAULT NULL COMMENT '术中输血量(ml)',
  `implants` varchar(500) DEFAULT NULL COMMENT '植入物信息',
  `emergency_flag` varchar(1) NOT NULL DEFAULT '0' COMMENT '是否急诊手术（1是，0否）',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_operation_patient` (`patient_id`,`operation_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='手术及操作记录表';


CREATE TABLE `dz_order` (
  `id` varchar(32) NOT NULL COMMENT '主键ID，无横杠UUID',
  `patient_id` varchar(32) NOT NULL COMMENT '患者ID，关联 dz_patient.id',
  `order_no` varchar(64) NOT NULL COMMENT '医嘱号/组号',
  `order_type` varchar(50) NOT NULL COMMENT '医嘱类型（DRUG/EXAM/TREATMENT/NURSING/DIET/OTHER）',
  `order_class` varchar(50) DEFAULT NULL COMMENT '医嘱大类（如 ANTIBIOTIC/CHEMO/RADIOTHERAPY/CT/MRI/PATHOLOGY 等，便于规则过滤）',
  `order_name` varchar(255) NOT NULL COMMENT '医嘱名称',
  `order_code` varchar(64) DEFAULT NULL COMMENT '医嘱编码（药品码、项目码）',
  `start_time` varchar(32) DEFAULT NULL COMMENT '医嘱开始时间',
  `stop_time` varchar(32) DEFAULT NULL COMMENT '医嘱停止时间',
  `execute_time` varchar(32) DEFAULT NULL COMMENT '首次执行时间（如适用）',
  `order_status` varchar(20) DEFAULT NULL COMMENT '状态（ACTIVE/STOPPED/CANCELLED/FINISHED 等）',
  `freq` varchar(50) DEFAULT NULL COMMENT '频次',
  `dosage` varchar(50) DEFAULT NULL COMMENT '剂量（文本）',
  `route` varchar(50) DEFAULT NULL COMMENT '给药途径',
  `level` varchar(20) DEFAULT NULL COMMENT '紧急程度（ROUTINE/STAT 等）',
  `doctor_id` varchar(64) DEFAULT NULL COMMENT '开立医生ID',
  `doctor_name` varchar(100) DEFAULT NULL COMMENT '开立医生姓名',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_order_patient_time` (`patient_id`,`start_time`),
  KEY `idx_order_patient_type` (`patient_id`,`order_type`,`order_class`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='住院医嘱表';


CREATE TABLE `dz_patient` (
  `id` varchar(32) NOT NULL COMMENT '主键ID，无横杠UUID',
  `patient_id` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '病案号/院内患者唯一编号',
  `id_card` varchar(32) DEFAULT NULL COMMENT '身份证号',
  `name` varchar(100) NOT NULL COMMENT '姓名',
  `gender_code` varchar(1) DEFAULT NULL COMMENT '性别代码（M/F/U等）',
  `birth_date` varchar(10) DEFAULT NULL COMMENT '出生日期 yyyy-MM-dd',
  `mobile` varchar(50) DEFAULT NULL COMMENT '联系电话',
  `marital_status` varchar(20) DEFAULT NULL COMMENT '婚姻状况',
  `occupation` varchar(100) DEFAULT NULL COMMENT '职业',
  `address` varchar(255) DEFAULT NULL COMMENT '现住址',
  `contact_name` varchar(100) DEFAULT NULL COMMENT '联系人姓名',
  `contact_phone` varchar(50) DEFAULT NULL COMMENT '联系人电话',
  `contact_relation` varchar(50) DEFAULT NULL COMMENT '与联系人关系',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_patient_no` (`patient_id`),
  KEY `idx_id_card` (`id_card`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='患者主索引表';


CREATE TABLE `dz_rescue` (
  `id` varchar(32) NOT NULL COMMENT '主键ID，无横杠UUID',
  `patient_id` varchar(32) NOT NULL COMMENT '患者ID，关联 dz_patient.id',
  `start_time` varchar(32) NOT NULL COMMENT '抢救开始时间',
  `end_time` varchar(32) DEFAULT NULL COMMENT '抢救结束时间',
  `rescue_process` text COMMENT '抢救经过',
  `participants` varchar(500) DEFAULT NULL COMMENT '参与抢救人员及职称',
  `outcome` varchar(200) DEFAULT NULL COMMENT '抢救结果',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_rescue_patient_time` (`patient_id`,`start_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='抢救记录表';


CREATE TABLE `dz_transfer` (
  `id` varchar(32) NOT NULL COMMENT '主键ID，无横杠UUID',
  `patient_id` varchar(32) NOT NULL COMMENT '患者ID，关联 dz_patient.id',
  `transfer_time` varchar(32) NOT NULL COMMENT '转科时间',
  `from_dept` varchar(100) DEFAULT NULL COMMENT '转出科室',
  `to_dept` varchar(100) DEFAULT NULL COMMENT '转入科室',
  `transfer_reason` varchar(500) DEFAULT NULL COMMENT '转科原因',
  `before_status` varchar(500) DEFAULT NULL COMMENT '转出前病情',
  `after_plan` varchar(500) DEFAULT NULL COMMENT '转入后诊疗计划',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_transfer_patient_time` (`patient_id`,`transfer_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='转科记录表';


CREATE TABLE `dz_transfusion` (
  `id` varchar(32) NOT NULL COMMENT '主键ID，无横杠UUID',
  `patient_id` varchar(32) NOT NULL COMMENT '患者ID，关联 dz_patient.id',
  `record_time` varchar(32) NOT NULL COMMENT '输血开始时间',
  `end_time` varchar(32) DEFAULT NULL COMMENT '输血结束时间',
  `blood_type` varchar(20) DEFAULT NULL COMMENT 'ABO/Rh 血型',
  `component_type` varchar(100) DEFAULT NULL COMMENT '血液成分种类',
  `quantity` varchar(20) DEFAULT NULL COMMENT '输注量',
  `unit` varchar(20) DEFAULT NULL COMMENT '单位（ml/U 等）',
  `indication` varchar(500) DEFAULT NULL COMMENT '输血适应证',
  `reaction_flag` varchar(1) NOT NULL DEFAULT '0' COMMENT '是否发生输血反应（1是，0否）',
  `reaction_desc` varchar(500) DEFAULT NULL COMMENT '输血反应描述',
  `effect_evaluation` varchar(500) DEFAULT NULL COMMENT '输血后效果评价',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_transfusion_patient` (`patient_id`,`record_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='输血记录表';

CREATE TABLE `dz_visit` (
  `id` varchar(32) NOT NULL COMMENT '主键ID，无横杠UUID',
  `patient_id` varchar(32) NOT NULL COMMENT '患者ID，关联 dz_patient.id',
  `visit_id` varchar(50) NOT NULL COMMENT '本次住院号/就诊号',
  `admission_time` varchar(32) DEFAULT NULL COMMENT '入院时间',
  `discharge_time` varchar(32) DEFAULT NULL COMMENT '出院时间',
  `admission_dept` varchar(100) DEFAULT NULL COMMENT '入院科室',
  `current_dept` varchar(100) DEFAULT NULL COMMENT '当前科室',
  `discharge_dept` varchar(100) DEFAULT NULL COMMENT '出院科室',
  `ward_name` varchar(100) DEFAULT NULL COMMENT '病区名称',
  `bed_no` varchar(50) DEFAULT NULL COMMENT '床位号',
  `admission_type` varchar(50) DEFAULT NULL COMMENT '入院方式（急诊/门诊/转院等）',
  `discharge_disposition` varchar(50) DEFAULT NULL COMMENT '离院方式（治愈/好转/死亡/自动出院等）',
  `birthday` varchar(20) DEFAULT NULL COMMENT '入院时年龄(天)，用于新生儿等判断',
  `attending_doctor_id` varchar(64) DEFAULT NULL COMMENT '主治医师ID',
  `attending_doctor_name` varchar(100) DEFAULT NULL COMMENT '主治医师姓名',
  `chief_doctor_id` varchar(64) DEFAULT NULL COMMENT '主任/副主任医师ID',
  `chief_doctor_name` varchar(100) DEFAULT NULL COMMENT '主任/副主任医师姓名',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_visit_id` (`visit_id`),
  KEY `idx_visit_patient` (`patient_id`),
  KEY `idx_visit_admission_time` (`admission_time`),
  KEY `idx_visit_discharge_time` (`discharge_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='住院就诊表';


CREATE TABLE `dz_vital_sign` (
  `id` varchar(32) NOT NULL COMMENT '主键ID，无横杠UUID',
  `patient_id` varchar(32) NOT NULL COMMENT '患者ID，关联 dz_patient.id',
  `record_time` varchar(32) NOT NULL COMMENT '记录时间',
  `source_type` varchar(50) NOT NULL COMMENT '来源类型（ADMISSION_PHYSICAL/COURSE/NURSING/POSTOP_FIRST 等）',
  `temperature` varchar(10) DEFAULT NULL COMMENT '体温(℃)',
  `pulse` varchar(10) DEFAULT NULL COMMENT '脉搏(次/分)',
  `heart_rate` varchar(10) DEFAULT NULL COMMENT '心率(次/分)',
  `respiratory_rate` varchar(10) DEFAULT NULL COMMENT '呼吸(次/分)',
  `systolic_bp` varchar(10) DEFAULT NULL COMMENT '收缩压(mmHg)',
  `diastolic_bp` varchar(10) DEFAULT NULL COMMENT '舒张压(mmHg)',
  `spo2` varchar(10) DEFAULT NULL COMMENT '血氧饱和度(%)',
  `height` varchar(10) DEFAULT NULL COMMENT '身高(cm)',
  `weight` varchar(10) DEFAULT NULL COMMENT '体重(kg)',
  `head_circumference` varchar(10) DEFAULT NULL COMMENT '头围(cm)',
  `waist_circumference` varchar(10) DEFAULT NULL COMMENT '腰围(cm)',
  `bmi` varchar(10) DEFAULT NULL COMMENT '体重指数BMI',
  `position` varchar(50) DEFAULT NULL COMMENT '体位（卧位/坐位等）',
  `remark` varchar(500) DEFAULT NULL COMMENT '备注',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_vital_patient_time` (`patient_id`,`record_time`),
  KEY `idx_vital_source` (`patient_id`,`source_type`,`record_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='生命体征记录表';