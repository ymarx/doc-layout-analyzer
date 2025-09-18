"""
Enhanced Modernized Pipeline
기존 ModernizedPipeline에 통합 템플릿 시스템을 적용한 개선된 파이프라인
"""

import logging
import asyncio
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field

# 기존 시스템 import
from .modernized_pipeline import ModernizedPipeline, ModernPipelineResult
from .integrated_template_system import IntegratedTemplateSystem, ImprovedTemplateMatch
from .user_annotations import DocumentTemplate as UserDocumentTemplate
from ..core.docjson import DocJSON
from ..core.simplified_config import PipelineConfig, ProcessingLevel

logger = logging.getLogger(__name__)


@dataclass
class EnhancedPipelineResult(ModernPipelineResult):
    """향상된 파이프라인 결과"""
    # 기본 결과에 추가 정보
    template_match: Optional[ImprovedTemplateMatch] = None
    user_template: Optional[UserDocumentTemplate] = None
    field_extraction_accuracy: float = 0.0
    bbox_improvement_score: float = 0.0
    template_suggestions: List[Dict[str, Any]] = field(default_factory=list)


class EnhancedModernizedPipeline(ModernizedPipeline):
    """향상된 현대화 파이프라인"""

    def __init__(self,
                 output_dir: Union[str, Path] = None,
                 templates_dir: Union[str, Path] = None,
                 **kwargs):

        # 기본 ModernizedPipeline 초기화
        super().__init__(output_dir=output_dir, **kwargs)

        # 통합 템플릿 시스템 추가
        self.integrated_template_system = IntegratedTemplateSystem(
            templates_dir=Path(templates_dir) if templates_dir else self.output_dir / "templates",
            annotations_dir=self.output_dir / "annotations"
        )

        logger.info("Enhanced Modernized Pipeline initialized with integrated template system")

    async def process_document(self,
                               document_path: Union[str, Path],
                               config: PipelineConfig) -> EnhancedPipelineResult:
        """향상된 문서 처리"""
        start_time = time.time()
        document_path = Path(document_path)

        # 결과 객체 초기화
        result = EnhancedPipelineResult(
            success=False,
            document_id=f"doc_{document_path.stem}_{int(time.time())}",
            processing_level=config.processing_level
        )

        try:
            logger.info(f"향상된 문서 처리 시작: {document_path.name}")

            # 1단계: 기본 문서 파싱 (기존 ModernizedPipeline 사용)
            logger.info("1단계: 기본 문서 파싱")
            basic_result = await super().process_document(document_path, config)

            if not basic_result.success:
                result.error = basic_result.error
                result.processing_time = time.time() - start_time
                return result

            # 기본 결과 복사
            result.docjson = basic_result.docjson
            result.vector_document = basic_result.vector_document
            result.annotation = basic_result.annotation
            result.stages_completed = basic_result.stages_completed.copy()
            result.output_files = basic_result.output_files.copy()
            result.metadata = basic_result.metadata.copy()

            # 2단계: 통합 템플릿 매칭
            logger.info("2단계: 통합 템플릿 매칭")
            if result.docjson:
                docjson_data = result.docjson.to_dict() if hasattr(result.docjson, 'to_dict') else result.docjson

                # raw_content 추출 (기존 파이프라인에서)
                raw_content = result.metadata.get('raw_parsing_result', {})

                # 템플릿 매칭 실행
                template_match = self.integrated_template_system.analyze_document_with_templates(
                    docjson_data, raw_content
                )

                result.template_match = template_match
                result.stages_completed.append("enhanced_template_matching")

                logger.info(f"템플릿 매칭 완료: {template_match.template_id} "
                           f"(신뢰도: {template_match.confidence:.2%})")

                # 3단계: 사용자 템플릿 생성
                if template_match.confidence > 0.3:  # 임계값 이상일 때만
                    logger.info("3단계: 사용자 템플릿 생성")
                    user_template = self.integrated_template_system.create_user_template_from_match(
                        template_match, document_path.stem
                    )
                    result.user_template = user_template
                    result.stages_completed.append("user_template_generation")

                    # 템플릿 저장
                    template_file = self.integrated_template_system.save_improved_template(
                        user_template, self.output_dir / "generated_templates"
                    )
                    result.output_files['user_template'] = template_file

                # 4단계: 품질 평가
                result.field_extraction_accuracy = self._calculate_field_accuracy(template_match)
                result.bbox_improvement_score = template_match.bbox_accuracy
                result.stages_completed.append("quality_assessment")

                # 5단계: DocJSON 개선
                logger.info("5단계: DocJSON 개선")
                enhanced_docjson = self._enhance_docjson_with_template(
                    result.docjson, template_match
                )
                result.docjson = enhanced_docjson
                result.stages_completed.append("docjson_enhancement")

                # 6단계: 결과 파일 저장
                await self._save_enhanced_results(result)

            result.success = True
            result.processing_time = time.time() - start_time

            logger.info(f"향상된 문서 처리 완료 (처리시간: {result.processing_time:.3f}초)")
            logger.info(f"완료된 단계: {', '.join(result.stages_completed)}")

        except Exception as e:
            logger.error(f"향상된 문서 처리 실패: {e}")
            result.error = str(e)
            result.processing_time = time.time() - start_time

        return result

    def _calculate_field_accuracy(self, template_match: ImprovedTemplateMatch) -> float:
        """필드 추출 정확도 계산"""
        if not template_match.matched_fields:
            return 0.0

        # 신뢰도가 있는 필드들의 평균
        confidences = []
        for field_data in template_match.matched_fields.values():
            confidence = field_data.get('confidence', 0.5)
            confidences.append(confidence)

        return sum(confidences) / len(confidences) if confidences else 0.0

    def _enhance_docjson_with_template(self,
                                     docjson: DocJSON,
                                     template_match: ImprovedTemplateMatch) -> DocJSON:
        """템플릿 정보로 DocJSON 강화"""

        if isinstance(docjson, dict):
            docjson_data = docjson
        else:
            docjson_data = docjson.to_dict() if hasattr(docjson, 'to_dict') else docjson

        # 메타데이터 강화
        metadata = docjson_data.get('metadata', {})

        # 템플릿 매칭 결과를 메타데이터에 추가
        for field_name, field_data in template_match.matched_fields.items():
            value = field_data.get('value', '')

            # 특정 필드들을 메타데이터에 직접 매핑
            if field_name in ['document_number', 'auto_code']:
                metadata['document_number'] = value
            elif field_name in ['effective_date', 'auto_date']:
                metadata['effective_date'] = value
            elif field_name in ['revision', 'auto_version']:
                metadata['revision'] = value.replace('Rev.', '').strip()
            elif field_name in ['title', 'auto_title'] and len(value) > 5:
                # 기존 긴 제목을 더 명확한 제목으로 교체
                if len(value) < len(metadata.get('title', '')):
                    metadata['title'] = value

        # 템플릿 정보 추가
        metadata.update({
            'template_id': template_match.template_id,
            'template_confidence': template_match.confidence,
            'template_strategy': template_match.strategy_used.value,
            'extracted_fields_count': len(template_match.matched_fields),
            'bbox_accuracy': template_match.bbox_accuracy
        })

        # 섹션 블록들의 바운딩 박스 개선
        sections = docjson_data.get('sections', [])
        for section in sections:
            for block in section.get('blocks', []):
                self._improve_block_bbox(block, template_match)

        # DocJSON 객체로 변환 (필요한 경우)
        if hasattr(docjson, 'to_dict'):
            # 기존 DocJSON 객체 업데이트
            docjson.metadata = DocJSON.DocumentMetadata.from_dict(metadata) if hasattr(DocJSON, 'DocumentMetadata') else metadata
            return docjson
        else:
            # dict 형태로 반환
            docjson_data['metadata'] = metadata
            return docjson_data

    def _improve_block_bbox(self, block: Dict[str, Any], template_match: ImprovedTemplateMatch):
        """블록의 바운딩 박스 개선"""
        block_text = block.get('content', {}).get('text', '')
        if not block_text:
            return

        # 템플릿 매칭 결과에서 해당 텍스트의 바운딩 박스 찾기
        for field_name, field_data in template_match.matched_fields.items():
            field_value = field_data.get('value', '')
            field_bbox = field_data.get('bbox')

            # 텍스트가 매칭되고 바운딩 박스가 있으면 업데이트
            if (field_value in block_text or block_text in field_value) and field_bbox:
                current_bbox = block.get('bbox', {})

                # 기본값 (0,0,100,20)을 더 정확한 값으로 교체
                if (current_bbox.get('x1', 0) == 0 and
                    current_bbox.get('y1', 0) == 0 and
                    current_bbox.get('x2', 100) == 100 and
                    current_bbox.get('y2', 20) == 20):

                    block['bbox'] = field_bbox
                    logger.debug(f"블록 바운딩 박스 개선됨: {field_name}")

    async def _save_enhanced_results(self, result: EnhancedPipelineResult):
        """향상된 결과 저장"""

        # 1. 향상된 DocJSON 저장
        if result.docjson:
            enhanced_docjson_file = self.output_dir / f"{result.document_id}_enhanced.json"

            if hasattr(result.docjson, 'to_dict'):
                docjson_data = result.docjson.to_dict()
            else:
                docjson_data = result.docjson

            import json
            with open(enhanced_docjson_file, 'w', encoding='utf-8') as f:
                json.dump(docjson_data, f, ensure_ascii=False, indent=2)

            result.output_files['enhanced_docjson'] = enhanced_docjson_file

        # 2. 템플릿 매칭 리포트 저장
        if result.template_match:
            template_report = {
                'template_id': result.template_match.template_id,
                'confidence': result.template_match.confidence,
                'strategy_used': result.template_match.strategy_used.value,
                'matched_fields': result.template_match.matched_fields,
                'missing_fields': result.template_match.missing_fields,
                'bbox_accuracy': result.template_match.bbox_accuracy,
                'match_details': result.template_match.match_details
            }

            template_report_file = self.output_dir / f"{result.document_id}_template_report.json"

            import json
            with open(template_report_file, 'w', encoding='utf-8') as f:
                json.dump(template_report, f, ensure_ascii=False, indent=2)

            result.output_files['template_report'] = template_report_file

        # 3. 품질 평가 리포트 저장
        quality_report = {
            'field_extraction_accuracy': result.field_extraction_accuracy,
            'bbox_improvement_score': result.bbox_improvement_score,
            'template_confidence': result.template_match.confidence if result.template_match else 0.0,
            'stages_completed': result.stages_completed,
            'processing_time': result.processing_time,
            'improvement_summary': {
                'original_confidence': 0.33,  # 기존 시스템 기준
                'improved_confidence': result.template_match.confidence if result.template_match else 0.0,
                'improvement_rate': ((result.template_match.confidence if result.template_match else 0.0) - 0.33) / 0.33 * 100
            }
        }

        quality_report_file = self.output_dir / f"{result.document_id}_quality_report.json"

        import json
        with open(quality_report_file, 'w', encoding='utf-8') as f:
            json.dump(quality_report, f, ensure_ascii=False, indent=2)

        result.output_files['quality_report'] = quality_report_file

        logger.info(f"향상된 결과 파일들 저장 완료: {len(result.output_files)}개")

    async def batch_process_with_learning(self,
                                        document_paths: List[Union[str, Path]],
                                        config: PipelineConfig) -> List[EnhancedPipelineResult]:
        """학습 기능이 있는 배치 처리"""

        results = []
        learned_patterns = {}

        for i, doc_path in enumerate(document_paths):
            logger.info(f"배치 처리 중 ({i+1}/{len(document_paths)}): {Path(doc_path).name}")

            # 문서 처리
            result = await self.process_document(doc_path, config)
            results.append(result)

            # 성공적인 결과에서 패턴 학습
            if result.success and result.template_match and result.template_match.confidence > 0.5:
                template_id = result.template_match.template_id

                if template_id not in learned_patterns:
                    learned_patterns[template_id] = []

                learned_patterns[template_id].append({
                    'document': Path(doc_path).name,
                    'confidence': result.template_match.confidence,
                    'matched_fields': list(result.template_match.matched_fields.keys()),
                    'bbox_accuracy': result.template_match.bbox_accuracy
                })

        # 학습된 패턴으로 템플릿 개선
        await self._improve_templates_from_batch_learning(learned_patterns)

        logger.info(f"배치 처리 완료: {len(results)}개 문서")
        return results

    async def _improve_templates_from_batch_learning(self, learned_patterns: Dict[str, List[Dict]]):
        """배치 학습으로부터 템플릿 개선"""

        improvements_file = self.output_dir / "template_improvements.json"

        improvements = {}

        for template_id, pattern_data in learned_patterns.items():
            if len(pattern_data) >= 2:  # 최소 2개 문서에서 학습
                avg_confidence = sum(p['confidence'] for p in pattern_data) / len(pattern_data)
                avg_bbox_accuracy = sum(p['bbox_accuracy'] for p in pattern_data) / len(pattern_data)

                # 공통 필드 패턴
                all_fields = [set(p['matched_fields']) for p in pattern_data]
                common_fields = set.intersection(*all_fields) if all_fields else set()

                improvements[template_id] = {
                    'documents_analyzed': len(pattern_data),
                    'average_confidence': avg_confidence,
                    'average_bbox_accuracy': avg_bbox_accuracy,
                    'common_fields': list(common_fields),
                    'suggested_improvements': self._generate_template_improvements(pattern_data)
                }

        # 개선 사항 저장
        import json
        with open(improvements_file, 'w', encoding='utf-8') as f:
            json.dump(improvements, f, ensure_ascii=False, indent=2)

        logger.info(f"템플릿 개선 사항 저장됨: {improvements_file}")

    def _generate_template_improvements(self, pattern_data: List[Dict]) -> List[str]:
        """패턴 데이터에서 개선 제안 생성"""
        suggestions = []

        # 신뢰도 분석
        confidences = [p['confidence'] for p in pattern_data]
        avg_confidence = sum(confidences) / len(confidences)

        if avg_confidence < 0.6:
            suggestions.append("패턴 정규식 개선 필요")

        if avg_confidence > 0.8:
            suggestions.append("우수한 템플릿 - 다른 템플릿의 기준으로 활용 가능")

        # 바운딩 박스 정확도 분석
        bbox_accuracies = [p['bbox_accuracy'] for p in pattern_data]
        avg_bbox_accuracy = sum(bbox_accuracies) / len(bbox_accuracies)

        if avg_bbox_accuracy < 0.5:
            suggestions.append("바운딩 박스 위치 추정 알고리즘 개선 필요")

        # 필드 일관성 분석
        field_sets = [set(p['matched_fields']) for p in pattern_data]
        if len(set(len(fs) for fs in field_sets)) > 1:
            suggestions.append("추출되는 필드 수가 문서마다 다름 - 템플릿 견고성 개선 필요")

        return suggestions