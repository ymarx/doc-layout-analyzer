"""
문서 템플릿 시스템
Document Template System for flexible parsing
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

class ElementType(Enum):
    """문서 요소 유형"""
    FIXED = "fixed"           # 고정 요소 (문서번호, 날짜 등)
    STRUCTURAL = "structural" # 구조 요소 (제목, 번호 체계)
    CONTENT = "content"       # 내용 요소 (자유 텍스트)
    TABLE = "table"          # 표 요소
    DIAGRAM = "diagram"      # 다이어그램 요소

class ExtractionMethod(Enum):
    """추출 방법"""
    REGEX = "regex"           # 정규식 패턴
    POSITION = "position"     # 위치 기반
    PATTERN = "pattern"       # 패턴 인식
    INFERENCE = "inference"   # AI 추론

@dataclass
class TemplateElement:
    """템플릿 요소 정의"""
    name: str                          # 요소 이름
    element_type: ElementType          # 요소 유형
    extraction_method: ExtractionMethod # 추출 방법
    patterns: List[str] = field(default_factory=list)  # 패턴 목록
    positions: Dict[str, Any] = field(default_factory=dict)  # 위치 정보
    confidence_threshold: float = 0.7   # 신뢰도 임계값
    required: bool = True              # 필수 여부
    alternatives: List[str] = field(default_factory=list)  # 대안 패턴

@dataclass
class DocumentTemplate:
    """문서 템플릿"""
    template_id: str
    name: str
    description: str
    document_type: str
    version: str
    elements: List[TemplateElement] = field(default_factory=list)
    hierarchy_patterns: Dict[str, str] = field(default_factory=dict)
    metadata_mapping: Dict[str, str] = field(default_factory=dict)

class TemplateManager:
    """템플릿 관리자"""

    def __init__(self, templates_dir: str = None):
        if templates_dir is None:
            # 현재 파일 위치에서 상대 경로로 설정
            current_dir = Path(__file__).parent.parent.parent
            templates_dir = current_dir / "templates" / "definitions"
        self.templates_dir = Path(templates_dir)
        self.templates: Dict[str, DocumentTemplate] = {}
        self.load_templates()

    def load_templates(self):
        """템플릿 파일들 로드"""
        if not self.templates_dir.exists():
            self.templates_dir.mkdir(parents=True, exist_ok=True)
            self.create_default_templates()

        for template_file in self.templates_dir.glob("*.json"):
            template = self.load_template(template_file)
            if template:
                self.templates[template.template_id] = template

    def load_template(self, file_path: Path) -> Optional[DocumentTemplate]:
        """단일 템플릿 파일 로드"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            elements = []
            for elem_data in data.get('elements', []):
                element = TemplateElement(
                    name=elem_data['name'],
                    element_type=ElementType(elem_data['element_type']),
                    extraction_method=ExtractionMethod(elem_data['extraction_method']),
                    patterns=elem_data.get('patterns', []),
                    positions=elem_data.get('positions', {}),
                    confidence_threshold=elem_data.get('confidence_threshold', 0.7),
                    required=elem_data.get('required', True),
                    alternatives=elem_data.get('alternatives', [])
                )
                elements.append(element)

            return DocumentTemplate(
                template_id=data['template_id'],
                name=data['name'],
                description=data['description'],
                document_type=data['document_type'],
                version=data['version'],
                elements=elements,
                hierarchy_patterns=data.get('hierarchy_patterns', {}),
                metadata_mapping=data.get('metadata_mapping', {})
            )
        except Exception as e:
            print(f"템플릿 로드 실패 {file_path}: {e}")
            return None

    def create_default_templates(self):
        """기본 템플릿들 생성"""
        # 기술기준서 템플릿
        technical_standard_template = {
            "template_id": "technical_standard_v1",
            "name": "기술기준서",
            "description": "제철소 기술기준서 표준 양식",
            "document_type": "docx",
            "version": "1.0",
            "elements": [
                {
                    "name": "document_number",
                    "element_type": "fixed",
                    "extraction_method": "regex",
                    "patterns": [
                        r"TP-\d{3}-\d{3}-\d{3}",
                        r"[A-Z]{2,3}-\d{3}-\d{3}-\d{3}",
                        r"문서번호[:\s]*([A-Z0-9-]+)"
                    ],
                    "required": True,
                    "confidence_threshold": 0.9
                },
                {
                    "name": "effective_date",
                    "element_type": "fixed",
                    "extraction_method": "regex",
                    "patterns": [
                        r"\d{2}\.\d{2}\.\d{2}",
                        r"\d{4}-\d{2}-\d{2}",
                        r"시행일[:\s]*(\d{2}\.\d{2}\.\d{2})"
                    ],
                    "required": True
                },
                {
                    "name": "revision",
                    "element_type": "fixed",
                    "extraction_method": "regex",
                    "patterns": [
                        r"Rev\.(\d+)",
                        r"개정[:\s]*(\d+)",
                        r"버전[:\s]*(\d+)"
                    ],
                    "required": False
                },
                {
                    "name": "author",
                    "element_type": "fixed",
                    "extraction_method": "regex",
                    "patterns": [
                        r"작성자[:\s]*([가-힣\s]+)",
                        r"작성[:\s]*([가-힣\s]+)"
                    ],
                    "required": False
                },
                {
                    "name": "section_headers",
                    "element_type": "structural",
                    "extraction_method": "pattern",
                    "patterns": [
                        r"^\d+\.\s+(.+)",
                        r"^\d+\.\d+\s+(.+)",
                        r"^\d+\.\d+\.\d+\s+(.+)"
                    ],
                    "required": True
                },
                {
                    "name": "process_flow",
                    "element_type": "diagram",
                    "extraction_method": "inference",
                    "patterns": [
                        r"[①②③④⑤⑥⑦⑧⑨⑩]",
                        r"\d+\.\s*[^→]*→",
                        r"단계|수순|흐름|프로세스"
                    ],
                    "required": False
                }
            ],
            "hierarchy_patterns": {
                "level_1": r"^\d+\.\s+(.+)",
                "level_2": r"^\d+\.\d+\s+(.+)",
                "level_3": r"^\d+\.\d+\.\d+\s+(.+)"
            },
            "metadata_mapping": {
                "title": "제목",
                "department": "부서",
                "process": "공정"
            }
        }

        # 템플릿 파일 저장
        template_path = self.templates_dir / "technical_standard_v1.json"
        with open(template_path, 'w', encoding='utf-8') as f:
            json.dump(technical_standard_template, f, ensure_ascii=False, indent=2)

    def match_template(self, document_content: Dict[str, Any]) -> Tuple[str, float]:
        """문서에 가장 적합한 템플릿 찾기"""
        best_match = None
        best_score = 0.0

        for template_id, template in self.templates.items():
            score = self._calculate_template_score(document_content, template)
            if score > best_score:
                best_score = score
                best_match = template_id

        return best_match, best_score

    def _calculate_template_score(self, content: Dict[str, Any], template: DocumentTemplate) -> float:
        """템플릿 매칭 점수 계산"""
        total_score = 0.0
        total_weight = 0.0

        # 텍스트 콘텐츠 결합
        all_text = ""
        if 'paragraphs' in content:
            all_text += " ".join([p.get('text', '') if isinstance(p, dict) else str(p) for p in content['paragraphs']])
        if 'headers_footers' in content:
            for hf in content['headers_footers']:
                if isinstance(hf, dict):
                    all_text += " " + hf.get('text', '')
                else:
                    all_text += " " + str(hf)

        for element in template.elements:
            weight = 2.0 if element.required else 1.0
            total_weight += weight

            element_score = self._match_element(all_text, element)
            total_score += element_score * weight

        return total_score / total_weight if total_weight > 0 else 0.0

    def _match_element(self, text: str, element: TemplateElement) -> float:
        """개별 요소 매칭 점수"""
        if element.extraction_method == ExtractionMethod.REGEX:
            for pattern in element.patterns:
                if re.search(pattern, text):
                    return 1.0
            return 0.0
        elif element.extraction_method == ExtractionMethod.PATTERN:
            # 패턴 기반 매칭 (부분 점수 가능)
            matches = 0
            for pattern in element.patterns:
                if re.search(pattern, text, re.MULTILINE):
                    matches += 1
            return min(1.0, matches / len(element.patterns)) if element.patterns else 0.0
        else:
            # 추론 기반은 기본값
            return 0.5

    def get_template(self, template_id: str) -> Optional[DocumentTemplate]:
        """템플릿 ID로 템플릿 가져오기"""
        return self.templates.get(template_id)

    def extract_elements(self, document_content: Dict[str, Any], template_id: str) -> Dict[str, Any]:
        """템플릿 기반 요소 추출"""
        template = self.get_template(template_id)
        if not template:
            return {}

        # 텍스트 콘텐츠 결합
        all_text = ""
        paragraphs = []

        if 'paragraphs' in document_content:
            paragraphs = document_content['paragraphs']
            all_text += " ".join([p.get('text', '') if isinstance(p, dict) else str(p) for p in paragraphs])

        if 'headers_footers' in document_content:
            for hf in document_content['headers_footers']:
                if isinstance(hf, dict):
                    all_text += " " + hf.get('text', '')
                else:
                    all_text += " " + str(hf)

        extracted = {}

        for element in template.elements:
            value = self._extract_element_value(all_text, paragraphs, element)
            if value:
                extracted[element.name] = value

        return extracted

    def _extract_element_value(self, text: str, paragraphs: List[Dict], element: TemplateElement) -> Any:
        """개별 요소 값 추출"""
        if element.extraction_method == ExtractionMethod.REGEX:
            for pattern in element.patterns:
                match = re.search(pattern, text)
                if match:
                    return match.group(1) if match.groups() else match.group(0)

        elif element.extraction_method == ExtractionMethod.PATTERN:
            if element.element_type == ElementType.STRUCTURAL:
                # 구조적 요소 (제목, 번호 체계)
                matches = []
                for para in paragraphs:
                    para_text = para.get('text', '') if isinstance(para, dict) else str(para)
                    for pattern in element.patterns:
                        match = re.search(pattern, para_text)
                        if match:
                            matches.append({
                                'text': para_text,
                                'match': match.group(1) if match.groups() else match.group(0),
                                'level': self._determine_hierarchy_level(para_text)
                            })
                return matches

        return None

    def _determine_hierarchy_level(self, text: str) -> int:
        """계층 레벨 결정"""
        if re.match(r'^\d+\.\d+\.\d+', text):
            return 3
        elif re.match(r'^\d+\.\d+', text):
            return 2
        elif re.match(r'^\d+\.', text):
            return 1
        return 0

# 전역 템플릿 매니저 인스턴스
template_manager = TemplateManager()