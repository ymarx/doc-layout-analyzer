"""
RAG 시스템을 위한 문서 청킹 및 최적화
Document Chunker for RAG Vector Embedding Optimization
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re
import hashlib
from datetime import datetime

class ChunkType(Enum):
    """청크 유형"""
    METADATA = "metadata"           # 메타데이터 청크
    HEADER = "header"              # 제목/헤더 청크
    CONTENT = "content"            # 내용 청크
    TABLE = "table"                # 표 청크
    DIAGRAM = "diagram"            # 다이어그램 청크
    PROCESS_FLOW = "process_flow"  # 프로세스 흐름 청크
    SECTION = "section"            # 섹션 청크

@dataclass
class DocumentChunk:
    """RAG용 문서 청크"""
    chunk_id: str                           # 청크 고유 ID
    chunk_type: ChunkType                   # 청크 유형
    text: str                              # 임베딩할 텍스트
    metadata: Dict[str, Any]               # 메타데이터
    hierarchy_level: int = 0               # 계층 레벨
    parent_chunk_id: Optional[str] = None  # 상위 청크 ID
    child_chunk_ids: List[str] = field(default_factory=list)  # 하위 청크 ID들
    embedding_text: Optional[str] = None   # 최적화된 임베딩 텍스트
    relevance_keywords: List[str] = field(default_factory=list)  # 관련 키워드
    confidence: float = 1.0                # 추출 신뢰도

class RAGDocumentProcessor:
    """RAG 시스템을 위한 문서 처리기"""

    def __init__(self):
        self.chunk_size_limits = {
            ChunkType.METADATA: 200,        # 메타데이터는 간결하게
            ChunkType.HEADER: 100,          # 헤더는 짧게
            ChunkType.CONTENT: 512,         # 내용은 적당한 크기
            ChunkType.TABLE: 800,           # 표는 구조 정보 포함
            ChunkType.DIAGRAM: 400,         # 다이어그램 설명
            ChunkType.PROCESS_FLOW: 600,    # 프로세스는 순서 포함
            ChunkType.SECTION: 1000         # 섹션 전체 요약
        }

    def process_document(self, docjson: Dict[str, Any], template_extracted: Dict[str, Any] = None) -> List[DocumentChunk]:
        """문서를 RAG용 청크로 변환"""
        chunks = []
        document_id = docjson.get('doc_id', 'unknown')

        # 1. 메타데이터 청크 생성
        metadata_chunk = self._create_metadata_chunk(docjson, template_extracted, document_id)
        chunks.append(metadata_chunk)

        # 2. 섹션별 청크 생성
        sections = docjson.get('sections', [])
        for section in sections:
            section_chunks = self._process_section(section, document_id, template_extracted)
            chunks.extend(section_chunks)

        # 3. 프로세스 흐름 청크 생성 (있는 경우)
        if template_extracted and 'process_flows' in template_extracted:
            process_chunks = self._create_process_flow_chunks(
                template_extracted['process_flows'], document_id
            )
            chunks.extend(process_chunks)

        # 4. 청크 간 관계 설정
        self._establish_chunk_relationships(chunks)

        return chunks

    def _create_metadata_chunk(self, docjson: Dict[str, Any], template_extracted: Dict[str, Any], document_id: str) -> DocumentChunk:
        """메타데이터 청크 생성"""
        metadata = docjson.get('metadata', {})

        # 메타데이터 텍스트 구성
        metadata_text_parts = []

        # 기본 문서 정보
        if metadata.get('title'):
            metadata_text_parts.append(f"문서제목: {metadata['title']}")

        # 템플릿에서 추출된 정보 추가
        if template_extracted:
            if template_extracted.get('document_number'):
                metadata_text_parts.append(f"문서번호: {template_extracted['document_number']}")
            if template_extracted.get('effective_date'):
                metadata_text_parts.append(f"시행일: {template_extracted['effective_date']}")
            if template_extracted.get('revision'):
                metadata_text_parts.append(f"개정: {template_extracted['revision']}")
            if template_extracted.get('author'):
                metadata_text_parts.append(f"작성자: {template_extracted['author']}")

        metadata_text = " | ".join(metadata_text_parts)

        # 키워드 추출
        keywords = []
        if metadata.get('title'):
            keywords.extend(self._extract_keywords(metadata['title']))
        if template_extracted and template_extracted.get('document_number'):
            keywords.append(template_extracted['document_number'])

        return DocumentChunk(
            chunk_id=f"{document_id}_metadata",
            chunk_type=ChunkType.METADATA,
            text=metadata_text,
            metadata={
                'document_type': metadata.get('doc_type'),
                'created': metadata.get('created'),
                'pages': metadata.get('pages'),
                **({k: v for k, v in template_extracted.items() if v} if template_extracted else {})
            },
            embedding_text=self._optimize_for_embedding(metadata_text, ChunkType.METADATA),
            relevance_keywords=keywords,
            confidence=0.95
        )

    def _process_section(self, section: Dict[str, Any], document_id: str, template_extracted: Dict[str, Any]) -> List[DocumentChunk]:
        """섹션을 청크로 변환"""
        chunks = []
        section_id = section.get('id', 'unknown_section')

        # 섹션 헤더 청크
        if section.get('heading'):
            header_chunk = self._create_header_chunk(section, document_id)
            chunks.append(header_chunk)

        # 블록별 청크 처리
        blocks = section.get('blocks', [])
        for block in blocks:
            block_chunks = self._process_block(block, document_id, section_id)
            chunks.extend(block_chunks)

        return chunks

    def _create_header_chunk(self, section: Dict[str, Any], document_id: str) -> DocumentChunk:
        """헤더 청크 생성"""
        heading = section.get('heading', '')
        level = section.get('level', 1)
        section_id = section.get('id', 'unknown')

        # 계층 정보 포함 텍스트
        hierarchy_prefix = "  " * (level - 1)  # 들여쓰기로 계층 표현
        embedding_text = f"{hierarchy_prefix}{heading}"

        keywords = self._extract_keywords(heading)

        return DocumentChunk(
            chunk_id=f"{document_id}_{section_id}_header",
            chunk_type=ChunkType.HEADER,
            text=heading,
            metadata={
                'hierarchy_level': level,
                'section_id': section_id,
                'section_path': section.get('path', [])
            },
            hierarchy_level=level,
            embedding_text=embedding_text,
            relevance_keywords=keywords,
            confidence=0.9
        )

    def _process_block(self, block: Dict[str, Any], document_id: str, section_id: str) -> List[DocumentChunk]:
        """블록을 청크로 변환"""
        chunks = []
        block_type = block.get('type', 'unknown')
        block_id = block.get('id', 'unknown_block')

        if block_type == 'paragraph':
            chunk = self._create_content_chunk(block, document_id, section_id)
            if chunk:
                chunks.append(chunk)

        elif block_type == 'table':
            chunk = self._create_table_chunk(block, document_id, section_id)
            if chunk:
                chunks.append(chunk)

        return chunks

    def _create_content_chunk(self, block: Dict[str, Any], document_id: str, section_id: str) -> Optional[DocumentChunk]:
        """내용 청크 생성"""
        content = block.get('content', {})
        text = content.get('text', '').strip()

        if not text or len(text) < 10:  # 너무 짧은 텍스트 제외
            return None

        block_id = block.get('id', 'unknown_block')

        # 구조적 요소인지 확인
        is_structural = self._is_structural_element(text)
        chunk_type = ChunkType.HEADER if is_structural else ChunkType.CONTENT

        # 키워드 추출
        keywords = self._extract_keywords(text)

        return DocumentChunk(
            chunk_id=f"{document_id}_{section_id}_{block_id}",
            chunk_type=chunk_type,
            text=text,
            metadata={
                'section_id': section_id,
                'block_id': block_id,
                'page': block.get('page', 1),
                'bbox': block.get('bbox', {}),
                'is_structural': is_structural
            },
            embedding_text=self._optimize_for_embedding(text, chunk_type),
            relevance_keywords=keywords,
            confidence=0.8
        )

    def _create_table_chunk(self, block: Dict[str, Any], document_id: str, section_id: str) -> Optional[DocumentChunk]:
        """표 청크 생성"""
        content = block.get('content', {})
        table_data = content.get('table_data', [])

        if not table_data:
            return None

        block_id = block.get('id', 'unknown_table')

        # 표를 텍스트로 변환
        table_text = self._table_to_text(table_data)

        # 표 구조 분석
        structure_info = self._analyze_table_structure(table_data)

        # 키워드 추출 (표 내용에서)
        keywords = []
        for row in table_data:
            for cell in row:
                keywords.extend(self._extract_keywords(str(cell)))

        return DocumentChunk(
            chunk_id=f"{document_id}_{section_id}_{block_id}",
            chunk_type=ChunkType.TABLE,
            text=table_text,
            metadata={
                'section_id': section_id,
                'block_id': block_id,
                'table_structure': structure_info,
                'row_count': len(table_data),
                'column_count': len(table_data[0]) if table_data else 0
            },
            embedding_text=self._optimize_table_for_embedding(table_data, structure_info),
            relevance_keywords=list(set(keywords)),
            confidence=0.85
        )

    def _create_process_flow_chunks(self, process_flows: List[Dict[str, Any]], document_id: str) -> List[DocumentChunk]:
        """프로세스 흐름 청크 생성"""
        chunks = []

        for i, flow in enumerate(process_flows):
            flow_name = flow.get('name', f'프로세스_{i+1}')
            steps = flow.get('steps', [])

            # 프로세스 전체 텍스트
            flow_text = f"프로세스: {flow_name}\n"
            step_texts = []

            for step in steps:
                marker = step.get('marker', '')
                title = step.get('title', '')
                details = step.get('details', [])

                step_text = f"{marker} {title}"
                if details:
                    step_text += f" ({', '.join(details)})"
                step_texts.append(step_text)

            flow_text += " → ".join(step_texts)

            # 키워드 추출
            keywords = [flow_name]
            for step in steps:
                keywords.extend(self._extract_keywords(step.get('title', '')))

            chunk = DocumentChunk(
                chunk_id=f"{document_id}_process_flow_{i}",
                chunk_type=ChunkType.PROCESS_FLOW,
                text=flow_text,
                metadata={
                    'flow_name': flow_name,
                    'flow_type': flow.get('type', 'sequential'),
                    'step_count': len(steps),
                    'confidence': flow.get('confidence', 0.8),
                    'steps': steps
                },
                embedding_text=self._optimize_process_for_embedding(flow_text, steps),
                relevance_keywords=list(set(keywords)),
                confidence=flow.get('confidence', 0.8)
            )
            chunks.append(chunk)

        return chunks

    def _is_structural_element(self, text: str) -> bool:
        """구조적 요소인지 판단"""
        # 번호 체계로 시작하는지 확인
        structural_patterns = [
            r'^\d+\.\s+',           # 1.
            r'^\d+\.\d+\s+',        # 1.1
            r'^\d+\.\d+\.\d+\s+',   # 1.1.1
            r'^[①②③④⑤⑥⑦⑧⑨⑩]',  # 원숫자
        ]

        for pattern in structural_patterns:
            if re.match(pattern, text):
                return True
        return False

    def _extract_keywords(self, text: str) -> List[str]:
        """키워드 추출"""
        # 한글 단어 추출 (2글자 이상)
        korean_words = re.findall(r'[가-힣]{2,}', text)

        # 영문 단어 추출 (3글자 이상)
        english_words = re.findall(r'[A-Za-z]{3,}', text)

        # 숫자 포함 단어 (문서번호 등)
        alphanumeric = re.findall(r'[A-Za-z0-9-]{3,}', text)

        keywords = korean_words + english_words + alphanumeric
        return list(set(keywords))

    def _optimize_for_embedding(self, text: str, chunk_type: ChunkType) -> str:
        """임베딩을 위한 텍스트 최적화"""
        # 길이 제한
        max_length = self.chunk_size_limits.get(chunk_type, 512)

        if len(text) <= max_length:
            return text

        # chunk_type에 따른 최적화 전략
        if chunk_type == ChunkType.METADATA:
            # 메타데이터는 핵심 정보만
            return text[:max_length]

        elif chunk_type == ChunkType.CONTENT:
            # 내용은 문장 단위로 자르기
            sentences = re.split(r'[.!?]\s+', text)
            optimized = ""
            for sentence in sentences:
                if len(optimized + sentence) <= max_length:
                    optimized += sentence + ". "
                else:
                    break
            return optimized.strip()

        return text[:max_length]

    def _table_to_text(self, table_data: List[List[str]]) -> str:
        """표를 텍스트로 변환"""
        if not table_data:
            return ""

        text_parts = []

        # 첫 번째 행을 헤더로 가정
        if len(table_data) > 0:
            headers = table_data[0]
            text_parts.append(f"표 헤더: {' | '.join(headers)}")

        # 데이터 행들
        for i, row in enumerate(table_data[1:], 1):
            row_text = ' | '.join(str(cell) for cell in row)
            text_parts.append(f"행 {i}: {row_text}")

        return "\n".join(text_parts)

    def _analyze_table_structure(self, table_data: List[List[str]]) -> Dict[str, Any]:
        """표 구조 분석"""
        if not table_data:
            return {}

        return {
            'has_header': True,  # 첫 행이 헤더라고 가정
            'row_count': len(table_data),
            'column_count': len(table_data[0]) if table_data else 0,
            'headers': table_data[0] if table_data else [],
            'data_types': self._analyze_column_types(table_data)
        }

    def _analyze_column_types(self, table_data: List[List[str]]) -> List[str]:
        """컬럼 데이터 타입 분석"""
        if len(table_data) < 2:
            return []

        column_count = len(table_data[0])
        types = []

        for col_idx in range(column_count):
            column_values = [row[col_idx] for row in table_data[1:] if col_idx < len(row)]

            # 숫자인지 확인
            is_numeric = all(re.match(r'^[\d.,]+$', str(val).strip()) for val in column_values if val)

            if is_numeric:
                types.append('numeric')
            else:
                types.append('text')

        return types

    def _optimize_table_for_embedding(self, table_data: List[List[str]], structure_info: Dict[str, Any]) -> str:
        """표 임베딩 최적화"""
        if not table_data:
            return ""

        # 헤더 + 구조 정보로 요약
        headers = structure_info.get('headers', [])
        summary_parts = []

        if headers:
            summary_parts.append(f"표 구성: {' | '.join(headers)}")

        summary_parts.append(f"데이터 {len(table_data)-1}행 {len(headers)}열")

        # 샘플 데이터 (첫 번째 데이터 행)
        if len(table_data) > 1:
            sample_row = table_data[1]
            sample_text = ' | '.join(str(cell) for cell in sample_row)
            summary_parts.append(f"예시: {sample_text}")

        return " / ".join(summary_parts)

    def _optimize_process_for_embedding(self, flow_text: str, steps: List[Dict[str, Any]]) -> str:
        """프로세스 흐름 임베딩 최적화"""
        # 단계 제목만 추출하여 간결하게
        step_titles = []
        for step in steps:
            title = step.get('title', '')
            if title:
                step_titles.append(title)

        if step_titles:
            return f"프로세스 단계: {' → '.join(step_titles)}"

        return flow_text

    def _establish_chunk_relationships(self, chunks: List[DocumentChunk]):
        """청크 간 관계 설정"""
        # 계층 구조 기반으로 부모-자식 관계 설정
        for i, chunk in enumerate(chunks):
            if chunk.chunk_type == ChunkType.HEADER:
                # 같은 레벨이나 하위 레벨의 다음 청크들을 자식으로 설정
                for j in range(i + 1, len(chunks)):
                    next_chunk = chunks[j]

                    # 더 높은 레벨의 헤더가 나오면 중단
                    if (next_chunk.chunk_type == ChunkType.HEADER and
                        next_chunk.hierarchy_level <= chunk.hierarchy_level):
                        break

                    # 직계 자식 관계 설정
                    if (next_chunk.hierarchy_level == chunk.hierarchy_level + 1 or
                        next_chunk.chunk_type in [ChunkType.CONTENT, ChunkType.TABLE]):
                        next_chunk.parent_chunk_id = chunk.chunk_id
                        chunk.child_chunk_ids.append(next_chunk.chunk_id)

    def export_for_vector_db(self, chunks: List[DocumentChunk]) -> List[Dict[str, Any]]:
        """벡터 DB 저장용 형식으로 변환"""
        vector_docs = []

        for chunk in chunks:
            vector_doc = {
                'id': chunk.chunk_id,
                'text': chunk.embedding_text or chunk.text,
                'metadata': {
                    'chunk_type': chunk.chunk_type.value,
                    'hierarchy_level': chunk.hierarchy_level,
                    'parent_chunk_id': chunk.parent_chunk_id,
                    'child_chunk_ids': chunk.child_chunk_ids,
                    'keywords': chunk.relevance_keywords,
                    'confidence': chunk.confidence,
                    **chunk.metadata
                }
            }
            vector_docs.append(vector_doc)

        return vector_docs