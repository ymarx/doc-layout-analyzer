"""
Vectorization Engine - LLM 친화적 메타데이터 벡터화 시스템
DocJSON을 LLM이 효율적으로 소비할 수 있는 다층 벡터 구조로 변환
"""

import logging
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import re

from .docjson import DocJSON, ContentBlock, SemanticInfo, ContentBlockType

logger = logging.getLogger(__name__)


class GranularityLevel(Enum):
    """벡터화 세분화 수준"""
    DOCUMENT = "document"      # 문서 전체 레벨
    SECTION = "section"        # 섹션 레벨
    BLOCK = "block"           # 블록 레벨
    SENTENCE = "sentence"      # 문장 레벨
    SEMANTIC = "semantic"      # 의미 단위 레벨


class ContentType(Enum):
    """콘텐츠 타입"""
    TEXT = "text"
    TABLE = "table"
    DIAGRAM = "diagram"
    CODE = "code"
    FORMULA = "formula"
    REFERENCE = "reference"
    METADATA = "metadata"


@dataclass
class VectorChunk:
    """벡터화 청크"""
    chunk_id: str
    content: str
    content_type: ContentType
    granularity: GranularityLevel
    metadata: Dict[str, Any] = field(default_factory=dict)
    relationships: List[str] = field(default_factory=list)  # 다른 청크와의 관계
    importance_score: float = 1.0
    semantic_density: float = 1.0  # 의미 밀도
    context_window: Dict[str, str] = field(default_factory=dict)  # 문맥 정보
    embedding_hints: Dict[str, Any] = field(default_factory=dict)  # 임베딩 힌트

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        result = asdict(self)
        result['content_type'] = self.content_type.value
        result['granularity'] = self.granularity.value
        return result

    def to_llm_prompt(self) -> str:
        """LLM 프롬프트 형식으로 변환"""
        prompt_parts = []

        # 메타데이터 컨텍스트
        if self.metadata:
            doc_type = self.metadata.get('document_type', '')
            section = self.metadata.get('section_title', '')
            if doc_type:
                prompt_parts.append(f"[문서유형: {doc_type}]")
            if section:
                prompt_parts.append(f"[섹션: {section}]")

        # 콘텐츠 타입 표시
        prompt_parts.append(f"[{self.content_type.value.upper()}]")

        # 주요 콘텐츠
        prompt_parts.append(self.content)

        # 중요도 표시
        if self.importance_score > 1.5:
            prompt_parts.append("[중요]")

        return " ".join(prompt_parts)


@dataclass
class VectorDocument:
    """벡터화된 문서"""
    document_id: str
    title: str
    document_type: str
    chunks: List[VectorChunk] = field(default_factory=list)
    relationships: Dict[str, List[str]] = field(default_factory=dict)  # 청크 간 관계 매핑
    summary: Optional[str] = None
    key_concepts: List[str] = field(default_factory=list)
    hierarchical_structure: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'document_id': self.document_id,
            'title': self.title,
            'document_type': self.document_type,
            'chunks': [chunk.to_dict() for chunk in self.chunks],
            'relationships': self.relationships,
            'summary': self.summary,
            'key_concepts': self.key_concepts,
            'hierarchical_structure': self.hierarchical_structure,
            'created_at': self.created_at
        }


class VectorizationEngine:
    """벡터화 엔진"""

    def __init__(self, output_path: Union[str, Path] = None):
        self.output_path = Path(output_path or "vectorized_docs")
        self.output_path.mkdir(exist_ok=True)

        # 기술문서 특화 설정
        self.technical_patterns = {
            'document_numbers': r'[A-Z]{2,3}-\d{3,}-\d{3,}-\d{3,}',
            'version_numbers': r'(?:Rev\.|Version|v\.?)\s*\d+(?:\.\d+)*',
            'section_numbers': r'\d+(?:\.\d+)*\.',
            'references': r'(?:참조|Reference|Ref\.)\s*[:\-]?\s*[^\n]+',
            'dates': r'\d{2,4}[.\-/]\d{1,2}[.\-/]\d{1,4}',
            'technical_codes': r'[A-Z]{1,3}\d{2,6}(?:[A-Z]\d*)?'
        }

        # 중요도 가중치
        self.importance_weights = {
            'document_title': 3.0,
            'section_header': 2.5,
            'technical_code': 2.0,
            'version_info': 2.0,
            'safety_info': 2.5,
            'procedure_step': 1.8,
            'reference': 1.5,
            'diagram_caption': 1.7,
            'table_header': 1.6,
            'regular_text': 1.0
        }

    async def vectorize_docjson(self, docjson: DocJSON,
                              granularity_levels: List[GranularityLevel] = None) -> VectorDocument:
        """DocJSON을 벡터화"""
        if granularity_levels is None:
            granularity_levels = [GranularityLevel.DOCUMENT, GranularityLevel.SECTION, GranularityLevel.BLOCK]

        logger.info(f"벡터화 시작: {docjson.metadata.title}")

        vector_doc = VectorDocument(
            document_id=docjson.doc_id,
            title=docjson.metadata.title,
            document_type=docjson.metadata.doc_type
        )

        # 1. 문서 레벨 벡터화
        if GranularityLevel.DOCUMENT in granularity_levels:
            doc_chunk = await self._create_document_chunk(docjson)
            vector_doc.chunks.append(doc_chunk)

        # 2. 섹션 레벨 벡터화
        if GranularityLevel.SECTION in granularity_levels:
            section_chunks = await self._create_section_chunks(docjson)
            vector_doc.chunks.extend(section_chunks)

        # 3. 블록 레벨 벡터화
        if GranularityLevel.BLOCK in granularity_levels:
            block_chunks = await self._create_block_chunks(docjson)
            vector_doc.chunks.extend(block_chunks)

        # 4. 의미 단위 벡터화
        if GranularityLevel.SEMANTIC in granularity_levels:
            semantic_chunks = await self._create_semantic_chunks(docjson)
            vector_doc.chunks.extend(semantic_chunks)

        # 5. 관계 분석
        vector_doc.relationships = self._analyze_chunk_relationships(vector_doc.chunks)

        # 6. 계층 구조 생성
        vector_doc.hierarchical_structure = self._create_hierarchical_structure(docjson)

        # 7. 문서 요약 및 핵심 개념
        vector_doc.summary = self._generate_document_summary(vector_doc.chunks)
        vector_doc.key_concepts = self._extract_key_concepts(vector_doc.chunks)

        logger.info(f"벡터화 완료: {len(vector_doc.chunks)} 청크 생성")
        return vector_doc

    async def _create_document_chunk(self, docjson: DocJSON) -> VectorChunk:
        """문서 레벨 청크 생성"""
        # 전체 문서의 대표 텍스트 생성
        title = docjson.metadata.title
        doc_type = docjson.metadata.doc_type

        # 주요 메타데이터 수집
        metadata_text = f"문서제목: {title}, 문서유형: {doc_type}"

        # 섹션 제목들 수집
        section_titles = [section.heading for section in docjson.sections if section.heading]
        if section_titles:
            metadata_text += f", 주요섹션: {', '.join(section_titles[:5])}"

        # 기술적 식별자 추출
        tech_identifiers = []
        for section in docjson.sections:
            for block in section.blocks:
                content_text = block.content.get('text', '')
                tech_identifiers.extend(self._extract_technical_identifiers(content_text))

        if tech_identifiers:
            metadata_text += f", 기술식별자: {', '.join(set(tech_identifiers[:10]))}"

        chunk_id = f"doc_{docjson.doc_id}"

        return VectorChunk(
            chunk_id=chunk_id,
            content=metadata_text,
            content_type=ContentType.METADATA,
            granularity=GranularityLevel.DOCUMENT,
            metadata={
                'document_id': docjson.doc_id,
                'document_type': doc_type,
                'title': title,
                'total_sections': len(docjson.sections),
                'total_blocks': sum(len(s.blocks) for s in docjson.sections)
            },
            importance_score=self.importance_weights['document_title'],
            embedding_hints={
                'focus': 'document_overview',
                'keywords': tech_identifiers[:10]
            }
        )

    async def _create_section_chunks(self, docjson: DocJSON) -> List[VectorChunk]:
        """섹션 레벨 청크 생성"""
        chunks = []

        for section_idx, section in enumerate(docjson.sections):
            # 섹션 콘텐츠 집계
            section_text = f"섹션: {section.heading}\n\n"

            block_texts = []
            for block in section.blocks:
                content_text = block.content.get('text', '')
                if content_text.strip():
                    # 블록 타입에 따른 처리
                    if block.type == ContentBlockType.TABLE:
                        cleaned_text = self._clean_table_html(content_text)
                        block_texts.append(f"[표] {cleaned_text}")
                    elif block.type == ContentBlockType.IMAGE:
                        block_texts.append(f"[다이어그램] {content_text}")
                    else:
                        block_texts.append(content_text)

            section_text += "\n".join(block_texts)

            # 중요도 계산
            importance = self._calculate_section_importance(section, section_text)

            chunk_id = f"sec_{docjson.doc_id}_{section_idx}"

            chunk = VectorChunk(
                chunk_id=chunk_id,
                content=section_text,
                content_type=ContentType.TEXT,
                granularity=GranularityLevel.SECTION,
                metadata={
                    'document_id': docjson.doc_id,
                    'document_type': docjson.metadata.doc_type,
                    'section_title': section.heading,
                    'section_level': section.level,
                    'section_index': section_idx,
                    'block_count': len(section.blocks)
                },
                importance_score=importance,
                context_window={
                    'document_title': docjson.metadata.title,
                    'document_type': docjson.metadata.doc_type
                },
                embedding_hints={
                    'focus': 'section_content',
                    'section_type': self._classify_section_type(section.heading)
                }
            )

            chunks.append(chunk)

        return chunks

    async def _create_block_chunks(self, docjson: DocJSON) -> List[VectorChunk]:
        """블록 레벨 청크 생성"""
        chunks = []

        for section_idx, section in enumerate(docjson.sections):
            for block_idx, block in enumerate(section.blocks):
                content_text = block.content.get('text', '')

                if not content_text.strip():
                    continue

                # 블록 타입에 따른 콘텐츠 타입 결정
                content_type = self._determine_content_type(block)

                # 콘텐츠 전처리
                processed_content = self._preprocess_block_content(block, content_text)

                # 중요도 계산
                importance = self._calculate_block_importance(block, section)

                chunk_id = f"blk_{docjson.doc_id}_{section_idx}_{block_idx}"

                chunk = VectorChunk(
                    chunk_id=chunk_id,
                    content=processed_content,
                    content_type=content_type,
                    granularity=GranularityLevel.BLOCK,
                    metadata={
                        'document_id': docjson.doc_id,
                        'document_type': docjson.metadata.doc_type,
                        'section_title': section.heading,
                        'section_index': section_idx,
                        'block_index': block_idx,
                        'block_type': block.type,
                        'confidence': block.content.get('confidence', 1.0)
                    },
                    importance_score=importance,
                    context_window={
                        'document_title': docjson.metadata.title,
                        'section_title': section.heading,
                        'prev_block': self._get_previous_block_summary(docjson, section_idx, block_idx),
                        'next_block': self._get_next_block_summary(docjson, section_idx, block_idx)
                    },
                    embedding_hints={
                        'focus': 'detailed_content',
                        'content_structure': self._analyze_content_structure(content_text)
                    }
                )

                chunks.append(chunk)

        return chunks

    async def _create_semantic_chunks(self, docjson: DocJSON) -> List[VectorChunk]:
        """의미 단위 청크 생성"""
        chunks = []

        for section_idx, section in enumerate(docjson.sections):
            for block_idx, block in enumerate(section.blocks):
                content_text = block.content.get('text', '')

                if not content_text.strip():
                    continue

                # 의미 단위로 분할
                semantic_units = self._split_into_semantic_units(content_text, block)

                for unit_idx, unit in enumerate(semantic_units):
                    if len(unit['text'].strip()) < 10:  # 너무 짧은 단위는 제외
                        continue

                    chunk_id = f"sem_{docjson.doc_id}_{section_idx}_{block_idx}_{unit_idx}"

                    chunk = VectorChunk(
                        chunk_id=chunk_id,
                        content=unit['text'],
                        content_type=ContentType.TEXT,
                        granularity=GranularityLevel.SEMANTIC,
                        metadata={
                            'document_id': docjson.doc_id,
                            'document_type': docjson.metadata.doc_type,
                            'section_title': section.heading,
                            'semantic_type': unit['type'],
                            'parent_block_id': f"blk_{docjson.doc_id}_{section_idx}_{block_idx}"
                        },
                        importance_score=unit['importance'],
                        semantic_density=unit['density'],
                        embedding_hints={
                            'focus': 'semantic_precision',
                            'semantic_role': unit['type']
                        }
                    )

                    chunks.append(chunk)

        return chunks

    def _extract_technical_identifiers(self, text: str) -> List[str]:
        """기술적 식별자 추출"""
        identifiers = []

        for pattern_name, pattern in self.technical_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            identifiers.extend(matches)

        return identifiers

    def _clean_table_html(self, html_text: str) -> str:
        """HTML 표 내용 정리"""
        # HTML 태그 제거하고 셀 내용만 추출
        import re
        # 간단한 HTML 태그 제거
        text = re.sub(r'<[^>]+>', ' ', html_text)
        # 여러 공백을 하나로
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _calculate_section_importance(self, section, section_text: str) -> float:
        """섹션 중요도 계산"""
        base_importance = self.importance_weights['section_header']

        # 섹션 제목 기반 가중치
        title_lower = section.heading.lower()

        if any(keyword in title_lower for keyword in ['목적', 'purpose', '개요']):
            base_importance *= 1.3
        elif any(keyword in title_lower for keyword in ['안전', 'safety', '위험']):
            base_importance *= 1.4
        elif any(keyword in title_lower for keyword in ['절차', 'procedure', '방법']):
            base_importance *= 1.2

        # 기술적 내용 밀도
        tech_count = len(self._extract_technical_identifiers(section_text))
        if tech_count > 5:
            base_importance *= 1.1

        return min(base_importance, 3.0)  # 최대값 제한

    def _classify_section_type(self, heading: str) -> str:
        """섹션 타입 분류"""
        heading_lower = heading.lower()

        if any(keyword in heading_lower for keyword in ['목적', 'purpose']):
            return 'purpose'
        elif any(keyword in heading_lower for keyword in ['범위', 'scope']):
            return 'scope'
        elif any(keyword in heading_lower for keyword in ['절차', 'procedure']):
            return 'procedure'
        elif any(keyword in heading_lower for keyword in ['안전', 'safety']):
            return 'safety'
        elif any(keyword in heading_lower for keyword in ['참조', 'reference']):
            return 'reference'
        else:
            return 'general'

    def _determine_content_type(self, block: ContentBlock) -> ContentType:
        """블록의 콘텐츠 타입 결정"""
        if block.type == ContentBlockType.TABLE:
            return ContentType.TABLE
        elif block.type == ContentBlockType.IMAGE:
            return ContentType.DIAGRAM
        elif any(keyword in block.content.get('text', '').lower()
                for keyword in ['참조', 'reference', 'ref.']):
            return ContentType.REFERENCE
        else:
            return ContentType.TEXT

    def _preprocess_block_content(self, block: ContentBlock, content_text: str) -> str:
        """블록 콘텐츠 전처리"""
        if block.type == 'table':
            # 표 내용 정리
            return self._clean_table_html(content_text)
        elif block.type == 'diagram':
            # 다이어그램 설명 개선
            return f"다이어그램 설명: {content_text}"
        else:
            # 일반 텍스트 정리
            return content_text.strip()

    def _calculate_block_importance(self, block: ContentBlock, section) -> float:
        """블록 중요도 계산"""
        base_importance = self.importance_weights['regular_text']

        # 블록 타입에 따른 가중치
        if block.type == 'table':
            base_importance = self.importance_weights['table_header']
        elif block.type == 'diagram':
            base_importance = self.importance_weights['diagram_caption']

        # 시맨틱 정보 기반 가중치
        if block.semantic:
            if block.semantic.entities:
                base_importance *= 1.1
            if block.semantic.keywords:
                base_importance *= 1.05

        return base_importance

    def _split_into_semantic_units(self, text: str, block: ContentBlock) -> List[Dict[str, Any]]:
        """텍스트를 의미 단위로 분할"""
        units = []

        # 문장 단위로 분할
        sentences = re.split(r'[.!?]\s+', text)

        for sentence in sentences:
            if len(sentence.strip()) < 10:
                continue

            # 의미 단위 분류
            unit_type = self._classify_semantic_unit(sentence)
            importance = self._calculate_semantic_importance(sentence, unit_type)
            density = self._calculate_semantic_density(sentence)

            units.append({
                'text': sentence.strip(),
                'type': unit_type,
                'importance': importance,
                'density': density
            })

        return units

    def _classify_semantic_unit(self, text: str) -> str:
        """의미 단위 분류"""
        text_lower = text.lower()

        if any(pattern in text_lower for pattern in ['단계', 'step', '절차']):
            return 'procedure_step'
        elif any(pattern in text_lower for pattern in ['주의', '경고', '위험', 'caution', 'warning']):
            return 'safety_notice'
        elif re.search(self.technical_patterns['document_numbers'], text):
            return 'technical_reference'
        elif re.search(r'\d+\.\s', text):
            return 'numbered_item'
        else:
            return 'general_statement'

    def _calculate_semantic_importance(self, text: str, unit_type: str) -> float:
        """의미 단위 중요도 계산"""
        base_scores = {
            'procedure_step': 1.8,
            'safety_notice': 2.5,
            'technical_reference': 2.0,
            'numbered_item': 1.5,
            'general_statement': 1.0
        }

        return base_scores.get(unit_type, 1.0)

    def _calculate_semantic_density(self, text: str) -> float:
        """의미 밀도 계산"""
        # 기술 용어 밀도 계산
        tech_identifiers = self._extract_technical_identifiers(text)
        word_count = len(text.split())

        if word_count == 0:
            return 0.0

        density = len(tech_identifiers) / word_count
        return min(density * 10, 2.0)  # 정규화

    def _analyze_chunk_relationships(self, chunks: List[VectorChunk]) -> Dict[str, List[str]]:
        """청크 간 관계 분석"""
        relationships = {}

        for chunk in chunks:
            related_chunks = []

            # 같은 섹션 내 청크들
            section_chunks = [c for c in chunks
                            if c.metadata.get('section_index') == chunk.metadata.get('section_index')
                            and c.chunk_id != chunk.chunk_id]

            related_chunks.extend([c.chunk_id for c in section_chunks])

            # 기술적 식별자 공유하는 청크들
            chunk_identifiers = set(self._extract_technical_identifiers(chunk.content))
            if chunk_identifiers:
                for other_chunk in chunks:
                    if other_chunk.chunk_id == chunk.chunk_id:
                        continue

                    other_identifiers = set(self._extract_technical_identifiers(other_chunk.content))
                    if chunk_identifiers & other_identifiers:  # 교집합이 있으면
                        related_chunks.append(other_chunk.chunk_id)

            relationships[chunk.chunk_id] = list(set(related_chunks))

        return relationships

    def _create_hierarchical_structure(self, docjson: DocJSON) -> Dict[str, Any]:
        """계층 구조 생성"""
        structure = {
            'document': {
                'id': docjson.doc_id,
                'title': docjson.metadata.title,
                'type': docjson.metadata.doc_type,
                'sections': []
            }
        }

        for section_idx, section in enumerate(docjson.sections):
            section_structure = {
                'id': f"sec_{docjson.doc_id}_{section_idx}",
                'title': section.heading,
                'level': section.level,
                'blocks': []
            }

            for block_idx, block in enumerate(section.blocks):
                block_structure = {
                    'id': f"blk_{docjson.doc_id}_{section_idx}_{block_idx}",
                    'type': block.type,
                    'importance': self._calculate_block_importance(block, section)
                }
                section_structure['blocks'].append(block_structure)

            structure['document']['sections'].append(section_structure)

        return structure

    def _generate_document_summary(self, chunks: List[VectorChunk]) -> str:
        """문서 요약 생성"""
        # 높은 중요도 청크들로 요약 생성
        important_chunks = sorted(chunks, key=lambda x: x.importance_score, reverse=True)[:5]

        summary_parts = []
        for chunk in important_chunks:
            if chunk.granularity == GranularityLevel.DOCUMENT:
                summary_parts.append(chunk.content)
            elif chunk.granularity == GranularityLevel.SECTION:
                section_title = chunk.metadata.get('section_title', '')
                if section_title:
                    summary_parts.append(f"{section_title} 섹션")

        return ". ".join(summary_parts)

    def _extract_key_concepts(self, chunks: List[VectorChunk]) -> List[str]:
        """핵심 개념 추출"""
        all_identifiers = []

        for chunk in chunks:
            identifiers = self._extract_technical_identifiers(chunk.content)
            all_identifiers.extend(identifiers)

        # 빈도 기반 핵심 개념 선별
        from collections import Counter
        concept_counts = Counter(all_identifiers)

        return [concept for concept, count in concept_counts.most_common(20)]

    # Helper methods
    def _get_previous_block_summary(self, docjson: DocJSON, section_idx: int, block_idx: int) -> str:
        """이전 블록 요약"""
        if block_idx > 0:
            prev_block = docjson.sections[section_idx].blocks[block_idx - 1]
            content = prev_block.content.get('text', '')
            return content[:100] + "..." if len(content) > 100 else content
        return ""

    def _get_next_block_summary(self, docjson: DocJSON, section_idx: int, block_idx: int) -> str:
        """다음 블록 요약"""
        section = docjson.sections[section_idx]
        if block_idx < len(section.blocks) - 1:
            next_block = section.blocks[block_idx + 1]
            content = next_block.content.get('text', '')
            return content[:100] + "..." if len(content) > 100 else content
        return ""

    def _analyze_content_structure(self, text: str) -> Dict[str, Any]:
        """콘텐츠 구조 분석"""
        return {
            'has_numbering': bool(re.search(r'\d+\.', text)),
            'has_bullet_points': bool(re.search(r'[•\-\*]\s', text)),
            'has_technical_refs': bool(self._extract_technical_identifiers(text)),
            'sentence_count': len(re.split(r'[.!?]', text)),
            'paragraph_count': len(text.split('\n\n'))
        }

    async def save_vectorized_document(self, vector_doc: VectorDocument) -> Path:
        """벡터화된 문서 저장"""
        output_file = self.output_path / f"{vector_doc.document_id}_vectorized.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(vector_doc.to_dict(), f, ensure_ascii=False, indent=2)

        logger.info(f"벡터화된 문서 저장: {output_file}")
        return output_file

    async def load_vectorized_document(self, document_id: str) -> Optional[VectorDocument]:
        """벡터화된 문서 로드"""
        vector_file = self.output_path / f"{document_id}_vectorized.json"

        if not vector_file.exists():
            return None

        try:
            with open(vector_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # VectorDocument 재구성
            chunks = [VectorChunk(**chunk_data) for chunk_data in data['chunks']]

            return VectorDocument(
                document_id=data['document_id'],
                title=data['title'],
                document_type=data['document_type'],
                chunks=chunks,
                relationships=data.get('relationships', {}),
                summary=data.get('summary'),
                key_concepts=data.get('key_concepts', []),
                hierarchical_structure=data.get('hierarchical_structure', {}),
                created_at=data.get('created_at', '')
            )

        except Exception as e:
            logger.error(f"벡터화된 문서 로드 실패: {e}")
            return None