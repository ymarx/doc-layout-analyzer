"""
User Annotations - 사용자 정의 바운딩 박스 및 의미 주석 시스템
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum

from .docjson import BoundingBox


class FieldType(Enum):
    """필드 타입 정의"""
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    CODE = "code"  # 기술 코드, 부품 번호 등
    TITLE = "title"
    HEADER = "header"
    FOOTER = "footer"
    SIGNATURE = "signature"
    CHECKBOX = "checkbox"
    TABLE_CELL = "table_cell"
    DIAGRAM = "diagram"
    REFERENCE = "reference"
    VERSION = "version"
    STATUS = "status"
    CUSTOM = "custom"


class FieldImportance(Enum):
    """필드 중요도"""
    CRITICAL = "critical"      # 핵심 정보 (문서 번호, 제목 등)
    HIGH = "high"             # 중요 정보
    MEDIUM = "medium"         # 일반 정보
    LOW = "low"              # 참고 정보


@dataclass
class UserField:
    """사용자 정의 필드"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    field_type: FieldType = FieldType.TEXT
    bbox: BoundingBox = None
    importance: FieldImportance = FieldImportance.MEDIUM
    description: str = ""
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    relationships: List[str] = field(default_factory=list)  # 다른 필드 ID와의 관계
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        result = asdict(self)
        if self.bbox:
            result['bbox'] = self.bbox.to_dict()
        result['field_type'] = self.field_type.value
        result['importance'] = self.importance.value
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserField':
        """딕셔너리에서 생성"""
        field_data = data.copy()

        # Enum 변환
        field_data['field_type'] = FieldType(data.get('field_type', 'text'))
        field_data['importance'] = FieldImportance(data.get('importance', 'medium'))

        # BoundingBox 변환
        if 'bbox' in field_data and field_data['bbox']:
            field_data['bbox'] = BoundingBox.from_dict(field_data['bbox'])

        return cls(**field_data)


@dataclass
class DocumentTemplate:
    """문서 템플릿 (공통 양식 정의)"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    document_type: str = ""  # 기술기준, 작업표준 등
    fields: List[UserField] = field(default_factory=list)
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'document_type': self.document_type,
            'fields': [field.to_dict() for field in self.fields],
            'validation_rules': self.validation_rules,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocumentTemplate':
        """딕셔너리에서 생성"""
        template_data = data.copy()
        template_data['fields'] = [UserField.from_dict(field_data)
                                  for field_data in data.get('fields', [])]
        return cls(**template_data)


@dataclass
class DocumentAnnotation:
    """문서별 사용자 주석"""
    document_id: str = ""
    document_path: str = ""
    template_id: Optional[str] = None
    fields: List[UserField] = field(default_factory=list)
    extracted_values: Dict[str, Any] = field(default_factory=dict)  # 필드별 추출된 값
    validation_results: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'document_id': self.document_id,
            'document_path': self.document_path,
            'template_id': self.template_id,
            'fields': [field.to_dict() for field in self.fields],
            'extracted_values': self.extracted_values,
            'validation_results': self.validation_results,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocumentAnnotation':
        """딕셔너리에서 생성"""
        annotation_data = data.copy()
        annotation_data['fields'] = [UserField.from_dict(field_data)
                                   for field_data in data.get('fields', [])]
        return cls(**annotation_data)


class UserAnnotationManager:
    """사용자 주석 관리자"""

    def __init__(self, storage_path: Union[str, Path] = None):
        self.storage_path = Path(storage_path or "annotations")
        self.storage_path.mkdir(exist_ok=True)

        # 저장 경로 설정
        self.templates_path = self.storage_path / "templates"
        self.annotations_path = self.storage_path / "documents"
        self.templates_path.mkdir(exist_ok=True)
        self.annotations_path.mkdir(exist_ok=True)

    def create_template(self, name: str, document_type: str, description: str = "") -> DocumentTemplate:
        """새 템플릿 생성"""
        template = DocumentTemplate(
            name=name,
            document_type=document_type,
            description=description
        )
        self.save_template(template)
        return template

    def save_template(self, template: DocumentTemplate) -> None:
        """템플릿 저장"""
        template.updated_at = datetime.now().isoformat()
        template_file = self.templates_path / f"{template.id}.json"

        with open(template_file, 'w', encoding='utf-8') as f:
            json.dump(template.to_dict(), f, ensure_ascii=False, indent=2)

    def load_template(self, template_id: str) -> Optional[DocumentTemplate]:
        """템플릿 로드"""
        template_file = self.templates_path / f"{template_id}.json"

        if not template_file.exists():
            return None

        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return DocumentTemplate.from_dict(data)
        except Exception:
            return None

    def list_templates(self) -> List[Dict[str, Any]]:
        """템플릿 목록 조회"""
        templates = []

        for template_file in self.templates_path.glob("*.json"):
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                templates.append({
                    'id': data['id'],
                    'name': data['name'],
                    'document_type': data['document_type'],
                    'field_count': len(data.get('fields', [])),
                    'created_at': data.get('created_at', ''),
                    'updated_at': data.get('updated_at', '')
                })
            except Exception:
                continue

        return sorted(templates, key=lambda x: x['updated_at'], reverse=True)

    def create_annotation(self, document_path: str, template_id: str = None) -> DocumentAnnotation:
        """문서 주석 생성"""
        document_id = str(uuid.uuid4())

        annotation = DocumentAnnotation(
            document_id=document_id,
            document_path=document_path,
            template_id=template_id
        )

        # 템플릿이 있으면 필드 복사
        if template_id:
            template = self.load_template(template_id)
            if template:
                annotation.fields = [field for field in template.fields]  # 복사

        self.save_annotation(annotation)
        return annotation

    def save_annotation(self, annotation: DocumentAnnotation) -> None:
        """주석 저장"""
        annotation.updated_at = datetime.now().isoformat()
        annotation_file = self.annotations_path / f"{annotation.document_id}.json"

        with open(annotation_file, 'w', encoding='utf-8') as f:
            json.dump(annotation.to_dict(), f, ensure_ascii=False, indent=2)

    def load_annotation(self, document_id: str) -> Optional[DocumentAnnotation]:
        """주석 로드"""
        annotation_file = self.annotations_path / f"{document_id}.json"

        if not annotation_file.exists():
            return None

        try:
            with open(annotation_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return DocumentAnnotation.from_dict(data)
        except Exception as e:
            print(f"주석 로드 에러 {document_id}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def load_annotation_by_path(self, document_path: str) -> Optional[DocumentAnnotation]:
        """문서 경로로 주석 찾기"""
        for annotation_file in self.annotations_path.glob("*.json"):
            try:
                with open(annotation_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if data.get('document_path') == document_path:
                    return DocumentAnnotation.from_dict(data)
            except Exception:
                continue
        return None

    def add_field_to_annotation(self, document_id: str, field: UserField) -> bool:
        """주석에 필드 추가"""
        annotation = self.load_annotation(document_id)
        if not annotation:
            return False

        annotation.fields.append(field)
        self.save_annotation(annotation)
        return True

    def update_field_value(self, document_id: str, field_id: str, value: Any) -> bool:
        """필드 값 업데이트"""
        annotation = self.load_annotation(document_id)
        if not annotation:
            return False

        annotation.extracted_values[field_id] = value
        self.save_annotation(annotation)
        return True

    def auto_detect_fields(self, docjson_data: Dict[str, Any], document_path: str) -> DocumentAnnotation:
        """DocJSON 데이터에서 자동으로 필드 감지 및 주석 생성"""

        # 새 주석 생성
        annotation = DocumentAnnotation()
        annotation.document_path = document_path
        annotation.document_id = str(uuid.uuid4())
        annotation.fields = []
        annotation.extracted_values = {}

        # 메타데이터에서 필드 추출
        metadata = docjson_data.get('metadata', {})
        self._extract_metadata_fields(annotation, metadata)

        # 섹션에서 필드 추출
        sections = docjson_data.get('sections', [])
        self._extract_section_fields(annotation, sections)

        # 헤더/푸터에서 필드 추출
        headers = docjson_data.get('headers', [])
        footers = docjson_data.get('footers', [])
        self._extract_header_footer_fields(annotation, headers, footers)

        return annotation

    def _calculate_document_hash(self, document_path: str) -> str:
        """문서 해시 계산"""
        import hashlib
        try:
            with open(document_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return str(uuid.uuid4())

    def _extract_metadata_fields(self, annotation: DocumentAnnotation, metadata: Dict[str, Any]) -> None:
        """메타데이터에서 필드 추출"""
        metadata_mappings = {
            'title': (FieldType.TITLE, FieldImportance.CRITICAL),
            'document_number': (FieldType.CODE, FieldImportance.CRITICAL),
            'effective_date': (FieldType.DATE, FieldImportance.HIGH),
            'author': (FieldType.TEXT, FieldImportance.MEDIUM),
            'version': (FieldType.VERSION, FieldImportance.MEDIUM),
            'revision': (FieldType.VERSION, FieldImportance.MEDIUM)
        }

        for key, value in metadata.items():
            if key in metadata_mappings and value:
                field_type, importance = metadata_mappings[key]

                field = UserField(
                    name=key,
                    field_type=field_type,
                    importance=importance,
                    bbox=None,  # 메타데이터는 위치 정보 없음
                    validation_rules=self._get_validation_rules(field_type),
                    description=f"Extracted from metadata: {key}"
                )

                annotation.fields.append(field)
                annotation.extracted_values[field.id] = value

    def _extract_section_fields(self, annotation: DocumentAnnotation, sections: List[Dict[str, Any]]) -> None:
        """섹션에서 필드 추출"""
        for section in sections:
            section_type = section.get('type', 'content')

            for block in section.get('blocks', []):
                content = block.get('content', {})
                text = content.get('text', '')
                bbox_data = block.get('bbox', {})

                if text and self._is_significant_text(text):
                    # 필드 타입 추론
                    field_type = self._infer_field_type(text, section_type)
                    importance = self._infer_importance(text, field_type)

                    # 바운딩박스 생성
                    bbox = None
                    if bbox_data:
                        try:
                            bbox = BoundingBox(
                                x1=float(bbox_data.get('x1', 0)),
                                y1=float(bbox_data.get('y1', 0)),
                                x2=float(bbox_data.get('x2', 100)),
                                y2=float(bbox_data.get('y2', 20)),
                                page=int(bbox_data.get('page', 1))
                            )
                        except (ValueError, TypeError):
                            bbox = None

                    field = UserField(
                        name=self._generate_field_name(text),
                        field_type=field_type,
                        importance=importance,
                        bbox=bbox,
                        validation_rules=self._get_validation_rules(field_type),
                        description=f"Auto-detected from {section_type} section"
                    )

                    annotation.fields.append(field)
                    annotation.extracted_values[field.id] = text[:100]  # 처음 100글자만

    def _extract_header_footer_fields(self, annotation: DocumentAnnotation,
                                    headers: List[Dict[str, Any]],
                                    footers: List[Dict[str, Any]]) -> None:
        """헤더/푸터에서 필드 추출"""
        for header_footer_list, area_type in [(headers, 'header'), (footers, 'footer')]:
            for item in header_footer_list:
                content = item.get('content', '')
                if content and len(content.strip()) > 3:
                    bbox_data = item.get('bbox', {})

                    # 바운딩박스 생성
                    bbox = None
                    if bbox_data:
                        try:
                            bbox = BoundingBox(
                                x1=float(bbox_data.get('x1', 0)),
                                y1=float(bbox_data.get('y1', 0)),
                                x2=float(bbox_data.get('x2', 100)),
                                y2=float(bbox_data.get('y2', 20)),
                                page=int(bbox_data.get('page', 1))
                            )
                        except (ValueError, TypeError):
                            bbox = None

                    field_type = FieldType.HEADER if area_type == 'header' else FieldType.FOOTER

                    field = UserField(
                        name=f"{area_type}_{len([f for f in annotation.fields if f.field_type == field_type]) + 1}",
                        field_type=field_type,
                        importance=FieldImportance.MEDIUM,
                        bbox=bbox,
                        validation_rules=self._get_validation_rules(field_type),
                        description=f"Auto-detected from document {area_type}"
                    )

                    annotation.fields.append(field)
                    annotation.extracted_values[field.id] = content

    def _is_significant_text(self, text: str) -> bool:
        """텍스트가 필드로 의미있는지 판단"""
        text = text.strip()
        return (
            len(text) >= 3 and
            len(text) <= 200 and
            not text.isspace() and
            any(c.isalnum() for c in text)
        )

    def _infer_field_type(self, text: str, section_type: str) -> FieldType:
        """텍스트 내용으로 필드 타입 추론"""
        text_lower = text.lower()

        # 날짜 패턴
        import re
        if re.search(r'\d{2,4}[-/.]\d{1,2}[-/.]\d{1,4}', text):
            return FieldType.DATE

        # 코드 패턴 (문자+숫자+하이픈)
        if re.search(r'[A-Z]{2,4}-\d{3}-\d{3}', text):
            return FieldType.CODE

        # 숫자만 있는 경우
        if text.replace('.', '').replace(',', '').isdigit():
            return FieldType.NUMBER

        # 섹션 타입에 따른 추론
        if section_type == 'title' or '제목' in text_lower:
            return FieldType.TITLE

        # 기본값
        return FieldType.TEXT

    def _infer_importance(self, text: str, field_type: FieldType) -> FieldImportance:
        """텍스트 내용으로 중요도 추론"""
        text_lower = text.lower()

        # 핵심 키워드
        critical_keywords = ['문서번호', 'document', '제목', 'title', '번호']
        if any(keyword in text_lower for keyword in critical_keywords):
            return FieldImportance.CRITICAL

        # 필드 타입별 기본 중요도
        type_importance = {
            FieldType.CODE: FieldImportance.CRITICAL,
            FieldType.TITLE: FieldImportance.CRITICAL,
            FieldType.DATE: FieldImportance.HIGH,
            FieldType.NUMBER: FieldImportance.MEDIUM,
            FieldType.HEADER: FieldImportance.MEDIUM,
            FieldType.FOOTER: FieldImportance.LOW
        }

        return type_importance.get(field_type, FieldImportance.MEDIUM)

    def _generate_field_name(self, text: str) -> str:
        """텍스트에서 필드명 생성"""
        # 간단한 필드명 생성 로직
        text = text.strip()[:30]  # 30글자로 제한

        # 특수문자 제거 및 공백을 언더스코어로 변경
        import re
        field_name = re.sub(r'[^\w\s가-힣]', '', text)
        field_name = re.sub(r'\s+', '_', field_name)

        return field_name or 'auto_field'

    def _get_validation_rules(self, field_type: FieldType) -> Dict[str, Any]:
        """필드 타입별 검증 규칙 반환"""
        rules = {
            FieldType.DATE: {
                'pattern': r'\d{2,4}[-/.]\d{1,2}[-/.]\d{1,4}',
                'required': False
            },
            FieldType.CODE: {
                'pattern': r'[A-Z0-9-]+',
                'min_length': 5,
                'required': True
            },
            FieldType.NUMBER: {
                'type': 'numeric',
                'required': False
            },
            FieldType.TEXT: {
                'max_length': 500,
                'required': False
            }
        }

        return rules.get(field_type, {'required': False})

    def validate_annotation(self, annotation: DocumentAnnotation) -> Dict[str, Any]:
        """주석 검증"""
        results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }

        # 필수 필드 체크
        critical_fields = [f for f in annotation.fields if f.importance == FieldImportance.CRITICAL]
        for field in critical_fields:
            if field.id not in annotation.extracted_values:
                results['errors'].append(f"필수 필드 '{field.name}'에 값이 없습니다.")
                results['valid'] = False

        # 필드별 검증 규칙 적용
        for field in annotation.fields:
            if field.id in annotation.extracted_values:
                value = annotation.extracted_values[field.id]

                # 타입별 검증
                if field.field_type == FieldType.NUMBER:
                    try:
                        float(str(value))
                    except ValueError:
                        results['errors'].append(f"필드 '{field.name}'은 숫자여야 합니다.")
                        results['valid'] = False

                elif field.field_type == FieldType.DATE:
                    # 날짜 형식 검증 (간단한 예시)
                    if not any(char.isdigit() for char in str(value)):
                        results['warnings'].append(f"필드 '{field.name}'의 날짜 형식을 확인하세요.")

        return results

    def get_common_fields_for_type(self, document_type: str) -> List[UserField]:
        """문서 타입별 공통 필드 제안"""
        common_fields = {
            "기술기준": [
                UserField(
                    name="문서번호",
                    field_type=FieldType.CODE,
                    importance=FieldImportance.CRITICAL,
                    description="기술기준 문서의 고유 번호"
                ),
                UserField(
                    name="개정번호",
                    field_type=FieldType.VERSION,
                    importance=FieldImportance.HIGH,
                    description="문서 개정 정보"
                ),
                UserField(
                    name="발행일자",
                    field_type=FieldType.DATE,
                    importance=FieldImportance.HIGH,
                    description="문서 발행 날짜"
                ),
                UserField(
                    name="페이지",
                    field_type=FieldType.TEXT,
                    importance=FieldImportance.MEDIUM,
                    description="페이지 정보"
                )
            ]
        }

        return common_fields.get(document_type, [])