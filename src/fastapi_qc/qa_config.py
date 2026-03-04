"""
质量保障配置加载模块
从 quality_assurance.yaml 和环境变量加载配置
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml
except ImportError:
    yaml = None


class QAConfig:
    """质量保障配置类"""

    def __init__(self, config_path: Optional[Path] = None):
        """
        初始化配置

        Args:
            config_path: 配置文件路径，默认为 config/quality_assurance.yaml
        """
        self._config: Dict[str, Any] = {}

        # 默认配置路径
        if config_path is None:
            root = Path(__file__).parent.parent.parent
            config_path = root / "config" / "quality_assurance.yaml"

        # 加载 YAML 配置
        if config_path.exists() and yaml is not None:
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    self._config = yaml.safe_load(f) or {}
            except Exception:
                self._config = {}

        # 环境变量覆盖配置
        self._apply_env_overrides()

    def _apply_env_overrides(self) -> None:
        """应用环境变量覆盖"""
        # 置信度配置
        if "QA_MIN_CONFIDENCE" in os.environ:
            if "confidence" not in self._config:
                self._config["confidence"] = {}
            self._config["confidence"]["min_threshold"] = float(os.getenv("QA_MIN_CONFIDENCE", "0.7"))

        # 健壮性配置
        if "robustness" not in self._config:
            self._config["robustness"] = {}

        if "QA_MAX_RETRIES" in os.environ:
            self._config["robustness"]["max_retries"] = int(os.getenv("QA_MAX_RETRIES", "3"))

        if "QA_TIMEOUT" in os.environ:
            self._config["robustness"]["timeout"] = int(os.getenv("QA_TIMEOUT", "30"))

        # 人工复核配置
        if "review" not in self._config:
            self._config["review"] = {}

        if "QA_ENABLE_REVIEW" in os.environ:
            enable_review = os.getenv("QA_ENABLE_REVIEW", "false").lower()
            self._config["review"]["enable"] = enable_review in ("true", "1", "yes")

        if "QA_REVIEW_THRESHOLD" in os.environ:
            self._config["review"]["confidence_threshold"] = float(os.getenv("QA_REVIEW_THRESHOLD", "0.6"))

    @property
    def min_confidence(self) -> float:
        """最小置信度阈值"""
        return self._config.get("confidence", {}).get("min_threshold", 0.7)

    @property
    def max_retries(self) -> int:
        """最大重试次数"""
        return self._config.get("robustness", {}).get("max_retries", 3)

    @property
    def timeout(self) -> int:
        """超时时间（秒）"""
        return self._config.get("robustness", {}).get("timeout", 30)

    @property
    def enable_review(self) -> bool:
        """是否启用人工复核"""
        return self._config.get("review", {}).get("enable", False)

    @property
    def review_threshold(self) -> float:
        """复核置信度阈值"""
        return self._config.get("review", {}).get("confidence_threshold", 0.6)

    @property
    def enable_validation(self) -> bool:
        """是否启用验证"""
        return self._config.get("accuracy", {}).get("enable_validation", True)

    @property
    def enable_explainability(self) -> bool:
        """是否启用可解释性增强"""
        return self._config.get("explainability", {}).get("enable", True)

    @property
    def include_content_snippets(self) -> bool:
        """是否包含内容片段"""
        return self._config.get("explainability", {}).get("include_content_snippets", True)

    @property
    def max_snippet_length(self) -> int:
        """最大内容片段长度"""
        return self._config.get("explainability", {}).get("max_snippet_length", 200)

    def get_confidence_weights(self) -> Dict[str, float]:
        """获取置信度权重配置"""
        return self._config.get("confidence", {}).get("weights", {
            "llm_confidence": 0.4,
            "validation_score": 0.3,
            "data_completeness": 0.2,
            "rule_complexity": 0.1,
        })

    def get_confidence_levels(self) -> Dict[str, float]:
        """获取置信度等级阈值"""
        return self._config.get("confidence", {}).get("levels", {
            "high": 0.85,
            "medium": 0.65,
        })

    def to_dict(self) -> Dict[str, Any]:
        """导出配置为字典"""
        return {
            "min_confidence": self.min_confidence,
            "max_retries": self.max_retries,
            "timeout": self.timeout,
            "enable_review": self.enable_review,
            "review_threshold": self.review_threshold,
            "enable_validation": self.enable_validation,
            "enable_explainability": self.enable_explainability,
            "confidence_weights": self.get_confidence_weights(),
            "confidence_levels": self.get_confidence_levels(),
        }


# 全局配置实例
_qa_config: Optional[QAConfig] = None


def get_qa_config() -> QAConfig:
    """获取全局 QA 配置实例"""
    global _qa_config
    if _qa_config is None:
        _qa_config = QAConfig()
    return _qa_config

