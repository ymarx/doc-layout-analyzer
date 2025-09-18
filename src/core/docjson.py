"""
DocJSON Schema and Converter
문서를 표준화된 JSON 형식으로 변환하고 검증하는 모듈
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
import json
import jsonschema
from jsonschema import validate, ValidationError

from ..analyzers.layout_analyzer import LayoutElement, LayoutElementType
from ..extractors.content_extractor import ExtractedContent

logger = logging.getLogger(__name__)


class ContentBlockType(Enum):
    """콘텐츠 블록 타입"""
    PARAGRAPH = "paragraph"
    TITLE = "title"
    HEADING = "heading"
    TABLE = "table"
    DIAGRAM = "diagram"
    IMAGE = "image"
    LIST = "list"
    CAPTION = "caption"
    FOOTNOTE = "footnote"
    FORMULA = "formula"


@dataclass
class BoundingBox:
    """바운딩 박스"""
    x1: float
    y1: float
    x2: float
    y2: float
    page: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x1": float(self.x1),
            "y1": float(self.y1),
            "x2": float(self.x2),
            "y2": float(self.y2),
            "page": int(self.page)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BoundingBox':
        """딕셔너리에서 BoundingBox 생성"""
        return cls(
            x1=float(data["x1"]),
            y1=float(data["y1"]),
            x2=float(data["x2"]),
            y2=float(data["y2"]),
            page=int(data["page"])
        )

    @classmethod
    def from_list(cls, bbox_list: List[float], page: int = 1):
        """리스트에서 바운딩 박스 생성"""
        if len(bbox_list) >= 4:
            return cls(bbox_list[0], bbox_list[1], bbox_list[2], bbox_list[3], page)
        return None


@dataclass
class SemanticInfo:
    """의미적 정보"""
    keywords: List[str] = None
    entities: List[str] = None
    cross_refs: List[str] = None
    topics: List[str] = None
    confidence: float = 0.0

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.entities is None:
            self.entities = []
        if self.cross_refs is None:
            self.cross_refs = []
        if self.topics is None:
            self.topics = []

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SemanticInfo':
        """딕셔너리에서 SemanticInfo 생성"""
        return cls(**data)


@dataclass
class ContentBlock:
    """콘텐츠 블록"""
    id: str = ""
    type: ContentBlockType = ContentBlockType.PARAGRAPH
    page: int = 1
    bbox: Optional[BoundingBox] = None
    content: Dict[str, Any] = field(default_factory=dict)
    semantic: Optional[SemanticInfo] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "type": self.type.value,
            "page": self.page
        }

        if self.bbox:
            result["bbox"] = self.bbox.to_dict()

        if self.content:
            result["content"] = self.content

        if self.semantic:
            result["semantic"] = self.semantic.to_dict()

        if self.metadata:
            result["metadata"] = self.metadata

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContentBlock':
        """딕셔너리에서 ContentBlock 생성"""
        bbox = BoundingBox.from_dict(data['bbox']) if 'bbox' in data and data['bbox'] else None
        semantic = SemanticInfo.from_dict(data['semantic']) if 'semantic' in data and data['semantic'] else None

        return cls(
            id=data.get('id', ''),
            type=ContentBlockType(data.get('type', 'paragraph')),
            page=data.get('page', 1),
            bbox=bbox,
            content=data.get('content', {}),
            semantic=semantic,
            metadata=data.get('metadata', {})
        )


@dataclass
class DocumentSection:
    """문서 섹션"""
    id: str
    path: List[str]
    heading: str
    level: int
    blocks: List[ContentBlock] = None

    def __post_init__(self):
        if self.blocks is None:
            self.blocks = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "path": self.path,
            "heading": self.heading,
            "level": self.level,
            "blocks": [block.to_dict() for block in self.blocks]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocumentSection':
        """딕셔너리에서 DocumentSection 생성"""
        blocks = [ContentBlock.from_dict(block_data) for block_data in data.get('blocks', [])]
        return cls(
            id=data['id'],
            path=data['path'],
            heading=data['heading'],
            level=data['level'],
            blocks=blocks
        )


@dataclass
class DocumentMetadata:
    """문서 메타데이터"""
    title: str
    doc_type: str
    version: Optional[str] = None
    effective_date: Optional[str] = None
    language: List[str] = None
    author: Optional[str] = None
    created: Optional[str] = None
    modified: Optional[str] = None
    source: Optional[Dict[str, Any]] = None
    pages: int = 0
    file_size: int = 0
    # 추가 메타데이터 필드
    document_number: Optional[str] = None
    revision: Optional[str] = None

    def __post_init__(self):
        if self.language is None:
            self.language = ["ko", "en"]
        if not self.created:
            self.created = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocumentMetadata':
        """딕셔너리에서 DocumentMetadata 생성"""
        return cls(**data)


@dataclass
class DocJSON:
    """DocJSON 문서"""
    version: str
    doc_id: str
    metadata: DocumentMetadata
    sections: List[DocumentSection] = None
    embeddings_info: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.sections is None:
            self.sections = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "doc_id": self.doc_id,
            "metadata": self.metadata.to_dict(),
            "sections": [section.to_dict() for section in self.sections],
            "embeddings_info": self.embeddings_info
        }

    def to_json(self, indent: int = 2) -> str:
        """JSON 문자열로 변환"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocJSON':
        """딕셔너리에서 DocJSON 생성"""
        metadata = DocumentMetadata.from_dict(data['metadata']) if 'metadata' in data else None
        sections = [DocumentSection.from_dict(section_data) for section_data in data.get('sections', [])]

        return cls(
            version=data.get('version', '2.0'),
            doc_id=data.get('doc_id', str(uuid.uuid4())),
            metadata=metadata,
            sections=sections,
            embeddings_info=data.get('embeddings_info')
        )


class DocJSONConverter:
    """DocJSON 변환기"""

    DOCJSON_VERSION = "2.0"

    def __init__(self):
        self.schema = self._load_schema()

    def _load_schema(self) -> Dict[str, Any]:
        """DocJSON 스키마 정의"""
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["version", "doc_id", "metadata", "sections"],
            "properties": {
                "version": {
                    "type": "string",
                    "pattern": "^\\d+\\.\\d+$"
                },
                "doc_id": {
                    "type": "string",
                    "format": "uuid"
                },
                "metadata": {
                    "type": "object",
                    "required": ["title", "doc_type"],
                    "properties": {
                        "title": {"type": "string"},
                        "doc_type": {"type": "string"},
                        "version": {"type": ["string", "null"]},
                        "effective_date": {"type": ["string", "null"]},
                        "language": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "author": {"type": ["string", "null"]},
                        "created": {"type": "string"},
                        "modified": {"type": ["string", "null"]},
                        "pages": {"type": "integer", "minimum": 0},
                        "file_size": {"type": "integer", "minimum": 0}
                    }
                },
                "sections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["id", "path", "heading", "level", "blocks"],
                        "properties": {
                            "id": {"type": "string"},
                            "path": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "heading": {"type": "string"},
                            "level": {"type": "integer", "minimum": 1},
                            "blocks": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["id", "type", "page"],
                                    "properties": {
                                        "id": {"type": "string"},
                                        "type": {
                                            "type": "string",
                                            "enum": [
                                                "paragraph", "title", "heading", "table",
                                                "diagram", "image", "list", "caption",
                                                "footnote", "formula"
                                            ]
                                        },
                                        "page": {"type": "integer", "minimum": 1}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

    def convert_to_docjson(self,
                          layout_elements: List[LayoutElement],
                          extracted_content: List[ExtractedContent],
                          document_metadata: Dict[str, Any],
                          file_path: Union[str, Path] = None) -> DocJSON:
        """레이아웃과 추출된 콘텐츠를 DocJSON으로 변환"""

        try:
            # 기본 메타데이터 생성
            metadata = self._create_metadata(document_metadata, file_path)

            # 콘텐츠 블록 생성
            blocks = self._create_content_blocks(layout_elements, extracted_content)

            # 섹션 구조화
            sections = self._organize_into_sections(blocks)

            # DocJSON 생성
            docjson = DocJSON(
                version=self.DOCJSON_VERSION,
                doc_id=str(uuid.uuid4()),
                metadata=metadata,
                sections=sections
            )

            return docjson

        except Exception as e:
            logger.error(f"DocJSON 변환 실패: {e}")
            raise

    def _create_metadata(self, document_metadata: Dict[str, Any], file_path: Union[str, Path] = None) -> DocumentMetadata:
        """메타데이터 생성"""

        # 파일 정보
        source_info = None
        if file_path:
            file_path = Path(file_path)
            source_info = {
                "file": file_path.name,
                "path": str(file_path.absolute()),
                "extension": file_path.suffix.lower(),
                "size": file_path.stat().st_size if file_path.exists() else 0
            }

        # 문서 타입 추론
        doc_type = self._infer_document_type(document_metadata, file_path)

        return DocumentMetadata(
            title=document_metadata.get("title", "Untitled Document"),
            doc_type=doc_type,
            version=document_metadata.get("version"),
            effective_date=document_metadata.get("effective_date"),
            language=document_metadata.get("language", ["ko", "en"]),
            author=document_metadata.get("author"),
            created=document_metadata.get("created"),
            modified=document_metadata.get("modified"),
            source=source_info,
            pages=document_metadata.get("pages", 0),
            file_size=document_metadata.get("file_size", 0)
        )

    def _infer_document_type(self, metadata: Dict[str, Any], file_path: Union[str, Path] = None) -> str:
        """문서 타입 추론"""

        # 명시적 타입이 있으면 사용
        if "doc_type" in metadata:
            return metadata["doc_type"]

        # 제목에서 추론
        title = metadata.get("title", "").lower()

        if any(keyword in title for keyword in ["기술기준", "기술 기준", "technical standard"]):
            return "기술기준"
        elif any(keyword in title for keyword in ["작업표준", "작업 표준", "work standard"]):
            return "작업표준"
        elif any(keyword in title for keyword in ["현황", "보고서", "report", "status"]):
            return "현황보고"
        elif any(keyword in title for keyword in ["매뉴얼", "manual", "가이드", "guide"]):
            return "매뉴얼"

        # 파일명에서 추론
        if file_path:
            filename = Path(file_path).name.lower()
            if any(keyword in filename for keyword in ["기술기준", "tech_standard"]):
                return "기술기준"
            elif any(keyword in filename for keyword in ["작업표준", "work_standard"]):
                return "작업표준"

        return "일반문서"

    def _create_content_blocks(self,
                              layout_elements: List[LayoutElement],
                              extracted_content: List[ExtractedContent]) -> List[ContentBlock]:
        """콘텐츠 블록 생성"""
        blocks = []

        # 추출된 콘텐츠를 ID로 인덱싱
        content_by_bbox = {}
        for content in extracted_content:
            if content.bbox:
                bbox_key = tuple(content.bbox)
                content_by_bbox[bbox_key] = content

        # 레이아웃 요소를 기반으로 블록 생성
        for i, element in enumerate(layout_elements):
            # 콘텐츠 블록 타입 매핑
            block_type = self._map_element_type_to_block_type(element.element_type)

            # 바운딩 박스 생성
            bbox = None
            if element.bbox:
                bbox = BoundingBox.from_list(element.bbox, element.page_number)

            # 매칭되는 추출된 콘텐츠 찾기
            content_data = None
            bbox_key = tuple(element.bbox) if element.bbox else None
            if bbox_key in content_by_bbox:
                extracted = content_by_bbox[bbox_key]
                content_data = self._format_content_data(extracted, block_type)

            # 텍스트가 레이아웃 요소에 있으면 사용
            elif element.text:
                content_data = {
                    "text": element.text,
                    "confidence": element.confidence,
                    "language": "auto"
                }

            # 의미적 정보 생성
            semantic = self._extract_semantic_info(element, content_data)

            # 블록 생성
            block = ContentBlock(
                id=f"block_{i:04d}",
                type=block_type,
                page=element.page_number,
                bbox=bbox,
                content=content_data,
                semantic=semantic,
                metadata={
                    "confidence": element.confidence,
                    "original_element_type": element.element_type.value if hasattr(element.element_type, 'value') else str(element.element_type),
                    "extraction_source": getattr(element, 'properties', {}).get('source', 'layout')
                }
            )
            blocks.append(block)

        return blocks

    def _map_element_type_to_block_type(self, element_type: LayoutElementType) -> ContentBlockType:
        """레이아웃 요소 타입을 블록 타입으로 매핑"""
        mapping = {
            LayoutElementType.TEXT: ContentBlockType.PARAGRAPH,
            LayoutElementType.TITLE: ContentBlockType.TITLE,
            LayoutElementType.HEADING: ContentBlockType.HEADING,
            LayoutElementType.TABLE: ContentBlockType.TABLE,
            LayoutElementType.FIGURE: ContentBlockType.IMAGE,
            LayoutElementType.IMAGE: ContentBlockType.IMAGE,
            LayoutElementType.CAPTION: ContentBlockType.CAPTION,
            LayoutElementType.FOOTNOTE: ContentBlockType.FOOTNOTE,
            LayoutElementType.LIST: ContentBlockType.LIST,
            LayoutElementType.DIAGRAM: ContentBlockType.DIAGRAM,
        }
        return mapping.get(element_type, ContentBlockType.PARAGRAPH)

    def _format_content_data(self, extracted: ExtractedContent, block_type: ContentBlockType) -> Dict[str, Any]:
        """추출된 콘텐츠를 블록 타입에 맞게 포맷"""

        if block_type == ContentBlockType.TABLE:
            # 표 데이터 포맷
            table_data = extracted.data
            return {
                "data": table_data.get("data", []),
                "headers": table_data.get("headers", []),
                "structure": {
                    "rows": table_data.get("rows", len(table_data.get("data", []))),
                    "cols": table_data.get("cols", len(table_data.get("headers", []))),
                    "has_header": bool(table_data.get("headers"))
                },
                "html": table_data.get("html"),
                "csv": table_data.get("csv"),
                "extraction_method": extracted.metadata.get("extraction_method", "unknown")
            }

        elif block_type == ContentBlockType.DIAGRAM:
            # 다이어그램 데이터 포맷
            diagram_data = extracted.data
            return {
                "graph": diagram_data.get("graph", {}),
                "type": "flowchart",  # 기본값
                "shapes": diagram_data.get("shapes", []),
                "connectors": diagram_data.get("connectors", []),
                "description": self._generate_diagram_description(diagram_data.get("graph", {}))
            }

        elif block_type == ContentBlockType.IMAGE:
            # 이미지 데이터 포맷
            image_data = extracted.data
            return {
                "format": image_data.get("format", "unknown"),
                "width": image_data.get("width", 0),
                "height": image_data.get("height", 0),
                "size_bytes": image_data.get("size", 0),
                "alt_text": "",  # TODO: 이미지 캡션 분석
                "has_text": False  # TODO: 이미지 내 텍스트 존재 여부
            }

        else:
            # 기본 텍스트 포맷
            if isinstance(extracted.data, str):
                return {
                    "text": extracted.data,
                    "confidence": extracted.confidence,
                    "language": "auto"
                }
            else:
                return {
                    "text": str(extracted.data),
                    "confidence": extracted.confidence,
                    "language": "auto"
                }

    def _generate_diagram_description(self, graph: Dict[str, Any]) -> str:
        """다이어그램 설명 생성"""
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])

        if not nodes:
            return "빈 다이어그램"

        description_parts = []

        # 노드 정보
        node_labels = [node.get("label", "").strip() for node in nodes if node.get("label", "").strip()]
        if node_labels:
            description_parts.append(f"주요 단계: {', '.join(node_labels[:5])}")

        # 연결 정보
        if edges:
            description_parts.append(f"연결 관계: {len(edges)}개")

        # 전체 설명
        if len(nodes) == 1:
            description_parts.append("단일 요소")
        else:
            description_parts.append(f"총 {len(nodes)}개 요소로 구성된 프로세스 플로우")

        return ". ".join(description_parts)

    def _extract_semantic_info(self, element: LayoutElement, content_data: Dict[str, Any] = None) -> SemanticInfo:
        """의미적 정보 추출"""
        semantic = SemanticInfo()

        # 텍스트에서 키워드 추출
        text = ""
        if content_data and "text" in content_data:
            text = content_data["text"]
        elif element.text:
            text = element.text

        if text:
            # 간단한 키워드 추출 (한국어 지원)
            keywords = self._extract_keywords(text)
            semantic.keywords = keywords

            # 엔티티 추출 (숫자, 단위 등)
            entities = self._extract_entities(text)
            semantic.entities = entities

            # 교차 참조 찾기
            cross_refs = self._find_cross_references(text)
            semantic.cross_refs = cross_refs

        semantic.confidence = element.confidence

        return semantic

    def _extract_keywords(self, text: str) -> List[str]:
        """간단한 키워드 추출"""
        if not text or len(text.strip()) < 3:
            return []

        # 기본적인 키워드 추출 (실제로는 KoNLPy 등 사용 권장)
        keywords = []

        # 기술 관련 키워드
        tech_keywords = [
            "온도", "압력", "속도", "출선", "고로", "안전", "점검", "측정", "제어", "운전",
            "temperature", "pressure", "speed", "safety", "control", "operation"
        ]

        text_lower = text.lower()
        for keyword in tech_keywords:
            if keyword in text_lower:
                keywords.append(keyword)

        # 숫자 + 단위 패턴
        import re
        unit_patterns = [
            r'\d+\.?\d*\s*°C',  # 온도
            r'\d+\.?\d*\s*℃',   # 온도
            r'\d+\.?\d*\s*bar',  # 압력
            r'\d+\.?\d*\s*kg',   # 중량
            r'\d+\.?\d*\s*m/s',  # 속도
        ]

        for pattern in unit_patterns:
            matches = re.findall(pattern, text)
            keywords.extend(matches)

        return list(set(keywords))  # 중복 제거

    def _extract_entities(self, text: str) -> List[str]:
        """엔티티 추출 (장비명, 공정명 등)"""
        entities = []

        # 장비명 패턴
        equipment_patterns = [
            r'고로\s*\d+호?',
            r'터빈\s*\d+호?',
            r'펌프\s*\d+호?',
            r'밸브\s*\d+',
            r'[A-Z]{2,}-\d+'  # 장비 코드 패턴
        ]

        import re
        for pattern in equipment_patterns:
            matches = re.findall(pattern, text)
            entities.extend(matches)

        return entities

    def _find_cross_references(self, text: str) -> List[str]:
        """교차 참조 찾기"""
        cross_refs = []

        import re
        # 표/그림 참조 패턴
        ref_patterns = [
            r'표\s*\d+[-.]?\d*',
            r'그림\s*\d+[-.]?\d*',
            r'도\s*\d+[-.]?\d*',
            r'Table\s*\d+[-.]?\d*',
            r'Figure\s*\d+[-.]?\d*',
            r'Fig\.\s*\d+[-.]?\d*'
        ]

        for pattern in ref_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            cross_refs.extend(matches)

        return cross_refs

    def _organize_into_sections(self, blocks: List[ContentBlock]) -> List[DocumentSection]:
        """블록을 섹션으로 구조화"""
        sections = []
        current_section = None

        for block in blocks:
            # 제목이나 헤딩 블록이면 새 섹션 시작
            if block.type in [ContentBlockType.TITLE, ContentBlockType.HEADING]:
                # 이전 섹션 저장
                if current_section:
                    sections.append(current_section)

                # 새 섹션 생성
                heading_text = ""
                if block.content and "text" in block.content:
                    heading_text = block.content["text"]

                level = self._determine_heading_level(heading_text, block.type)
                path = self._generate_section_path(heading_text, level, len(sections))

                current_section = DocumentSection(
                    id=f"section_{len(sections):03d}",
                    path=path,
                    heading=heading_text,
                    level=level,
                    blocks=[block]
                )

            else:
                # 현재 섹션에 블록 추가
                if current_section is None:
                    # 첫 섹션 생성 (제목이 없는 경우)
                    current_section = DocumentSection(
                        id="section_000",
                        path=["0"],
                        heading="서론",
                        level=1,
                        blocks=[]
                    )

                current_section.blocks.append(block)

        # 마지막 섹션 저장
        if current_section:
            sections.append(current_section)

        return sections

    def _determine_heading_level(self, heading_text: str, block_type: ContentBlockType) -> int:
        """제목 레벨 결정"""
        if block_type == ContentBlockType.TITLE:
            return 1

        # 텍스트 패턴으로 레벨 판단
        import re

        # 숫자 패턴 분석
        patterns = [
            (r'^\d+\.\s+', 1),      # 1. 제목
            (r'^\d+\.\d+\s+', 2),   # 1.1 제목
            (r'^\d+\.\d+\.\d+\s+', 3),  # 1.1.1 제목
            (r'^[가-힣]\.\s+', 2),  # 가. 제목
            (r'^[가-힣]\)\s+', 2),  # 가) 제목
            (r'^\([가-힣]\)\s+', 3), # (가) 제목
        ]

        for pattern, level in patterns:
            if re.match(pattern, heading_text):
                return level

        return 2  # 기본값

    def _generate_section_path(self, heading_text: str, level: int, section_index: int) -> List[str]:
        """섹션 경로 생성"""
        import re

        # 번호 패턴에서 경로 추출
        number_match = re.match(r'^(\d+(?:\.\d+)*)', heading_text)
        if number_match:
            number_str = number_match.group(1)
            return number_str.split('.')

        # 한글 번호 패턴
        korean_match = re.match(r'^([가-힣])[\.\)]', heading_text)
        if korean_match:
            korean_char = korean_match.group(1)
            # 가, 나, 다... -> 1, 2, 3...
            korean_index = ord(korean_char) - ord('가') + 1
            return [str(korean_index)]

        # 기본 순서 번호
        return [str(section_index + 1)]

    def validate_docjson(self, docjson_dict: Dict[str, Any]) -> bool:
        """DocJSON 유효성 검증"""
        try:
            validate(instance=docjson_dict, schema=self.schema)
            return True
        except ValidationError as e:
            logger.error(f"DocJSON 검증 실패: {e.message}")
            return False
        except Exception as e:
            logger.error(f"DocJSON 검증 중 오류: {e}")
            return False

    def save_docjson(self, docjson: DocJSON, output_path: Union[str, Path]) -> bool:
        """DocJSON을 파일로 저장"""
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # JSON으로 변환
            docjson_dict = docjson.to_dict()

            # 검증
            if not self.validate_docjson(docjson_dict):
                logger.error("DocJSON 검증 실패로 저장하지 않습니다.")
                return False

            # 파일 저장
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(docjson_dict, f, indent=2, ensure_ascii=False)

            logger.info(f"DocJSON 저장 완료: {output_path}")
            return True

        except Exception as e:
            logger.error(f"DocJSON 저장 실패: {e}")
            return False

    def load_docjson(self, input_path: Union[str, Path]) -> Optional[DocJSON]:
        """파일에서 DocJSON 로드"""
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 검증
            if not self.validate_docjson(data):
                return None

            # DocJSON 객체로 변환 (간단한 구현)
            # 실제로는 더 정교한 변환 로직 필요
            return data

        except Exception as e:
            logger.error(f"DocJSON 로드 실패: {e}")
            return None