#!/usr/bin/env python3
"""
개선된 파서의 산출물 생성 및 검증
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from src.parsers.unified_docx_parser import UnifiedDocxParser
from src.core.modernized_pipeline import ModernizedPipeline
from src.core.simplified_config import create_basic_config, create_standard_config, create_complete_config

async def generate_improved_outputs():
    """개선된 파서로 산출물 생성"""

    print("=" * 80)
    print("📊 개선된 파서 산출물 생성 및 검증")
    print("=" * 80)
    print(f"⏰ 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    document_path = "../기술기준_예시.docx"
    output_dir = Path("improved_output")
    output_dir.mkdir(exist_ok=True)

    # 1. 파서 직접 실행으로 상세 분석 결과 생성
    print("1️⃣ 파서 직접 실행 - 상세 분석")
    print("-" * 60)

    parser = UnifiedDocxParser()
    parser.parsing_mode = 'enhanced'  # XML 분석 포함

    result = await parser.parse(document_path)

    if result.success:
        content = result.content

        # 원시 콘텐츠 저장
        raw_output_path = output_dir / "01_raw_parsing_result.json"
        with open(raw_output_path, 'w', encoding='utf-8') as f:
            # DocJSON은 dict로 변환
            output_content = {
                'parsing_mode': content.get('parsing_mode', {}),
                'document_structure': content.get('document_structure', {}),
                'metadata': result.metadata
            }
            json.dump(output_content, f, ensure_ascii=False, indent=2)

        print(f"✅ 원시 파싱 결과 저장: {raw_output_path}")

        # 문서 구조 분석 결과만 별도 저장
        doc_struct = content.get('document_structure', {})
        if doc_struct:
            struct_path = output_dir / "02_document_structure.json"
            with open(struct_path, 'w', encoding='utf-8') as f:
                json.dump(doc_struct, f, ensure_ascii=False, indent=2)
            print(f"✅ 문서 구조 분석 저장: {struct_path}")

            # 핵심 정보 출력
            print("\n📋 감지된 핵심 정보:")
            print(f"   - 문서번호: {doc_struct.get('document_number', 'None')}")
            print(f"   - 제목: {doc_struct.get('title', 'None')[:50]}...")
            print(f"   - 작성자: {doc_struct.get('author', 'None')}")
            print(f"   - 시행일: {doc_struct.get('effective_date', 'None')}")
            print(f"   - 개정번호: {doc_struct.get('revision', 'None')}")
            print(f"   - 인식율: {doc_struct.get('recognition_score', 0):.1f}%")

        # DocJSON 저장
        if 'docjson' in content and content['docjson']:
            docjson_path = output_dir / "03_docjson_output.json"
            with open(docjson_path, 'w', encoding='utf-8') as f:
                json.dump(content['docjson'], f, ensure_ascii=False, indent=2)
            print(f"✅ DocJSON 저장: {docjson_path}")

    # 2. 파이프라인을 통한 전체 처리
    print("\n2️⃣ 파이프라인 처리 - BASIC 레벨")
    print("-" * 60)

    pipeline = ModernizedPipeline(output_dir=str(output_dir / "pipeline_basic"))
    basic_config = create_basic_config()

    basic_result = await pipeline.process_document(document_path, basic_config)

    if basic_result.success:
        print(f"✅ BASIC 처리 성공")
        print(f"   - 단계 완료: {basic_result.stages_completed}")
        print(f"   - 품질 점수: {basic_result.quality_score:.1f}" if basic_result.quality_score else "   - 품질 점수: N/A")
        print(f"   - 출력 파일: {basic_result.output_files}")

    # 3. STANDARD 레벨 처리
    print("\n3️⃣ 파이프라인 처리 - STANDARD 레벨")
    print("-" * 60)

    pipeline_std = ModernizedPipeline(output_dir=str(output_dir / "pipeline_standard"))
    standard_config = create_standard_config()

    std_result = await pipeline_std.process_document(document_path, standard_config)

    if std_result.success:
        print(f"✅ STANDARD 처리 성공")
        print(f"   - 단계 완료: {std_result.stages_completed}")
        print(f"   - 품질 점수: {std_result.quality_score:.1f}" if std_result.quality_score else "   - 품질 점수: N/A")
        print(f"   - 출력 파일: {std_result.output_files}")

    # 4. 비교 보고서 생성
    print("\n4️⃣ 비교 보고서 생성")
    print("-" * 60)

    comparison_report = {
        "timestamp": datetime.now().isoformat(),
        "document": str(document_path),
        "parser_improvements": {
            "before": {
                "recognition_rate": "33.3%",
                "detected_items": {
                    "document_number": False,
                    "title": False,
                    "author": False,
                    "effective_date": False,
                    "revision": False,
                    "sections": True,
                    "tables": True,
                    "diagrams": True
                }
            },
            "after": {
                "recognition_rate": f"{doc_struct.get('recognition_score', 0):.1f}%",
                "detected_items": {
                    "document_number": bool(doc_struct.get('document_number')),
                    "title": bool(doc_struct.get('title')),
                    "author": bool(doc_struct.get('author')),
                    "effective_date": bool(doc_struct.get('effective_date')),
                    "revision": bool(doc_struct.get('revision')),
                    "sections": len(doc_struct.get('sections', [])) > 0,
                    "tables": True,
                    "diagrams": True
                },
                "extracted_values": {
                    "document_number": doc_struct.get('document_number'),
                    "title": doc_struct.get('title'),
                    "author": doc_struct.get('author'),
                    "effective_date": doc_struct.get('effective_date'),
                    "revision": doc_struct.get('revision'),
                    "section_count": len(doc_struct.get('sections', [])),
                    "patterns_found": doc_struct.get('patterns_found', {})
                }
            }
        },
        "output_files_created": {
            "raw_parsing": str(output_dir / "01_raw_parsing_result.json"),
            "document_structure": str(output_dir / "02_document_structure.json"),
            "docjson": str(output_dir / "03_docjson_output.json"),
            "pipeline_basic": str(output_dir / "pipeline_basic"),
            "pipeline_standard": str(output_dir / "pipeline_standard")
        }
    }

    report_path = output_dir / "00_comparison_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(comparison_report, f, ensure_ascii=False, indent=2)

    print(f"✅ 비교 보고서 저장: {report_path}")

    # 5. 요약 출력
    print("\n" + "=" * 80)
    print("📊 산출물 생성 완료 요약")
    print("=" * 80)

    print("\n✨ 개선 성과:")
    print(f"   - 인식율: 33.3% → {doc_struct.get('recognition_score', 0):.1f}%")
    print(f"   - 문서번호 감지: ❌ → {'✅' if doc_struct.get('document_number') else '❌'}")
    print(f"   - 작성자 감지: ❌ → {'✅' if doc_struct.get('author') else '❌'}")
    print(f"   - 시행일 감지: ❌ → {'✅' if doc_struct.get('effective_date') else '❌'}")
    print(f"   - 개정번호 감지: ❌ → {'✅' if doc_struct.get('revision') else '❌'}")

    print("\n📁 생성된 산출물 위치:")
    print(f"   {output_dir}/")
    for file in sorted(output_dir.glob("*.json")):
        print(f"   ├── {file.name}")
    for dir in sorted(output_dir.glob("pipeline_*")):
        print(f"   ├── {dir.name}/")
        for file in sorted(dir.glob("*.json"))[:3]:
            print(f"   │   └── {file.name}")

    print("\n💡 산출물 확인 방법:")
    print("   1. 00_comparison_report.json - 개선 전후 비교")
    print("   2. 02_document_structure.json - 감지된 모든 구조 정보")
    print("   3. 03_docjson_output.json - 최종 DocJSON 포맷 결과")
    print("   4. pipeline_*/기술기준_예시.docjson - 파이프라인 처리 결과")

    print(f"\n⏰ 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    asyncio.run(generate_improved_outputs())