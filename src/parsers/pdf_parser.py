"""
PDF Parser - PDF 문서 파서
pdfplumber, PyPDF2, Camelot을 이용한 텍스트 및 표 추출
OCR 지원을 위해 OCRmyPDF 통합
"""

import logging
import time
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, BinaryIO, Tuple
import tempfile
import subprocess
import fitz  # PyMuPDF
import io

# PDF 처리 라이브러리
import pdfplumber
import camelot
from PyPDF2 import PdfReader

from .base_parser import BaseParser, ParseResult, ProcessingOptions, DocumentType

logger = logging.getLogger(__name__)


class PDFParser(BaseParser):
    """PDF 파서 - 벡터 PDF와 스캔 PDF 자동 처리"""

    def __init__(self, device_manager=None, config=None):
        super().__init__(device_manager, config)
        self.supported_formats = ['.pdf']
        self._ocr_available = self._check_ocr_availability()

    def can_handle(self, file_path: Union[str, Path]) -> bool:
        """PDF 파일 처리 가능 여부"""
        if isinstance(file_path, (str, Path)):
            return Path(file_path).suffix.lower() == '.pdf'
        return False

    def _check_ocr_availability(self) -> bool:
        """OCR 도구 사용 가능 여부 확인"""
        try:
            # OCRmyPDF 확인
            result = subprocess.run(['ocrmypdf', '--version'],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"OCRmyPDF 사용 가능: {result.stdout.strip()}")
                return True
        except FileNotFoundError:
            pass

        logger.warning("OCRmyPDF를 찾을 수 없습니다. 스캔 PDF 처리가 제한됩니다.")
        return False

    async def parse(self,
                   file_path: Union[str, Path, BinaryIO],
                   options: ProcessingOptions = None) -> ParseResult:
        """PDF 문서 파싱"""
        start_time = time.time()
        options = options or ProcessingOptions()

        try:
            # 파일 유효성 검사
            if isinstance(file_path, (str, Path)) and not self.validate_file(file_path):
                return ParseResult(
                    success=False,
                    document_type=DocumentType.PDF,
                    error="File validation failed"
                )

            # 임시 파일 처리 (BinaryIO인 경우)
            temp_file_path = None
            if isinstance(file_path, (str, Path)):
                pdf_path = str(file_path)
                file_info = self.get_file_info(file_path)
            else:
                temp_file_path = await self._save_to_temp_file(file_path)
                pdf_path = temp_file_path
                file_info = {"filename": "stream_input", "size": 0}

            try:
                # PDF 타입 확인 (스캔 vs 벡터)
                is_scanned = self._is_scanned_pdf(pdf_path)

                # OCR 전처리 (스캔 PDF인 경우)
                processed_pdf_path = pdf_path
                if is_scanned and options.ocr_enabled and self._ocr_available:
                    processed_pdf_path = await self._preprocess_with_ocr(pdf_path)

                # 내용 추출
                content = await self._extract_content(processed_pdf_path, options, is_scanned)

                # 메타데이터 추출
                metadata = await self._extract_metadata(pdf_path, file_info)

                processing_time = time.time() - start_time
                self.update_stats(processing_time, True)

                return ParseResult(
                    success=True,
                    document_type=DocumentType.SCANNED_PDF if is_scanned else DocumentType.PDF,
                    content=content,
                    metadata=metadata,
                    processing_time=processing_time,
                    pages=content.get("total_pages", 0),
                    file_size=file_info.get("size", 0)
                )

            finally:
                # 임시 파일 정리
                if temp_file_path and Path(temp_file_path).exists():
                    Path(temp_file_path).unlink()

                # OCR 처리된 임시 파일 정리
                if processed_pdf_path != pdf_path and Path(processed_pdf_path).exists():
                    Path(processed_pdf_path).unlink()

        except Exception as e:
            processing_time = time.time() - start_time
            self.update_stats(processing_time, False)
            logger.error(f"PDF 파싱 실패: {e}")

            return ParseResult(
                success=False,
                document_type=DocumentType.PDF,
                error=str(e),
                processing_time=processing_time
            )

    async def _save_to_temp_file(self, file_obj: BinaryIO) -> str:
        """BinaryIO를 임시 파일로 저장"""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            content = await asyncio.to_thread(file_obj.read)
            temp_file.write(content)
            return temp_file.name

    async def _preprocess_with_ocr(self, pdf_path: str) -> str:
        """OCRmyPDF로 스캔 PDF 전처리"""
        try:
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                output_path = temp_file.name

            # OCRmyPDF 명령어 구성
            cmd = [
                'ocrmypdf',
                '--language', 'kor+eng',  # 한국어 + 영어
                '--deskew',  # 기울어진 페이지 교정
                '--clean',  # 이미지 정리
                '--optimize', '1',  # 최적화 레벨
                '--output-type', 'pdf',
                '--force-ocr',  # 기존 텍스트가 있어도 OCR 수행
                pdf_path,
                output_path
            ]

            # 비동기 실행
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                logger.info(f"OCR 전처리 완료: {pdf_path}")
                return output_path
            else:
                logger.warning(f"OCR 전처리 실패: {stderr.decode()}")
                # 실패 시 원본 반환
                Path(output_path).unlink(missing_ok=True)
                return pdf_path

        except Exception as e:
            logger.error(f"OCR 전처리 중 오류: {e}")
            return pdf_path

    async def _extract_content(self, pdf_path: str, options: ProcessingOptions,
                              is_scanned: bool) -> Dict[str, Any]:
        """PDF 내용 추출"""
        content = {
            "pages": [],
            "text": "",
            "tables": [],
            "images": [],
            "metadata": {},
            "total_pages": 0
        }

        try:
            # PyMuPDF로 기본 정보 수집
            doc = fitz.open(pdf_path)
            content["total_pages"] = len(doc)

            # pdfplumber로 상세 내용 추출
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_content = await self._extract_page_content(page, page_num, options, is_scanned)
                    content["pages"].append(page_content)

                    # 전체 텍스트에 추가
                    if page_content.get("text"):
                        content["text"] += page_content["text"] + "\n\n"

                    # 표 추가
                    content["tables"].extend(page_content.get("tables", []))

            # 이미지 추출 (PyMuPDF 사용)
            if options.extract_images:
                content["images"] = await self._extract_images(doc)

            doc.close()

        except Exception as e:
            logger.error(f"PDF 내용 추출 실패: {e}")
            raise

        return content

    async def _extract_page_content(self, page, page_num: int, options: ProcessingOptions,
                                   is_scanned: bool) -> Dict[str, Any]:
        """페이지별 내용 추출"""
        page_content = {
            "page_number": page_num + 1,
            "text": "",
            "tables": [],
            "layout": {
                "width": page.width,
                "height": page.height,
                "bbox": [0, 0, page.width, page.height]
            }
        }

        try:
            # 텍스트 추출
            if options.extract_text:
                text = page.extract_text()
                if text:
                    page_content["text"] = text.strip()

            # 표 추출
            if options.extract_tables:
                tables = await self._extract_page_tables(page, page_num)
                page_content["tables"] = tables

        except Exception as e:
            logger.warning(f"페이지 {page_num + 1} 내용 추출 실패: {e}")

        return page_content

    async def _extract_page_tables(self, page, page_num: int) -> List[Dict[str, Any]]:
        """페이지에서 표 추출"""
        tables = []

        try:
            # pdfplumber로 표 추출
            page_tables = page.extract_tables()

            for i, table in enumerate(page_tables):
                if table:  # None이 아닌 경우
                    table_data = {
                        "id": f"table_{page_num}_{i}",
                        "page": page_num + 1,
                        "data": table,
                        "rows": len(table),
                        "cols": len(table[0]) if table else 0,
                        "bbox": None,  # pdfplumber는 표 bbox 제공하지 않음
                        "extraction_method": "pdfplumber"
                    }
                    tables.append(table_data)

        except Exception as e:
            logger.debug(f"pdfplumber 표 추출 실패: {e}")

        # Camelot으로 보완 시도 (벡터 PDF인 경우)
        try:
            page_bbox = [0, 0, page.width, page.height]
            camelot_tables = camelot.read_pdf(
                str(page.pdf.stream.name) if hasattr(page.pdf.stream, 'name') else page.pdf.stream,
                pages=str(page_num + 1),
                flavor='lattice',  # 먼저 lattice 시도
                table_areas=[f"{page_bbox[0]},{page_bbox[1]},{page_bbox[2]},{page_bbox[3]}"]
            )

            for i, table in enumerate(camelot_tables):
                if table.accuracy > 0.8:  # 정확도 임계값
                    table_data = {
                        "id": f"camelot_table_{page_num}_{i}",
                        "page": page_num + 1,
                        "data": table.df.values.tolist(),
                        "rows": len(table.df),
                        "cols": len(table.df.columns),
                        "bbox": table._bbox if hasattr(table, '_bbox') else None,
                        "accuracy": table.accuracy,
                        "extraction_method": "camelot"
                    }
                    tables.append(table_data)

        except Exception as e:
            logger.debug(f"Camelot 표 추출 실패: {e}")
            # stream 모드로 재시도
            try:
                camelot_tables = camelot.read_pdf(
                    str(page.pdf.stream.name) if hasattr(page.pdf.stream, 'name') else page.pdf.stream,
                    pages=str(page_num + 1),
                    flavor='stream'
                )

                for i, table in enumerate(camelot_tables):
                    if table.accuracy > 0.7:
                        table_data = {
                            "id": f"camelot_stream_table_{page_num}_{i}",
                            "page": page_num + 1,
                            "data": table.df.values.tolist(),
                            "rows": len(table.df),
                            "cols": len(table.df.columns),
                            "accuracy": table.accuracy,
                            "extraction_method": "camelot_stream"
                        }
                        tables.append(table_data)

            except Exception as e2:
                logger.debug(f"Camelot stream 표 추출 실패: {e2}")

        return tables

    async def _extract_images(self, doc: fitz.Document) -> List[Dict[str, Any]]:
        """이미지 추출"""
        images = []

        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()

                for img_index, img in enumerate(image_list):
                    try:
                        xref = img[0]
                        base_image = doc.extract_image(xref)

                        image_data = {
                            "id": f"image_{page_num}_{img_index}",
                            "page": page_num + 1,
                            "xref": xref,
                            "format": base_image["ext"],
                            "width": base_image["width"],
                            "height": base_image["height"],
                            "colorspace": base_image["colorspace"],
                            "bpc": base_image["bpc"],  # bits per component
                            "size": len(base_image["image"]),
                            "image_data": base_image["image"]  # 실제 이미지 바이트
                        }
                        images.append(image_data)

                    except Exception as e:
                        logger.debug(f"이미지 추출 실패 (페이지 {page_num + 1}, 인덱스 {img_index}): {e}")

        except Exception as e:
            logger.error(f"이미지 추출 중 오류: {e}")

        return images

    async def _extract_metadata(self, pdf_path: str, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """PDF 메타데이터 추출"""
        metadata = file_info.copy()

        try:
            # PyPDF2로 메타데이터 추출
            with open(pdf_path, 'rb') as file:
                reader = PdfReader(file)

                if reader.metadata:
                    pdf_metadata = {
                        "title": reader.metadata.get("/Title", ""),
                        "author": reader.metadata.get("/Author", ""),
                        "subject": reader.metadata.get("/Subject", ""),
                        "creator": reader.metadata.get("/Creator", ""),
                        "producer": reader.metadata.get("/Producer", ""),
                        "creation_date": str(reader.metadata.get("/CreationDate", "")),
                        "modification_date": str(reader.metadata.get("/ModDate", "")),
                    }
                    metadata.update(pdf_metadata)

                # 페이지 수
                metadata["page_count"] = len(reader.pages)

                # 첫 번째 페이지 크기
                if reader.pages:
                    first_page = reader.pages[0]
                    media_box = first_page.mediabox
                    metadata["page_size"] = {
                        "width": float(media_box.width),
                        "height": float(media_box.height)
                    }

        except Exception as e:
            logger.debug(f"PDF 메타데이터 추출 실패: {e}")

        # PyMuPDF로 추가 정보
        try:
            doc = fitz.open(pdf_path)
            fitz_metadata = doc.metadata

            if fitz_metadata:
                metadata.update({
                    "format": fitz_metadata.get("format", ""),
                    "encryption": fitz_metadata.get("encryption", ""),
                    "pages": len(doc)
                })

            doc.close()

        except Exception as e:
            logger.debug(f"PyMuPDF 메타데이터 추출 실패: {e}")

        return metadata

    def _is_scanned_pdf(self, file_path: Union[str, Path]) -> bool:
        """PDF가 스캔된 문서인지 판단 (기본 클래스 메서드 재정의)"""
        try:
            doc = fitz.open(str(file_path))

            # 첫 몇 페이지 검사
            text_char_count = 0
            image_count = 0
            total_pages = min(5, len(doc))

            for page_num in range(total_pages):
                page = doc[page_num]

                # 텍스트 문자 수
                text = page.get_text()
                text_char_count += len(text.strip())

                # 이미지 수
                images = page.get_images()
                image_count += len(images)

            doc.close()

            # 평균 텍스트 문자 수가 적고 이미지가 많으면 스캔본으로 판단
            avg_text_chars = text_char_count / total_pages if total_pages > 0 else 0
            avg_images = image_count / total_pages if total_pages > 0 else 0

            # 스캔 PDF 판단 기준
            is_scanned = (avg_text_chars < 100 and avg_images > 0) or (avg_text_chars < 50)

            logger.info(f"PDF 분석 결과 - 평균 텍스트: {avg_text_chars:.1f}자, "
                       f"평균 이미지: {avg_images:.1f}개, 스캔본: {is_scanned}")

            return is_scanned

        except Exception as e:
            logger.warning(f"PDF 스캔 여부 판단 실패: {e}")
            return False