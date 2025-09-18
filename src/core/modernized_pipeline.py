"""
Modernized Integrated Pipeline - 리팩토링된 통합 파이프라인
통합 파서와 단순화된 설정 시스템 사용
"""

import logging
import asyncio
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import time

# 새로운 컴포넌트들
from ..parsers.unified_docx_parser import UnifiedDocxParser
from ..parsers.pdf_parser import PDFParser
from ..analyzers.layout_analyzer import LayoutAnalyzer
from ..core.docjson import DocJSON
from ..core.vectorization_engine import VectorizationEngine, VectorDocument
from ..core.user_annotations import UserAnnotationManager, DocumentAnnotation
from ..core.template_manager import TemplateManager, TemplateMatchResult
from ..core.device_manager import DeviceManager
from ..core.simplified_config import (
    SimplifiedConfigManager, PipelineConfig, ProcessingPreset,
    ProcessingLevel, DocumentFormat, ConfigValidation
)

logger = logging.getLogger(__name__)


@dataclass
class ModernPipelineResult:
    """현대화된 파이프라인 결과"""
    success: bool
    document_id: str
    processing_level: ProcessingLevel

    # 핵심 결과물
    docjson: Optional[DocJSON] = None
    vector_document: Optional[VectorDocument] = None
    annotation: Optional[DocumentAnnotation] = None
    template_match: Optional[TemplateMatchResult] = None

    # 성능 지표
    processing_time: float = 0.0
    stages_completed: List[str] = None

    # 파일 및 메타데이터
    output_files: Dict[str, Path] = None
    metadata: Dict[str, Any] = None
    error: Optional[str] = None

    # 품질 지표
    quality_score: Optional[float] = None
    confidence_scores: Dict[str, float] = None

    def __post_init__(self):
        if self.stages_completed is None:
            self.stages_completed = []
        if self.output_files is None:
            self.output_files = {}
        if self.metadata is None:
            self.metadata = {}
        if self.confidence_scores is None:
            self.confidence_scores = {}


class ModernizedPipeline:
    """현대화된 통합 문서 처리 파이프라인"""

    def __init__(self,
                 output_dir: Union[str, Path] = None,
                 device_manager: DeviceManager = None,
                 config_manager: SimplifiedConfigManager = None):

        # 기본 설정
        self.output_dir = Path(output_dir or "pipeline_output")
        self.output_dir.mkdir(exist_ok=True)

        self.device_manager = device_manager or DeviceManager()
        self.config_manager = config_manager or SimplifiedConfigManager()

        # 핵심 컴포넌트들 - 통합된 파서 사용
        self.docx_parser = UnifiedDocxParser(self.device_manager)
        self.pdf_parser = PDFParser(self.device_manager)
        self.layout_analyzer = LayoutAnalyzer(self.device_manager)

        # 고급 컴포넌트들
        self.vectorization_engine = VectorizationEngine(self.output_dir / "vectorized")
        self.annotation_manager = UserAnnotationManager(self.output_dir / "annotations")
        self.template_manager = TemplateManager(self.output_dir / "annotations" / "templates")

        logger.info("Modernized pipeline initialized")

    async def process_document(self,
                               document_path: Union[str, Path],
                               config: PipelineConfig) -> ModernPipelineResult:
        """문서 처리 메인 메서드"""
        start_time = time.time()
        document_id = str(uuid.uuid4())

        logger.info(f"Processing document: {document_path} with level: {config.processing_level.value}")

        try:
            # 설정 검증
            validation_warnings = ConfigValidation.validate_config(config)
            if validation_warnings:
                for warning in validation_warnings:
                    logger.warning(f"Config validation: {warning}")

            # 프리셋 가져오기
            preset = config.to_preset(self.config_manager)
            preset_warnings = ConfigValidation.validate_preset(preset)
            if preset_warnings:
                for warning in preset_warnings:
                    logger.warning(f"Preset validation: {warning}")

            # 결과 객체 초기화
            result = ModernPipelineResult(
                success=False,
                document_id=document_id,
                processing_level=config.processing_level
            )

            # 단계별 처리
            await self._execute_processing_stages(document_path, preset, result)

            # 최종 처리 시간 기록
            result.processing_time = time.time() - start_time
            result.success = True

            logger.info(f"Document processing completed in {result.processing_time:.2f}s")
            return result

        except Exception as e:
            error_msg = f"Pipeline processing failed: {e}"
            logger.error(error_msg)

            return ModernPipelineResult(
                success=False,
                document_id=document_id,
                processing_level=config.processing_level,
                processing_time=time.time() - start_time,
                error=error_msg
            )

    async def _execute_processing_stages(self,
                                         document_path: Union[str, Path],
                                         preset: ProcessingPreset,
                                         result: ModernPipelineResult):
        """처리 단계들을 순차적으로 실행"""

        # Stage 1: 문서 파싱
        await self._stage_document_parsing(document_path, preset, result)

        # Stage 2: 템플릿 매칭 (설정에 따라)
        if preset.enable_template_matching:
            await self._stage_template_matching(document_path, preset, result)

        # Stage 3: 주석 생성 (설정에 따라)
        if preset.enable_auto_annotations:
            await self._stage_annotation_generation(preset, result)

        # Stage 4: 벡터화 (설정에 따라)
        if preset.enable_vectorization:
            await self._stage_vectorization(preset, result)

        # Stage 5: 출력 파일 생성
        await self._stage_output_generation(preset, result)

        # Stage 6: 품질 평가
        await self._stage_quality_assessment(result)

    async def _stage_document_parsing(self,
                                      document_path: Union[str, Path],
                                      preset: ProcessingPreset,
                                      result: ModernPipelineResult):
        """Stage 1: 문서 파싱"""
        logger.info("Stage 1: Document parsing")

        try:
            # 문서 타입 감지
            file_path = Path(document_path)
            extension = file_path.suffix.lower()

            # 적절한 파서 선택
            if extension == '.docx':
                # 통합 DOCX 파서 사용
                parse_result = await self.docx_parser.parse(document_path)

                if parse_result.success and parse_result.content:
                    # DocJSON 객체 직접 할당
                    if 'docjson' in parse_result.content:
                        docjson_data = parse_result.content['docjson']
                        if docjson_data is not None:
                            result.docjson = docjson_data

            elif extension == '.pdf':
                parse_result = await self.pdf_parser.parse(document_path)

                if parse_result.success and parse_result.content:
                    result.docjson = parse_result.content.get('docjson')

            else:
                raise ValueError(f"Unsupported document format: {extension}")

            if result.docjson:
                result.stages_completed.append("parsing")
                result.confidence_scores["parsing"] = 0.95
                logger.info("Document parsing completed successfully")
            else:
                raise ValueError("Failed to generate DocJSON")

        except Exception as e:
            logger.error(f"Document parsing failed: {e}")
            raise

    async def _stage_template_matching(self,
                                       document_path: Union[str, Path],
                                       preset: ProcessingPreset,
                                       result: ModernPipelineResult):
        """Stage 2: 템플릿 매칭"""
        logger.info("Stage 2: Template matching")

        try:
            if not result.docjson:
                logger.warning("No DocJSON available for template matching")
                return

            # 템플릿 매칭 실행
            template_match = await asyncio.to_thread(
                self.template_manager.match_document,
                result.docjson,
                confidence_threshold=preset.template_confidence_threshold
            )

            if template_match and template_match.confidence >= preset.template_confidence_threshold:
                result.template_match = template_match
                result.confidence_scores["template_matching"] = template_match.confidence

                # 자동 템플릿 적용
                if preset.auto_apply_templates:
                    applied_annotation = await asyncio.to_thread(
                        self.template_manager.apply_template_to_document,
                        document_path,
                        template_match.template_id
                    )

                    if applied_annotation:
                        result.annotation = applied_annotation
                        result.confidence_scores["template_application"] = 0.9
                        logger.info(f"Template applied: {template_match.template_name}")

                result.stages_completed.append("template_matching")
            else:
                logger.info("No suitable template found or confidence too low")

        except Exception as e:
            logger.error(f"Template matching failed: {e}")
            # 템플릿 매칭 실패는 전체 파이프라인을 중단하지 않음

    async def _stage_annotation_generation(self,
                                           preset: ProcessingPreset,
                                           result: ModernPipelineResult):
        """Stage 3: 주석 생성"""
        logger.info("Stage 3: Annotation generation")

        try:
            if result.annotation:
                # 템플릿 적용으로 이미 주석이 있는 경우
                logger.info("Annotation already exists from template application")
                result.stages_completed.append("annotation_generation")
                return

            if not result.docjson:
                logger.warning("No DocJSON available for annotation generation")
                return

            # 자동 주석 생성
            auto_annotation = await asyncio.to_thread(
                self.annotation_manager.auto_detect_fields,
                result.docjson,
                document_path
            )

            if auto_annotation:
                result.annotation = auto_annotation
                result.confidence_scores["auto_annotation"] = 0.8
                result.stages_completed.append("annotation_generation")
                logger.info("Auto annotation generated successfully")

        except Exception as e:
            logger.error(f"Annotation generation failed: {e}")

    async def _stage_vectorization(self,
                                   preset: ProcessingPreset,
                                   result: ModernPipelineResult):
        """Stage 4: 벡터화"""
        logger.info("Stage 4: Vectorization")

        try:
            if not result.docjson:
                logger.warning("No DocJSON available for vectorization")
                return

            # 벡터화 실행
            vector_doc = await asyncio.to_thread(
                self.vectorization_engine.vectorize_document,
                result.docjson,
                result.document_id
            )

            if vector_doc:
                result.vector_document = vector_doc
                result.confidence_scores["vectorization"] = 0.95
                result.stages_completed.append("vectorization")
                logger.info("Vectorization completed successfully")

        except Exception as e:
            logger.error(f"Vectorization failed: {e}")

    async def _stage_output_generation(self,
                                       preset: ProcessingPreset,
                                       result: ModernPipelineResult):
        """Stage 5: 출력 파일 생성"""
        logger.info("Stage 5: Output generation")

        try:
            output_files = {}

            # DocJSON 저장
            if "docjson" in preset.output_formats and result.docjson:
                docjson_path = self.output_dir / f"{result.document_id}.docjson"
                await asyncio.to_thread(
                    self._save_docjson, result.docjson, docjson_path
                )
                output_files["docjson"] = docjson_path

            # 주석 저장
            if "annotations" in preset.output_formats and result.annotation:
                annotation_path = self.output_dir / "annotations" / "documents" / f"{result.document_id}.json"
                await asyncio.to_thread(
                    self.annotation_manager.save_annotation,
                    result.annotation
                )
                output_files["annotation"] = annotation_path

            # 벡터 저장
            if "vectors" in preset.output_formats and result.vector_document:
                vector_path = self.output_dir / "vectorized" / f"{result.document_id}.vectors"
                # 벡터화 엔진이 자체적으로 저장하므로 경로만 기록
                output_files["vectors"] = vector_path

            # 메타데이터 저장
            metadata_path = self.output_dir / f"{result.document_id}.metadata.json"
            metadata = self._generate_metadata(result, preset)
            await asyncio.to_thread(
                self._save_metadata, metadata, metadata_path
            )
            output_files["metadata"] = metadata_path

            result.output_files = output_files
            result.stages_completed.append("output_generation")
            logger.info(f"Generated {len(output_files)} output files")

        except Exception as e:
            logger.error(f"Output generation failed: {e}")
            raise

    async def _stage_quality_assessment(self, result: ModernPipelineResult):
        """Stage 6: 품질 평가"""
        logger.info("Stage 6: Quality assessment")

        try:
            # 각 단계별 점수 계산
            stage_scores = []

            if "parsing" in result.stages_completed:
                stage_scores.append(result.confidence_scores.get("parsing", 0) * 25)

            if "template_matching" in result.stages_completed:
                stage_scores.append(result.confidence_scores.get("template_matching", 0) * 35)
            elif "annotation_generation" in result.stages_completed:
                stage_scores.append(result.confidence_scores.get("auto_annotation", 0) * 30)

            if "vectorization" in result.stages_completed:
                stage_scores.append(result.confidence_scores.get("vectorization", 0) * 10)

            if "output_generation" in result.stages_completed:
                stage_scores.append(25)  # 출력 생성은 성공/실패만 평가

            # 전체 품질 점수 계산
            if stage_scores:
                result.quality_score = sum(stage_scores) / len(stage_scores)
            else:
                result.quality_score = 0.0

            result.stages_completed.append("quality_assessment")
            logger.info(f"Quality assessment completed: {result.quality_score:.1f}/100")

        except Exception as e:
            logger.error(f"Quality assessment failed: {e}")

    def _save_docjson(self, docjson, path: Path):
        """DocJSON 저장"""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            import json
            # DocJSON 객체인지 딕셔너리인지 확인
            if hasattr(docjson, 'to_dict'):
                # DocJSON 객체인 경우
                json.dump(docjson.to_dict(), f, ensure_ascii=False, indent=2)
            else:
                # 이미 딕셔너리인 경우
                json.dump(docjson, f, ensure_ascii=False, indent=2)

    def _save_metadata(self, metadata: Dict[str, Any], path: Path):
        """메타데이터 저장"""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            import json
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    def _generate_metadata(self, result: ModernPipelineResult, preset: ProcessingPreset) -> Dict[str, Any]:
        """메타데이터 생성"""
        return {
            "document_id": result.document_id,
            "processing_level": result.processing_level.value,
            "processing_time": result.processing_time,
            "stages_completed": result.stages_completed,
            "confidence_scores": result.confidence_scores,
            "quality_score": result.quality_score,
            "preset_used": {
                "description": preset.description,
                "template_matching": preset.enable_template_matching,
                "auto_annotations": preset.enable_auto_annotations,
                "vectorization": preset.enable_vectorization
            },
            "timestamp": datetime.now().isoformat(),
            "pipeline_version": "2.0"
        }

    def get_processing_statistics(self) -> Dict[str, Any]:
        """처리 통계 정보"""
        # 최근 처리된 파일들의 메타데이터를 분석하여 통계 제공
        metadata_files = list(self.output_dir.glob("*.metadata.json"))

        if not metadata_files:
            return {
                "total_processed": 0,
                "average_processing_time": 0.0,
                "average_quality_score": 0.0,
                "processing_levels": {},
                "analyzed_files": 0
            }

        import json
        total_processed = len(metadata_files)
        avg_processing_time = 0
        avg_quality_score = 0
        level_counts = {}
        analyzed_count = 0

        for metadata_file in metadata_files[-10:]:  # 최근 10개만 분석
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)

                avg_processing_time += metadata.get('processing_time', 0)
                avg_quality_score += metadata.get('quality_score', 0)

                level = metadata.get('processing_level', 'unknown')
                level_counts[level] = level_counts.get(level, 0) + 1
                analyzed_count += 1

            except Exception as e:
                logger.warning(f"Failed to read metadata {metadata_file}: {e}")

        return {
            "total_processed": total_processed,
            "average_processing_time": avg_processing_time / analyzed_count if analyzed_count > 0 else 0.0,
            "average_quality_score": avg_quality_score / analyzed_count if analyzed_count > 0 else 0.0,
            "processing_levels": level_counts,
            "analyzed_files": analyzed_count
        }


# 편의 함수들
async def quick_process(document_path: Union[str, Path],
                        level: ProcessingLevel = ProcessingLevel.STANDARD,
                        output_dir: str = None) -> ModernPipelineResult:
    """빠른 문서 처리"""
    pipeline = ModernizedPipeline(output_dir)
    config = PipelineConfig(processing_level=level)
    return await pipeline.process_document(document_path, config)


async def batch_process(document_paths: List[Union[str, Path]],
                        level: ProcessingLevel = ProcessingLevel.STANDARD,
                        output_dir: str = None) -> List[ModernPipelineResult]:
    """배치 문서 처리"""
    pipeline = ModernizedPipeline(output_dir)
    config = PipelineConfig(processing_level=level)

    results = []
    for doc_path in document_paths:
        try:
            result = await pipeline.process_document(doc_path, config)
            results.append(result)
            logger.info(f"Completed: {doc_path} - Quality: {result.quality_score:.1f}")
        except Exception as e:
            logger.error(f"Failed to process {doc_path}: {e}")
            results.append(ModernPipelineResult(
                success=False,
                document_id=str(uuid.uuid4()),
                processing_level=level,
                error=str(e)
            ))

    return results