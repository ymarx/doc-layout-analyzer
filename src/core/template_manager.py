"""
Template Manager - 문서 양식 템플릿 관리 시스템
수동 조정된 주석을 템플릿으로 저장하고 새로운 문서에 적용
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
import logging

from .user_annotations import (
    UserField, FieldType, FieldImportance, DocumentAnnotation,
    UserAnnotationManager, BoundingBox
)

logger = logging.getLogger(__name__)


@dataclass
class DocumentTemplate:
    """문서 템플릿"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    document_type: str = ""  # 기술기준, 작업표준 등
    description: str = ""

    # 템플릿 필드들
    template_fields: List[UserField] = field(default_factory=list)

    # 패턴 매칭 규칙
    header_patterns: List[str] = field(default_factory=list)
    section_patterns: List[str] = field(default_factory=list)
    identifier_patterns: List[str] = field(default_factory=list)

    # 통계 정보
    source_documents: List[str] = field(default_factory=list)
    usage_count: int = 0
    success_rate: float = 0.0

    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'id': self.id,
            'name': self.name,
            'document_type': self.document_type,
            'description': self.description,
            'template_fields': [field.to_dict() for field in self.template_fields],
            'header_patterns': self.header_patterns,
            'section_patterns': self.section_patterns,
            'identifier_patterns': self.identifier_patterns,
            'source_documents': self.source_documents,
            'usage_count': self.usage_count,
            'success_rate': self.success_rate,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocumentTemplate':
        """딕셔너리에서 생성"""
        template_data = data.copy()

        # UserField 리스트 변환
        if 'template_fields' in template_data:
            template_data['template_fields'] = [
                UserField.from_dict(field_data)
                for field_data in template_data['template_fields']
            ]

        return cls(**template_data)


@dataclass
class TemplateMatchResult:
    """템플릿 매칭 결과"""
    template_id: str
    template_name: str
    confidence: float  # 0.0 ~ 1.0
    matched_fields: List[Tuple[str, str, float]]  # (template_field_id, content, confidence)
    unmatched_fields: List[str]  # template_field_id
    suggested_positions: Dict[str, BoundingBox]  # field_id -> bbox
    match_details: Dict[str, Any] = field(default_factory=dict)


class TemplateManager:
    """문서 템플릿 관리자"""

    def __init__(self, templates_dir: Path):
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(exist_ok=True)
        self.templates: Dict[str, DocumentTemplate] = {}
        self.load_templates()

    def load_templates(self):
        """저장된 템플릿들 로드"""
        for template_file in self.templates_dir.glob("*.json"):
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)
                template = DocumentTemplate.from_dict(template_data)
                self.templates[template.id] = template
                logger.info(f"템플릿 로드: {template.name} ({template.id[:8]})")
            except Exception as e:
                logger.error(f"템플릿 로드 실패 {template_file}: {e}")

    def save_template(self, template: DocumentTemplate):
        """템플릿 저장"""
        template.updated_at = datetime.now().isoformat()
        template_file = self.templates_dir / f"{template.id}.json"

        with open(template_file, 'w', encoding='utf-8') as f:
            json.dump(template.to_dict(), f, ensure_ascii=False, indent=2)

        self.templates[template.id] = template
        logger.info(f"템플릿 저장: {template.name}")

    def create_template_from_annotation_data(self, annotation_data: Dict[str, Any],
                                           template_name: str, description: str = "") -> DocumentTemplate:
        """주석 데이터에서 직접 템플릿 생성"""
        from ..core.user_annotations import UserField, BoundingBox, FieldType, FieldImportance

        template = DocumentTemplate(
            name=template_name,
            description=description,
            document_type="기술기준",  # annotation_data에서 추출 가능하면 사용
            template_fields=[]
        )

        # 필드 변환
        for field_data in annotation_data.get('fields', []):
            # BoundingBox 변환
            bbox = None
            if 'bbox' in field_data and field_data['bbox']:
                bbox_data = field_data['bbox']
                bbox = BoundingBox(
                    x1=float(bbox_data['x1']),
                    y1=float(bbox_data['y1']),
                    x2=float(bbox_data['x2']),
                    y2=float(bbox_data['y2']),
                    page=int(bbox_data['page'])
                )

            # UserField 생성
            field = UserField(
                id=field_data.get('id', ''),
                name=field_data.get('name', ''),
                field_type=FieldType(field_data.get('field_type', 'text')),
                bbox=bbox,
                importance=FieldImportance(field_data.get('importance', 'medium')),
                description=field_data.get('description', ''),
                validation_rules=field_data.get('validation_rules', {}),
                relationships=field_data.get('relationships', []),
                metadata=field_data.get('metadata', {}),
                created_at=field_data.get('created_at', '')
            )
            template.template_fields.append(field)

        return template

    def create_template_from_annotation(self,
                                       annotation: DocumentAnnotation,
                                       template_name: str,
                                       description: str = "") -> DocumentTemplate:
        """주석에서 템플릿 생성"""

        # 문서 타입 추론
        doc_type = self._infer_document_type(annotation)

        # 패턴 추출
        header_patterns = self._extract_header_patterns(annotation)
        section_patterns = self._extract_section_patterns(annotation)
        identifier_patterns = self._extract_identifier_patterns(annotation)

        template = DocumentTemplate(
            name=template_name,
            document_type=doc_type,
            description=description,
            template_fields=annotation.fields.copy(),
            header_patterns=header_patterns,
            section_patterns=section_patterns,
            identifier_patterns=identifier_patterns,
            source_documents=[annotation.document_path]
        )

        self.save_template(template)
        return template

    def _infer_document_type(self, annotation: DocumentAnnotation) -> str:
        """주석에서 문서 타입 추론"""
        path = annotation.document_path.lower()

        if '기술기준' in path or any('기술기준' in f.description for f in annotation.fields):
            return "기술기준"
        elif '작업표준' in path:
            return "작업표준"
        elif '절차서' in path:
            return "절차서"
        else:
            return "일반문서"

    def _extract_header_patterns(self, annotation: DocumentAnnotation) -> List[str]:
        """헤더 패턴 추출"""
        patterns = []
        for field in annotation.fields:
            if field.field_type == FieldType.HEADER or 'header' in field.name.lower():
                if field.description:
                    patterns.append(field.description)
        return patterns

    def _extract_section_patterns(self, annotation: DocumentAnnotation) -> List[str]:
        """섹션 패턴 추출"""
        patterns = []
        for field in annotation.fields:
            if '항목' in field.name or field.field_type == FieldType.TITLE:
                # 번호 매겨진 패턴 추출
                if '번호 매겨진 항목:' in field.description:
                    pattern = field.description.replace('번호 매겨진 항목: ', '')
                    patterns.append(pattern)
        return patterns

    def _extract_identifier_patterns(self, annotation: DocumentAnnotation) -> List[str]:
        """식별자 패턴 추출"""
        patterns = []
        for field in annotation.fields:
            if field.field_type == FieldType.CODE:
                if 'TP-' in field.description:
                    patterns.append(r'TP-\d{3}-\d{3}-\d{3}')
                patterns.append(field.description)
        return patterns

    def find_best_template(self,
                          document_content: Dict[str, Any],
                          doc_type: str = None,
                          confidence_threshold: float = 0.3) -> Optional[TemplateMatchResult]:
        """문서에 가장 적합한 템플릿 찾기"""

        if not self.templates:
            return None

        best_match = None
        best_confidence = 0.0

        for template in self.templates.values():
            # 문서 타입 필터링
            if doc_type and template.document_type != doc_type:
                continue

            match_result = self._match_template(template, document_content)

            if match_result.confidence > best_confidence:
                best_confidence = match_result.confidence
                best_match = match_result

        return best_match if best_confidence > confidence_threshold else None

    def _match_template(self,
                       template: DocumentTemplate,
                       document_content: Dict[str, Any]) -> TemplateMatchResult:
        """템플릿과 문서 매칭"""

        total_fields = len(template.template_fields)
        matched_fields = []
        unmatched_fields = []
        suggested_positions = {}

        # 문서 텍스트 추출
        doc_text = self._extract_document_text(document_content)

        for field in template.template_fields:
            match_confidence, content, bbox = self._match_field(field, doc_text, document_content)

            if match_confidence > 0.5:
                matched_fields.append((field.id, content, match_confidence))
                if bbox:
                    suggested_positions[field.id] = bbox
            else:
                unmatched_fields.append(field.id)

        # 전체 매칭 신뢰도 계산
        if total_fields > 0:
            confidence = len(matched_fields) / total_fields
        else:
            confidence = 0.0

        # 패턴 매칭 보너스
        pattern_bonus = self._calculate_pattern_bonus(template, doc_text)
        confidence = min(1.0, confidence + pattern_bonus)

        return TemplateMatchResult(
            template_id=template.id,
            template_name=template.name,
            confidence=confidence,
            matched_fields=matched_fields,
            unmatched_fields=unmatched_fields,
            suggested_positions=suggested_positions,
            match_details={
                'pattern_bonus': pattern_bonus,
                'field_matches': len(matched_fields),
                'total_fields': total_fields
            }
        )

    def _extract_document_text(self, document_content: Dict[str, Any]) -> str:
        """문서에서 텍스트 추출"""
        texts = []

        # DocJSON 형식에서 텍스트 추출
        if 'sections' in document_content:
            for section in document_content['sections']:
                for block in section.get('blocks', []):
                    content = block.get('content', {})
                    if 'text' in content:
                        texts.append(content['text'])

        return ' '.join(texts)

    def _match_field(self,
                    field: UserField,
                    doc_text: str,
                    document_content: Dict[str, Any]) -> Tuple[float, str, Optional[BoundingBox]]:
        """개별 필드 매칭"""

        # 필드 설명에서 패턴 추출
        if field.description:
            if '번호 매겨진 항목:' in field.description:
                # 번호 매겨진 항목 매칭
                pattern = field.description.replace('번호 매겨진 항목: ', '').strip()
                if pattern in doc_text:
                    bbox = self._find_text_position(pattern, document_content)
                    return 0.9, pattern, bbox

            elif '자동 감지:' in field.description:
                # 자동 감지된 내용 매칭
                content = field.description.replace('자동 감지: ', '').strip()
                if content[:20] in doc_text:  # 처음 20글자로 매칭
                    bbox = self._find_text_position(content[:50], document_content)
                    return 0.8, content, bbox

        # 필드 이름 기반 매칭
        field_keywords = {
            '문서번호': ['TP-', '문서번호'],
            '제목': ['기준', '표준', '절차'],
            '적용범위': ['적용범위', '범위'],
            '목적': ['목적', '목표'],
            '작성자': ['작성자', '담당자']
        }

        for keyword_group in field_keywords.get(field.name, []):
            if any(keyword in doc_text for keyword in keyword_group):
                bbox = self._find_text_position(keyword_group[0], document_content)
                return 0.7, keyword_group[0], bbox

        return 0.0, "", None

    def _find_text_position(self,
                           text: str,
                           document_content: Dict[str, Any]) -> Optional[BoundingBox]:
        """텍스트의 위치 찾기"""

        if 'sections' in document_content:
            for section in document_content['sections']:
                for block in section.get('blocks', []):
                    content = block.get('content', {})
                    if 'text' in content and text in content['text']:
                        bbox_data = block.get('bbox')
                        if bbox_data:
                            return BoundingBox(
                                bbox_data.get('x1', 0),
                                bbox_data.get('y1', 0),
                                bbox_data.get('x2', 100),
                                bbox_data.get('y2', 20),
                                bbox_data.get('page', 1)
                            )

        return None

    def _calculate_pattern_bonus(self, template: DocumentTemplate, doc_text: str) -> float:
        """패턴 매칭 보너스 계산"""
        bonus = 0.0

        # 헤더 패턴 매칭
        for pattern in template.header_patterns:
            if pattern in doc_text:
                bonus += 0.1

        # 섹션 패턴 매칭
        section_matches = 0
        for pattern in template.section_patterns:
            if pattern in doc_text:
                section_matches += 1

        if template.section_patterns:
            bonus += 0.2 * (section_matches / len(template.section_patterns))

        # 식별자 패턴 매칭
        import re
        for pattern in template.identifier_patterns:
            if re.search(pattern, doc_text):
                bonus += 0.1

        return min(0.3, bonus)  # 최대 30% 보너스

    def apply_template_to_document(self,
                                  template_result: TemplateMatchResult,
                                  document_content: Dict[str, Any]) -> DocumentAnnotation:
        """템플릿을 문서에 적용하여 주석 생성"""

        template = self.templates[template_result.template_id]

        # 새 주석 생성
        annotation = DocumentAnnotation(
            document_id=str(uuid.uuid4()),
            document_path="new_document.docx",
            template_id=template.id
        )

        # 매칭된 필드들 추가 및 콘텐츠 추출
        for field in template.template_fields:
            new_field = UserField(
                name=field.name,
                field_type=field.field_type,
                importance=field.importance,
                description=field.description,
                validation_rules=field.validation_rules.copy()
            )

            # 제안된 위치가 있으면 적용
            if field.id in template_result.suggested_positions:
                new_field.bbox = template_result.suggested_positions[field.id]
            else:
                # 기본 위치 사용
                new_field.bbox = field.bbox

            annotation.fields.append(new_field)

            # 🔥 실제 콘텐츠 추출 로직 추가
            extracted_text = self._extract_field_content(field, document_content)
            if extracted_text:
                annotation.extracted_values[new_field.id] = extracted_text
                logger.info(f"필드 '{field.name}'에서 추출: {extracted_text[:50]}...")

        # 템플릿 사용 통계 업데이트
        template.usage_count += 1
        self.save_template(template)

        logger.info(f"템플릿 적용 완료: {len(annotation.fields)}개 필드, {len(annotation.extracted_values)}개 값 추출")
        return annotation

    def _extract_field_content(self, field: UserField, document_content: Dict[str, Any]) -> str:
        """필드에 해당하는 콘텐츠를 문서에서 추출"""

        # 1. 필드 이름/설명 기반 키워드 매칭
        keywords = self._get_field_keywords(field)

        # 2. 문서의 모든 텍스트 블록에서 검색
        extracted_texts = []

        if 'sections' in document_content:
            for section in document_content['sections']:
                for block in section.get('blocks', []):
                    content = block.get('content', {})
                    if 'text' in content:
                        text = content['text'].strip()

                        # 키워드 매칭으로 관련 텍스트 찾기
                        for keyword in keywords:
                            if keyword.lower() in text.lower():
                                # 키워드 다음의 텍스트 추출
                                extracted = self._extract_text_after_keyword(text, keyword)
                                if extracted:
                                    extracted_texts.append(extracted)
                                    logger.debug(f"키워드 '{keyword}'로 추출: {extracted}")

        # 3. 가장 적절한 텍스트 선택
        if extracted_texts:
            # 가장 긴 텍스트를 선택 (더 많은 정보를 포함할 가능성)
            return max(extracted_texts, key=len)

        # 4. 키워드 매칭 실패시 필드 설명에서 텍스트 추출 시도
        if field.description and '자동 감지:' in field.description:
            desc_text = field.description.split('자동 감지:')[1].strip()
            if desc_text:
                return desc_text[:200]  # 최대 200자

        return ""

    def _get_field_keywords(self, field: UserField) -> List[str]:
        """필드의 검색 키워드 생성"""
        keywords = []

        # 필드 이름에서 키워드 추출
        if field.name:
            # "항목_1" -> ["1.", "적용범위"]
            if field.name.startswith('항목_'):
                number = field.name.split('_')[1]
                keywords.extend([f"{number}.", f"{number}"])

            # "제목_또는_주요내용" -> ["제목", "주요내용"]
            if '제목' in field.name:
                keywords.extend(['제목', '목적', '적용범위', '기준'])

        # 필드 설명에서 키워드 추출
        if field.description:
            # "번호 매겨진 항목: 1. 적용범위" -> ["1.", "적용범위"]
            if ':' in field.description:
                desc_part = field.description.split(':')[1].strip()
                keywords.append(desc_part)

            # 일반적인 기술기준 키워드
            tech_keywords = ['적용범위', '목적', '기준', '방법', '절차', '주의사항', '참고사항']
            for keyword in tech_keywords:
                if keyword in field.description:
                    keywords.append(keyword)

        # 중복 제거 및 정리
        return list(set([k for k in keywords if k and len(k) > 1]))

    def _extract_text_after_keyword(self, text: str, keyword: str) -> str:
        """키워드 다음의 텍스트 추출"""
        text_lower = text.lower()
        keyword_lower = keyword.lower()

        if keyword_lower in text_lower:
            # 키워드 위치 찾기
            start_idx = text_lower.find(keyword_lower)
            if start_idx != -1:
                # 키워드 다음부터 텍스트 추출
                after_keyword = text[start_idx + len(keyword):].strip()

                # 첫 번째 문장이나 적절한 길이까지 추출
                if after_keyword:
                    # 문장 구분자로 분할
                    sentences = after_keyword.replace('.', '.\n').replace('다.', '다.\n').split('\n')
                    if sentences and sentences[0].strip():
                        return sentences[0].strip()[:150]  # 최대 150자

        return ""

    def get_template_stats(self) -> Dict[str, Any]:
        """템플릿 통계 정보"""
        if not self.templates:
            return {"total_templates": 0}

        stats = {
            "total_templates": len(self.templates),
            "by_type": {},
            "most_used": None,
            "avg_success_rate": 0.0
        }

        for template in self.templates.values():
            doc_type = template.document_type
            stats["by_type"][doc_type] = stats["by_type"].get(doc_type, 0) + 1

        # 가장 많이 사용된 템플릿
        most_used = max(self.templates.values(), key=lambda t: t.usage_count)
        stats["most_used"] = {
            "name": most_used.name,
            "usage_count": most_used.usage_count,
            "success_rate": most_used.success_rate
        }

        # 평균 성공률
        if self.templates:
            avg_success = sum(t.success_rate for t in self.templates.values()) / len(self.templates)
            stats["avg_success_rate"] = avg_success

        return stats

    def list_templates(self, document_type: str = None) -> List[Dict[str, Any]]:
        """템플릿 목록 조회"""
        templates = list(self.templates.values())

        if document_type:
            templates = [t for t in templates if t.document_type == document_type]

        return [
            {
                "id": t.id,
                "name": t.name,
                "document_type": t.document_type,
                "field_count": len(t.template_fields),
                "usage_count": t.usage_count,
                "success_rate": t.success_rate,
                "created_at": t.created_at
            }
            for t in templates
        ]

    def match_document(self, docjson, confidence_threshold: float = 0.5) -> Optional[TemplateMatchResult]:
        """문서와 템플릿 매칭"""
        # DocJSON을 dict로 변환 (필요한 경우)
        if hasattr(docjson, 'to_dict'):
            document_content = docjson.to_dict()
        else:
            document_content = docjson

        return self.find_best_template(document_content, confidence_threshold=confidence_threshold)

    def delete_template(self, template_id: str) -> bool:
        """템플릿 삭제"""
        if template_id not in self.templates:
            return False

        template = self.templates[template_id]
        template_file = self.templates_dir / f"{template_id}.json"

        try:
            if template_file.exists():
                template_file.unlink()
            del self.templates[template_id]
            logger.info(f"템플릿 삭제: {template.name}")
            return True
        except Exception as e:
            logger.error(f"템플릿 삭제 실패: {e}")
            return False