#!/usr/bin/env python3
"""
다이어그램 내용 분석 - 프로세스 흐름 추출
"""

import asyncio
import re
from src.parsers.unified_docx_parser import UnifiedDocxParser

async def analyze_diagram_content():
    """다이어그램 내용 분석"""
    print("🎨 다이어그램 내용 분석")
    print("=" * 60)

    parser = UnifiedDocxParser()
    parser.parsing_mode = 'enhanced'

    result = await parser.parse("../기술기준_예시.docx")

    if result.success:
        content = result.content
        raw_content = content.get('raw_content', {})

        # 1. 모든 텍스트에서 프로세스 흐름 찾기
        print("1. 텍스트에서 프로세스 흐름 패턴 검색")
        print("-" * 40)

        # 단락에서 검색
        flow_patterns = [
            r'(\d+\.\s*[^→\n]+)(?:\s*→\s*(\d+\.\s*[^→\n]+))+',  # 1. xxx → 2. xxx
            r'([^→\n]+)\s*→\s*([^→\n]+)(?:\s*→\s*([^→\n]+))*',  # xxx → yyy → zzz
            r'①([^②③④⑤]+)②([^③④⑤]+)③?([^④⑤]+)?④?([^⑤]+)?⑤?(.+)?'  # ① ② ③ ④ ⑤ 패턴
        ]

        found_flows = []

        for i, para in enumerate(raw_content.get('paragraphs', [])):
            text = para.get('text', '') if isinstance(para, dict) else str(para)

            # 프로세스 흐름 패턴 검색
            for pattern_name, pattern in enumerate(flow_patterns):
                matches = re.finditer(pattern, text)
                for match in matches:
                    found_flows.append({
                        'paragraph_index': i,
                        'pattern_type': pattern_name,
                        'text': text,
                        'match_groups': match.groups(),
                        'full_match': match.group(0)
                    })

        if found_flows:
            print("✅ 발견된 프로세스 흐름:")
            for flow in found_flows:
                print(f"   패러그래프 {flow['paragraph_index']}: {flow['full_match'][:100]}...")
                if flow['match_groups']:
                    steps = [step for step in flow['match_groups'] if step and step.strip()]
                    print(f"   단계: {' → '.join(steps)}")
                print()

        # 2. 특정 키워드로 검색 (노열확보, 통기성확보, 풍량확보, 조업도상승)
        print("2. 특정 프로세스 키워드 검색")
        print("-" * 40)

        process_keywords = [
            "노열확보", "통기성확보", "풍량확보", "조업도상승", "조업도 상승",
            "증광", "증산", "연화융착대형성", "연화융착대 형성"
        ]

        keyword_locations = {}
        for keyword in process_keywords:
            keyword_locations[keyword] = []

        for i, para in enumerate(raw_content.get('paragraphs', [])):
            text = para.get('text', '') if isinstance(para, dict) else str(para)
            for keyword in process_keywords:
                if keyword in text:
                    keyword_locations[keyword].append({
                        'paragraph': i,
                        'context': text[:200] + '...' if len(text) > 200 else text
                    })

        print("✅ 발견된 프로세스 키워드:")
        for keyword, locations in keyword_locations.items():
            if locations:
                print(f"   🔹 {keyword}: {len(locations)}회 발견")
                for loc in locations[:2]:  # 처음 2개만 표시
                    print(f"      └─ 문단 {loc['paragraph']}: {loc['context']}")

        # 3. 다이어그램 영역 상세 분석
        print("\n3. 다이어그램 영역 상세 분석")
        print("-" * 40)

        diagrams = raw_content.get('diagrams', [])
        print(f"✅ 감지된 다이어그램: {len(diagrams)}개")

        # XML 구조에서 더 상세한 정보 찾기
        xml_struct = raw_content.get('xml_structure', {})
        if xml_struct:
            # 다이어그램 관련 요소들 찾기
            drawing_elements = []

            print("   XML에서 다이어그램 관련 요소 검색 중...")
            # 이건 실제 구현에서는 XML 파싱으로 해야 함
            print("   (상세 XML 분석 필요)")

        # 4. 시퀀스 추출 시도
        print("\n4. 프로세스 시퀀스 재구성")
        print("-" * 40)

        # 발견된 키워드들을 순서대로 정렬 시도
        if any(keyword_locations.values()):
            print("✅ 추출된 프로세스 흐름 재구성:")

            # 일반적인 제철 프로세스 순서로 정렬
            expected_sequence = [
                "노열확보", "통기성확보", "풍량확보", "연화융착대형성",
                "조업도상승", "증광", "증산"
            ]

            found_sequence = []
            for step in expected_sequence:
                if keyword_locations.get(step) or keyword_locations.get(step.replace("상승", " 상승")):
                    found_sequence.append(step)

            if found_sequence:
                print("   🔄 재구성된 프로세스:")
                for i, step in enumerate(found_sequence):
                    arrow = " → " if i < len(found_sequence) - 1 else ""
                    print(f"   {i+1}. {step}{arrow}", end="")
                print()

                # 각 단계의 상세 정보
                print("\n   📋 각 단계 상세:")
                for step in found_sequence:
                    locs = keyword_locations.get(step, [])
                    if locs:
                        print(f"   • {step}: {locs[0]['context'][:100]}...")

        print("\n" + "=" * 60)
        print("💡 다이어그램 파싱 개선 방향:")
        print("   1. XML에서 drawing/shape 요소의 텍스트 추출")
        print("   2. 텍스트박스와 화살표의 위치 관계 분석")
        print("   3. 프로세스 흐름 패턴 인식 강화")
        print("   4. 순서 추론 알고리즘 구현")

if __name__ == "__main__":
    asyncio.run(analyze_diagram_content())