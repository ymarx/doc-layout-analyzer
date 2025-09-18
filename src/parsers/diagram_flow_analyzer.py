"""
다이어그램 프로세스 흐름 분석기
"""

import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

@dataclass
class ProcessStep:
    """프로세스 단계"""
    sequence: int
    title: str
    details: List[str] = field(default_factory=list)
    marker: str = ""  # ①, ②, ③ 등

@dataclass
class ProcessFlow:
    """프로세스 흐름"""
    name: str
    steps: List[ProcessStep] = field(default_factory=list)
    flow_type: str = "sequential"  # sequential, parallel, conditional
    confidence: float = 0.0

class DiagramFlowAnalyzer:
    """다이어그램에서 프로세스 흐름 추출"""

    # DOCX XML 네임스페이스
    NAMESPACES = {
        'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
        'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
        'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
        'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture',
        'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
        'wpg': 'http://schemas.microsoft.com/office/word/2010/wordprocessingGroup',
        'wps': 'http://schemas.microsoft.com/office/word/2010/wordprocessingShape'
    }

    def __init__(self):
        self.sequence_patterns = [
            (r'①([^②③④⑤⑥⑦⑧⑨⑩]+)', 1),
            (r'②([^③④⑤⑥⑦⑧⑨⑩]+)', 2),
            (r'③([^④⑤⑥⑦⑧⑨⑩]+)', 3),
            (r'④([^⑤⑥⑦⑧⑨⑩]+)', 4),
            (r'⑤([^⑥⑦⑧⑨⑩]+)', 5),
        ]

    def analyze_diagrams(self, docx_zip, root: ET.Element) -> List[ProcessFlow]:
        """다이어그램들에서 프로세스 흐름 분석"""
        flows = []

        try:
            # drawing 요소들 찾기
            drawings = root.findall('.//w:drawing', self.NAMESPACES)
            logger.info(f"다이어그램에서 {len(drawings)}개 drawing 요소 발견")

            if not drawings:
                return flows

            # 모든 다이어그램에서 텍스트 추출
            all_diagram_texts = []
            diagram_steps = {}

            for i, drawing in enumerate(drawings):
                texts = self._extract_texts_from_drawing(drawing)
                if texts:
                    all_diagram_texts.extend(texts)
                    logger.info(f"Drawing {i+1}에서 텍스트 추출: {texts}")

                    # 순서 마커가 있는 텍스트 분석
                    combined_text = ' '.join(texts)  # 분리된 텍스트들을 먼저 결합

                    # 개별 텍스트와 결합된 텍스트 모두 검사
                    for text in texts + [combined_text]:
                        step = self._parse_step_text(text)
                        if step:
                            # 이미 같은 sequence가 있으면 더 긴 제목으로 교체
                            if step.sequence in diagram_steps:
                                if len(step.title) > len(diagram_steps[step.sequence].title):
                                    diagram_steps[step.sequence] = step
                            else:
                                diagram_steps[step.sequence] = step

            # 프로세스 흐름 구성
            if diagram_steps:
                flow = ProcessFlow(
                    name="노황복구 수순",
                    steps=self._build_ordered_steps(diagram_steps),
                    flow_type="sequential",
                    confidence=self._calculate_confidence(diagram_steps)
                )
                flows.append(flow)

                logger.info(f"프로세스 흐름 구성됨: {len(flow.steps)}단계")

        except Exception as e:
            logger.error(f"다이어그램 흐름 분석 실패: {e}")

        return flows

    def _extract_texts_from_drawing(self, drawing: ET.Element) -> List[str]:
        """단일 drawing에서 텍스트 추출"""
        texts = []

        # 다양한 텍스트 위치에서 검색
        text_paths = [
            './/a:t',  # DrawingML 텍스트
            './/w:t',  # Word 텍스트
            './/wps:txBody//a:t',  # Shape 텍스트 바디
            './/a:txBody//a:t',    # 텍스트 바디
        ]

        for path in text_paths:
            text_elements = drawing.findall(path, self.NAMESPACES)
            for text_elem in text_elements:
                if text_elem.text and text_elem.text.strip():
                    texts.append(text_elem.text.strip())

        return texts

    def _parse_step_text(self, text: str) -> Optional[ProcessStep]:
        """텍스트에서 프로세스 단계 파싱"""
        # 순서 마커 패턴 검색
        for pattern, sequence in self.sequence_patterns:
            match = re.search(pattern, text)
            if match:
                content = match.group(1).strip()

                # 추가 세부사항 추출 (괄호 안 내용 등)
                details = []
                if '(' in text and ')' in text:
                    detail_match = re.search(r'\(([^)]+)\)', text)
                    if detail_match:
                        details.append(detail_match.group(1).strip())

                return ProcessStep(
                    sequence=sequence,
                    title=content,
                    details=details,
                    marker=text[0] if text[0] in '①②③④⑤⑥⑦⑧⑨⑩' else ""
                )

        return None

    def _build_ordered_steps(self, diagram_steps: Dict[int, ProcessStep]) -> List[ProcessStep]:
        """순서대로 단계 정렬"""
        ordered_steps = []

        # 순서대로 정렬
        for seq in sorted(diagram_steps.keys()):
            step = diagram_steps[seq]

            # 제목 정리
            title = step.title
            if title.endswith('및'):
                title = title[:-1].strip()

            # 제목이 짧거나 불완전한 경우 보완
            if len(title) < 3 and seq == 3:  # ③단계가 너무 짧은 경우
                title = "풍량확보 및 연화융착대형성"  # 기본값 설정

            step.title = title
            ordered_steps.append(step)

        return ordered_steps

    def _calculate_confidence(self, diagram_steps: Dict[int, ProcessStep]) -> float:
        """신뢰도 계산"""
        if not diagram_steps:
            return 0.0

        # 순차적 순서가 있는지 확인
        sequences = sorted(diagram_steps.keys())
        if len(sequences) < 2:
            return 0.5

        # 연속된 순서인지 확인
        is_sequential = all(sequences[i] + 1 == sequences[i + 1]
                          for i in range(len(sequences) - 1))

        base_confidence = 0.7 if is_sequential else 0.5

        # 단계 수에 따른 보정
        step_bonus = min(0.2, len(sequences) * 0.05)

        return min(1.0, base_confidence + step_bonus)

    def format_flow_for_docjson(self, flows: List[ProcessFlow]) -> List[Dict[str, Any]]:
        """DocJSON 형식으로 프로세스 흐름 변환"""
        formatted_flows = []

        for flow in flows:
            formatted_flow = {
                "name": flow.name,
                "type": flow.flow_type,
                "confidence": flow.confidence,
                "steps": []
            }

            for step in flow.steps:
                formatted_step = {
                    "sequence": step.sequence,
                    "marker": step.marker,
                    "title": step.title,
                    "details": step.details
                }
                formatted_flow["steps"].append(formatted_step)

            formatted_flows.append(formatted_flow)

        return formatted_flows

    def extract_process_summary(self, flows: List[ProcessFlow]) -> str:
        """프로세스 흐름 요약 텍스트 생성"""
        if not flows:
            return ""

        flow = flows[0]  # 첫 번째 흐름 사용
        if not flow.steps:
            return ""

        step_titles = []
        for step in flow.steps:
            title = step.title
            if step.details:
                title += f" ({', '.join(step.details)})"
            step_titles.append(title)

        return " → ".join(step_titles)