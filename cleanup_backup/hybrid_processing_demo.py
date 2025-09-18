#!/usr/bin/env python3
"""
하이브리드 문서 처리 데모
템플릿 매칭 + 자동감지 조합 시스템
"""
import asyncio
from pathlib import Path
from src.core.integrated_pipeline import IntegratedPipeline, PipelineConfig, ProcessingMode

async def hybrid_document_processing(document_path: str, template_id: str = None):
    """
    하이브리드 문서 처리 데모

    Args:
        document_path: 처리할 문서 경로
        template_id: 사용할 템플릿 ID (없으면 자동 매칭)
    """

    # 1. 파이프라인 초기화
    pipeline = IntegratedPipeline("pipeline_output")

    # 2. 하이브리드 처리 설정
    config = PipelineConfig(
        processing_mode=ProcessingMode.COMPLETE,  # 전체 처리

        # 🤖 템플릿 시스템 활성화
        enable_template_matching=True,      # 템플릿 매칭 활성화
        auto_apply_template=True,           # 자동 템플릿 적용
        template_confidence_threshold=0.6,  # 신뢰도 임계값 (60%)
        custom_template_id=template_id,     # 특정 템플릿 강제 사용

        # 🔍 자동감지 시스템 활성화
        enable_ocr=True,                    # OCR 활성화
        enable_diagrams=True,               # 다이어그램 감지

        # 📝 주석 시스템 활성화
        enable_user_annotations=True,       # 사용자 주석 시스템

        # 📊 벡터화 (선택)
        enable_vectorization=False,         # 필요시 True로 변경

        # 📄 출력 형식
        output_formats=["json", "markdown", "summary"]
    )

    print(f"🚀 하이브리드 문서 처리 시작: {document_path}")
    print(f"🎯 템플릿 매칭: {'활성화' if config.enable_template_matching else '비활성화'}")
    print(f"🤖 자동 적용: {'활성화' if config.auto_apply_template else '비활성화'}")
    print(f"📊 신뢰도 임계값: {config.template_confidence_threshold}")

    # 3. 문서 처리 실행
    try:
        result = await pipeline.process_document(document_path, config)

        # 4. 결과 분석 및 출력
        print("\n" + "="*60)
        print("📋 처리 결과 요약")
        print("="*60)

        # 기본 정보
        print(f"📄 문서: {result.docjson.metadata.source.get('path', 'Unknown')}")
        print(f"⏱️ 처리 시간: {result.processing_time:.2f}초")

        # 템플릿 매칭 결과
        if result.template_match:
            print(f"\n🎯 템플릿 매칭 성공!")
            print(f"   📝 템플릿: {result.template_match.template_name}")
            print(f"   📊 신뢰도: {result.template_match.confidence:.2f}")
            print(f"   🎮 적용 여부: {'✅ 자동 적용됨' if result.metadata.get('template_applied') else '❌ 수동 확인 필요'}")

            # 매칭된 필드들
            if result.template_match.matched_fields:
                print(f"   🔍 매칭된 필드: {len(result.template_match.matched_fields)}개")
                for field_name, confidence in list(result.template_match.matched_fields.items())[:3]:
                    print(f"      • {field_name}: {confidence:.2f}")
                if len(result.template_match.matched_fields) > 3:
                    print(f"      • ... 외 {len(result.template_match.matched_fields) - 3}개")
        else:
            print(f"\n❌ 템플릿 매칭 실패 - 자동감지 모드로 처리")

        # 자동감지 결과
        if result.docjson:
            sections = len([b for b in result.docjson.blocks if b.block_type.value == 'section_header'])
            tables = len([b for b in result.docjson.blocks if b.block_type.value == 'table'])
            diagrams = len([b for b in result.docjson.blocks if b.block_type.value == 'diagram'])

            print(f"\n🔍 자동감지 결과:")
            print(f"   📑 총 블록: {len(result.docjson.blocks)}개")
            print(f"   📋 섹션: {sections}개")
            print(f"   📊 표: {tables}개")
            print(f"   🖼️ 다이어그램: {diagrams}개")

        # 하이브리드 통합 결과
        if result.annotation:
            print(f"\n🎭 하이브리드 통합 결과:")
            print(f"   📝 총 필드: {len(result.annotation.fields)}개")
            template_fields = len([f for f in result.annotation.fields if f.metadata.get('source') == 'template'])
            auto_fields = len([f for f in result.annotation.fields if f.metadata.get('source') == 'auto_detection'])
            print(f"   🎯 템플릿 필드: {template_fields}개")
            print(f"   🤖 자동감지 필드: {auto_fields}개")

            # 추출된 값들
            extracted = len([k for k, v in result.annotation.extracted_values.items() if v])
            print(f"   ✅ 추출된 값: {extracted}개")

        # 출력 파일들
        print(f"\n📁 생성된 파일:")
        for file_type, file_path in result.intermediate_files.items():
            print(f"   📄 {file_type}: {file_path}")

        return result

    except Exception as e:
        print(f"❌ 처리 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None

def demo_template_usage():
    """템플릿 활용 데모"""

    print("🎯 템플릿 기반 하이브리드 처리 데모")
    print("="*50)

    # 기존 템플릿 확인
    from src.core.template_manager import TemplateManager
    template_manager = TemplateManager(Path("pipeline_output/annotations/templates"))

    if template_manager.templates:
        print("📋 사용 가능한 템플릿:")
        for i, (template_id, template) in enumerate(template_manager.templates.items(), 1):
            print(f"   {i}. {template.name} ({template.document_type})")
            print(f"      ID: {template_id}")
            print(f"      필드: {len(template.template_fields)}개")

        # 첫 번째 템플릿 선택
        first_template = list(template_manager.templates.values())[0]
        print(f"\n🎯 사용할 템플릿: {first_template.name}")
        return first_template.id
    else:
        print("❌ 등록된 템플릿이 없습니다.")
        print("   먼저 python create_template_simple.py를 실행하세요.")
        return None

async def main():
    """메인 실행 함수"""

    # 템플릿 확인
    template_id = demo_template_usage()

    if not template_id:
        return

    print(f"\n" + "="*60)
    print("🚀 하이브리드 처리 시작")
    print("="*60)

    # 테스트 문서 (기존 문서로 테스트)
    test_document = "../기술기준_예시.docx"

    if not Path(test_document).exists():
        print(f"❌ 테스트 문서를 찾을 수 없습니다: {test_document}")
        print("   다른 문서 경로를 지정하거나 해당 문서를 준비하세요.")
        return

    # 시나리오 1: 템플릿 자동 매칭
    print("\n🎯 시나리오 1: 템플릿 자동 매칭")
    await hybrid_document_processing(test_document)

    # 시나리오 2: 특정 템플릿 강제 사용
    print("\n🎯 시나리오 2: 특정 템플릿 강제 사용")
    await hybrid_document_processing(test_document, template_id)

if __name__ == "__main__":
    asyncio.run(main())