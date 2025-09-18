#!/usr/bin/env python3
"""
DocJSON 생성 디버깅 스크립트
파이프라인에서 DocJSON이 실패하는 원인을 찾기 위한 디버깅
"""

import asyncio
import sys
from pathlib import Path

from src.parsers.unified_docx_parser import UnifiedDocxParser
from src.core.modernized_pipeline import ModernizedPipeline
from src.core.simplified_config import create_basic_config


async def debug_parser_directly():
    """파서 직접 테스트"""
    print("🔧 파서 직접 테스트")
    print("-" * 40)

    document_path = "../기술기준_예시.docx"
    if not Path(document_path).exists():
        print(f"❌ 문서를 찾을 수 없습니다: {document_path}")
        return False

    try:
        parser = UnifiedDocxParser()
        result = await parser.parse(document_path)

        print(f"✅ 파싱 성공: {result.success}")
        print(f"📄 콘텐츠 있음: {result.content is not None}")

        if result.content:
            print(f"🔑 콘텐츠 키들: {list(result.content.keys())}")

            if 'docjson' in result.content:
                docjson = result.content['docjson']
                print(f"📋 DocJSON 타입: {type(docjson)}")
                print(f"📊 DocJSON None 여부: {docjson is None}")

                if docjson:
                    print(f"📖 DocJSON 속성들:")
                    if hasattr(docjson, 'metadata'):
                        print(f"   - metadata: {type(docjson.metadata)}")
                    if hasattr(docjson, 'sections'):
                        print(f"   - sections: {len(docjson.sections) if docjson.sections else 0}개")
                    if hasattr(docjson, 'doc_id'):
                        print(f"   - doc_id: {docjson.doc_id}")

        return result.success

    except Exception as e:
        print(f"❌ 파서 직접 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def debug_pipeline_stage():
    """파이프라인 단계 디버깅"""
    print("\n🏭 파이프라인 단계 디버깅")
    print("-" * 40)

    document_path = "../기술기준_예시.docx"

    try:
        pipeline = ModernizedPipeline(output_dir="debug_output")
        config = create_basic_config()
        preset = config.to_preset(pipeline.config_manager)

        # 모의 결과 객체
        from src.core.modernized_pipeline import ModernPipelineResult
        from src.core.simplified_config import ProcessingLevel

        mock_result = ModernPipelineResult(
            success=False,
            document_id="debug_test",
            processing_level=ProcessingLevel.BASIC
        )

        print(f"📁 문서 경로: {document_path}")
        print(f"⚙️ 프리셋: {preset.description}")

        # Stage 1 실행
        print("\n🎬 Stage 1 실행 중...")
        await pipeline._stage_document_parsing(document_path, preset, mock_result)

        print(f"✅ Stage 1 완료")
        print(f"📊 완료된 단계: {mock_result.stages_completed}")
        print(f"📋 DocJSON 생성됨: {mock_result.docjson is not None}")

        if mock_result.docjson:
            print(f"📖 DocJSON 타입: {type(mock_result.docjson)}")
            if hasattr(mock_result.docjson, 'sections'):
                print(f"📄 섹션 수: {len(mock_result.docjson.sections) if mock_result.docjson.sections else 0}")

        return mock_result.docjson is not None

    except Exception as e:
        print(f"❌ 파이프라인 단계 디버깅 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def debug_docjson_creation():
    """DocJSON 생성 과정 디버깅"""
    print("\n📝 DocJSON 생성 과정 디버깅")
    print("-" * 40)

    try:
        from src.core.docjson import DocJSON, DocumentMetadata, DocumentSection, ContentBlock, ContentBlockType, BoundingBox, SemanticInfo

        # 수동으로 DocJSON 생성 테스트
        print("🏗️ 수동 DocJSON 생성 테스트...")

        metadata = DocumentMetadata(
            title="테스트 문서",
            doc_type="docx",
            author="테스트",
            pages=1
        )
        print(f"✅ DocumentMetadata 생성: {metadata.title}")

        section = DocumentSection(
            id="test_section",
            path=["root"],
            heading="테스트 섹션",
            level=1,
            blocks=[]
        )
        print(f"✅ DocumentSection 생성: {section.heading}")

        docjson = DocJSON(
            version="2.0",
            doc_id="test_doc",
            metadata=metadata,
            sections=[section]
        )
        print(f"✅ DocJSON 생성: {docjson.doc_id}")

        # 딕셔너리 변환 테스트
        docjson_dict = docjson.to_dict()
        print(f"✅ to_dict() 성공: {len(docjson_dict)} 키")

        # from_dict 테스트
        restored_docjson = DocJSON.from_dict(docjson_dict)
        print(f"✅ from_dict() 성공: {restored_docjson.doc_id}")

        return True

    except Exception as e:
        print(f"❌ DocJSON 생성 과정 디버깅 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """메인 디버깅 실행"""
    print("🔍 DocJSON 생성 디버깅 시작")
    print("=" * 50)

    results = []

    # 1. 파서 직접 테스트
    result1 = await debug_parser_directly()
    results.append(("파서 직접 테스트", result1))

    # 2. 파이프라인 단계 디버깅
    result2 = await debug_pipeline_stage()
    results.append(("파이프라인 단계", result2))

    # 3. DocJSON 생성 과정
    result3 = await debug_docjson_creation()
    results.append(("DocJSON 생성 과정", result3))

    # 결과 요약
    print("\n" + "=" * 50)
    print("🎯 디버깅 결과 요약")
    print("=" * 50)

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:20s}: {status}")

    successful = sum(1 for _, success in results if success)
    total = len(results)

    print(f"\n📊 성공률: {successful}/{total} ({successful/total*100:.1f}%)")

    if successful == total:
        print("🎉 모든 테스트 성공! DocJSON 생성에 문제가 없습니다.")
    else:
        print("⚠️ 일부 테스트 실패. 추가 디버깅이 필요합니다.")


if __name__ == "__main__":
    asyncio.run(main())