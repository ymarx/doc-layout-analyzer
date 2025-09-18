#!/usr/bin/env python3
"""
파서가 실제로 무엇을 추출하는지 상세 검사
"""

import asyncio
import json
from pathlib import Path
from src.parsers.unified_docx_parser import UnifiedDocxParser
import re

async def inspect_document_parsing():
    """문서 파싱 결과 상세 검사"""
    print("🔍 기술기준_예시.docx 상세 분석")
    print("=" * 60)

    document_path = "../기술기준_예시.docx"

    parser = UnifiedDocxParser()

    # Enhanced 모드로 파싱 (XML 분석 포함)
    parser.parsing_mode = 'enhanced'  # XML 분석 포함
    result = await parser.parse(document_path)

    if not result.success:
        print(f"❌ 파싱 실패: {result.error}")
        return

    content = result.content
    raw_content = content.get('raw_content', {})

    print("\n📄 추출된 원시 콘텐츠:")
    print("-" * 40)

    # 1. 단락 분석
    if 'paragraphs' in raw_content:
        paragraphs = raw_content['paragraphs']
        print(f"\n📝 단락 수: {len(paragraphs)}")

        # 패턴 감지
        doc_number_pattern = r'TP-\d{3}-\d{3}-\d{3}'
        date_pattern = r'\d{2}\.\d{2}\.\d{2}'
        section_pattern = r'^\d+\.\s+'

        doc_numbers = []
        dates = []
        sections = []

        for i, para in enumerate(paragraphs[:20]):  # 처음 20개만
            text = para.get('text', '').strip()
            if text:
                print(f"  [{i:2d}] {text[:80]}...")

                # 문서번호 찾기
                if match := re.search(doc_number_pattern, text):
                    doc_numbers.append(match.group())

                # 날짜 찾기
                if match := re.search(date_pattern, text):
                    dates.append(match.group())

                # 섹션 찾기
                if re.match(section_pattern, text):
                    sections.append(text)

    # 2. 표 분석
    if 'tables' in raw_content:
        tables = raw_content['tables']
        print(f"\n📊 표 수: {len(tables)}")
        for i, table in enumerate(tables):
            if isinstance(table, dict):
                rows = table.get('rows', [])
                if isinstance(rows, list):
                    print(f"  표 {i+1}: {len(rows)}행")
                    if rows and len(rows) > 0:
                        print(f"    첫 행: {rows[0][:3] if len(rows[0]) > 3 else rows[0]}")
                else:
                    print(f"  표 {i+1}: rows가 list가 아님 (타입: {type(rows)})")
            else:
                print(f"  표 {i+1}: dict가 아님 (타입: {type(table)})")

    # 3. XML 구조 분석
    if 'xml_structure' in raw_content:
        xml_struct = raw_content['xml_structure']
        print(f"\n📋 XML 구조 정보:")
        for key, value in xml_struct.items():
            if key != 'body_text':  # body_text는 너무 길어서 제외
                print(f"  {key}: {str(value)[:100]}")

    # 4. 다이어그램 분석
    if 'diagrams' in raw_content:
        diagrams = raw_content['diagrams']
        print(f"\n🎨 다이어그램 수: {len(diagrams)}")

    # 5. 패턴 분석 결과
    print("\n🔍 감지된 패턴:")
    print("-" * 40)
    if doc_numbers:
        print(f"📌 문서번호: {', '.join(set(doc_numbers))}")
    if dates:
        print(f"📅 날짜: {', '.join(set(dates))}")
    if sections:
        print(f"📑 섹션:")
        for section in sections[:10]:
            print(f"   - {section}")

    # 6. DocJSON 분석
    if 'docjson' in content:
        docjson = content['docjson']
        if docjson:
            print("\n📄 DocJSON 구조:")
            print("-" * 40)
            if hasattr(docjson, 'to_dict'):
                docjson_dict = docjson.to_dict()
            else:
                docjson_dict = docjson

            if docjson_dict:
                # 메타데이터
                if 'metadata' in docjson_dict:
                    print("📋 메타데이터:")
                    for key, value in docjson_dict['metadata'].items():
                        print(f"   {key}: {value}")

                # 섹션 구조
                if 'sections' in docjson_dict:
                    sections = docjson_dict['sections']
                    print(f"\n📑 섹션 수: {len(sections)}")
                    for section in sections[:5]:
                        print(f"   - {section.get('heading', 'No heading')}")

    # 7. 새로운 구조 분석 결과 확인
    if 'document_structure' in content:
        doc_struct = content['document_structure']
        print("\n🆕 고급 구조 분석 결과:")
        print("-" * 40)
        print(f"📌 문서번호: {doc_struct.get('document_number', 'None')}")
        print(f"📝 제목: {doc_struct.get('title', 'None')}")
        print(f"👤 작성자: {doc_struct.get('author', 'None')}")
        print(f"📅 시행일: {doc_struct.get('effective_date', 'None')}")
        print(f"🔄 개정번호: {doc_struct.get('revision', 'None')}")
        print(f"📊 인식율: {doc_struct.get('recognition_score', 0):.1f}%")

        if doc_struct.get('patterns_found'):
            print(f"\n🔍 감지된 패턴들:")
            for pattern, value in doc_struct['patterns_found'].items():
                print(f"   - {pattern}: {value}")

    # 8. 구조 인식 능력 평가
    print("\n🎯 구조 인식 평가:")
    print("-" * 40)

    capabilities = {
        "문서번호 감지": len(doc_numbers) > 0,
        "날짜 감지": len(dates) > 0,
        "섹션 구조 감지": len(sections) > 0,
        "표 감지": len(tables) if 'tables' in raw_content else 0,
        "다이어그램 감지": len(diagrams) if 'diagrams' in raw_content else 0
    }

    for capability, result in capabilities.items():
        status = "✅" if result else "❌"
        print(f"  {status} {capability}: {result}")

    # 8. ANNOTATION_GUIDE.md와 비교
    print("\n📊 ANNOTATION_GUIDE.md 대비 실제 능력:")
    print("-" * 40)

    expected = {
        "문서 타입 인식 (기술기준)": False,  # 아직 구현 안됨
        "구조 파싱 (10개 섹션)": len(sections) >= 10 if sections else False,
        "다이어그램 감지 (7개)": len(diagrams) >= 7 if 'diagrams' in raw_content else False,
        "헤더 정보 추출": len(doc_numbers) > 0,
        "작성자 정보": False,  # 확인 필요
        "번호 매겨진 섹션": len(sections) > 0
    }

    for feature, detected in expected.items():
        status = "✅" if detected else "❌"
        print(f"  {status} {feature}")

    success_rate = sum(1 for v in expected.values() if v) / len(expected) * 100
    print(f"\n📈 전체 인식율: {success_rate:.1f}%")

    if success_rate < 50:
        print("\n⚠️ 인식율이 낮습니다. 파서 개선이 필요합니다!")
        print("💡 제안: 패턴 인식과 구조 분석 기능을 강화해야 합니다.")

if __name__ == "__main__":
    asyncio.run(inspect_document_parsing())