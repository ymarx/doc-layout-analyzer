#!/usr/bin/env python3
"""
리팩토링된 시스템 간단 테스트
새로운 통합 파서와 단순화된 설정 시스템 검증
"""

import asyncio
import sys
from pathlib import Path

# 새로운 시스템 임포트
from src.core.simplified_config import (
    ProcessingLevel, PipelineConfig,
    create_basic_config, create_standard_config,
    SimplifiedConfigManager
)
from src.core.modernized_pipeline import ModernizedPipeline, quick_process
from src.parsers.unified_docx_parser import UnifiedDocxParser


async def test_unified_parser():
    """통합 파서 테스트"""
    print("=" * 50)
    print("🔧 통합 파서 테스트")
    print("=" * 50)

    try:
        parser = UnifiedDocxParser()
        print("✅ UnifiedDocxParser 초기화 성공")

        # 지원 형식 확인
        test_files = ["test.docx", "test.pdf", "test.txt"]
        for file in test_files:
            can_handle = parser.can_handle(file)
            print(f"   {file}: {'✅' if can_handle else '❌'} {'지원' if can_handle else '미지원'}")

    except Exception as e:
        print(f"❌ 통합 파서 테스트 실패: {e}")
        return False

    return True


async def test_simplified_config():
    """단순화된 설정 시스템 테스트"""
    print("\n" + "=" * 50)
    print("⚙️ 단순화된 설정 시스템 테스트")
    print("=" * 50)

    try:
        # 설정 관리자 초기화
        config_manager = SimplifiedConfigManager()
        print("✅ SimplifiedConfigManager 초기화 성공")

        # 각 처리 레벨 테스트
        levels = [ProcessingLevel.BASIC, ProcessingLevel.STANDARD, ProcessingLevel.COMPLETE]

        for level in levels:
            preset = config_manager.get_preset(level)
            print(f"\n📋 {level.value.upper()} 레벨:")
            print(f"   설명: {preset.description}")
            print(f"   템플릿 매칭: {'✅' if preset.enable_template_matching else '❌'}")
            print(f"   자동 주석: {'✅' if preset.enable_auto_annotations else '❌'}")
            print(f"   벡터화: {'✅' if preset.enable_vectorization else '❌'}")

        # 편의 함수 테스트
        basic_config = create_basic_config()
        standard_config = create_standard_config()
        print(f"\n✅ 편의 함수 테스트 완료")
        print(f"   기본 설정: {basic_config.processing_level.value}")
        print(f"   표준 설정: {standard_config.processing_level.value}")

    except Exception as e:
        print(f"❌ 설정 시스템 테스트 실패: {e}")
        return False

    return True


async def test_modernized_pipeline():
    """현대화된 파이프라인 테스트"""
    print("\n" + "=" * 50)
    print("🏭 현대화된 파이프라인 테스트")
    print("=" * 50)

    try:
        # 파이프라인 초기화
        pipeline = ModernizedPipeline(output_dir="test_refactor_output")
        print("✅ ModernizedPipeline 초기화 성공")

        # 설정 생성
        config = create_basic_config()
        print(f"✅ 설정 생성 완료: {config.processing_level.value}")

        # 통계 정보 가져오기
        stats = pipeline.get_processing_statistics()
        print(f"📊 처리 통계:")
        print(f"   총 처리된 문서: {stats['total_processed']}개")
        print(f"   평균 처리 시간: {stats['average_processing_time']:.3f}초")
        print(f"   평균 품질 점수: {stats['average_quality_score']:.1f}/100")

    except Exception as e:
        print(f"❌ 파이프라인 테스트 실패: {e}")
        return False

    return True


async def test_document_processing():
    """실제 문서 처리 테스트 (문서가 있는 경우)"""
    print("\n" + "=" * 50)
    print("📄 문서 처리 테스트")
    print("=" * 50)

    # 테스트 문서 경로들
    test_documents = [
        "../기술기준_예시.docx",
        "기술기준_예시.docx"
    ]

    document_path = None
    for doc_path in test_documents:
        if Path(doc_path).exists():
            document_path = doc_path
            break

    if not document_path:
        print("⚠️ 테스트 문서를 찾을 수 없어 스킵합니다")
        print("   (기술기준_예시.docx 파일이 필요합니다)")
        return True

    try:
        print(f"📄 테스트 문서: {document_path}")

        # 간단한 처리 테스트
        result = await quick_process(
            document_path,
            ProcessingLevel.BASIC,
            "test_refactor_output"
        )

        if result.success:
            print("✅ 문서 처리 성공!")
            print(f"   문서 ID: {result.document_id}")
            print(f"   처리 시간: {result.processing_time:.3f}초")
            print(f"   완료된 단계: {', '.join(result.stages_completed)}")
            print(f"   품질 점수: {result.quality_score:.1f}/100")

            if result.docjson:
                print(f"   DocJSON 생성: ✅")
                print(f"   섹션 수: {len(result.docjson.sections)}")
        else:
            print(f"❌ 문서 처리 실패: {result.error}")
            return False

    except Exception as e:
        print(f"❌ 문서 처리 테스트 실패: {e}")
        return False

    return True


async def test_legacy_compatibility():
    """레거시 호환성 테스트"""
    print("\n" + "=" * 50)
    print("🔄 레거시 호환성 테스트")
    print("=" * 50)

    try:
        # 레거시 설정 마이그레이션 테스트
        from src.core.simplified_config import migrate_legacy_config

        legacy_config = {
            'processing_mode': 'enhanced',
            'template_confidence_threshold': 0.7,
            'output_formats': ['docjson', 'annotations']
        }

        new_config = migrate_legacy_config(legacy_config)
        print("✅ 레거시 설정 마이그레이션 성공")
        print(f"   {legacy_config['processing_mode']} → {new_config.processing_level.value}")
        print(f"   임계값: {new_config.override_template_threshold}")

        # 레거시 파서 팩토리 테스트
        from src.parsers import DocumentParserFactory

        # 새 방식
        factory_new = DocumentParserFactory(use_legacy=False)
        parser_new = factory_new.get_parser('test.docx')
        print(f"✅ 새 팩토리: {parser_new.__class__.__name__}")

        # 레거시 방식
        factory_legacy = DocumentParserFactory(use_legacy=True)
        parser_legacy = factory_legacy.get_parser('test.docx')
        print(f"✅ 레거시 팩토리: {parser_legacy.__class__.__name__}")

    except Exception as e:
        print(f"❌ 레거시 호환성 테스트 실패: {e}")
        return False

    return True


async def main():
    """메인 테스트 실행"""
    print("🚀 리팩토링된 시스템 검증 테스트 시작")
    print("=" * 60)

    tests = [
        ("통합 파서", test_unified_parser),
        ("설정 시스템", test_simplified_config),
        ("파이프라인", test_modernized_pipeline),
        ("문서 처리", test_document_processing),
        ("레거시 호환성", test_legacy_compatibility)
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 테스트 예외 발생: {e}")
            results.append((test_name, False))

    # 결과 요약
    print("\n" + "=" * 60)
    print("📊 테스트 결과 요약")
    print("=" * 60)

    passed = 0
    failed = 0

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:15s}: {status}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\n총 {len(results)}개 테스트 중 {passed}개 성공, {failed}개 실패")

    if failed == 0:
        print("🎉 모든 테스트 통과! 리팩토링이 성공적으로 완료되었습니다.")
        return True
    else:
        print("⚠️ 일부 테스트 실패. 문제를 해결하고 다시 시도해주세요.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)