"""
Enhanced DOCX Parser - 기술문서 전용 고급 DOCX 파싱 시스템
XML 구조 직접 분석을 통한 문서 패턴 인식 및 다이어그램 추출
"""

import logging
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
import re
from datetime import datetime

# 기존 시스템과 통합
from .base_parser import BaseParser, ParseResult, DocumentType
from ..core.docjson import DocJSON, BoundingBox, ContentBlock, SemanticInfo, ContentBlockType, DocumentMetadata, DocumentSection
from ..core.user_annotations import DocumentTemplate, UserField, FieldType

logger = logging.getLogger(__name__)

# DOCX XML 네임스페이스 정의
NAMESPACES = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    've': 'http://schemas.openxmlformats.org/markup-compatibility/2006',
    'o': 'urn:schemas-microsoft-com:office:office',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'v': 'urn:schemas-microsoft-com:vml',
    'w10': 'urn:schemas-microsoft-com:office:word',
    'w14': 'http://schemas.microsoft.com/office/word/2010/wordml',
    'wpg': 'http://schemas.microsoft.com/office/word/2010/wordprocessingGroup',
    'wpi': 'http://schemas.microsoft.com/office/word/2010/wordprocessingInk',
    'wne': 'http://schemas.microsoft.com/office/word/2006/wordml',
    'wps': 'http://schemas.microsoft.com/office/word/2010/wordprocessingShape'
}


@dataclass
class DocumentStructure:
    """문서 구조 정보"""
    headers: List[Dict[str, Any]] = field(default_factory=list)
    footers: List[Dict[str, Any]] = field(default_factory=list)
    sections: List[Dict[str, Any]] = field(default_factory=list)
    tables: List[Dict[str, Any]] = field(default_factory=list)
    diagrams: List[Dict[str, Any]] = field(default_factory=list)
    numbering_patterns: Dict[str, Any] = field(default_factory=dict)
    styles: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DiagramElement:
    """다이어그램 요소"""
    element_id: str
    element_type: str  # shape, connector, textbox, smartart
    text: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    position: Dict[str, float] = field(default_factory=dict)
    relationships: List[str] = field(default_factory=list)


@dataclass
class ProcessedDiagram:
    """처리된 다이어그램"""
    diagram_id: str
    diagram_type: str  # flowchart, organizational, process, custom
    elements: List[DiagramElement] = field(default_factory=list)
    connections: List[Dict[str, Any]] = field(default_factory=list)
    semantic_structure: Dict[str, Any] = field(default_factory=dict)


class DocxEnhancedParser(BaseParser):
    """강화된 DOCX 파서"""

    def __init__(self):
        super().__init__()
        self.supported_formats = ['.docx']

        # 기술문서 패턴 정의
        self.document_patterns = {
            "기술기준": {
                "identifiers": ["기술기준", "technical standard", "TP-"],
                "numbering_pattern": r"(\d+\.)+\d*",
                "section_headers": ["목적", "적용범위", "관련문서", "용어정의", "기술기준"],
                "required_fields": ["문서번호", "개정번호", "발행일자"]
            },
            "작업표준": {
                "identifiers": ["작업표준", "work standard", "WS-"],
                "numbering_pattern": r"(\d+\.)+\d*",
                "section_headers": ["목적", "적용범위", "작업절차", "안전사항"],
                "required_fields": ["작업번호", "개정번호", "승인일자"]
            }
        }

    def can_handle(self, file_path: Union[str, Path]) -> bool:
        """파일 처리 가능 여부 확인"""
        file_path = Path(file_path)
        return file_path.suffix.lower() in self.supported_formats

    async def parse(self, file_path: Union[str, Path]) -> ParseResult:
        """DOCX 파일 파싱"""
        file_path = Path(file_path)

        if not file_path.exists():
            return ParseResult(
                success=False,
                document_type=DocumentType.DOCX,
                error=f"파일을 찾을 수 없습니다: {file_path}"
            )

        try:
            logger.info(f"DOCX 파싱 시작: {file_path}")

            # 1. DOCX ZIP 구조 분석
            document_structure = await self._analyze_docx_structure(file_path)

            # 2. 문서 타입 식별
            document_type = self._identify_document_type(document_structure)

            # 3. 콘텐츠 추출
            content_data = await self._extract_content(file_path, document_structure, document_type)

            # 4. 다이어그램 처리
            diagrams = await self._process_diagrams(file_path, document_structure)

            # 5. DocJSON 변환
            docjson = await self._convert_to_docjson(file_path, content_data, diagrams, document_type)

            logger.info(f"DOCX 파싱 완료: {len(content_data.get('sections', []))} 섹션, {len(diagrams)} 다이어그램")

            return ParseResult(
                success=True,
                document_type=DocumentType.DOCX,
                content=docjson,
                metadata={
                    'document_type': document_type,
                    'structure': document_structure,
                    'diagrams_count': len(diagrams),
                    'parsing_method': 'enhanced_docx'
                }
            )

        except Exception as e:
            logger.error(f"DOCX 파싱 실패: {e}")
            return ParseResult(
                success=False,
                document_type=DocumentType.DOCX,
                error=str(e)
            )

    async def _analyze_docx_structure(self, file_path: Path) -> DocumentStructure:
        """DOCX 구조 분석"""
        structure = DocumentStructure()

        try:
            with zipfile.ZipFile(file_path, 'r') as docx_zip:
                # 1. 문서 본문 구조 분석
                if 'word/document.xml' in docx_zip.namelist():
                    document_xml = docx_zip.read('word/document.xml')
                    doc_root = ET.fromstring(document_xml)
                    structure.sections = self._parse_document_sections(doc_root)
                    structure.tables = self._parse_document_tables(doc_root)

                # 2. 스타일 정보 분석
                if 'word/styles.xml' in docx_zip.namelist():
                    styles_xml = docx_zip.read('word/styles.xml')
                    styles_root = ET.fromstring(styles_xml)
                    structure.styles = self._parse_styles(styles_root)

                # 3. 넘버링 패턴 분석
                if 'word/numbering.xml' in docx_zip.namelist():
                    numbering_xml = docx_zip.read('word/numbering.xml')
                    numbering_root = ET.fromstring(numbering_xml)
                    structure.numbering_patterns = self._parse_numbering(numbering_root)

                # 4. 헤더/푸터 분석
                header_footer_files = [f for f in docx_zip.namelist()
                                     if f.startswith('word/header') or f.startswith('word/footer')]

                for hf_file in header_footer_files:
                    hf_xml = docx_zip.read(hf_file)
                    hf_root = ET.fromstring(hf_xml)

                    if 'header' in hf_file:
                        structure.headers.append(self._parse_header_footer(hf_root, 'header'))
                    else:
                        structure.footers.append(self._parse_header_footer(hf_root, 'footer'))

        except Exception as e:
            logger.error(f"DOCX 구조 분석 실패: {e}")

        return structure

    def _parse_document_sections(self, doc_root: ET.Element) -> List[Dict[str, Any]]:
        """문서 섹션 파싱"""
        sections = []

        try:
            # 단락(paragraph) 기반으로 섹션 식별
            paragraphs = doc_root.findall('.//w:p', NAMESPACES)

            current_section = None
            section_level = 0

            for para in paragraphs:
                para_text = self._extract_paragraph_text(para)
                para_style = self._get_paragraph_style(para)

                # 헤딩 스타일 확인 (제목, 부제목 등)
                if para_style and ('heading' in para_style.lower() or 'title' in para_style.lower()):
                    # 새 섹션 시작
                    if current_section:
                        sections.append(current_section)

                    current_section = {
                        'title': para_text,
                        'level': self._determine_heading_level(para_style),
                        'style': para_style,
                        'content': [],
                        'numbering': self._extract_numbering(para)
                    }

                elif current_section:
                    # 현재 섹션에 내용 추가
                    current_section['content'].append({
                        'type': 'paragraph',
                        'text': para_text,
                        'style': para_style
                    })

                else:
                    # 첫 번째 섹션 생성 (제목이 없는 경우)
                    if not sections and not current_section:
                        current_section = {
                            'title': 'Introduction',
                            'level': 1,
                            'content': [],
                            'numbering': None
                        }
                        current_section['content'].append({
                            'type': 'paragraph',
                            'text': para_text,
                            'style': para_style
                        })

            # 마지막 섹션 추가
            if current_section:
                sections.append(current_section)

        except Exception as e:
            logger.error(f"문서 섹션 파싱 실패: {e}")

        return sections

    def _parse_document_tables(self, doc_root: ET.Element) -> List[Dict[str, Any]]:
        """문서 표 파싱"""
        tables = []

        try:
            table_elements = doc_root.findall('.//w:tbl', NAMESPACES)

            for i, table_elem in enumerate(table_elements):
                table_data = {
                    'table_id': f'table_{i}',
                    'rows': [],
                    'properties': self._parse_table_properties(table_elem)
                }

                # 행(row) 파싱
                rows = table_elem.findall('.//w:tr', NAMESPACES)
                for row in rows:
                    row_data = []
                    cells = row.findall('.//w:tc', NAMESPACES)

                    for cell in cells:
                        cell_text = self._extract_cell_text(cell)
                        cell_properties = self._parse_cell_properties(cell)

                        row_data.append({
                            'text': cell_text,
                            'properties': cell_properties
                        })

                    table_data['rows'].append(row_data)

                tables.append(table_data)

        except Exception as e:
            logger.error(f"표 파싱 실패: {e}")

        return tables

    def _parse_styles(self, styles_root: ET.Element) -> Dict[str, Any]:
        """스타일 정보 파싱"""
        styles = {}

        try:
            style_elements = styles_root.findall('.//w:style', NAMESPACES)

            for style_elem in style_elements:
                style_id = style_elem.get('{' + NAMESPACES['w'] + '}styleId')
                style_type = style_elem.get('{' + NAMESPACES['w'] + '}type')

                name_elem = style_elem.find('.//w:name', NAMESPACES)
                style_name = name_elem.get('{' + NAMESPACES['w'] + '}val') if name_elem is not None else style_id

                styles[style_id] = {
                    'name': style_name,
                    'type': style_type,
                    'properties': self._parse_style_properties(style_elem)
                }

        except Exception as e:
            logger.error(f"스타일 파싱 실패: {e}")

        return styles

    def _parse_numbering(self, numbering_root: ET.Element) -> Dict[str, Any]:
        """넘버링 패턴 파싱"""
        numbering = {}

        try:
            # 추상 넘버링 정의
            abstract_nums = numbering_root.findall('.//w:abstractNum', NAMESPACES)
            for abstract_num in abstract_nums:
                abstract_id = abstract_num.get('{' + NAMESPACES['w'] + '}abstractNumId')
                numbering[f'abstract_{abstract_id}'] = self._parse_abstract_numbering(abstract_num)

            # 넘버링 인스턴스
            num_instances = numbering_root.findall('.//w:num', NAMESPACES)
            for num_instance in num_instances:
                num_id = num_instance.get('{' + NAMESPACES['w'] + '}numId')
                numbering[f'instance_{num_id}'] = self._parse_numbering_instance(num_instance)

        except Exception as e:
            logger.error(f"넘버링 파싱 실패: {e}")

        return numbering

    def _parse_header_footer(self, hf_root: ET.Element, hf_type: str) -> Dict[str, Any]:
        """헤더/푸터 파싱"""
        hf_data = {
            'type': hf_type,
            'content': []
        }

        try:
            paragraphs = hf_root.findall('.//w:p', NAMESPACES)
            for para in paragraphs:
                para_text = self._extract_paragraph_text(para)
                if para_text.strip():
                    hf_data['content'].append({
                        'text': para_text,
                        'style': self._get_paragraph_style(para)
                    })

        except Exception as e:
            logger.error(f"헤더/푸터 파싱 실패: {e}")

        return hf_data

    def _identify_document_type(self, structure: DocumentStructure) -> str:
        """문서 타입 식별"""
        # 헤더, 섹션 제목 등에서 문서 타입 키워드 찾기
        all_text = ""

        # 헤더/푸터 텍스트 수집
        for header in structure.headers:
            for content in header.get('content', []):
                all_text += content.get('text', '') + " "

        # 섹션 제목 수집
        for section in structure.sections:
            all_text += section.get('title', '') + " "

        all_text = all_text.lower()

        # 패턴 매칭으로 문서 타입 결정
        for doc_type, patterns in self.document_patterns.items():
            for identifier in patterns['identifiers']:
                if identifier.lower() in all_text:
                    return doc_type

        return "일반문서"

    async def _extract_content(self, file_path: Path, structure: DocumentStructure, document_type: str) -> Dict[str, Any]:
        """콘텐츠 추출"""
        content = {
            'document_type': document_type,
            'sections': structure.sections,
            'tables': structure.tables,
            'headers': structure.headers,
            'footers': structure.footers,
            'metadata': {
                'numbering_patterns': structure.numbering_patterns,
                'styles': structure.styles
            }
        }

        return content

    async def _process_diagrams(self, file_path: Path, structure: DocumentStructure) -> List[ProcessedDiagram]:
        """다이어그램 처리"""
        diagrams = []

        try:
            with zipfile.ZipFile(file_path, 'r') as docx_zip:
                # 1. document.xml에서 그리기 객체 찾기
                if 'word/document.xml' in docx_zip.namelist():
                    document_xml = docx_zip.read('word/document.xml')
                    doc_root = ET.fromstring(document_xml)

                    # Drawing 요소 찾기
                    drawings = doc_root.findall('.//w:drawing', NAMESPACES)

                    for i, drawing in enumerate(drawings):
                        diagram = await self._process_drawing_element(drawing, i, docx_zip)
                        if diagram:
                            diagrams.append(diagram)

                # 2. SmartArt 다이어그램 처리
                smartarts = doc_root.findall('.//w:smartartPr', NAMESPACES) if 'doc_root' in locals() else []
                for i, smartart in enumerate(smartarts):
                    diagram = await self._process_smartart_element(smartart, i, docx_zip)
                    if diagram:
                        diagrams.append(diagram)

        except Exception as e:
            logger.error(f"다이어그램 처리 실패: {e}")

        return diagrams

    async def _process_drawing_element(self, drawing: ET.Element, index: int, docx_zip: zipfile.ZipFile) -> Optional[ProcessedDiagram]:
        """그리기 요소 처리"""
        try:
            diagram = ProcessedDiagram(
                diagram_id=f"drawing_{index}",
                diagram_type="custom"
            )

            # 인라인 및 앵커 도형 찾기
            inlines = drawing.findall('.//wp:inline', NAMESPACES)
            anchors = drawing.findall('.//wp:anchor', NAMESPACES)

            all_shapes = inlines + anchors

            for shape_elem in all_shapes:
                element = await self._parse_shape_element(shape_elem)
                if element:
                    diagram.elements.append(element)

            # 연결 관계 분석
            diagram.connections = self._analyze_shape_connections(diagram.elements)

            # 의미론적 구조 분석
            diagram.semantic_structure = self._analyze_diagram_semantics(diagram)

            return diagram if diagram.elements else None

        except Exception as e:
            logger.error(f"그리기 요소 처리 실패: {e}")
            return None

    async def _parse_shape_element(self, shape_elem: ET.Element) -> Optional[DiagramElement]:
        """도형 요소 파싱"""
        try:
            # 도형 ID 추출
            element_id = shape_elem.get('id', f'shape_{hash(ET.tostring(shape_elem))}')

            # 텍스트 추출
            text_elements = shape_elem.findall('.//a:t', NAMESPACES)
            text = ' '.join([elem.text or '' for elem in text_elements])

            # 위치 정보 추출
            position = {}
            extent = shape_elem.find('.//wp:extent', NAMESPACES)
            if extent is not None:
                position['width'] = int(extent.get('cx', 0))
                position['height'] = int(extent.get('cy', 0))

            pos_offset = shape_elem.find('.//wp:positionH/wp:posOffset', NAMESPACES)
            if pos_offset is not None:
                position['x'] = int(pos_offset.text or 0)

            pos_v_offset = shape_elem.find('.//wp:positionV/wp:posOffset', NAMESPACES)
            if pos_v_offset is not None:
                position['y'] = int(pos_v_offset.text or 0)

            # 도형 타입 결정
            element_type = "shape"
            if shape_elem.find('.//a:ln', NAMESPACES) is not None:
                element_type = "connector"
            elif text and not shape_elem.find('.//pic:pic', NAMESPACES):
                element_type = "textbox"

            return DiagramElement(
                element_id=element_id,
                element_type=element_type,
                text=text,
                position=position,
                properties=self._extract_shape_properties(shape_elem)
            )

        except Exception as e:
            logger.error(f"도형 요소 파싱 실패: {e}")
            return None

    def _analyze_shape_connections(self, elements: List[DiagramElement]) -> List[Dict[str, Any]]:
        """도형 간 연결 관계 분석"""
        connections = []

        # 간단한 위치 기반 연결 분석
        connectors = [elem for elem in elements if elem.element_type == "connector"]
        shapes = [elem for elem in elements if elem.element_type in ["shape", "textbox"]]

        for connector in connectors:
            # 커넥터와 가까운 도형들 찾기
            nearby_shapes = self._find_nearby_shapes(connector, shapes)

            if len(nearby_shapes) >= 2:
                connections.append({
                    'connector_id': connector.element_id,
                    'from': nearby_shapes[0].element_id,
                    'to': nearby_shapes[1].element_id,
                    'type': 'flow'
                })

        return connections

    def _analyze_diagram_semantics(self, diagram: ProcessedDiagram) -> Dict[str, Any]:
        """다이어그램 의미론적 분석"""
        semantics = {
            'diagram_type': 'process',
            'flow_direction': 'top_to_bottom',
            'key_concepts': [],
            'decision_points': [],
            'start_nodes': [],
            'end_nodes': []
        }

        # 텍스트 기반 의미 분석
        for element in diagram.elements:
            text_lower = element.text.lower()

            # 결정점 식별
            if any(keyword in text_lower for keyword in ['if', '판단', '결정', '선택', '?']):
                semantics['decision_points'].append(element.element_id)

            # 시작/종료 노드 식별
            if any(keyword in text_lower for keyword in ['시작', 'start', '개시']):
                semantics['start_nodes'].append(element.element_id)
            elif any(keyword in text_lower for keyword in ['종료', 'end', '완료', '끝']):
                semantics['end_nodes'].append(element.element_id)

            # 핵심 개념 추출
            if element.text.strip() and len(element.text.strip()) > 2:
                semantics['key_concepts'].append(element.text.strip())

        return semantics

    async def _convert_to_docjson(self, file_path: Path, content_data: Dict[str, Any],
                                 diagrams: List[ProcessedDiagram], document_type: str) -> DocJSON:
        """DocJSON 변환"""
        try:
            # DocJSON 객체 생성
            import uuid

            metadata = DocumentMetadata(
                title=file_path.stem,
                doc_type=document_type,
                created=datetime.now().isoformat(),
                source={
                    'file': file_path.name,
                    'path': str(file_path),
                    'extension': file_path.suffix,
                    'size': file_path.stat().st_size if file_path.exists() else 0
                },
                pages=1,
                file_size=file_path.stat().st_size if file_path.exists() else 0
            )

            docjson = DocJSON(
                version="2.0",
                doc_id=str(uuid.uuid4()),
                metadata=metadata
            )

            # 섹션 변환
            for i, section_data in enumerate(content_data.get('sections', [])):
                section = DocumentSection(
                    id=f"section_{i}",
                    path=[str(i)],
                    heading=section_data.get('title', f'Section {i+1}'),
                    level=section_data.get('level', 1),
                    blocks=[]
                )

                # 섹션 내 블록 추가
                for content_item in section_data.get('content', []):
                    if content_item['type'] == 'paragraph' and content_item['text'].strip():
                        block = ContentBlock(
                            type=ContentBlockType.PARAGRAPH,
                            page=1,  # DOCX는 페이지 정보가 명확하지 않음
                            bbox=BoundingBox(0, 0, 100, 20, 1),  # 임시 바운딩박스
                            content={
                                'text': content_item['text'],
                                'confidence': 1.0,
                                'language': 'auto'
                            }
                        )

                        # 의미 정보 추가
                        block.semantic = self._create_semantic_info(content_item['text'])
                        section.blocks.append(block)

                docjson.sections.append(section)

            # 표 추가
            for i, table_data in enumerate(content_data.get('tables', [])):
                table_section = DocumentSection(
                    id=f"table_section_{i}",
                    path=[str(len(docjson.sections))],
                    heading=f"Table {i+1}",
                    level=2,
                    blocks=[]
                )

                # 표를 HTML로 변환
                html_table = self._convert_table_to_html(table_data)

                table_block = ContentBlock(
                    type=ContentBlockType.TABLE,
                    page=1,
                    bbox=BoundingBox(0, 0, 200, 100, 1),
                    content={
                        'text': html_table,
                        'confidence': 1.0,
                        'language': 'auto'
                    }
                )

                table_block.semantic = SemanticInfo(
                    keywords=['table', 'data'],
                    confidence=1.0
                )

                table_section.blocks.append(table_block)
                docjson.sections.append(table_section)

            # 다이어그램 추가
            for diagram in diagrams:
                diagram_section = DocumentSection(
                    id=f"diagram_section_{diagram.diagram_id}",
                    path=[str(len(docjson.sections))],
                    heading=f"Diagram: {diagram.diagram_id}",
                    level=2,
                    blocks=[]
                )

                # 다이어그램을 구조화된 텍스트로 변환
                diagram_text = self._diagram_to_text(diagram)

                diagram_block = ContentBlock(
                    type=ContentBlockType.DIAGRAM,
                    page=1,
                    bbox=BoundingBox(0, 0, 300, 200, 1),
                    content={
                        'text': diagram_text,
                        'confidence': 0.9,
                        'language': 'auto'
                    }
                )

                diagram_block.semantic = SemanticInfo(
                    keywords=diagram.semantic_structure.get('key_concepts', []),
                    entities=[elem.text for elem in diagram.elements if elem.text],
                    confidence=0.9
                )

                # 다이어그램 구조 정보를 메타데이터에 저장
                diagram_block.metadata = {
                    'diagram_type': diagram.diagram_type,
                    'elements': [elem.__dict__ for elem in diagram.elements],
                    'connections': diagram.connections,
                    'semantic_structure': diagram.semantic_structure
                }

                diagram_section.blocks.append(diagram_block)
                docjson.sections.append(diagram_section)

            return docjson

        except Exception as e:
            logger.error(f"DocJSON 변환 실패: {e}")
            raise

    # Helper methods
    def _extract_paragraph_text(self, para: ET.Element) -> str:
        """단락 텍스트 추출"""
        text_elements = para.findall('.//w:t', NAMESPACES)
        return ''.join([elem.text or '' for elem in text_elements])

    def _get_paragraph_style(self, para: ET.Element) -> Optional[str]:
        """단락 스타일 추출"""
        style_elem = para.find('.//w:pStyle', NAMESPACES)
        return style_elem.get('{' + NAMESPACES['w'] + '}val') if style_elem is not None else None

    def _determine_heading_level(self, style: str) -> int:
        """헤딩 레벨 결정"""
        if not style:
            return 1

        style_lower = style.lower()
        if 'heading1' in style_lower or 'title' in style_lower:
            return 1
        elif 'heading2' in style_lower:
            return 2
        elif 'heading3' in style_lower:
            return 3
        else:
            return 1

    def _create_semantic_info(self, text: str) -> SemanticInfo:
        """의미 정보 생성 (기본 키워드 추출)"""
        semantic = SemanticInfo()

        # 기술문서 키워드 패턴
        tech_patterns = [
            r'TP-\d+', r'WS-\d+',  # 문서번호
            r'\d+\.\d+\.\d+',       # 버전번호
            r'Rev\.\d+',            # 개정번호
        ]

        entities = []
        for pattern in tech_patterns:
            matches = re.findall(pattern, text)
            entities.extend(matches)

        semantic.entities = list(set(entities))
        semantic.keywords = self._extract_technical_keywords(text)
        semantic.confidence = 0.8

        return semantic

    def _extract_technical_keywords(self, text: str) -> List[str]:
        """기술 키워드 추출"""
        keywords = []
        tech_keywords = [
            '기술기준', '작업표준', '안전사항', '점검사항',
            '목적', '적용범위', '관련문서', '용어정의'
        ]

        text_lower = text.lower()
        for keyword in tech_keywords:
            if keyword in text_lower:
                keywords.append(keyword)

        return keywords

    def _convert_table_to_html(self, table_data: Dict[str, Any]) -> str:
        """표를 HTML로 변환"""
        html = "<table>"

        for row in table_data.get('rows', []):
            html += "<tr>"
            for cell in row:
                cell_text = cell.get('text', '').strip()
                html += f"<td>{cell_text}</td>"
            html += "</tr>"

        html += "</table>"
        return html

    def _diagram_to_text(self, diagram: ProcessedDiagram) -> str:
        """다이어그램을 텍스트로 변환"""
        text_parts = [f"Diagram Type: {diagram.diagram_type}"]

        # 요소 설명
        text_parts.append("Elements:")
        for elem in diagram.elements:
            if elem.text:
                text_parts.append(f"- {elem.element_type}: {elem.text}")

        # 연결 관계 설명
        if diagram.connections:
            text_parts.append("Connections:")
            for conn in diagram.connections:
                text_parts.append(f"- {conn.get('from')} → {conn.get('to')}")

        return '\n'.join(text_parts)

    # 추가 Helper methods들...
    def _extract_numbering(self, para: ET.Element) -> Optional[str]:
        """넘버링 추출"""
        # 구현 필요
        return None

    def _parse_table_properties(self, table_elem: ET.Element) -> Dict[str, Any]:
        """표 속성 파싱"""
        return {}

    def _extract_cell_text(self, cell: ET.Element) -> str:
        """셀 텍스트 추출"""
        text_elements = cell.findall('.//w:t', NAMESPACES)
        return ''.join([elem.text or '' for elem in text_elements])

    def _parse_cell_properties(self, cell: ET.Element) -> Dict[str, Any]:
        """셀 속성 파싱"""
        return {}

    def _parse_style_properties(self, style_elem: ET.Element) -> Dict[str, Any]:
        """스타일 속성 파싱"""
        return {}

    def _parse_abstract_numbering(self, abstract_num: ET.Element) -> Dict[str, Any]:
        """추상 넘버링 파싱"""
        return {}

    def _parse_numbering_instance(self, num_instance: ET.Element) -> Dict[str, Any]:
        """넘버링 인스턴스 파싱"""
        return {}

    def _extract_shape_properties(self, shape_elem: ET.Element) -> Dict[str, Any]:
        """도형 속성 추출"""
        return {}

    def _find_nearby_shapes(self, connector: DiagramElement, shapes: List[DiagramElement]) -> List[DiagramElement]:
        """주변 도형 찾기"""
        # 간단한 거리 기반 구현
        return shapes[:2] if len(shapes) >= 2 else shapes

    async def _process_smartart_element(self, smartart: ET.Element, index: int, docx_zip: zipfile.ZipFile) -> Optional[ProcessedDiagram]:
        """SmartArt 요소 처리"""
        # 구현 필요
        return None