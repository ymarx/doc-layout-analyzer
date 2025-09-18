"""
Document Parsers Package
다양한 문서 형식을 처리하는 파서들
"""

from .base_parser import (
    BaseParser,
    ParseResult,
    ProcessingOptions,
    DocumentType,
    ProcessingStatus,
    ParserFactory
)

from .unified_docx_parser import UnifiedDocxParser
from .pdf_parser import PDFParser

# 기존 파서들 (레거시 지원)
from .docx_parser import DocxParser
from .docx_enhanced_parser import DocxEnhancedParser

# 파서 팩토리 구현
class DocumentParserFactory(ParserFactory):
    """문서 파서 팩토리 - 통합 파서 사용"""

    def __init__(self, device_manager=None, config=None, use_legacy=False):
        super().__init__(device_manager, config)
        self.use_legacy = use_legacy
        self._register_parsers()

    def _register_parsers(self):
        """파서 등록 - 통합 파서 우선 사용"""
        if getattr(self, 'use_legacy', False):
            # 레거시 모드: 기존 파서들 사용
            self._parsers['docx'] = DocxParser
        else:
            # 기본 모드: 통합 파서 사용
            self._parsers['docx'] = UnifiedDocxParser

        self._parsers['pdf'] = PDFParser

        # TODO: 추가 파서들
        # self.register_parser('pptx', PptxParser)
        # self.register_parser('image', ImageParser)
        # self.register_parser('scanned_pdf', ScannedPDFParser)


# 편의를 위한 팩토리 인스턴스
_factory = None

def get_parser_factory(device_manager=None, config=None):
    """파서 팩토리 인스턴스 반환"""
    global _factory
    if _factory is None:
        _factory = DocumentParserFactory(device_manager, config)
    return _factory


def parse_document(file_path, options=None, device_manager=None, config=None):
    """문서 파싱 편의 함수"""
    factory = get_parser_factory(device_manager, config)
    parser = factory.get_parser(file_path)

    if parser is None:
        raise ValueError(f"Unsupported file format: {file_path}")

    return parser.parse(file_path, options)


__all__ = [
    'BaseParser',
    'ParseResult',
    'ProcessingOptions',
    'DocumentType',
    'ProcessingStatus',
    'UnifiedDocxParser',  # 새로운 통합 파서
    'DocxParser',         # 레거시 지원
    'DocxEnhancedParser', # 레거시 지원
    'PDFParser',
    'DocumentParserFactory',
    'get_parser_factory',
    'parse_document'
]