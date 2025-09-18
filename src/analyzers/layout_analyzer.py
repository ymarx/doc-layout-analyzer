"""
Layout Analyzer - CPU/GPU 듀얼 모드 지원 레이아웃 분석 엔진
PaddleOCR PP-Structure와 Docling을 이용한 문서 레이아웃 분석
"""

import logging
import time
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
import numpy as np
from PIL import Image
import io
import json
from dataclasses import dataclass
from enum import Enum

# Logger 설정
logger = logging.getLogger(__name__)

# PaddleOCR 관련
try:
    import paddleocr
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    logger.warning("PaddleOCR 라이브러리를 찾을 수 없습니다.")

# PaddleX 관련 (PP-Structure 대체)
try:
    import paddlex as pdx
    PADDLEX_AVAILABLE = True
except ImportError:
    PADDLEX_AVAILABLE = False
    logger.warning("PaddleX 라이브러리를 찾을 수 없습니다.")

from ..core.device_manager import DeviceManager
from ..core.config import ConfigManager

# Logger 설정을 먼저
logger = logging.getLogger(__name__)

# Docling 관련 (백업)
try:
    from docling.document_converter import DocumentConverter
    DOCLING_AVAILABLE = True
    logger.info("Docling 라이브러리 사용 가능")
except ImportError as e:
    DOCLING_AVAILABLE = False
    logger.warning(f"Docling 라이브러리를 찾을 수 없습니다: {e}")
except Exception as e:
    DOCLING_AVAILABLE = False
    logger.warning(f"Docling 초기화 실패: {e}")


class LayoutElementType(Enum):
    """레이아웃 요소 타입"""
    TEXT = "text"
    TITLE = "title"
    HEADING = "heading"
    TABLE = "table"
    FIGURE = "figure"
    IMAGE = "image"
    CAPTION = "caption"
    FOOTNOTE = "footnote"
    HEADER = "header"
    FOOTER = "footer"
    LIST = "list"
    DIAGRAM = "diagram"
    UNKNOWN = "unknown"


@dataclass
class LayoutElement:
    """레이아웃 요소"""
    element_type: LayoutElementType
    bbox: List[float]  # [x1, y1, x2, y2]
    confidence: float
    page_number: int
    text: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None


@dataclass
class LayoutAnalysisResult:
    """레이아웃 분석 결과"""
    success: bool
    elements: List[LayoutElement] = None
    page_count: int = 0
    processing_time: float = 0.0
    method_used: str = ""
    error: Optional[str] = None


class LayoutAnalyzer:
    """레이아웃 분석 엔진 - CPU/GPU 자동 전환 지원"""

    def __init__(self, device_manager: DeviceManager = None, config: ConfigManager = None):
        self.device_manager = device_manager
        self.config = config
        self.current_device = "cpu"

        # 분석기 초기화
        self.paddleocr_analyzer = None
        self.paddlex_pipeline = None
        self.docling_analyzer = None

        # 사용 가능한 분석기 확인
        self.available_analyzers = self._check_available_analyzers()

        # 기본 분석기 설정
        if self.available_analyzers:
            self._initialize_analyzers()

        # 커스텀 라벨 매핑
        self.label_mapper = self._create_label_mapper()

        logger.info(f"Layout Analyzer 초기화 완료. 사용 가능한 분석기: {self.available_analyzers}")

    def _check_available_analyzers(self) -> List[str]:
        """사용 가능한 분석기 확인"""
        analyzers = []

        if PADDLEX_AVAILABLE:
            analyzers.append("paddlex")

        if PADDLEOCR_AVAILABLE:
            analyzers.append("paddleocr")

        if DOCLING_AVAILABLE:
            analyzers.append("docling")

        if not analyzers:
            logger.error("사용 가능한 레이아웃 분석기가 없습니다!")

        return analyzers

    def _initialize_analyzers(self):
        """분석기 초기화"""
        # 디바이스 설정
        use_gpu = False
        if self.device_manager and self.config:
            self.current_device = self.device_manager.get_optimal_device(prefer_gpu=True, min_memory_mb=2000)
            use_gpu = self.current_device != "cpu" and self.config.ocr.use_gpu

        # PaddleX 초기화 (우선순위)
        if "paddlex" in self.available_analyzers:
            try:
                self.paddlex_pipeline = pdx.create_pipeline('layout_parsing')
                logger.info(f"PaddleX layout_parsing 파이프라인 초기화 완료")
            except Exception as e:
                logger.error(f"PaddleX 초기화 실패: {e}")
                self.paddlex_pipeline = None

        # PaddleOCR 초기화 (백업용)
        if "paddleocr" in self.available_analyzers:
            try:
                self.paddleocr_analyzer = PaddleOCR(
                    use_angle_cls=True,
                    lang="korean",
                    det_model_dir=None,  # 기본 모델 사용
                    rec_model_dir=None,
                    cls_model_dir=None,
                )

                logger.info(f"PaddleOCR 초기화 완료 (GPU: {use_gpu}, Device: {self.current_device})")

            except Exception as e:
                logger.error(f"PaddleOCR 초기화 실패: {e}")
                self.paddleocr_analyzer = None

        # Docling 초기화 (백업용)
        if "docling" in self.available_analyzers:
            try:
                self.docling_analyzer = DocumentConverter()
                logger.info("Docling 초기화 완료")
            except Exception as e:
                logger.error(f"Docling 초기화 실패: {e}")
                self.docling_analyzer = None

    def _create_label_mapper(self) -> Dict[str, LayoutElementType]:
        """커스텀 라벨 매핑 생성"""
        # 기본 라벨 매핑
        base_mapping = {
            # PaddleOCR 라벨
            "text": LayoutElementType.TEXT,
            "title": LayoutElementType.TITLE,
            "figure": LayoutElementType.FIGURE,
            "table": LayoutElementType.TABLE,
            "header": LayoutElementType.HEADER,
            "footer": LayoutElementType.FOOTER,

            # 한국어 사내 표준 라벨 (커스터마이징 가능)
            "기술기준_제목": LayoutElementType.TITLE,
            "작업표준_헤더": LayoutElementType.HEADER,
            "주의사항": LayoutElementType.TEXT,
            "경고": LayoutElementType.TEXT,
            "절차단계": LayoutElementType.LIST,
            "온도표": LayoutElementType.TABLE,
            "플로우차트": LayoutElementType.DIAGRAM,
        }

        # 설정에서 추가 매핑이 있다면 병합
        if self.config and hasattr(self.config, 'layout_labels'):
            custom_mapping = getattr(self.config, 'layout_labels', {})
            for key, value in custom_mapping.items():
                if isinstance(value, str):
                    try:
                        base_mapping[key] = LayoutElementType(value)
                    except ValueError:
                        logger.warning(f"알 수 없는 레이아웃 타입: {value}")

        return base_mapping

    async def analyze_document(self,
                              document_path: Union[str, Path],
                              page_images: List[np.ndarray] = None) -> LayoutAnalysisResult:
        """문서 레이아웃 분석"""
        start_time = time.time()

        try:
            # 이미지 준비
            if page_images is None:
                page_images = await self._convert_document_to_images(document_path)

            if not page_images:
                return LayoutAnalysisResult(
                    success=False,
                    error="문서를 이미지로 변환할 수 없습니다."
                )

            # 분석 방법 선택 및 실행 (우선순위: PaddleX > PaddleOCR > Docling)
            if self.paddlex_pipeline:
                result = await self._analyze_with_paddlex(page_images, document_path)
                result.method_used = "paddlex"
            elif self.paddleocr_analyzer:
                result = await self._analyze_with_paddleocr(page_images)
                result.method_used = "paddleocr"
            elif self.docling_analyzer:
                result = await self._analyze_with_docling(document_path)
                result.method_used = "docling"
            else:
                return LayoutAnalysisResult(
                    success=False,
                    error="사용 가능한 레이아웃 분석기가 없습니다."
                )

            result.processing_time = time.time() - start_time
            result.page_count = len(page_images)

            logger.info(f"레이아웃 분석 완료: {len(result.elements)}개 요소, "
                       f"{result.processing_time:.2f}초, 방법: {result.method_used}")

            return result

        except Exception as e:
            logger.error(f"레이아웃 분석 실패: {e}")
            return LayoutAnalysisResult(
                success=False,
                error=str(e),
                processing_time=time.time() - start_time
            )

    async def _analyze_with_paddlex(self, page_images: List[np.ndarray], document_path: Union[str, Path]) -> LayoutAnalysisResult:
        """PaddleX를 이용한 레이아웃 분석"""
        elements = []

        try:
            logger.info(f"PaddleX 분석 시작: {document_path}")
            logger.info(f"페이지 이미지 수: {len(page_images) if page_images else 'None'}")

            # 문서 경로로 직접 분석 (PaddleX는 파일 경로를 받음)
            result = await asyncio.to_thread(
                self.paddlex_pipeline.predict, str(document_path)
            )

            logger.info(f"PaddleX 원시 결과 타입: {type(result)}")

            # PaddleX는 generator를 반환하므로 list로 변환
            if result:
                result_list = list(result)
                logger.info(f"PaddleX 결과 페이지 수: {len(result_list)}")

                for page_num, page_result in enumerate(result_list):
                    logger.info(f"PaddleX 페이지 {page_num + 1} 결과 구조: {type(page_result)}")
                    logger.info(f"PaddleX 페이지 {page_num + 1} 키: {list(page_result.keys()) if hasattr(page_result, 'keys') else 'No keys'}")

                    # 결과 내용 로깅 (처음 몇 줄만)
                    if hasattr(page_result, 'keys'):
                        for key, value in page_result.items():
                            if isinstance(value, list):
                                logger.info(f"  {key}: {len(value)} items")
                                if len(value) > 0:
                                    logger.info(f"    첫 번째 항목: {type(value[0])}")
                                    if hasattr(value[0], 'keys'):
                                        logger.info(f"    첫 번째 항목 키: {list(value[0].keys())}")
                            else:
                                logger.info(f"  {key}: {type(value)} - {str(value)[:100]}")

                    page_elements = self._parse_paddlex_result(page_result, page_num)
                    elements.extend(page_elements)
                    logger.info(f"PaddleX 페이지 {page_num + 1}에서 추출된 요소: {len(page_elements)}개")

            return LayoutAnalysisResult(
                success=True,
                elements=elements
            )

        except Exception as e:
            logger.error(f"PaddleX 분석 실패: {e}")
            return LayoutAnalysisResult(
                success=False,
                error=str(e)
            )

    def _parse_paddlex_result(self, page_result: Dict[str, Any], page_num: int) -> List[LayoutElement]:
        """PaddleX 결과 파싱"""
        elements = []

        try:
            # Layout detection results
            if 'layout_det_res' in page_result and page_result['layout_det_res']:
                layout_det = page_result['layout_det_res']
                if hasattr(layout_det, 'boxes') and hasattr(layout_det, 'labels'):
                    for i in range(len(layout_det.boxes)):
                        box = layout_det.boxes[i]
                        label = layout_det.labels[i] if i < len(layout_det.labels) else 'unknown'
                        score = layout_det.scores[i] if hasattr(layout_det, 'scores') and i < len(layout_det.scores) else 0.0

                        element = LayoutElement(
                            element_type=self.label_mapper.get(label, LayoutElementType.UNKNOWN),
                            bbox=[float(box[0]), float(box[1]), float(box[2]), float(box[3])],
                            confidence=float(score),
                            page_number=page_num + 1,
                            properties={
                                'original_label': label,
                                'source': 'paddlex_layout_det'
                            }
                        )
                        elements.append(element)

            # OCR results
            if 'overall_ocr_res' in page_result and page_result['overall_ocr_res']:
                ocr_res = page_result['overall_ocr_res']
                if hasattr(ocr_res, 'boxes') and hasattr(ocr_res, 'texts'):
                    for i in range(len(ocr_res.boxes)):
                        box = ocr_res.boxes[i]
                        text = ocr_res.texts[i] if i < len(ocr_res.texts) else ''
                        score = ocr_res.scores[i] if hasattr(ocr_res, 'scores') and i < len(ocr_res.scores) else 0.9

                        element = LayoutElement(
                            element_type=LayoutElementType.TEXT,
                            bbox=[float(box[0]), float(box[1]), float(box[2]), float(box[3])],
                            confidence=float(score),
                            page_number=page_num + 1,
                            text=text,
                            properties={
                                'source': 'paddlex_ocr'
                            }
                        )
                        elements.append(element)

            # Parsing results (structured content)
            if 'parsing_res_list' in page_result and page_result['parsing_res_list']:
                for parsing_item in page_result['parsing_res_list']:
                    if 'block_bbox' in parsing_item and 'block_content' in parsing_item:
                        bbox = parsing_item['block_bbox']
                        content = parsing_item['block_content']
                        label = parsing_item.get('block_label', 'text')

                        element = LayoutElement(
                            element_type=self.label_mapper.get(label, LayoutElementType.UNKNOWN),
                            bbox=bbox,
                            confidence=0.9,
                            page_number=page_num + 1,
                            text=content,
                            properties={
                                'original_label': label,
                                'source': 'paddlex_parsing',
                                'structured': True
                            }
                        )
                        elements.append(element)

            # Table results
            if 'table_res_list' in page_result and page_result['table_res_list']:
                for table_item in page_result['table_res_list']:
                    if 'pred_html' in table_item and table_item['pred_html']:
                        # Extract table region if available
                        bbox = [0, 0, 1000, 1000]  # Default bbox

                        element = LayoutElement(
                            element_type=LayoutElementType.TABLE,
                            bbox=bbox,
                            confidence=0.9,
                            page_number=page_num + 1,
                            text=table_item['pred_html'],
                            properties={
                                'source': 'paddlex_table',
                                'html_structure': True,
                                'table_ocr': table_item.get('table_ocr_pred')
                            }
                        )
                        elements.append(element)

        except Exception as e:
            logger.error(f"PaddleX 결과 파싱 실패: {e}")

        return elements

    def _parse_paddlex_layout_item(self, item: Dict[str, Any], page_num: int) -> Optional[LayoutElement]:
        """PaddleX 레이아웃 아이템 파싱"""
        try:
            bbox = item.get('bbox', [])
            if len(bbox) != 4:
                return None

            # 라벨 매핑
            label = item.get('label', 'text')
            element_type = self.label_mapper.get(label, LayoutElementType.UNKNOWN)

            confidence = item.get('score', item.get('confidence', 0.0))

            return LayoutElement(
                element_type=element_type,
                bbox=bbox,
                confidence=confidence,
                page_number=page_num + 1,
                text=item.get('text', None),
                properties={
                    'original_label': label,
                    'source': 'paddlex_layout'
                }
            )

        except Exception as e:
            logger.debug(f"PaddleX 레이아웃 아이템 파싱 실패: {e}")
            return None

    def _parse_paddlex_ocr_item(self, item: Dict[str, Any], page_num: int) -> Optional[LayoutElement]:
        """PaddleX OCR 아이템 파싱"""
        try:
            bbox = item.get('bbox', [])
            if len(bbox) != 4:
                return None

            text = item.get('text', '')
            confidence = item.get('score', item.get('confidence', 0.0))

            return LayoutElement(
                element_type=LayoutElementType.TEXT,
                bbox=bbox,
                confidence=confidence,
                page_number=page_num + 1,
                text=text,
                properties={
                    'source': 'paddlex_ocr'
                }
            )

        except Exception as e:
            logger.debug(f"PaddleX OCR 아이템 파싱 실패: {e}")
            return None

    async def _analyze_with_paddleocr(self, page_images: List[np.ndarray]) -> LayoutAnalysisResult:
        """PaddleOCR PP-Structure를 이용한 분석"""
        elements = []

        try:
            for page_num, page_image in enumerate(page_images):
                # PP-Structure로 레이아웃 분석
                page_elements = await asyncio.to_thread(
                    self._process_page_with_paddleocr, page_image, page_num
                )
                elements.extend(page_elements)

            return LayoutAnalysisResult(
                success=True,
                elements=elements
            )

        except Exception as e:
            logger.error(f"PaddleOCR 분석 실패: {e}")
            return LayoutAnalysisResult(
                success=False,
                error=str(e)
            )

    def _process_page_with_paddleocr(self, page_image: np.ndarray, page_num: int) -> List[LayoutElement]:
        """PaddleOCR로 페이지 분석"""
        elements = []

        try:
            # PIL Image로 변환
            if isinstance(page_image, np.ndarray):
                pil_image = Image.fromarray(page_image)
            else:
                pil_image = page_image

            # 기본 PaddleOCR 사용
            result = self.paddleocr_analyzer.ocr(np.array(pil_image))

            # OCR 결과를 레이아웃 형식으로 변환
            if result and len(result) > 0:
                for line_result in result[0]:
                    element = self._parse_paddleocr_ocr_item(line_result, page_num)
                    if element:
                        elements.append(element)

            return elements

            # 결과는 위에서 처리됨

        except Exception as e:
            logger.error(f"PaddleOCR 페이지 {page_num + 1} 분석 실패: {e}")

        return elements

    def _convert_ocr_to_layout_format(self, ocr_result, page_num: int) -> List[Dict[str, Any]]:
        """OCR 결과를 레이아웃 형식으로 변환"""
        converted = []

        if not ocr_result or len(ocr_result) == 0:
            return converted

        try:
            page_result = ocr_result[0]  # 첫 번째 페이지 결과

            layout_result = {
                'layout': [],
                'ocr': page_result if page_result else []
            }

            converted.append(layout_result)

        except Exception as e:
            logger.debug(f"OCR 결과 변환 실패: {e}")

        return converted

    def _parse_paddleocr_layout_item(self, layout_item: Dict[str, Any], page_num: int) -> Optional[LayoutElement]:
        """PaddleOCR 레이아웃 결과 파싱"""
        try:
            bbox = layout_item.get('bbox', [])
            if len(bbox) != 4:
                return None

            # 라벨 매핑
            label = layout_item.get('label', 'text')
            element_type = self.label_mapper.get(label, LayoutElementType.UNKNOWN)

            confidence = layout_item.get('confidence', 0.0)

            return LayoutElement(
                element_type=element_type,
                bbox=bbox,
                confidence=confidence,
                page_number=page_num + 1,
                text=layout_item.get('text', None),
                properties={
                    'original_label': label,
                    'source': 'paddleocr_layout'
                }
            )

        except Exception as e:
            logger.debug(f"레이아웃 아이템 파싱 실패: {e}")
            return None

    def _parse_paddleocr_ocr_item(self, ocr_item: Dict[str, Any], page_num: int) -> Optional[LayoutElement]:
        """PaddleOCR OCR 결과 파싱"""
        try:
            if not isinstance(ocr_item, list) or len(ocr_item) < 2:
                return None

            bbox_coords = ocr_item[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            text_info = ocr_item[1]   # (text, confidence)

            # bbox를 [x1, y1, x2, y2] 형태로 변환
            if isinstance(bbox_coords, list) and len(bbox_coords) >= 4:
                x_coords = [point[0] for point in bbox_coords]
                y_coords = [point[1] for point in bbox_coords]
                bbox = [min(x_coords), min(y_coords), max(x_coords), max(y_coords)]
            else:
                return None

            # 텍스트와 신뢰도
            text = text_info[0] if isinstance(text_info, tuple) else text_info
            confidence = text_info[1] if isinstance(text_info, tuple) and len(text_info) > 1 else 0.9

            return LayoutElement(
                element_type=LayoutElementType.TEXT,
                bbox=bbox,
                confidence=confidence,
                page_number=page_num + 1,
                text=text,
                properties={
                    'source': 'paddleocr_ocr'
                }
            )

        except Exception as e:
            logger.debug(f"OCR 아이템 파싱 실패: {e}")
            return None

    async def _analyze_with_docling(self, document_path: Union[str, Path]) -> LayoutAnalysisResult:
        """Docling을 이용한 분석 (백업)"""
        elements = []

        try:
            # Docling으로 문서 변환
            result = await asyncio.to_thread(
                self.docling_analyzer.convert, str(document_path)
            )

            # 결과 파싱 (Docling 결과 구조에 따라 구현)
            # 실제 Docling API에 따라 수정 필요
            if hasattr(result, 'document') and result.document:
                elements = self._parse_docling_result(result.document)

            return LayoutAnalysisResult(
                success=True,
                elements=elements
            )

        except Exception as e:
            logger.error(f"Docling 분석 실패: {e}")
            return LayoutAnalysisResult(
                success=False,
                error=str(e)
            )

    def _parse_docling_result(self, docling_document) -> List[LayoutElement]:
        """Docling 결과 파싱"""
        elements = []

        # TODO: 실제 Docling 결과 구조에 따라 구현
        # 현재는 플레이스홀더

        return elements

    async def _convert_document_to_images(self, document_path: Union[str, Path]) -> List[np.ndarray]:
        """문서를 페이지별 이미지로 변환"""
        document_path = Path(document_path)
        images = []

        try:
            if document_path.suffix.lower() == '.pdf':
                images = await self._convert_pdf_to_images(document_path)
            else:
                # 다른 형식은 PIL로 처리
                image = Image.open(document_path)
                images = [np.array(image)]

        except Exception as e:
            logger.error(f"문서 이미지 변환 실패: {e}")

        return images

    async def _convert_pdf_to_images(self, pdf_path: Path) -> List[np.ndarray]:
        """PDF를 이미지로 변환"""
        images = []

        try:
            import fitz  # PyMuPDF

            doc = fitz.open(str(pdf_path))

            for page_num in range(len(doc)):
                page = doc[page_num]

                # 적절한 해상도로 렌더링
                mat = fitz.Matrix(2.0, 2.0)  # 2배 확대 (200 DPI 정도)
                pix = page.get_pixmap(matrix=mat)

                # numpy 배열로 변환
                img_data = pix.samples
                img_array = np.frombuffer(img_data, dtype=np.uint8)
                img_array = img_array.reshape(pix.height, pix.width, pix.n)

                # RGB로 변환 (필요한 경우)
                if pix.n == 4:  # RGBA
                    img_array = img_array[:, :, :3]  # A 채널 제거

                images.append(img_array)

            doc.close()

        except ImportError:
            logger.error("PyMuPDF(fitz)가 설치되지 않았습니다.")
        except Exception as e:
            logger.error(f"PDF 이미지 변환 실패: {e}")

        return images

    def cleanup_memory(self):
        """메모리 정리"""
        if self.device_manager:
            self.device_manager.cleanup_memory(self.current_device)

    def get_processing_stats(self) -> Dict[str, Any]:
        """처리 통계 반환"""
        return {
            "current_device": self.current_device,
            "available_analyzers": self.available_analyzers,
            "paddlex_enabled": self.paddlex_pipeline is not None,
            "paddleocr_enabled": self.paddleocr_analyzer is not None,
            "docling_enabled": self.docling_analyzer is not None
        }

    async def batch_analyze(self,
                           document_paths: List[Union[str, Path]]) -> List[LayoutAnalysisResult]:
        """배치 레이아웃 분석"""
        results = []

        for doc_path in document_paths:
            try:
                result = await self.analyze_document(doc_path)
                results.append(result)

                # 메모리 정리 (필요한 경우)
                if len(results) % 10 == 0:
                    self.cleanup_memory()

            except Exception as e:
                error_result = LayoutAnalysisResult(
                    success=False,
                    error=str(e)
                )
                results.append(error_result)

        return results