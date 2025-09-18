#!/usr/bin/env python3
"""
2단계: 템플릿 선택 및 적용 (Template Selection & Application)
사용 가능한 템플릿들을 확인하고 최적의 템플릿을 선택/적용합니다.
"""

import asyncio
import sys
import json
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.enhanced_modernized_pipeline import EnhancedModernizedPipeline
from src.core.simplified_config import PipelineConfig, ProcessingLevel
from src.core.integrated_template_system import IntegratedTemplateSystem

async def step2_template_selection():
    print("=" * 70)
    print("🎯 2단계: 템플릿 선택 및 적용")
    print("=" * 70)

    document_path = "../기술기준_예시.docx"

    # 1. 사용 가능한 템플릿 조회
    print("📚 사용 가능한 템플릿 조회...")
    templates_dir = Path("templates/definitions")

    if not templates_dir.exists():
        print(f"❌ 템플릿 디렉토리가 없습니다: {templates_dir}")
        return None

    template_files = list(templates_dir.glob("*.json"))
    print(f"✅ {len(template_files)}개의 템플릿 발견:")

    templates_info = []
    for template_file in template_files:
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                template_data = json.load(f)

            template_info = {
                'file': template_file.name,
                'id': template_data.get('template_id', 'unknown'),
                'name': template_data.get('name', 'Unknown'),
                'description': template_data.get('description', ''),
                'elements_count': len(template_data.get('elements', []))
            }
            templates_info.append(template_info)

            print(f"   📄 {template_info['name']} ({template_info['id']})")
            print(f"      파일: {template_info['file']}")
            print(f"      요소: {template_info['elements_count']}개")
            print(f"      설명: {template_info['description'][:80]}...")
            print()
        except Exception as e:
            print(f"   ❌ 템플릿 로드 오류 ({template_file.name}): {e}")

    # 2. 자동 템플릿 매칭 테스트
    print("🤖 자동 템플릿 매칭 수행...")
    template_system = IntegratedTemplateSystem(templates_dir)

    # 기본 문서 분석
    pipeline = EnhancedModernizedPipeline(
        output_dir="step2_template_test",
        templates_dir=str(templates_dir)
    )

    config = PipelineConfig(
        processing_level=ProcessingLevel.STANDARD,
        override_output_formats=['docjson']
    )

    # 템플릿 매칭 포함 처리
    result = await pipeline.process_document(document_path, config)

    if result.success and result.template_match:
        tm = result.template_match
        print("✅ 자동 템플릿 매칭 결과:")
        print(f"   🎯 선택된 템플릿: {tm.template_id}")
        print(f"   📊 신뢰도: {tm.confidence:.1%}")
        print(f"   🔧 사용된 전략: {tm.strategy_used.value}")
        print(f"   ✅ 매칭된 필드: {len(tm.matched_fields)}개")
        print(f"   ❌ 누락된 필드: {len(tm.missing_fields)}개")
        print()

        # 매칭된 필드 상세 (일부만 표시)
        print("🔍 매칭된 주요 필드:")
        important_fields = ['document_number', 'effective_date', 'title', 'author']
        for field_name in important_fields:
            if field_name in tm.matched_fields:
                field_data = tm.matched_fields[field_name]
                value = field_data.get('value', '')[:50]
                confidence = field_data.get('confidence', 0)
                method = field_data.get('method', 'unknown')
                print(f"   • {field_name}: \"{value}...\"")
                print(f"     신뢰도: {confidence:.2f}, 방법: {method}")

        if tm.missing_fields:
            print(f"\n⚠️ 누락된 필드: {', '.join(tm.missing_fields[:5])}")
            if len(tm.missing_fields) > 5:
                print(f"   ... 및 {len(tm.missing_fields) - 5}개 더")
        print()

        # 3. 수동 템플릿 선택 옵션 제시
        print("🛠️ 템플릿 선택 옵션:")
        print("   1. 자동 선택된 템플릿 사용 (권장)")
        print("   2. 다른 템플릿 강제 적용")
        print("   3. 새 템플릿 생성")
        print()

        # 자동 선택 템플릿으로 진행
        print("✅ 자동 선택된 템플릿으로 진행합니다.")

        return {
            'selected_template_id': tm.template_id,
            'template_confidence': tm.confidence,
            'template_match': tm,
            'available_templates': templates_info,
            'document_path': document_path
        }
    else:
        print("❌ 템플릿 매칭 실패")
        if not result.success:
            print(f"   오류: {result.error}")

        # 폴백: 첫 번째 사용 가능한 템플릿 사용
        if templates_info:
            fallback_template = templates_info[0]
            print(f"\n🔄 폴백: {fallback_template['name']} 템플릿 사용")
            return {
                'selected_template_id': fallback_template['id'],
                'template_confidence': 0.0,
                'template_match': None,
                'available_templates': templates_info,
                'document_path': document_path
            }
        else:
            return None

async def demonstrate_manual_template_selection():
    """수동 템플릿 선택 데모"""
    print("\n" + "="*50)
    print("🔧 수동 템플릿 선택 예시")
    print("="*50)

    # 특정 템플릿 강제 적용 예시
    document_path = "../기술기준_예시.docx"

    config_custom = PipelineConfig(
        processing_level=ProcessingLevel.STANDARD,
        custom_template_id="technical_standard_v2_improved",  # 특정 템플릿 지정
        override_output_formats=['docjson']
    )

    pipeline = EnhancedModernizedPipeline(
        output_dir="step2_manual_template",
        templates_dir="templates/definitions"
    )

    result = await pipeline.process_document(document_path, config_custom)

    if result.success:
        print(f"✅ 지정된 템플릿 적용 성공!")
        print(f"   템플릿 ID: {config_custom.custom_template_id}")
        if result.template_match:
            print(f"   매칭 신뢰도: {result.template_match.confidence:.1%}")
    else:
        print(f"❌ 지정된 템플릿 적용 실패: {result.error}")

if __name__ == "__main__":
    template_info = asyncio.run(step2_template_selection())

    if template_info:
        print("\n" + "="*70)
        print("✅ 템플릿 선택 완료! 이제 step3_annotation.py를 실행하세요.")
        print(f"선택된 템플릿: {template_info['selected_template_id']}")
        print(f"신뢰도: {template_info['template_confidence']:.1%}")
        print("="*70)

        # 수동 선택 데모도 실행
        print("\n🔧 수동 템플릿 선택 데모:")
        asyncio.run(demonstrate_manual_template_selection())