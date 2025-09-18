"""
문서 구조 고급 분석기
기술기준 문서의 패턴을 인식하고 구조를 분석
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class DocumentPattern:
    """문서 패턴 정의"""
    name: str
    pattern: str
    importance: str  # critical, high, medium
    extractor: Optional[callable] = None

@dataclass
class DocumentStructure:
    """분석된 문서 구조"""
    document_number: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    effective_date: Optional[str] = None
    revision: Optional[str] = None
    sections: List[Dict[str, Any]] = field(default_factory=list)
    tables: List[Dict[str, Any]] = field(default_factory=list)
    diagrams: List[Dict[str, Any]] = field(default_factory=list)
    patterns_found: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class DocumentAnalyzer:
    """고급 문서 구조 분석기"""

    # 기술기준 문서 패턴 정의
    TECHNICAL_PATTERNS = [
        DocumentPattern(
            name="document_number",
            pattern=r'TP-\d{3}-\d{3}-\d{3}',
            importance="critical"
        ),
        DocumentPattern(
            name="effective_date",
            pattern=r"(?:시행일|Effective Date)[:\s]*['\"]?(\d{2,4})[.\-/](\d{1,2})[.\-/](\d{1,2})",
            importance="critical"
        ),
        DocumentPattern(
            name="revision",
            pattern=r'Rev[\.\s]*:\s*(\d+)',
            importance="high"
        ),
        DocumentPattern(
            name="section_number",
            pattern=r'^(\d+(?:\.\d+)*)\s+(.+?)$',
            importance="high"
        ),
        DocumentPattern(
            name="korean_date",
            pattern=r"'?(\d{2})\.(\d{1,2})\.(\d{1,2})",
            importance="medium"
        ),
    ]

    def __init__(self):
        self.patterns = self.TECHNICAL_PATTERNS

    def analyze_document(self, content: Dict[str, Any]) -> DocumentStructure:
        """문서 전체 구조 분석"""
        structure = DocumentStructure()

        # 원시 콘텐츠 추출
        raw_content = content.get('raw_content', content)

        # 1. 텍스트 기반 패턴 분석
        self._extract_text_patterns(raw_content, structure)

        # 2. 표 분석
        self._analyze_tables(raw_content, structure)

        # 3. 섹션 구조 분석
        self._analyze_sections(raw_content, structure)

        # 4. 다이어그램 분석
        self._analyze_diagrams(raw_content, structure)

        # 5. 메타데이터 통합
        self._integrate_metadata(raw_content, structure)

        return structure

    def _extract_text_patterns(self, content: Dict[str, Any], structure: DocumentStructure):
        """텍스트에서 패턴 추출"""

        # 모든 텍스트 수집
        all_text = self._collect_all_text(content)

        # 문서번호 찾기
        doc_num_pattern = re.compile(r'TP-\d{3}-\d{3}-\d{3}')
        if match := doc_num_pattern.search(all_text):
            structure.document_number = match.group()
            structure.patterns_found['document_number'] = match.group()
            logger.info(f"문서번호 감지: {structure.document_number}")

        # 개정번호 찾기
        if match := re.search(r'Rev[\.\s]*:\s*(\d+)', all_text):
            structure.revision = match.group(1)
            structure.patterns_found['revision'] = match.group(1)
            logger.info(f"개정번호 감지: Rev.{structure.revision}")

        # 시행일 더 유연하게 찾기 (헤더에서: 시행일:  ' 25.07.28)
        # 먼저 시행일이 있는지 확인
        if not structure.effective_date and '시행일' in all_text:
            # 시행일 뒤의 날짜 패턴 찾기 (공백, 특수문자 무시)
            if match := re.search(r"시행일[:\s]*['\"]?\s*(\d{2,4})[.\-/](\d{1,2})[.\-/](\d{1,2})", all_text):
                structure.effective_date = f"{match.group(1)}.{match.group(2).zfill(2)}.{match.group(3).zfill(2)}"
                structure.patterns_found['effective_date'] = structure.effective_date
                logger.info(f"시행일 감지 (패턴1): {structure.effective_date}")
            # 더 넓은 패턴 (시행일과 날짜가 떨어져 있을 수 있음)
            elif match := re.search(r"시행일.*?['\"]?\s*(\d{2})[.\-/](\d{1,2})[.\-/](\d{1,2})", all_text, re.DOTALL):
                structure.effective_date = f"{match.group(1)}.{match.group(2).zfill(2)}.{match.group(3).zfill(2)}"
                structure.patterns_found['effective_date'] = structure.effective_date
                logger.info(f"시행일 감지 (패턴2): {structure.effective_date}")

    def _analyze_tables(self, content: Dict[str, Any], structure: DocumentStructure):
        """표 분석 및 구조화"""
        tables = content.get('tables', [])

        for i, table in enumerate(tables):
            table_info = {
                'index': i,
                'data': None,
                'type': None
            }

            # 표 데이터 추출
            if isinstance(table, dict):
                rows = table.get('rows', [])
                if isinstance(rows, list) and rows:
                    table_info['data'] = rows

                    # 첫 행 분석으로 표 타입 추론
                    if rows and len(rows) > 0:
                        first_row = rows[0]
                        if isinstance(first_row, list):
                            # 작성자 표 감지
                            if any('작성자' in str(cell) for cell in first_row):
                                table_info['type'] = 'author_info'
                                # 작성자 정보 추출
                                if len(rows) > 0 and len(first_row) > 1:
                                    structure.author = str(first_row[1]) if len(first_row) > 1 else None
                                    logger.info(f"작성자 감지: {structure.author}")

                            # 중점관리항목 표 감지
                            elif any('품질영향' in str(cell) or '공정영향' in str(cell) for cell in first_row):
                                table_info['type'] = 'management_items'

            structure.tables.append(table_info)

    def _analyze_sections(self, content: Dict[str, Any], structure: DocumentStructure):
        """섹션 구조 분석"""
        paragraphs = content.get('paragraphs', [])

        section_pattern = re.compile(r'^(\d+(?:\.\d+)*)\s+(.+?)$')

        for para in paragraphs:
            if isinstance(para, dict):
                text = para.get('text', '').strip()
            else:
                text = str(para).strip()

            if match := section_pattern.match(text):
                section = {
                    'number': match.group(1),
                    'title': match.group(2),
                    'level': len(match.group(1).split('.')),
                    'full_text': text
                }
                structure.sections.append(section)
                logger.info(f"섹션 감지: {section['number']} {section['title']}")

    def _analyze_diagrams(self, content: Dict[str, Any], structure: DocumentStructure):
        """다이어그램 분석"""
        diagrams = content.get('diagrams', [])

        for i, diagram in enumerate(diagrams):
            diagram_info = {
                'index': i,
                'type': diagram.get('type', 'unknown') if isinstance(diagram, dict) else 'drawing',
                'description': diagram.get('description', '') if isinstance(diagram, dict) else ''
            }
            structure.diagrams.append(diagram_info)

    def _collect_all_text(self, content: Dict[str, Any]) -> str:
        """모든 텍스트 수집"""
        texts = []

        # 헤더/푸터에서 텍스트 수집 (최우선)
        headers_footers = content.get('headers_footers', {})
        if headers_footers:
            for header in headers_footers.get('headers', []):
                if isinstance(header, dict) and 'text' in header:
                    texts.append(header['text'])
            for footer in headers_footers.get('footers', []):
                if isinstance(footer, dict) and 'text' in footer:
                    texts.append(footer['text'])

        # 단락에서 텍스트 수집
        for para in content.get('paragraphs', []):
            if isinstance(para, dict):
                texts.append(para.get('text', ''))
            else:
                texts.append(str(para))

        # 표에서 텍스트 수집
        for table in content.get('tables', []):
            if isinstance(table, dict):
                rows = table.get('rows', [])
                if isinstance(rows, list):
                    for row in rows:
                        if isinstance(row, list):
                            texts.extend(str(cell) for cell in row)

        # XML 구조에서 텍스트 수집
        xml_struct = content.get('xml_structure', {})
        if xml_struct and isinstance(xml_struct, dict):
            # 헤더/푸터 정보 추가
            if 'headers_footers' in xml_struct:
                hf = xml_struct['headers_footers']
                if isinstance(hf, dict):
                    for header in hf.get('headers', []):
                        if isinstance(header, dict) and 'text' in header:
                            texts.append(header['text'])
                    for footer in hf.get('footers', []):
                        if isinstance(footer, dict) and 'text' in footer:
                            texts.append(footer['text'])

            # XML에서 추가 텍스트 수집
            for table in xml_struct.get('tables', []):
                if isinstance(table, dict):
                    rows = table.get('rows', [])
                    if isinstance(rows, list):
                        for row in rows:
                            if isinstance(row, list):
                                texts.extend(str(cell) for cell in row)

        return '\n'.join(texts)

    def _integrate_metadata(self, content: Dict[str, Any], structure: DocumentStructure):
        """메타데이터 통합"""

        # XML 구조에서 추가 정보 추출
        xml_struct = content.get('xml_structure', {})
        if xml_struct:
            # XML 표에서 작성자 정보 재확인
            for table in xml_struct.get('tables', []):
                if isinstance(table, dict):
                    rows = table.get('rows', [])
                    if isinstance(rows, list) and rows:
                        first_row = rows[0]
                        if isinstance(first_row, list) and len(first_row) >= 2:
                            if '작성자' in str(first_row[0]):
                                structure.author = str(first_row[1])
                                structure.metadata['author_from_xml'] = structure.author

        # 문서 제목 추출 (첫 번째 주요 제목)
        if not structure.title and structure.sections:
            # 1. 적용범위 앞의 텍스트를 제목으로 추정
            for para in content.get('paragraphs', []):
                text = para.get('text', '') if isinstance(para, dict) else str(para)
                if '적용범위' not in text and not re.match(r'^\d+\.', text) and len(text) > 5:
                    # 문서번호나 날짜가 아닌 첫 번째 의미있는 텍스트
                    if not re.search(r'TP-\d{3}', text) and not re.search(r'\d{2}\.\d{2}\.\d{2}', text):
                        structure.title = text.strip()
                        break

        # 통계 정보
        structure.metadata['total_sections'] = len(structure.sections)
        structure.metadata['total_tables'] = len(structure.tables)
        structure.metadata['total_diagrams'] = len(structure.diagrams)
        structure.metadata['patterns_detected'] = len(structure.patterns_found)

    def get_recognition_score(self, structure: DocumentStructure) -> float:
        """인식율 점수 계산"""
        score = 0
        total = 0

        # Critical 항목 (각 20점)
        critical_items = [
            ('document_number', structure.document_number),
            ('title', structure.title),
            ('effective_date', structure.effective_date)
        ]

        for name, value in critical_items:
            total += 20
            if value:
                score += 20

        # High importance 항목 (각 10점)
        high_items = [
            ('author', structure.author),
            ('revision', structure.revision),
            ('sections', len(structure.sections) >= 4),
            ('tables', len(structure.tables) >= 1)
        ]

        for name, value in high_items:
            total += 10
            if value:
                score += 10

        # Medium importance 항목 (각 5점)
        medium_items = [
            ('diagrams', len(structure.diagrams) > 0),
            ('metadata', len(structure.metadata) > 3)
        ]

        for name, value in medium_items:
            total += 5
            if value:
                score += 5

        return (score / total * 100) if total > 0 else 0