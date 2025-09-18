"""
Integrated Pipeline - 통합 문서 처리 파이프라인
PDF OCR, DOCX 고급 파싱, 벡터화까지 전체 워크플로우 관리
"""

import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

from ..parsers.pdf_parser import PDFParser
from ..parsers.docx_enhanced_parser import DocxEnhancedParser
from ..analyzers.layout_analyzer import LayoutAnalyzer
from ..core.docjson import DocJSON
from ..core.vectorization_engine import VectorizationEngine, VectorDocument
from ..core.user_annotations import UserAnnotationManager, DocumentAnnotation
from ..core.template_manager import TemplateManager, TemplateMatchResult
from ..core.device_manager import DeviceManager
from ..core.config import ConfigManager

logger = logging.getLogger(__name__)


class ProcessingMode(Enum):
    """처리 모드"""
    FAST = "fast"           # 빠른 처리 (기본 OCR)
    ENHANCED = "enhanced"   # 고급 처리 (강화된 의미 분석)
    VECTORIZE = "vectorize" # 벡터화 포함
    COMPLETE = "complete"   # 전체 기능 (주석 + 벡터화)


class DocumentType(Enum):
    """문서 타입"""
    PDF = "pdf"
    DOCX = "docx"
    AUTO = "auto"


@dataclass
class PipelineConfig:
    """파이프라인 설정"""
    processing_mode: ProcessingMode = ProcessingMode.ENHANCED
    document_type: DocumentType = DocumentType.AUTO
    enable_ocr: bool = True
    enable_diagrams: bool = True
    enable_vectorization: bool = False
    enable_user_annotations: bool = False
    enable_template_matching: bool = True  # 템플릿 매칭 활성화
    auto_apply_template: bool = True       # 자동 템플릿 적용
    template_confidence_threshold: float = 0.6  # 템플릿 적용 최소 신뢰도
    output_formats: List[str] = None
    custom_template_id: Optional[str] = None

    def __post_init__(self):
        if self.output_formats is None:
            self.output_formats = ["docjson"]


@dataclass
class PipelineResult:
    """파이프라인 결과"""
    success: bool
    document_id: str
    docjson: Optional[DocJSON] = None
    vector_document: Optional[VectorDocument] = None
    annotation: Optional[DocumentAnnotation] = None
    template_match: Optional[TemplateMatchResult] = None  # 템플릿 매칭 결과
    processing_time: float = 0.0
    intermediate_files: Dict[str, Path] = None
    metadata: Dict[str, Any] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.intermediate_files is None:
            self.intermediate_files = {}
        if self.metadata is None:
            self.metadata = {}


class IntegratedPipeline:
    """통합 문서 처리 파이프라인"""

    def __init__(self,
                 device_manager: DeviceManager = None,
                 config_manager: ConfigManager = None,
                 output_dir: Union[str, Path] = None):

        self.device_manager = device_manager or DeviceManager()
        self.config_manager = config_manager or ConfigManager()
        self.output_dir = Path(output_dir or "pipeline_output")
        self.output_dir.mkdir(exist_ok=True)

        # 컴포넌트 초기화
        self.pdf_parser = PDFParser()
        self.docx_parser = DocxEnhancedParser()
        self.layout_analyzer = LayoutAnalyzer(device_manager, config_manager)
        self.vectorization_engine = VectorizationEngine(self.output_dir / "vectorized")
        self.annotation_manager = UserAnnotationManager(self.output_dir / "annotations")
        self.template_manager = TemplateManager(self.output_dir / "annotations" / "templates")

        logger.info("통합 파이프라인 초기화 완료")

    async def process_document(self,
                             file_path: Union[str, Path],
                             config: PipelineConfig = None) -> PipelineResult:
        """문서 처리 메인 함수"""
        start_time = asyncio.get_event_loop().time()
        file_path = Path(file_path)

        if config is None:
            config = PipelineConfig()

        logger.info(f"문서 처리 시작: {file_path} (모드: {config.processing_mode.value})")

        result = PipelineResult(
            success=False,
            document_id="",
            processing_time=0.0
        )

        try:
            # 1. 문서 타입 결정
            doc_type = self._determine_document_type(file_path, config.document_type)
            result.metadata['detected_type'] = doc_type.value

            # 2. 단계별 처리
            if doc_type == DocumentType.PDF:
                result = await self._process_pdf_pipeline(file_path, config, result)
            elif doc_type == DocumentType.DOCX:
                result = await self._process_docx_pipeline(file_path, config, result)
            else:
                result.error = f"지원하지 않는 문서 타입: {file_path.suffix}"
                return result

            # 3. 후처리 (벡터화, 주석)
            if result.success and result.docjson:
                result = await self._post_process(result, config)

            # 4. 결과 저장
            if result.success:
                await self._save_results(result, config)

            result.processing_time = asyncio.get_event_loop().time() - start_time
            logger.info(f"문서 처리 완료: {result.processing_time:.2f}초")

        except Exception as e:
            logger.error(f"문서 처리 실패: {e}")
            result.error = str(e)
            result.processing_time = asyncio.get_event_loop().time() - start_time

        return result

    def _determine_document_type(self, file_path: Path, config_type: DocumentType) -> DocumentType:
        """문서 타입 결정"""
        if config_type != DocumentType.AUTO:
            return config_type

        suffix = file_path.suffix.lower()
        if suffix == '.pdf':
            return DocumentType.PDF
        elif suffix in ['.docx', '.doc']:
            return DocumentType.DOCX
        else:
            raise ValueError(f"지원하지 않는 파일 형식: {suffix}")

    async def _process_pdf_pipeline(self, file_path: Path, config: PipelineConfig, result: PipelineResult) -> PipelineResult:
        """PDF 처리 파이프라인"""
        try:
            logger.info("PDF 파이프라인 실행")

            # 1. PDF 기본 파싱
            pdf_result = await self.pdf_parser.parse(file_path)
            if not pdf_result.success:
                result.error = f"PDF 파싱 실패: {pdf_result.error}"
                return result

            # 2. 레이아웃 분석 (OCR 포함)
            if config.enable_ocr:
                layout_result = await self.layout_analyzer.analyze_document(
                    file_path,
                    pdf_result.content.get('page_images', [])
                )

                if not layout_result.success:
                    result.error = f"레이아웃 분석 실패: {layout_result.error}"
                    return result

                # DocJSON 생성
                docjson = await self._create_docjson_from_layout(
                    file_path, layout_result.elements, pdf_result.metadata
                )
            else:
                # OCR 없이 기본 DocJSON 생성
                docjson = await self._create_basic_docjson(file_path, pdf_result.content)

            result.docjson = docjson
            result.document_id = docjson.doc_id
            result.success = True

            logger.info(f"PDF 처리 완료: {len(docjson.sections)} 섹션")

        except Exception as e:
            logger.error(f"PDF 파이프라인 실패: {e}")
            result.error = str(e)

        return result

    async def _process_docx_pipeline(self, file_path: Path, config: PipelineConfig, result: PipelineResult) -> PipelineResult:
        """DOCX 처리 파이프라인"""
        try:
            logger.info("DOCX 고급 파이프라인 실행")

            # DOCX 고급 파싱 (다이어그램 포함)
            docx_result = await self.docx_parser.parse(file_path)

            if not docx_result.success:
                result.error = f"DOCX 파싱 실패: {docx_result.error}"
                return result

            result.docjson = docx_result.content
            result.document_id = docx_result.content.doc_id
            result.success = True
            result.metadata.update(docx_result.metadata)

            logger.info(f"DOCX 처리 완료: {len(docx_result.content.sections)} 섹션, "
                       f"{result.metadata.get('diagrams_count', 0)} 다이어그램")

        except Exception as e:
            logger.error(f"DOCX 파이프라인 실패: {e}")
            result.error = str(e)

        return result

    async def _post_process(self, result: PipelineResult, config: PipelineConfig) -> PipelineResult:
        """후처리 (벡터화, 주석, 템플릿 매칭 등)"""
        try:
            # 1. 템플릿 매칭
            if config.enable_template_matching and result.docjson:
                logger.info("문서 템플릿 매칭 시작")

                # DocJSON을 딕셔너리로 변환하여 템플릿 매칭
                document_content = result.docjson.to_dict()
                doc_type = result.docjson.metadata.doc_type

                # 지정된 템플릿이 있으면 우선 사용
                if config.custom_template_id:
                    if config.custom_template_id in self.template_manager.templates:
                        template = self.template_manager.templates[config.custom_template_id]
                        result.template_match = self.template_manager._match_template(template, document_content)
                        logger.info(f"지정된 템플릿 사용: {template.name}")
                else:
                    # 자동 템플릿 매칭
                    result.template_match = self.template_manager.find_best_template(document_content, doc_type)

                if result.template_match:
                    logger.info(f"템플릿 매칭 성공: {result.template_match.template_name} "
                               f"(신뢰도: {result.template_match.confidence:.2f})")

                    # 신뢰도가 충분하면 자동 적용
                    if config.auto_apply_template and result.template_match.confidence >= config.template_confidence_threshold:
                        logger.info("템플릿 자동 적용")
                        applied_annotation = self.template_manager.apply_template_to_document(
                            result.template_match, document_content
                        )
                        applied_annotation.document_path = str(result.docjson.metadata.source.get('path', ''))
                        result.annotation = applied_annotation

                        # 템플릿 기반 주석 저장
                        self.annotation_manager.save_annotation(applied_annotation)

                        result.metadata['template_applied'] = True
                        result.metadata['template_name'] = result.template_match.template_name
                        result.metadata['template_confidence'] = result.template_match.confidence
                else:
                    logger.info("적합한 템플릿을 찾을 수 없음")

            # 2. 벡터화
            if config.enable_vectorization or config.processing_mode in [ProcessingMode.VECTORIZE, ProcessingMode.COMPLETE]:
                logger.info("문서 벡터화 시작")
                vector_doc = await self.vectorization_engine.vectorize_docjson(result.docjson)
                result.vector_document = vector_doc

                # 벡터화 문서 저장
                vector_file = await self.vectorization_engine.save_vectorized_document(vector_doc)
                result.intermediate_files['vectorized'] = vector_file

            # 3. 사용자 주석 처리 (템플릿이 적용되지 않은 경우)
            if (config.enable_user_annotations or config.processing_mode == ProcessingMode.COMPLETE) and not result.annotation:
                logger.info("사용자 주석 시스템 준비")

                # 기존 주석 확인
                source_path = str(result.docjson.metadata.source.get('path', '')) if result.docjson.metadata.source else ''
                annotation = self.annotation_manager.load_annotation_by_path(source_path)

                if not annotation:
                    # 새 주석 생성
                    annotation = self.annotation_manager.create_annotation(
                        source_path,
                        config.custom_template_id
                    )

                    # 문서 타입에 따른 기본 필드 추가
                    if result.docjson.metadata.doc_type:
                        common_fields = self.annotation_manager.get_common_fields_for_type(
                            result.docjson.metadata.doc_type
                        )
                        annotation.fields.extend(common_fields)
                        self.annotation_manager.save_annotation(annotation)

                result.annotation = annotation

        except Exception as e:
            logger.error(f"후처리 실패: {e}")
            # 후처리 실패는 전체 결과를 실패로 만들지 않음
            result.metadata['post_processing_error'] = str(e)

        return result

    async def _save_results(self, result: PipelineResult, config: PipelineConfig) -> None:
        """결과 저장"""
        try:
            output_base = self.output_dir / result.document_id

            # DocJSON 저장
            if "docjson" in config.output_formats and result.docjson:
                docjson_file = output_base.with_suffix('.docjson')
                docjson_content = result.docjson.to_dict()

                import json
                with open(docjson_file, 'w', encoding='utf-8') as f:
                    json.dump(docjson_content, f, ensure_ascii=False, indent=2)

                result.intermediate_files['docjson'] = docjson_file

            # XML 중간 형식 저장 (선택적)
            if "xml" in config.output_formats:
                xml_file = await self._export_to_xml(result.docjson, output_base)
                result.intermediate_files['xml'] = xml_file

            # 처리 메타데이터 저장
            metadata_file = output_base.with_suffix('.metadata.json')
            import json

            # 메타데이터를 JSON 직렬화 가능한 형태로 변환
            serializable_metadata = self._make_metadata_serializable(result.metadata)

            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'processing_config': {
                        'mode': config.processing_mode.value,
                        'document_type': config.document_type.value,
                        'enable_ocr': config.enable_ocr,
                        'enable_diagrams': config.enable_diagrams,
                        'enable_vectorization': config.enable_vectorization
                    },
                    'results': {
                        'success': result.success,
                        'processing_time': result.processing_time,
                        'document_id': result.document_id,
                        'sections_count': len(result.docjson.sections) if result.docjson else 0,
                        'vectorization_enabled': result.vector_document is not None
                    },
                    'metadata': serializable_metadata
                }, f, ensure_ascii=False, indent=2)

            result.intermediate_files['metadata'] = metadata_file

            logger.info(f"결과 저장 완료: {len(result.intermediate_files)} 파일")

        except Exception as e:
            logger.error(f"결과 저장 실패: {e}")

    def _make_metadata_serializable(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """메타데이터를 JSON 직렬화 가능한 형태로 변환"""
        serializable_metadata = {}

        for key, value in metadata.items():
            try:
                if hasattr(value, '__dict__'):
                    # dataclass나 객체인 경우 dictionary로 변환
                    if hasattr(value, 'headers') and hasattr(value, 'footers'):  # DocumentStructure
                        serializable_metadata[key] = {
                            'headers': value.headers,
                            'footers': value.footers,
                            'sections': value.sections,
                            'tables': value.tables,
                            'diagrams': value.diagrams,
                            'numbering_patterns': value.numbering_patterns,
                            'styles': value.styles
                        }
                    else:
                        # 일반 객체는 __dict__ 사용
                        serializable_metadata[key] = vars(value)
                elif isinstance(value, (list, dict, str, int, float, bool, type(None))):
                    # 기본 JSON 타입들
                    serializable_metadata[key] = value
                else:
                    # 기타 타입은 문자열로 변환
                    serializable_metadata[key] = str(value)
            except Exception as e:
                # 변환 실패시 키만 저장
                serializable_metadata[key] = f"<serialization_error: {type(value).__name__}>"

        return serializable_metadata

    async def _create_docjson_from_layout(self, file_path: Path, layout_elements, pdf_metadata) -> DocJSON:
        """레이아웃 분석 결과로부터 DocJSON 생성"""
        from ..core.docjson import DocJSONConverter

        converter = DocJSONConverter()
        docjson = await converter.from_layout_elements(
            layout_elements,
            str(file_path),
            pdf_metadata
        )

        return docjson

    async def _create_basic_docjson(self, file_path: Path, pdf_content) -> DocJSON:
        """기본 DocJSON 생성 (OCR 없이)"""
        from ..core.docjson import DocJSON, DocumentSection, ContentBlock, BoundingBox

        docjson = DocJSON()
        docjson.metadata.title = file_path.stem
        docjson.metadata.source.file = file_path.name
        docjson.metadata.source.path = str(file_path)

        # 간단한 섹션 생성
        section = DocumentSection(
            id="section_basic",
            path=["0"],
            heading="Document Content",
            level=1
        )

        # 텍스트가 있으면 블록으로 추가
        if 'text' in pdf_content and pdf_content['text']:
            block = ContentBlock(
                block_type="text",
                page=1,
                bbox=BoundingBox(0, 0, 100, 50, 1),
                content={
                    'text': pdf_content['text'],
                    'confidence': 0.8,
                    'language': 'auto'
                }
            )
            section.blocks.append(block)

        docjson.sections.append(section)
        return docjson

    async def _export_to_xml(self, docjson: DocJSON, output_base: Path) -> Path:
        """XML 형식으로 내보내기"""
        import xml.etree.ElementTree as ET

        # 기본 XML 구조 생성
        root = ET.Element("Document")
        root.set("id", docjson.doc_id)
        root.set("title", docjson.metadata.title)
        root.set("type", docjson.metadata.doc_type or "unknown")

        # 메타데이터
        metadata_elem = ET.SubElement(root, "Metadata")
        ET.SubElement(metadata_elem, "Title").text = docjson.metadata.title
        ET.SubElement(metadata_elem, "DocumentType").text = docjson.metadata.doc_type
        ET.SubElement(metadata_elem, "Source").text = docjson.metadata.source.file

        # 섹션들
        sections_elem = ET.SubElement(root, "Sections")
        for section in docjson.sections:
            section_elem = ET.SubElement(sections_elem, "Section")
            section_elem.set("id", section.id)
            section_elem.set("level", str(section.level))

            ET.SubElement(section_elem, "Heading").text = section.heading

            # 블록들
            blocks_elem = ET.SubElement(section_elem, "Blocks")
            for block in section.blocks:
                block_elem = ET.SubElement(blocks_elem, "Block")
                block_elem.set("id", block.id)
                block_elem.set("type", block.type)

                ET.SubElement(block_elem, "Content").text = block.content.get('text', '')

                if block.semantic:
                    semantic_elem = ET.SubElement(block_elem, "Semantic")
                    if block.semantic.keywords:
                        keywords_elem = ET.SubElement(semantic_elem, "Keywords")
                        for keyword in block.semantic.keywords:
                            ET.SubElement(keywords_elem, "Keyword").text = keyword

        # XML 파일 저장
        xml_file = output_base.with_suffix('.xml')
        tree = ET.ElementTree(root)
        tree.write(xml_file, encoding='utf-8', xml_declaration=True)

        return xml_file

    # 유틸리티 메서드들
    async def create_custom_template(self, name: str, document_type: str, sample_file: Path = None) -> str:
        """사용자 정의 템플릿 생성"""
        template = self.annotation_manager.create_template(name, document_type)

        if sample_file:
            # 샘플 파일 분석하여 필드 제안
            config = PipelineConfig(processing_mode=ProcessingMode.FAST)
            result = await self.process_document(sample_file, config)

            if result.success and result.docjson:
                suggested_fields = self._suggest_fields_from_document(result.docjson)
                template.fields.extend(suggested_fields)
                self.annotation_manager.save_template(template)

        return template.id

    def _suggest_fields_from_document(self, docjson: DocJSON):
        """문서에서 필드 제안"""
        from ..core.user_annotations import UserField, FieldType, FieldImportance, BoundingBox

        suggested_fields = []

        # 문서 타입에 따른 기본 필드들
        common_fields = self.annotation_manager.get_common_fields_for_type(docjson.metadata.doc_type)
        suggested_fields.extend(common_fields)

        # 문서 내용 분석하여 추가 필드 제안
        for section in docjson.sections:
            for block in section.blocks:
                content = block.content.get('text', '')

                # 패턴 기반 필드 제안
                if block.semantic and block.semantic.entities:
                    for entity in block.semantic.entities:
                        field = UserField(
                            name=f"식별자_{entity}",
                            field_type=FieldType.CODE,
                            importance=FieldImportance.HIGH,
                            description=f"자동 감지된 기술 식별자: {entity}",
                            bbox=BoundingBox.from_dict(block.bbox.to_dict()) if block.bbox else None
                        )
                        suggested_fields.append(field)

        return suggested_fields

    async def batch_process_documents(self, file_paths: List[Path], config: PipelineConfig = None) -> List[PipelineResult]:
        """배치 문서 처리"""
        logger.info(f"배치 처리 시작: {len(file_paths)} 문서")

        results = []
        for file_path in file_paths:
            try:
                result = await self.process_document(file_path, config)
                results.append(result)
                logger.info(f"처리 완료: {file_path} ({'성공' if result.success else '실패'})")
            except Exception as e:
                logger.error(f"문서 처리 실패 {file_path}: {e}")
                results.append(PipelineResult(
                    success=False,
                    document_id=file_path.stem,
                    error=str(e)
                ))

        success_count = sum(1 for r in results if r.success)
        logger.info(f"배치 처리 완료: {success_count}/{len(file_paths)} 성공")

        return results

    async def get_processing_statistics(self) -> Dict[str, Any]:
        """처리 통계 조회"""
        stats = {
            'total_documents': 0,
            'successful_documents': 0,
            'document_types': {},
            'vectorized_documents': 0,
            'annotated_documents': 0
        }

        # 출력 디렉토리 스캔
        if self.output_dir.exists():
            for file in self.output_dir.glob("*.metadata.json"):
                stats['total_documents'] += 1
                try:
                    import json
                    with open(file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)

                    if metadata.get('results', {}).get('success', False):
                        stats['successful_documents'] += 1

                    doc_type = metadata.get('processing_config', {}).get('document_type', 'unknown')
                    stats['document_types'][doc_type] = stats['document_types'].get(doc_type, 0) + 1

                    if metadata.get('results', {}).get('vectorization_enabled', False):
                        stats['vectorized_documents'] += 1

                except Exception:
                    continue

        # 주석 통계
        if (self.output_dir / "annotations" / "documents").exists():
            annotation_files = list((self.output_dir / "annotations" / "documents").glob("*.json"))
            stats['annotated_documents'] = len(annotation_files)

        return stats