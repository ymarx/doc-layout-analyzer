"""
Simplified Configuration System - 단순화된 설정 시스템
복잡한 옵션들을 명확한 3가지 모드로 정리
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ProcessingLevel(Enum):
    """처리 수준 - 명확한 3단계"""
    BASIC = "basic"         # 기본 처리: 빠르고 간단
    STANDARD = "standard"   # 표준 처리: 템플릿 + 주석
    COMPLETE = "complete"   # 완전 처리: 모든 기능 활성화


class DocumentFormat(Enum):
    """지원 문서 형식"""
    DOCX = "docx"
    PDF = "pdf"
    AUTO = "auto"


@dataclass
class ProcessingPreset:
    """처리 프리셋 - 각 레벨별 사전 정의된 설정"""
    level: ProcessingLevel
    description: str

    # 파싱 설정
    use_enhanced_parsing: bool = True
    extract_diagrams: bool = True
    deep_structure_analysis: bool = True

    # 템플릿 설정
    enable_template_matching: bool = True
    auto_apply_templates: bool = True
    template_confidence_threshold: float = 0.7

    # 주석 설정
    enable_auto_annotations: bool = True
    enable_user_annotations: bool = False

    # 벡터화 설정
    enable_vectorization: bool = False

    # 출력 설정
    output_formats: List[str] = None
    save_intermediate_files: bool = False

    def __post_init__(self):
        if self.output_formats is None:
            self.output_formats = ["docjson"]


class SimplifiedConfigManager:
    """단순화된 설정 관리자"""

    def __init__(self):
        self.presets = self._create_presets()
        self.current_preset = self.presets[ProcessingLevel.STANDARD]

    def _create_presets(self) -> Dict[ProcessingLevel, ProcessingPreset]:
        """사전 정의된 프리셋 생성"""
        return {
            ProcessingLevel.BASIC: ProcessingPreset(
                level=ProcessingLevel.BASIC,
                description="빠른 기본 처리 - 텍스트와 표만 추출",
                use_enhanced_parsing=False,
                extract_diagrams=False,
                deep_structure_analysis=False,
                enable_template_matching=False,
                auto_apply_templates=False,
                enable_auto_annotations=False,
                enable_user_annotations=False,
                enable_vectorization=False,
                output_formats=["docjson"],
                save_intermediate_files=False
            ),

            ProcessingLevel.STANDARD: ProcessingPreset(
                level=ProcessingLevel.STANDARD,
                description="표준 처리 - 템플릿 매칭과 자동 주석",
                use_enhanced_parsing=True,
                extract_diagrams=True,
                deep_structure_analysis=True,
                enable_template_matching=True,
                auto_apply_templates=True,
                template_confidence_threshold=0.7,
                enable_auto_annotations=True,
                enable_user_annotations=False,
                enable_vectorization=False,
                output_formats=["docjson", "annotations"],
                save_intermediate_files=False
            ),

            ProcessingLevel.COMPLETE: ProcessingPreset(
                level=ProcessingLevel.COMPLETE,
                description="완전 처리 - 모든 기능 활성화 (벡터화 포함)",
                use_enhanced_parsing=True,
                extract_diagrams=True,
                deep_structure_analysis=True,
                enable_template_matching=True,
                auto_apply_templates=True,
                template_confidence_threshold=0.6,
                enable_auto_annotations=True,
                enable_user_annotations=True,
                enable_vectorization=True,
                output_formats=["docjson", "annotations", "vectors"],
                save_intermediate_files=True
            )
        }

    def get_preset(self, level: ProcessingLevel) -> ProcessingPreset:
        """프리셋 가져오기"""
        return self.presets.get(level, self.presets[ProcessingLevel.STANDARD])

    def set_processing_level(self, level: ProcessingLevel):
        """처리 수준 설정"""
        self.current_preset = self.get_preset(level)
        logger.info(f"Processing level set to: {level.value} - {self.current_preset.description}")

    def customize_preset(self, level: ProcessingLevel, **kwargs) -> ProcessingPreset:
        """프리셋 커스터마이징"""
        preset = self.get_preset(level)

        # 허용된 커스터마이징 옵션들
        customizable_fields = [
            'template_confidence_threshold',
            'enable_vectorization',
            'output_formats',
            'save_intermediate_files'
        ]

        custom_preset = ProcessingPreset(**preset.__dict__)

        for key, value in kwargs.items():
            if key in customizable_fields:
                setattr(custom_preset, key, value)
                logger.info(f"Customized {key}: {value}")
            else:
                logger.warning(f"Cannot customize {key} - not allowed for this preset level")

        return custom_preset

    def get_config_summary(self, preset: ProcessingPreset = None) -> Dict[str, Any]:
        """설정 요약 정보"""
        if preset is None:
            preset = self.current_preset

        return {
            'level': preset.level.value,
            'description': preset.description,
            'features': {
                'enhanced_parsing': preset.use_enhanced_parsing,
                'diagram_extraction': preset.extract_diagrams,
                'template_matching': preset.enable_template_matching,
                'auto_annotations': preset.enable_auto_annotations,
                'user_annotations': preset.enable_user_annotations,
                'vectorization': preset.enable_vectorization
            },
            'thresholds': {
                'template_confidence': preset.template_confidence_threshold
            },
            'outputs': preset.output_formats
        }


@dataclass
class PipelineConfig:
    """단순화된 파이프라인 설정"""
    processing_level: ProcessingLevel = ProcessingLevel.STANDARD
    document_format: DocumentFormat = DocumentFormat.AUTO
    custom_template_id: Optional[str] = None
    output_directory: Optional[str] = None

    # 고급 사용자를 위한 오버라이드 옵션들
    override_template_threshold: Optional[float] = None
    override_output_formats: Optional[List[str]] = None

    def to_preset(self, config_manager: SimplifiedConfigManager) -> ProcessingPreset:
        """설정을 프리셋으로 변환"""
        preset = config_manager.get_preset(self.processing_level)

        # 오버라이드 적용
        if self.override_template_threshold is not None:
            preset.template_confidence_threshold = self.override_template_threshold

        if self.override_output_formats is not None:
            preset.output_formats = self.override_output_formats

        return preset


class ConfigValidation:
    """설정 유효성 검증"""

    @staticmethod
    def validate_preset(preset: ProcessingPreset) -> List[str]:
        """프리셋 유효성 검증"""
        warnings = []

        # 임계값 검증
        if preset.template_confidence_threshold < 0.0 or preset.template_confidence_threshold > 1.0:
            warnings.append(f"Template confidence threshold {preset.template_confidence_threshold} should be between 0.0 and 1.0")

        # 논리적 일관성 검증
        if not preset.enable_template_matching and preset.auto_apply_templates:
            warnings.append("Cannot auto-apply templates when template matching is disabled")

        if preset.enable_user_annotations and not preset.enable_auto_annotations:
            warnings.append("Enabling user annotations without auto annotations may result in empty annotations")

        # 성능 경고
        if preset.enable_vectorization and not preset.use_enhanced_parsing:
            warnings.append("Vectorization works best with enhanced parsing enabled")

        return warnings

    @staticmethod
    def validate_config(config: PipelineConfig) -> List[str]:
        """파이프라인 설정 유효성 검증"""
        warnings = []

        # 임계값 오버라이드 검증
        if config.override_template_threshold is not None:
            if config.override_template_threshold < 0.0 or config.override_template_threshold > 1.0:
                warnings.append("Override template threshold should be between 0.0 and 1.0")

        return warnings


# 편의 함수들
def create_basic_config() -> PipelineConfig:
    """기본 설정 생성"""
    return PipelineConfig(processing_level=ProcessingLevel.BASIC)


def create_standard_config(template_id: str = None) -> PipelineConfig:
    """표준 설정 생성"""
    return PipelineConfig(
        processing_level=ProcessingLevel.STANDARD,
        custom_template_id=template_id
    )


def create_complete_config(template_threshold: float = None) -> PipelineConfig:
    """완전 설정 생성"""
    return PipelineConfig(
        processing_level=ProcessingLevel.COMPLETE,
        override_template_threshold=template_threshold
    )


def get_recommended_config(document_type: str, use_case: str) -> PipelineConfig:
    """사용 사례별 권장 설정"""
    recommendations = {
        ('docx', 'quick_preview'): ProcessingLevel.BASIC,
        ('docx', 'template_processing'): ProcessingLevel.STANDARD,
        ('docx', 'full_analysis'): ProcessingLevel.COMPLETE,
        ('pdf', 'text_extraction'): ProcessingLevel.BASIC,
        ('pdf', 'layout_analysis'): ProcessingLevel.STANDARD,
        ('pdf', 'complete_processing'): ProcessingLevel.COMPLETE
    }

    key = (document_type.lower(), use_case.lower())
    level = recommendations.get(key, ProcessingLevel.STANDARD)

    return PipelineConfig(processing_level=level)


# 마이그레이션 헬퍼
def migrate_legacy_config(legacy_config: Dict[str, Any]) -> PipelineConfig:
    """기존 설정을 새 설정으로 마이그레이션"""
    # ProcessingMode 매핑
    mode_mapping = {
        'fast': ProcessingLevel.BASIC,
        'enhanced': ProcessingLevel.STANDARD,
        'vectorize': ProcessingLevel.COMPLETE,
        'complete': ProcessingLevel.COMPLETE
    }

    processing_mode = legacy_config.get('processing_mode', 'enhanced')
    level = mode_mapping.get(processing_mode, ProcessingLevel.STANDARD)

    config = PipelineConfig(processing_level=level)

    # 템플릿 임계값 마이그레이션
    if 'template_confidence_threshold' in legacy_config:
        config.override_template_threshold = legacy_config['template_confidence_threshold']

    # 출력 형식 마이그레이션
    if 'output_formats' in legacy_config:
        config.override_output_formats = legacy_config['output_formats']

    return config