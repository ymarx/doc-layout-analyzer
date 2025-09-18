"""
Base Parser Interface
모든 문서 파서의 기본 인터페이스
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, BinaryIO
from dataclasses import dataclass
from enum import Enum
import logging
import time

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """문서 타입"""
    DOCX = "docx"
    PPTX = "pptx"
    PDF = "pdf"
    IMAGE = "image"
    SCANNED_PDF = "scanned_pdf"
    UNKNOWN = "unknown"


class ProcessingStatus(Enum):
    """처리 상태"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"


@dataclass
class ParseResult:
    """파싱 결과"""
    success: bool
    document_type: DocumentType
    content: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    processing_time: float = 0.0
    pages: int = 0
    file_size: int = 0


@dataclass
class ProcessingOptions:
    """처리 옵션"""
    extract_text: bool = True
    extract_images: bool = True
    extract_tables: bool = True
    extract_diagrams: bool = True
    ocr_enabled: bool = True
    language: List[str] = None
    use_gpu: bool = False
    batch_size: int = 1
    timeout: int = 300  # seconds
    preserve_layout: bool = True

    def __post_init__(self):
        if self.language is None:
            self.language = ["ko", "en"]


class BaseParser(ABC):
    """기본 파서 클래스"""

    def __init__(self, device_manager=None, config=None):
        self.device_manager = device_manager
        self.config = config
        self.supported_formats: List[str] = []
        self.processing_stats = {
            "total_processed": 0,
            "total_failed": 0,
            "total_time": 0.0,
            "average_time": 0.0
        }

    @abstractmethod
    async def parse(self,
                   file_path: Union[str, Path, BinaryIO],
                   options: ProcessingOptions = None) -> ParseResult:
        """문서 파싱 (추상 메서드)"""
        pass

    @abstractmethod
    def can_handle(self, file_path: Union[str, Path]) -> bool:
        """파일 처리 가능 여부 확인"""
        pass

    def detect_document_type(self, file_path: Union[str, Path]) -> DocumentType:
        """문서 타입 감지"""
        if isinstance(file_path, (str, Path)):
            file_path = Path(file_path)
            suffix = file_path.suffix.lower()

            type_mapping = {
                '.docx': DocumentType.DOCX,
                '.pptx': DocumentType.PPTX,
                '.pdf': DocumentType.PDF,
                '.png': DocumentType.IMAGE,
                '.jpg': DocumentType.IMAGE,
                '.jpeg': DocumentType.IMAGE,
                '.tiff': DocumentType.IMAGE,
                '.tif': DocumentType.IMAGE,
                '.bmp': DocumentType.IMAGE,
            }

            return type_mapping.get(suffix, DocumentType.UNKNOWN)

        return DocumentType.UNKNOWN

    def _is_scanned_pdf(self, file_path: Union[str, Path]) -> bool:
        """PDF가 스캔된 문서인지 판단"""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(file_path))

            # 첫 몇 페이지 검사
            text_ratio = 0
            total_pages = min(5, len(doc))  # 최대 5페이지만 검사

            for page_num in range(total_pages):
                page = doc[page_num]
                text = page.get_text()
                images = page.get_images()

                # 텍스트가 거의 없고 이미지가 많으면 스캔본으로 판단
                if len(text.strip()) < 100 and len(images) > 0:
                    text_ratio += 0
                else:
                    text_ratio += len(text.strip())

            doc.close()

            # 평균 텍스트 양이 적으면 스캔본으로 판단
            avg_text = text_ratio / total_pages if total_pages > 0 else 0
            return avg_text < 50

        except Exception as e:
            logger.warning(f"PDF 스캔 여부 판단 실패: {e}")
            return False

    def get_file_info(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """파일 기본 정보 추출"""
        if isinstance(file_path, (str, Path)):
            file_path = Path(file_path)

            return {
                "filename": file_path.name,
                "extension": file_path.suffix.lower(),
                "size": file_path.stat().st_size if file_path.exists() else 0,
                "absolute_path": str(file_path.absolute()),
                "parent_dir": str(file_path.parent),
            }
        return {}

    def validate_file(self, file_path: Union[str, Path]) -> bool:
        """파일 유효성 검사"""
        try:
            if isinstance(file_path, (str, Path)):
                file_path = Path(file_path)

                # 파일 존재 여부
                if not file_path.exists():
                    logger.error(f"파일이 존재하지 않음: {file_path}")
                    return False

                # 파일 크기 확인
                file_size = file_path.stat().st_size
                max_size = self._parse_size(self.config.system.max_file_size if self.config else "100MB")

                if file_size > max_size:
                    logger.error(f"파일 크기 초과: {file_size} > {max_size}")
                    return False

                # 파일 읽기 권한 확인
                if not os.access(file_path, os.R_OK):
                    logger.error(f"파일 읽기 권한 없음: {file_path}")
                    return False

                return True

            return True  # BinaryIO의 경우

        except Exception as e:
            logger.error(f"파일 유효성 검사 실패: {e}")
            return False

    def _parse_size(self, size_str: str) -> int:
        """크기 문자열을 바이트로 변환"""
        size_str = size_str.upper().strip()

        if size_str.endswith('KB'):
            return int(float(size_str[:-2]) * 1024)
        elif size_str.endswith('MB'):
            return int(float(size_str[:-2]) * 1024 * 1024)
        elif size_str.endswith('GB'):
            return int(float(size_str[:-2]) * 1024 * 1024 * 1024)
        else:
            return int(size_str)  # 바이트 단위로 가정

    def update_stats(self, processing_time: float, success: bool):
        """처리 통계 업데이트"""
        if success:
            self.processing_stats["total_processed"] += 1
        else:
            self.processing_stats["total_failed"] += 1

        self.processing_stats["total_time"] += processing_time

        total_count = self.processing_stats["total_processed"] + self.processing_stats["total_failed"]
        if total_count > 0:
            self.processing_stats["average_time"] = self.processing_stats["total_time"] / total_count

    def get_processing_stats(self) -> Dict[str, Any]:
        """처리 통계 반환"""
        return self.processing_stats.copy()

    async def batch_parse(self,
                         file_paths: List[Union[str, Path]],
                         options: ProcessingOptions = None) -> List[ParseResult]:
        """배치 파싱"""
        results = []

        for file_path in file_paths:
            try:
                result = await self.parse(file_path, options)
                results.append(result)
            except Exception as e:
                error_result = ParseResult(
                    success=False,
                    document_type=self.detect_document_type(file_path),
                    error=str(e)
                )
                results.append(error_result)

        return results

    def cleanup(self):
        """리소스 정리"""
        pass


import os


class ParserFactory:
    """파서 팩토리 - 문서 타입에 따라 적절한 파서 선택"""

    def __init__(self, device_manager=None, config=None):
        self.device_manager = device_manager
        self.config = config
        self._parsers = {}
        self._register_parsers()

    def _register_parsers(self):
        """파서 등록"""
        # 동적 임포트로 순환 참조 방지
        pass  # 실제 파서들은 하위 클래스에서 등록

    def get_parser(self, file_path: Union[str, Path]) -> Optional[BaseParser]:
        """파일에 적합한 파서 반환"""
        if isinstance(file_path, (str, Path)):
            file_path = Path(file_path)

            # 파일 확장자로 1차 판단
            ext = file_path.suffix.lower()
            logger.debug(f"파일 확장자: {ext}, 등록된 파서: {list(self._parsers.keys())}")

            # PDF의 경우 스캔 여부 확인
            if ext == '.pdf':
                # PDF 파서가 있다면 그것의 스캔 PDF 확인 메서드 사용
                pdf_parser = self._parsers.get('pdf')
                if pdf_parser and hasattr(pdf_parser, '_is_scanned_pdf'):
                    try:
                        if pdf_parser._is_scanned_pdf(file_path):
                            # 스캔 PDF 파서가 따로 없다면 기본 PDF 파서 사용
                            scanned_parser = self._parsers.get('scanned_pdf')
                            return scanned_parser if scanned_parser else pdf_parser
                        else:
                            return pdf_parser
                    except:
                        # 에러 발생시 기본 PDF 파서 사용
                        return pdf_parser
                else:
                    return pdf_parser

            # 다른 형식들
            format_mapping = {
                '.docx': 'docx',
                '.pptx': 'pptx',
                '.pdf': 'pdf',
                '.png': 'image',
                '.jpg': 'image',
                '.jpeg': 'image',
                '.tiff': 'image',
                '.tif': 'image',
                '.bmp': 'image',
            }

            parser_type = format_mapping.get(ext)
            return self._parsers.get(parser_type)

        return None

    def register_parser(self, parser_type: str, parser_class: type):
        """파서 등록"""
        self._parsers[parser_type] = parser_class(
            device_manager=self.device_manager,
            config=self.config
        )

    def list_supported_formats(self) -> List[str]:
        """지원하는 형식 목록"""
        formats = set()
        for parser in self._parsers.values():
            formats.update(parser.supported_formats)
        return list(formats)