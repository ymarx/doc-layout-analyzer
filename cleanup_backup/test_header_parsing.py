#!/usr/bin/env python3
"""헤더/푸터 파싱 테스트"""

import asyncio
from src.parsers.unified_docx_parser import UnifiedDocxParser

async def test_header_footer():
    parser = UnifiedDocxParser()
    parser.parsing_mode = 'enhanced'

    result = await parser.parse("../기술기준_예시.docx")

    if result.success:
        content = result.content
        raw_content = content.get('raw_content', {})

        # XML 구조에서 헤더/푸터 확인
        xml_struct = raw_content.get('xml_structure', {})
        headers_footers = xml_struct.get('headers_footers', {})

        print("🔍 헤더/푸터 추출 결과:")
        print("-" * 40)

        if headers_footers:
            print(f"✅ 헤더 수: {len(headers_footers.get('headers', []))}")
            for header in headers_footers.get('headers', []):
                print(f"   헤더: {header.get('text', '')[:100]}...")

            print(f"✅ 푸터 수: {len(headers_footers.get('footers', []))}")
            for footer in headers_footers.get('footers', []):
                print(f"   푸터: {footer.get('text', '')[:100]}...")
        else:
            print("❌ 헤더/푸터를 찾을 수 없습니다")

        # 구조 분석 결과 확인
        doc_struct = content.get('document_structure', {})
        if doc_struct:
            print("\n📊 문서 구조 분석 결과:")
            print(f"   문서번호: {doc_struct.get('document_number')}")
            print(f"   시행일: {doc_struct.get('effective_date')}")
            print(f"   개정번호: {doc_struct.get('revision')}")

if __name__ == "__main__":
    asyncio.run(test_header_footer())