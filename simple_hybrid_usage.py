#!/usr/bin/env python3
"""
간단한 하이브리드 처리 사용법
"""
import asyncio
from pathlib import Path
from src.core.enhanced_modernized_pipeline import EnhancedModernizedPipeline
from src.core.simplified_config import PipelineConfig, ProcessingLevel

async def simple_hybrid_processing(document_path: str):
    """
    간단한 하이브리드 문서 처리

    Args:
        document_path: 처리할 문서 경로
    """

    print(f"📄 문서 처리 시작: {Path(document_path).name}")

    # 파이프라인 초기화
    pipeline = EnhancedModernizedPipeline(
        output_dir="pipeline_output",
        templates_dir="templates/definitions"
    )

    # 하이브리드 설정 (템플릿 자동 매칭 + 자동감지)
    config = PipelineConfig(
        processing_level=ProcessingLevel.COMPLETE,  # 🎯 완전 처리 모드
        override_output_formats=['docjson', 'annotations', 'vectors']  # 📄 출력 형식
    )

    try:
        # 문서 처리 실행
        result = await pipeline.process_document(document_path, config)

        print(f"✅ 처리 완료 ({result.processing_time:.1f}초)")

        # 템플릿 매칭 결과
        if result.template_match:
            print(f"🎯 템플릿 매칭: {result.template_match.template_name}")
            print(f"📊 신뢰도: {result.template_match.confidence:.1%}")

            if result.metadata.get('template_applied'):
                print("🤖 템플릿 자동 적용됨")
            else:
                print("⚠️ 신뢰도 부족 - 자동감지 모드")
        else:
            print("🔍 순수 자동감지 모드")

        # 추출 결과
        if result.annotation:
            total_fields = len(result.annotation.fields)
            extracted_values = len([v for v in result.annotation.extracted_values.values() if v])
            print(f"📋 총 필드: {total_fields}개, 추출 값: {extracted_values}개")

        # 생성된 파일
        print(f"📁 결과 파일:")
        for file_type, file_path in result.intermediate_files.items():
            print(f"   📄 {file_type}: {file_path.name}")

        return result

    except Exception as e:
        print(f"❌ 오류: {e}")
        return None

def main():
    """메인 함수"""
    import sys

    if len(sys.argv) != 2:
        print("사용법: python simple_hybrid_usage.py <문서경로>")
        print("예시: python simple_hybrid_usage.py ../기술기준_예시.docx")
        return

    document_path = sys.argv[1]

    if not Path(document_path).exists():
        print(f"❌ 파일을 찾을 수 없습니다: {document_path}")
        return

    # 비동기 실행
    asyncio.run(simple_hybrid_processing(document_path))

if __name__ == "__main__":
    main()