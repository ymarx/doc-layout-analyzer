"""
통합 템플릿 시스템 (Integrated Template System)
기존 시스템들을 통합하여 단기 개선 사항 적용
"""

import json
import logging
import re
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum

# 기존 시스템 import
from .user_annotations import UserField, DocumentTemplate as UserDocumentTemplate, FieldType, FieldImportance
from .docjson import BoundingBox, DocJSON, DocumentMetadata
from ..templates.document_template import (
    TemplateManager, DocumentTemplate, TemplateElement,
    ElementType, ExtractionMethod
)

logger = logging.getLogger(__name__)


class TemplateMatchStrategy(Enum):
    """템플릿 매칭 전략"""
    EXACT_PATTERN = "exact_pattern"      # 정확한 패턴 매칭
    FUZZY_MATCH = "fuzzy_match"          # 유사도 기반 매칭
    POSITION_BASED = "position_based"    # 위치 기반 매칭
    COMBINED = "combined"                # 복합 매칭


@dataclass
class ImprovedTemplateMatch:
    """개선된 템플릿 매칭 결과"""
    template_id: str
    confidence: float
    matched_fields: Dict[str, Any]
    missing_fields: List[str]
    bbox_accuracy: float
    strategy_used: TemplateMatchStrategy
    match_details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentFieldCandidate:
    """문서 필드 후보"""
    text: str
    bbox: BoundingBox
    field_type: FieldType
    confidence: float
    extraction_method: str
    context: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class IntegratedTemplateSystem:
    """통합 템플릿 시스템"""

    def __init__(self,
                 templates_dir: Optional[Path] = None,
                 annotations_dir: Optional[Path] = None):

        # 기존 시스템들 통합
        self.template_manager = TemplateManager(str(templates_dir) if templates_dir else None)
        self.annotations_dir = Path(annotations_dir or "annotations")
        self.annotations_dir.mkdir(exist_ok=True)

        # 개선된 매칭 전략들
        self.matching_strategies = {
            TemplateMatchStrategy.EXACT_PATTERN: self._exact_pattern_match,
            TemplateMatchStrategy.FUZZY_MATCH: self._fuzzy_match,
            TemplateMatchStrategy.POSITION_BASED: self._position_based_match,
            TemplateMatchStrategy.COMBINED: self._combined_match
        }

        # 필드 타입별 패턴 강화
        self.enhanced_patterns = {
            FieldType.CODE: [
                r'TP-\d{3}-\d{3}-\d{3}',           # TP-030-030-050
                r'[A-Z]{2,4}-\d{3}-\d{3}-\d{3}',   # 일반적인 기술코드
                r'문서번호[:\s]*([A-Z0-9-]+)',      # 라벨이 있는 경우
            ],
            FieldType.DATE: [
                r'\d{2}\.\d{2}\.\d{2}',           # 25.07.28
                r'\d{4}-\d{2}-\d{2}',             # 2025-07-28
                r'시행일[:\s]*(\d{2}\.\d{2}\.\d{2})',
                r'날짜[:\s]*(\d{4}-\d{2}-\d{2})',
            ],
            FieldType.VERSION: [
                r'Rev\.?\s*(\d+)',                # Rev. 10, Rev 10
                r'개정[:\s]*(\d+)',               # 개정: 10
                r'버전[:\s]*(\d+)',               # 버전: 10
                r'V\.?\s*(\d+)',                  # V.1, V1
            ],
            FieldType.TITLE: [
                r'^[가-힣\s\(\)]+(?:기준|표준|절차|지침)',  # 기준서 제목 패턴
                r'^[\d\.]+\s+([가-힣\s]+)',               # 번호가 있는 제목
            ]
        }

        # 바운딩 박스 추정을 위한 위치 패턴
        self.position_patterns = {
            'header': {'y_range': (0, 150), 'typical_height': 30},
            'title': {'y_range': (100, 250), 'typical_height': 40},
            'content': {'y_range': (200, 800), 'typical_height': 20},
            'footer': {'y_range': (750, 850), 'typical_height': 25},
        }

    def analyze_document_with_templates(self,
                                      docjson_data: Dict[str, Any],
                                      raw_content: Dict[str, Any]) -> ImprovedTemplateMatch:
        """문서를 템플릿들과 매칭하여 분석"""

        # 1. 모든 템플릿에 대해 매칭 시도
        all_matches = []

        for template_id, template in self.template_manager.templates.items():
            for strategy in self.matching_strategies.keys():
                match_result = self._match_with_strategy(
                    docjson_data, raw_content, template, strategy
                )
                if match_result.confidence > 0.1:  # 최소 임계값
                    all_matches.append(match_result)

        # 2. 최고 매칭 결과 선택
        if not all_matches:
            return self._create_fallback_match(docjson_data, raw_content)

        best_match = max(all_matches, key=lambda x: x.confidence)

        # 3. 매칭 결과 개선
        improved_match = self._improve_match_result(best_match, docjson_data, raw_content)

        logger.info(f"템플릿 매칭 완료: {improved_match.template_id} "
                   f"(신뢰도: {improved_match.confidence:.2%}, "
                   f"전략: {improved_match.strategy_used.value})")

        return improved_match

    def _match_with_strategy(self,
                           docjson_data: Dict[str, Any],
                           raw_content: Dict[str, Any],
                           template: DocumentTemplate,
                           strategy: TemplateMatchStrategy) -> ImprovedTemplateMatch:
        """특정 전략으로 템플릿 매칭"""

        matcher = self.matching_strategies[strategy]
        return matcher(docjson_data, raw_content, template)

    def _exact_pattern_match(self,
                           docjson_data: Dict[str, Any],
                           raw_content: Dict[str, Any],
                           template: DocumentTemplate) -> ImprovedTemplateMatch:
        """정확한 패턴 매칭"""

        # 전체 텍스트 추출
        all_text = self._extract_all_text(docjson_data, raw_content)

        matched_fields = {}
        total_score = 0.0
        total_weight = 0.0

        for element in template.elements:
            weight = 2.0 if element.required else 1.0
            total_weight += weight

            # 강화된 패턴으로 매칭
            field_type = self._element_type_to_field_type(element.element_type)
            patterns = self.enhanced_patterns.get(field_type, element.patterns)

            for pattern in patterns:
                try:
                    match = re.search(pattern, all_text, re.IGNORECASE | re.MULTILINE)
                    if match:
                        matched_fields[element.name] = {
                            'value': match.group(1) if match.groups() else match.group(0),
                            'pattern': pattern,
                            'confidence': 1.0
                        }
                        total_score += weight
                        break
                except re.error:
                    logger.warning(f"잘못된 정규식 패턴: {pattern}")

        confidence = total_score / total_weight if total_weight > 0 else 0.0
        missing_fields = [e.name for e in template.elements if e.name not in matched_fields]

        return ImprovedTemplateMatch(
            template_id=template.template_id,
            confidence=confidence,
            matched_fields=matched_fields,
            missing_fields=missing_fields,
            bbox_accuracy=0.0,  # 정확한 패턴 매칭은 바운딩 박스 없음
            strategy_used=TemplateMatchStrategy.EXACT_PATTERN
        )

    def _fuzzy_match(self,
                    docjson_data: Dict[str, Any],
                    raw_content: Dict[str, Any],
                    template: DocumentTemplate) -> ImprovedTemplateMatch:
        """유사도 기반 매칭"""

        # 섹션별 텍스트 분석
        sections = docjson_data.get('sections', [])
        matched_fields = {}
        total_score = 0.0

        for element in template.elements:
            # 각 섹션에서 유사한 내용 찾기
            best_match = self._find_fuzzy_match_in_sections(element, sections)

            if best_match:
                matched_fields[element.name] = best_match
                total_score += best_match['confidence']

        # 정규화
        confidence = total_score / len(template.elements) if template.elements else 0.0
        missing_fields = [e.name for e in template.elements if e.name not in matched_fields]

        return ImprovedTemplateMatch(
            template_id=template.template_id,
            confidence=confidence * 0.8,  # fuzzy는 약간 패널티
            matched_fields=matched_fields,
            missing_fields=missing_fields,
            bbox_accuracy=0.6,
            strategy_used=TemplateMatchStrategy.FUZZY_MATCH
        )

    def _position_based_match(self,
                            docjson_data: Dict[str, Any],
                            raw_content: Dict[str, Any],
                            template: DocumentTemplate) -> ImprovedTemplateMatch:
        """위치 기반 매칭"""

        sections = docjson_data.get('sections', [])
        blocks = []

        # 모든 블록 수집
        for section in sections:
            for block in section.get('blocks', []):
                if block.get('content', {}).get('text'):
                    blocks.append(block)

        matched_fields = {}
        bbox_scores = []

        for element in template.elements:
            # 필드 타입에 따른 예상 위치에서 검색
            field_type = self._element_type_to_field_type(element.element_type)
            position_candidates = self._find_position_candidates(blocks, field_type)

            if position_candidates:
                best_candidate = max(position_candidates, key=lambda x: x.confidence)
                matched_fields[element.name] = {
                    'value': best_candidate.text,
                    'bbox': best_candidate.bbox.to_dict() if best_candidate.bbox else None,
                    'confidence': best_candidate.confidence
                }
                bbox_scores.append(best_candidate.confidence)

        confidence = sum(bbox_scores) / len(template.elements) if template.elements else 0.0
        bbox_accuracy = sum(bbox_scores) / len(bbox_scores) if bbox_scores else 0.0
        missing_fields = [e.name for e in template.elements if e.name not in matched_fields]

        return ImprovedTemplateMatch(
            template_id=template.template_id,
            confidence=confidence * 0.7,  # 위치 기반은 더 보수적
            matched_fields=matched_fields,
            missing_fields=missing_fields,
            bbox_accuracy=bbox_accuracy,
            strategy_used=TemplateMatchStrategy.POSITION_BASED
        )

    def _combined_match(self,
                       docjson_data: Dict[str, Any],
                       raw_content: Dict[str, Any],
                       template: DocumentTemplate) -> ImprovedTemplateMatch:
        """복합 매칭 - 최고 성능"""

        # 세 가지 전략 모두 실행
        exact_match = self._exact_pattern_match(docjson_data, raw_content, template)
        fuzzy_match = self._fuzzy_match(docjson_data, raw_content, template)
        position_match = self._position_based_match(docjson_data, raw_content, template)

        # 최고 결과들을 조합
        combined_fields = {}

        # 각 필드별로 최고 신뢰도 결과 선택
        all_field_names = set()
        for match in [exact_match, fuzzy_match, position_match]:
            all_field_names.update(match.matched_fields.keys())

        for field_name in all_field_names:
            candidates = []

            if field_name in exact_match.matched_fields:
                candidates.append(('exact', exact_match.matched_fields[field_name]))
            if field_name in fuzzy_match.matched_fields:
                candidates.append(('fuzzy', fuzzy_match.matched_fields[field_name]))
            if field_name in position_match.matched_fields:
                candidates.append(('position', position_match.matched_fields[field_name]))

            if candidates:
                # 신뢰도 가중 평균으로 최고 후보 선택
                best_method, best_result = max(candidates, key=lambda x: x[1].get('confidence', 0))
                best_result['method'] = best_method
                combined_fields[field_name] = best_result

        # 전체 신뢰도 계산 (가중 평균)
        combined_confidence = (
            exact_match.confidence * 0.4 +
            fuzzy_match.confidence * 0.3 +
            position_match.confidence * 0.3
        )

        # 바운딩 박스 정확도
        combined_bbox_accuracy = (
            exact_match.bbox_accuracy * 0.2 +
            fuzzy_match.bbox_accuracy * 0.3 +
            position_match.bbox_accuracy * 0.5
        )

        missing_fields = [e.name for e in template.elements if e.name not in combined_fields]

        return ImprovedTemplateMatch(
            template_id=template.template_id,
            confidence=combined_confidence,
            matched_fields=combined_fields,
            missing_fields=missing_fields,
            bbox_accuracy=combined_bbox_accuracy,
            strategy_used=TemplateMatchStrategy.COMBINED,
            match_details={
                'exact_score': exact_match.confidence,
                'fuzzy_score': fuzzy_match.confidence,
                'position_score': position_match.confidence
            }
        )

    def _extract_all_text(self, docjson_data: Dict[str, Any], raw_content: Dict[str, Any]) -> str:
        """모든 텍스트 추출"""
        text_parts = []

        # DocJSON에서 텍스트 추출
        sections = docjson_data.get('sections', [])
        for section in sections:
            for block in section.get('blocks', []):
                content = block.get('content', {})
                if isinstance(content, dict) and 'text' in content:
                    text_parts.append(content['text'])
                elif isinstance(content, str):
                    text_parts.append(content)

        # raw_content에서 추가 텍스트 추출
        if 'paragraphs' in raw_content:
            for para in raw_content['paragraphs']:
                if isinstance(para, dict):
                    text_parts.append(para.get('text', ''))
                else:
                    text_parts.append(str(para))

        if 'headers_footers' in raw_content:
            for hf in raw_content['headers_footers']:
                if isinstance(hf, dict):
                    text_parts.append(hf.get('text', ''))
                else:
                    text_parts.append(str(hf))

        return ' '.join(text_parts)

    def _element_type_to_field_type(self, element_type: ElementType) -> FieldType:
        """ElementType을 FieldType으로 변환"""
        mapping = {
            ElementType.FIXED: FieldType.TEXT,
            ElementType.STRUCTURAL: FieldType.HEADER,
            ElementType.CONTENT: FieldType.TEXT,
            ElementType.TABLE: FieldType.TABLE_CELL,
            ElementType.DIAGRAM: FieldType.DIAGRAM
        }
        return mapping.get(element_type, FieldType.TEXT)

    def _find_fuzzy_match_in_sections(self, element: TemplateElement, sections: List[Dict]) -> Optional[Dict]:
        """섹션에서 유사 매칭 찾기"""
        # 간단한 키워드 기반 유사도 매칭
        element_keywords = element.name.lower().split()

        best_match = None
        best_score = 0.0

        for section in sections:
            for block in section.get('blocks', []):
                text = block.get('content', {}).get('text', '').lower()

                # 키워드 매칭 점수
                score = sum(1 for keyword in element_keywords if keyword in text)
                score = score / len(element_keywords) if element_keywords else 0.0

                if score > best_score and score > 0.3:  # 최소 임계값
                    best_score = score
                    best_match = {
                        'value': block.get('content', {}).get('text', ''),
                        'confidence': score,
                        'section_id': section.get('id'),
                        'block_id': block.get('id')
                    }

        return best_match

    def _find_position_candidates(self, blocks: List[Dict], field_type: FieldType) -> List[DocumentFieldCandidate]:
        """위치 기반 후보 찾기"""
        candidates = []

        # 필드 타입에 따른 위치 패턴 가져오기
        position_info = self._get_position_info_for_field_type(field_type)

        for block in blocks:
            bbox_data = block.get('bbox', {})
            if not bbox_data:
                continue

            # 바운딩 박스 생성
            try:
                bbox = BoundingBox(
                    x1=float(bbox_data.get('x1', 0)),
                    y1=float(bbox_data.get('y1', 0)),
                    x2=float(bbox_data.get('x2', 100)),
                    y2=float(bbox_data.get('y2', 20)),
                    page=int(bbox_data.get('page', 1))
                )

                # 위치 점수 계산
                position_score = self._calculate_position_score(bbox, position_info)

                if position_score > 0.3:  # 최소 임계값
                    candidate = DocumentFieldCandidate(
                        text=block.get('content', {}).get('text', ''),
                        bbox=bbox,
                        field_type=field_type,
                        confidence=position_score,
                        extraction_method='position_based'
                    )
                    candidates.append(candidate)

            except (ValueError, TypeError):
                continue

        return candidates

    def _get_position_info_for_field_type(self, field_type: FieldType) -> Dict[str, Any]:
        """필드 타입별 위치 정보 반환"""
        mapping = {
            FieldType.CODE: self.position_patterns['header'],
            FieldType.TITLE: self.position_patterns['title'],
            FieldType.DATE: self.position_patterns['header'],
            FieldType.VERSION: self.position_patterns['header'],
            FieldType.HEADER: self.position_patterns['header'],
            FieldType.TEXT: self.position_patterns['content']
        }
        return mapping.get(field_type, self.position_patterns['content'])

    def _calculate_position_score(self, bbox: BoundingBox, position_info: Dict[str, Any]) -> float:
        """위치 점수 계산"""
        y_range = position_info.get('y_range', (0, 1000))
        typical_height = position_info.get('typical_height', 20)

        # Y 위치 점수
        y_center = (bbox.y1 + bbox.y2) / 2
        y_score = 1.0 if y_range[0] <= y_center <= y_range[1] else 0.0

        # 높이 점수
        height = bbox.y2 - bbox.y1
        height_diff = abs(height - typical_height)
        height_score = max(0.0, 1.0 - height_diff / typical_height)

        # 전체 점수 (가중 평균)
        return y_score * 0.7 + height_score * 0.3

    def _improve_match_result(self,
                            match_result: ImprovedTemplateMatch,
                            docjson_data: Dict[str, Any],
                            raw_content: Dict[str, Any]) -> ImprovedTemplateMatch:
        """매칭 결과 개선"""

        # 0. DocJSON 메타데이터에서 누락된 필드 보완
        self._integrate_docjson_metadata(match_result, docjson_data)

        # 1. 바운딩 박스 개선
        improved_fields = {}

        for field_name, field_data in match_result.matched_fields.items():
            improved_field = field_data.copy()

            # 바운딩 박스가 없으면 추정
            if not field_data.get('bbox'):
                estimated_bbox = self._estimate_bbox_for_text(
                    field_data.get('value', ''), docjson_data
                )
                if estimated_bbox:
                    improved_field['bbox'] = estimated_bbox.to_dict()

            improved_fields[field_name] = improved_field

        # 2. 신뢰도 재계산
        improved_confidence = self._recalculate_confidence(match_result, improved_fields)

        # 3. 바운딩박스 정확도 계산
        bbox_accuracy = self._calculate_bbox_accuracy(improved_fields)

        # 결과 업데이트
        match_result.matched_fields = improved_fields
        match_result.confidence = improved_confidence
        match_result.bbox_accuracy = bbox_accuracy

        return match_result

    def _integrate_docjson_metadata(self,
                                  match_result: ImprovedTemplateMatch,
                                  docjson_data: Dict[str, Any]) -> None:
        """DocJSON에서 추출된 메타데이터를 템플릿 매칭 결과에 통합"""

        metadata = docjson_data.get('metadata', {})

        # 메타데이터 필드 매핑
        metadata_mappings = {
            'document_number': ['document_number', 'doc_number'],
            'effective_date': ['effective_date', 'date'],
            'author': ['author', 'creator'],
            'revision': ['version', 'revision'],
            'department': ['department', 'dept']
        }

        for template_field, metadata_keys in metadata_mappings.items():
            # 템플릿에서 누락된 필드만 보완
            if template_field in match_result.missing_fields:
                for key in metadata_keys:
                    if key in metadata and metadata[key]:
                        # 누락된 필드를 매칭된 필드로 이동
                        match_result.matched_fields[template_field] = {
                            'value': metadata[key],
                            'confidence': 0.95,  # 메타데이터는 높은 신뢰도
                            'method': 'docjson_metadata',
                            'bbox': None  # 메타데이터는 위치 정보 없음
                        }
                        match_result.missing_fields.remove(template_field)
                        logger.info(f"DocJSON 메타데이터에서 {template_field} 보완: {metadata[key]}")
                        break

        # 프로세스 플로우 통합
        self._integrate_process_flows(match_result, docjson_data)

    def _integrate_process_flows(self,
                               match_result: ImprovedTemplateMatch,
                               docjson_data: Dict[str, Any]) -> None:
        """프로세스 플로우 데이터를 템플릿 매칭 결과에 통합"""

        # 메타데이터의 source에서 프로세스 플로우 찾기
        sources = docjson_data.get('metadata', {}).get('source', [])

        for source in sources:
            if source.get('type') == 'sequential' and 'steps' in source:
                steps = source['steps']

                # 각 단계를 해당하는 템플릿 필드와 매핑
                for step in steps:
                    sequence = step.get('sequence')
                    field_name = f'process_flow_step_{sequence}'

                    if field_name in match_result.missing_fields:
                        step_title = step.get('title', '')
                        if step_title:
                            match_result.matched_fields[field_name] = {
                                'value': f"{step.get('marker', '')} {step_title}",
                                'confidence': 0.90,
                                'method': 'process_flow',
                                'bbox': None
                            }
                            match_result.missing_fields.remove(field_name)
                            logger.info(f"프로세스 플로우에서 {field_name} 보완: {step_title}")

    def _estimate_bbox_for_text(self, text: str, docjson_data: Dict[str, Any]) -> Optional[BoundingBox]:
        """텍스트에 대한 바운딩 박스 추정 - 개선된 버전"""
        if not text or not text.strip():
            return None

        target_text = text.strip()
        best_match_bbox = None
        best_match_score = 0.0

        sections = docjson_data.get('sections', [])

        for section in sections:
            for block in section.get('blocks', []):
                block_text = block.get('content', {}).get('text', '')

                if not block_text:
                    continue

                # 다양한 매칭 전략 시도
                match_score = self._calculate_text_match_score(target_text, block_text)

                if match_score > best_match_score and match_score >= 0.3:  # 최소 30% 매칭
                    bbox_data = block.get('bbox', {})
                    if bbox_data:
                        try:
                            bbox = BoundingBox(
                                x1=float(bbox_data.get('x1', 0)),
                                y1=float(bbox_data.get('y1', 0)),
                                x2=float(bbox_data.get('x2', 100)),
                                y2=float(bbox_data.get('y2', 20)),
                                page=int(bbox_data.get('page', 1))
                            )
                            best_match_bbox = bbox
                            best_match_score = match_score
                        except (ValueError, TypeError):
                            continue

        # 헤더/푸터에서도 검색
        if not best_match_bbox:
            best_match_bbox = self._search_in_headers_footers(target_text, docjson_data)

        return best_match_bbox

    def _calculate_text_match_score(self, target: str, candidate: str) -> float:
        """텍스트 매칭 점수 계산"""
        if not target or not candidate:
            return 0.0

        target = target.lower().strip()
        candidate = candidate.lower().strip()

        # 완전 매칭
        if target == candidate:
            return 1.0

        # 포함 관계
        if target in candidate:
            return len(target) / len(candidate)

        if candidate in target:
            return len(candidate) / len(target)

        # 부분 문자열 매칭 (첫 N글자)
        if len(target) >= 10:
            prefix = target[:10]
            if prefix in candidate:
                return 0.7

        # 키워드 기반 매칭
        target_words = set(target.split())
        candidate_words = set(candidate.split())

        if target_words and candidate_words:
            common_words = target_words.intersection(candidate_words)
            if common_words:
                return len(common_words) / max(len(target_words), len(candidate_words))

        return 0.0

    def _search_in_headers_footers(self, text: str, docjson_data: Dict[str, Any]) -> Optional[BoundingBox]:
        """헤더/푸터에서 텍스트 검색"""
        headers = docjson_data.get('headers', [])
        footers = docjson_data.get('footers', [])

        for header_footer_list in [headers, footers]:
            for item in header_footer_list:
                content = item.get('content', '')
                if text.lower() in content.lower():
                    bbox_data = item.get('bbox', {})
                    if bbox_data:
                        try:
                            return BoundingBox(
                                x1=float(bbox_data.get('x1', 0)),
                                y1=float(bbox_data.get('y1', 0)),
                                x2=float(bbox_data.get('x2', 100)),
                                y2=float(bbox_data.get('y2', 20)),
                                page=int(bbox_data.get('page', 1))
                            )
                        except (ValueError, TypeError):
                            continue

        return None

    def _recalculate_confidence(self,
                               match_result: ImprovedTemplateMatch,
                               improved_fields: Dict[str, Any]) -> float:
        """개선된 필드 기반 신뢰도 재계산"""

        base_confidence = match_result.confidence

        # 바운딩 박스가 있는 필드 비율
        fields_with_bbox = sum(1 for field in improved_fields.values() if field.get('bbox'))
        bbox_ratio = fields_with_bbox / len(improved_fields) if improved_fields else 0

        # 신뢰도 보정
        bbox_bonus = bbox_ratio * 0.2  # 최대 20% 보너스

        return min(1.0, base_confidence + bbox_bonus)

    def _calculate_bbox_accuracy(self, fields: Dict[str, Any]) -> float:
        """바운딩박스 정확도 계산"""
        if not fields:
            return 0.0

        total_fields = len(fields)
        fields_with_bbox = 0
        bbox_quality_score = 0.0

        for field_data in fields.values():
            bbox_info = field_data.get('bbox')
            if bbox_info:
                fields_with_bbox += 1

                # 바운딩박스 품질 평가
                try:
                    x1 = float(bbox_info.get('x1', 0))
                    y1 = float(bbox_info.get('y1', 0))
                    x2 = float(bbox_info.get('x2', 0))
                    y2 = float(bbox_info.get('y2', 0))

                    # 유효한 좌표인지 확인
                    if x2 > x1 and y2 > y1:
                        # 합리적인 크기인지 확인 (너무 크거나 작지 않은지)
                        width = x2 - x1
                        height = y2 - y1

                        if 5 <= width <= 800 and 5 <= height <= 100:  # 합리적인 텍스트 크기 범위
                            bbox_quality_score += 1.0
                        else:
                            bbox_quality_score += 0.5  # 크기가 이상하지만 좌표는 있음
                    else:
                        bbox_quality_score += 0.2  # 좌표는 있지만 유효하지 않음
                except (ValueError, TypeError):
                    continue

        # 바운딩박스 커버리지와 품질의 가중평균
        coverage_ratio = fields_with_bbox / total_fields
        quality_ratio = bbox_quality_score / total_fields

        # 70% 커버리지, 30% 품질로 계산
        return coverage_ratio * 0.7 + quality_ratio * 0.3

    def _create_fallback_match(self,
                             docjson_data: Dict[str, Any],
                             raw_content: Dict[str, Any]) -> ImprovedTemplateMatch:
        """폴백 매칭 결과 생성"""

        # 기본적인 정보라도 추출
        all_text = self._extract_all_text(docjson_data, raw_content)

        basic_fields = {}

        # 기본 패턴들로 추출 시도
        for field_type, patterns in self.enhanced_patterns.items():
            for pattern in patterns:
                try:
                    match = re.search(pattern, all_text)
                    if match:
                        field_name = f"auto_{field_type.value}"
                        basic_fields[field_name] = {
                            'value': match.group(1) if match.groups() else match.group(0),
                            'confidence': 0.6,
                            'method': 'fallback'
                        }
                        break
                except re.error:
                    continue

        return ImprovedTemplateMatch(
            template_id="fallback_template",
            confidence=0.4 if basic_fields else 0.1,
            matched_fields=basic_fields,
            missing_fields=[],
            bbox_accuracy=0.2,
            strategy_used=TemplateMatchStrategy.EXACT_PATTERN
        )

    def create_user_template_from_match(self,
                                      match_result: ImprovedTemplateMatch,
                                      document_name: str) -> UserDocumentTemplate:
        """매칭 결과에서 사용자 템플릿 생성"""

        user_fields = []

        for field_name, field_data in match_result.matched_fields.items():
            bbox_data = field_data.get('bbox')
            bbox = None

            if bbox_data:
                bbox = BoundingBox(
                    x1=float(bbox_data.get('x1', 0)),
                    y1=float(bbox_data.get('y1', 0)),
                    x2=float(bbox_data.get('x2', 100)),
                    y2=float(bbox_data.get('y2', 20)),
                    page=int(bbox_data.get('page', 1))
                )

            # 필드 타입 결정
            field_type = self._determine_field_type_from_value(field_data.get('value', ''))

            # 중요도 결정
            importance = self._determine_field_importance(field_name)

            user_field = UserField(
                name=field_name,
                field_type=field_type,
                bbox=bbox,
                importance=importance,
                description=f"자동 감지된 {field_name}",
                metadata={
                    'confidence': field_data.get('confidence', 0.5),
                    'extraction_method': field_data.get('method', 'auto'),
                    'template_id': match_result.template_id
                }
            )
            user_fields.append(user_field)

        return UserDocumentTemplate(
            name=f"{document_name}_template",
            description=f"{document_name}에서 자동 생성된 템플릿",
            document_type="기술기준",
            fields=user_fields
        )

    def _determine_field_type_from_value(self, value: str) -> FieldType:
        """값으로부터 필드 타입 결정"""
        value = value.strip()

        if re.match(r'^[A-Z]{2,4}-\d{3}-\d{3}-\d{3}$', value):
            return FieldType.CODE
        elif re.match(r'^\d{2}\.\d{2}\.\d{2}$', value):
            return FieldType.DATE
        elif re.match(r'^Rev\.?\s*\d+$', value):
            return FieldType.VERSION
        elif len(value) < 50 and ('기준' in value or '표준' in value):
            return FieldType.TITLE
        else:
            return FieldType.TEXT

    def _determine_field_importance(self, field_name: str) -> FieldImportance:
        """필드 이름으로부터 중요도 결정"""
        field_name_lower = field_name.lower()

        if any(keyword in field_name_lower for keyword in ['문서번호', 'document_number', 'code']):
            return FieldImportance.CRITICAL
        elif any(keyword in field_name_lower for keyword in ['제목', 'title', '날짜', 'date']):
            return FieldImportance.CRITICAL
        elif any(keyword in field_name_lower for keyword in ['버전', 'version', 'rev']):
            return FieldImportance.HIGH
        else:
            return FieldImportance.MEDIUM

    def save_improved_template(self, user_template: UserDocumentTemplate, output_dir: Path):
        """개선된 템플릿 저장"""
        output_dir.mkdir(exist_ok=True)
        template_file = output_dir / f"{user_template.name}.json"

        with open(template_file, 'w', encoding='utf-8') as f:
            json.dump(user_template.to_dict(), f, ensure_ascii=False, indent=2)

        logger.info(f"개선된 템플릿 저장됨: {template_file}")
        return template_file