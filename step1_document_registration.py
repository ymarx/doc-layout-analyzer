#!/usr/bin/env python3
"""
1단계: 문서 등재 (Document Registration)
새로운 문서를 시스템에 등재하고 기본 정보를 확인합니다.
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.enhanced_modernized_pipeline import EnhancedModernizedPipeline
from src.core.simplified_config import PipelineConfig, ProcessingLevel

async def step1_register_document():
    print("=" * 70)
    print("🔍 1단계: 문서 등재 및 기본 분석")
    print("=" * 70)

    # 사용할 문서 확인
    document_path = "../기술기준_예시.docx"
    doc_file = Path(document_path)

    if not doc_file.exists():
        print(f"❌ 문서를 찾을 수 없습니다: {document_path}")
        print("💡 다음 중 하나를 선택하세요:")
        print("   - 기술기준_예시.docx 파일을 상위 디렉토리에 배치")
        print("   - 다른 DOCX 파일 경로를 지정")
        return None

    print(f"✅ 문서 발견: {doc_file.name}")
    print(f"📁 파일 크기: {doc_file.stat().st_size:,} bytes")
    print()

    # 기본 파이프라인으로 문서 구조 분석
    print("📋 문서 기본 구조 분석 중...")
    pipeline = EnhancedModernizedPipeline(
        output_dir="step1_analysis",
        templates_dir="templates/definitions"
    )

    # 기본 분석만 수행 (빠른 처리)
    config = PipelineConfig(
        processing_level=ProcessingLevel.BASIC,
        override_output_formats=['docjson']
    )

    result = await pipeline.process_document(document_path, config)

    if result.success:
        print("✅ 문서 분석 완료!")
        print(f"⏱️ 처리 시간: {result.processing_time:.3f}초")
        print()

        # 문서 기본 정보 출력
        docjson = result.docjson
        metadata = docjson.get('metadata', {})

        print("📄 문서 기본 정보:")
        print(f"   제목: {metadata.get('title', 'N/A')[:100]}...")
        print(f"   문서번호: {metadata.get('document_number', 'N/A')}")
        print(f"   효력발생일: {metadata.get('effective_date', 'N/A')}")
        print(f"   작성자: {metadata.get('author', 'N/A')}")
        print(f"   언어: {metadata.get('language', 'N/A')}")
        print()

        # 문서 구조 정보
        sections = docjson.get('sections', [])
        print(f"📊 문서 구조:")
        print(f"   섹션 수: {len(sections)}개")

        total_blocks = sum(len(section.get('blocks', [])) for section in sections)
        print(f"   전체 블록: {total_blocks}개")

        # 헤더/푸터 정보
        headers = docjson.get('headers', [])
        footers = docjson.get('footers', [])
        print(f"   헤더: {len(headers)}개, 푸터: {len(footers)}개")
        print()

        # 프로세스 플로우 확인
        process_flows = metadata.get('source', [])
        flow_found = any(source.get('type') == 'sequential' for source in process_flows)
        if flow_found:
            print("🔄 프로세스 플로우 감지됨!")
            for source in process_flows:
                if source.get('type') == 'sequential':
                    steps = source.get('steps', [])
                    print(f"   단계 수: {len(steps)}개")
                    for step in steps[:3]:  # 처음 3개만 표시
                        print(f"   {step.get('marker', '')} {step.get('title', '')}")
                    if len(steps) > 3:
                        print(f"   ... 및 {len(steps) - 3}개 더")
        print()

        print("🎯 1단계 완료! 다음 단계에서 템플릿을 선택합니다.")
        return {
            'document_path': document_path,
            'docjson': docjson,
            'metadata': metadata,
            'structure_info': {
                'sections': len(sections),
                'blocks': total_blocks,
                'headers': len(headers),
                'footers': len(footers),
                'has_process_flow': flow_found
            }
        }
    else:
        print(f"❌ 문서 분석 실패: {result.error}")
        return None

if __name__ == "__main__":
    document_info = asyncio.run(step1_register_document())
    if document_info:
        print("\n" + "="*70)
        print("✅ 문서 등재 성공! 이제 step2_template_selection.py를 실행하세요.")
        print("="*70)