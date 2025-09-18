#!/usr/bin/env python3
"""최종 검증 - 완전히 수정된 파서 테스트"""

import asyncio
import json
from pathlib import Path
from src.parsers.unified_docx_parser import UnifiedDocxParser

async def final_verification():
    """최종 검증 실행"""
    print("🔍 최종 검증: 완전히 수정된 파서 테스트")
    print("=" * 60)

    parser = UnifiedDocxParser()
    parser.parsing_mode = 'enhanced'

    result = await parser.parse("../기술기준_예시.docx")

    if result.success:
        content = result.content
        doc_struct = content.get('document_structure', {})
        docjson = content.get('docjson')

        print("✅ 파싱 성공!")
        print(f"   인식율: {doc_struct.get('recognition_score', 0):.1f}%")
        print()

        # 핵심 정보 확인
        print("📋 감지된 핵심 정보:")
        items = [
            ("문서번호", doc_struct.get('document_number')),
            ("제목", (doc_struct.get('title') or "")[:50] + "..."),
            ("작성자", doc_struct.get('author')),
            ("시행일", doc_struct.get('effective_date')),
            ("개정번호", doc_struct.get('revision')),
        ]

        for name, value in items:
            status = "✅" if value else "❌"
            print(f"   {status} {name}: {value}")

        # DocJSON 생성 확인
        print(f"\n📄 DocJSON 생성: {'✅' if docjson else '❌'}")

        if docjson:
            print("   DocJSON 메타데이터:")
            if isinstance(docjson, dict):
                metadata = docjson.get('metadata', {})
                print(f"   - 문서번호: {metadata.get('document_number', 'None')}")
                print(f"   - 작성자: {metadata.get('author', 'None')}")
                print(f"   - 시행일: {metadata.get('effective_date', 'None')}")
                print(f"   - 개정번호: {metadata.get('revision', 'None')}")

            # 완전한 DocJSON 저장
            final_output_dir = Path("final_output")
            final_output_dir.mkdir(exist_ok=True)

            docjson_path = final_output_dir / "완전한_DocJSON.json"
            with open(docjson_path, 'w', encoding='utf-8') as f:
                json.dump(docjson, f, ensure_ascii=False, indent=2)

            print(f"\n💾 완전한 DocJSON 저장: {docjson_path}")

        # ANNOTATION_GUIDE.md 달성도 확인
        print("\n📊 ANNOTATION_GUIDE.md 달성도:")
        guide_requirements = {
            "문서 타입 인식": "기술기준" in str(doc_struct.get('title', '')),
            "문서번호 추출": bool(doc_struct.get('document_number')),
            "작성자 정보": bool(doc_struct.get('author')),
            "시행일 정보": bool(doc_struct.get('effective_date')),
            "개정번호": bool(doc_struct.get('revision')),
            "섹션 구조": len(doc_struct.get('sections', [])) > 0,
            "다이어그램 감지": doc_struct.get('metadata', {}).get('total_diagrams', 0) > 0
        }

        achieved = 0
        total = len(guide_requirements)

        for requirement, achieved_bool in guide_requirements.items():
            status = "✅" if achieved_bool else "❌"
            if achieved_bool:
                achieved += 1
            print(f"   {status} {requirement}")

        achievement_rate = (achieved / total) * 100
        print(f"\n🎯 ANNOTATION_GUIDE.md 달성률: {achievement_rate:.1f}% ({achieved}/{total})")

        if achievement_rate >= 80:
            print("🎉 ANNOTATION_GUIDE.md에서 약속한 수준을 달성했습니다!")
        else:
            print("⚠️ 추가 개선이 필요합니다.")

    else:
        print(f"❌ 파싱 실패: {result.error}")

if __name__ == "__main__":
    asyncio.run(final_verification())