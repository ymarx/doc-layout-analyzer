"""
Enhanced Document Parser
템플릿 기반 + 패턴 인식 + RAG 최적화 통합 파서
"""

import logging
import time
import asyncio
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

from .unified_docx_parser import UnifiedDocxParser, ParseResult, ProcessingOptions
from ..templates.document_template import TemplateManager, template_manager
from ..rag.document_chunker import RAGDocumentProcessor, DocumentChunk
from ..core.docjson import DocJSON

logger = logging.getLogger(__name__)

class EnhancedParseResult:
    """확장된 파싱 결과"""

    def __init__(self):
        self.success: bool = False
        self.docjson: Optional[DocJSON] = None
        self.template_extracted: Dict[str, Any] = {}
        self.rag_chunks: List[DocumentChunk] = []
        self.vector_documents: List[Dict[str, Any]] = []
        self.template_id: Optional[str] = None
        self.template_confidence: float = 0.0
        self.processing_time: float = 0.0
        self.error: Optional[str] = None
        self.metadata: Dict[str, Any] = {}

class EnhancedDocumentParser:
    """향상된 문서 파서"""

    def __init__(self):
        self.base_parser = UnifiedDocxParser()
        self.template_manager = template_manager
        self.rag_processor = RAGDocumentProcessor()

    async def parse(self,
                   file_path: Union[str, Path],
                   options: ProcessingOptions = None,
                   enable_rag_optimization: bool = True) -> EnhancedParseResult:
        """향상된 문서 파싱"""
        start_time = time.time()
        result = EnhancedParseResult()

        try:
            # 1. 기본 파싱 실행
            logger.info("기본 문서 파싱 시작")
            base_result = await self.base_parser.parse(file_path, options)

            if not base_result.success:
                result.error = base_result.error
                result.processing_time = time.time() - start_time
                return result

            # 2. 템플릿 매칭 및 요소 추출
            logger.info("템플릿 매칭 시작")
            raw_content = base_result.content.get('raw_content', {})
            template_id, template_confidence = self.template_manager.match_template(raw_content)

            result.template_id = template_id
            result.template_confidence = template_confidence

            if template_id and template_confidence > 0.5:
                logger.info(f"템플릿 매칭됨: {template_id} (신뢰도: {template_confidence:.2f})")
                template_extracted = self.template_manager.extract_elements(raw_content, template_id)
                result.template_extracted = template_extracted
            else:
                logger.warning("적합한 템플릿을 찾지 못함")
                result.template_extracted = {}

            # 3. 개선된 DocJSON 생성
            logger.info("개선된 DocJSON 생성")
            enhanced_docjson = self._create_enhanced_docjson(
                base_result.content.get('docjson'),
                result.template_extracted,
                raw_content
            )
            result.docjson = enhanced_docjson

            # 4. RAG 최적화 (선택사항)
            if enable_rag_optimization and enhanced_docjson:
                logger.info("RAG 최적화 청킹 시작")
                docjson_dict = enhanced_docjson.to_dict() if hasattr(enhanced_docjson, 'to_dict') else enhanced_docjson

                rag_chunks = self.rag_processor.process_document(
                    docjson_dict,
                    result.template_extracted
                )
                result.rag_chunks = rag_chunks

                # 벡터 DB용 문서 변환
                vector_docs = self.rag_processor.export_for_vector_db(rag_chunks)
                result.vector_documents = vector_docs

                logger.info(f"RAG 청킹 완료: {len(rag_chunks)}개 청크 생성")

            # 5. 메타데이터 설정
            result.metadata = {
                **base_result.metadata,
                'template_used': template_id,
                'template_confidence': template_confidence,
                'rag_chunks_count': len(result.rag_chunks),
                'enhancement_version': '1.0'
            }

            result.success = True
            result.processing_time = time.time() - start_time

            logger.info(f"향상된 파싱 완료 (처리시간: {result.processing_time:.3f}초)")

        except Exception as e:
            logger.error(f"향상된 파싱 실패: {e}")
            result.error = str(e)
            result.processing_time = time.time() - start_time

        return result

    def _create_enhanced_docjson(self,
                                base_docjson: Any,
                                template_extracted: Dict[str, Any],
                                raw_content: Dict[str, Any]) -> Optional[DocJSON]:
        """템플릿 정보를 반영한 개선된 DocJSON 생성"""

        if not base_docjson:
            return None

        try:
            # 기본 DocJSON이 dict인 경우 처리
            if isinstance(base_docjson, dict):
                docjson_data = base_docjson
            else:
                docjson_data = base_docjson.to_dict() if hasattr(base_docjson, 'to_dict') else base_docjson

            # 메타데이터 강화
            if 'metadata' in docjson_data and template_extracted:
                metadata = docjson_data['metadata']

                # 템플릿에서 추출한 정보로 메타데이터 업데이트
                if template_extracted.get('document_number'):
                    metadata['document_number'] = template_extracted['document_number']
                if template_extracted.get('effective_date'):
                    metadata['effective_date'] = template_extracted['effective_date']
                if template_extracted.get('revision'):
                    metadata['revision'] = template_extracted['revision']
                if template_extracted.get('author'):
                    metadata['author'] = template_extracted['author']

                # 제목 개선 (템플릿에서 더 정확한 제목 추출 가능)
                if template_extracted.get('title'):
                    metadata['title'] = template_extracted['title']

            # 섹션 구조 강화
            if 'sections' in docjson_data and template_extracted.get('section_headers'):
                self._enhance_section_structure(docjson_data['sections'], template_extracted['section_headers'])

            # 프로세스 흐름 정보 추가
            if raw_content.get('process_flows'):
                if 'metadata' not in docjson_data:
                    docjson_data['metadata'] = {}
                docjson_data['metadata']['process_flows'] = raw_content['process_flows']

            # DocJSON 객체로 변환 (필요한 경우)
            if isinstance(docjson_data, dict):
                from ..core.docjson import DocJSON
                return DocJSON.from_dict(docjson_data)

            return docjson_data

        except Exception as e:
            logger.error(f"DocJSON 강화 실패: {e}")
            return base_docjson

    def _enhance_section_structure(self, sections: List[Dict], section_headers: List[Dict]):
        """섹션 구조 강화"""

        # 템플릿에서 추출한 구조적 헤더들을 이용해 섹션 구조 개선
        hierarchy_map = {}

        for header in section_headers:
            level = header.get('level', 1)
            text = header.get('text', '')
            match_info = header.get('match', '')

            hierarchy_map[text] = {
                'level': level,
                'match': match_info,
                'type': 'structural_header'
            }

        # 기존 섹션들과 매칭하여 구조 정보 보강
        for section in sections:
            heading = section.get('heading', '')

            # 정확히 매칭되는 헤더 찾기
            if heading in hierarchy_map:
                section['enhanced_level'] = hierarchy_map[heading]['level']
                section['structural_type'] = 'template_matched'
            else:
                # 부분 매칭 시도
                for template_header, info in hierarchy_map.items():
                    if template_header in heading or heading in template_header:
                        section['enhanced_level'] = info['level']
                        section['structural_type'] = 'partial_matched'
                        break

    def get_template_info(self) -> Dict[str, Any]:
        """현재 로드된 템플릿 정보 반환"""
        templates_info = {}

        for template_id, template in self.template_manager.templates.items():
            templates_info[template_id] = {
                'name': template.name,
                'description': template.description,
                'version': template.version,
                'element_count': len(template.elements)
            }

        return templates_info

    def add_custom_template(self, template_data: Dict[str, Any]) -> bool:
        """사용자 정의 템플릿 추가"""
        try:
            # 템플릿 검증 및 저장 로직
            # (실제 구현에서는 더 상세한 검증 필요)
            template_id = template_data.get('template_id')
            if not template_id:
                return False

            # 템플릿 파일로 저장
            template_path = self.template_manager.templates_dir / f"{template_id}.json"

            import json
            with open(template_path, 'w', encoding='utf-8') as f:
                json.dump(template_data, f, ensure_ascii=False, indent=2)

            # 템플릿 다시 로드
            template = self.template_manager.load_template(template_path)
            if template:
                self.template_manager.templates[template_id] = template
                return True

        except Exception as e:
            logger.error(f"사용자 정의 템플릿 추가 실패: {e}")

        return False

    async def batch_process(self,
                           file_paths: List[Union[str, Path]],
                           options: ProcessingOptions = None) -> List[EnhancedParseResult]:
        """배치 처리"""

        results = []

        # 동시 처리 (최대 3개)
        semaphore = asyncio.Semaphore(3)

        async def process_single(file_path):
            async with semaphore:
                return await self.parse(file_path, options)

        tasks = [process_single(fp) for fp in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 예외 처리
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_result = EnhancedParseResult()
                error_result.error = str(result)
                error_result.success = False
                processed_results.append(error_result)
            else:
                processed_results.append(result)

        return processed_results