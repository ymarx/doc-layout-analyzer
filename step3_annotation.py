#!/usr/bin/env python3
"""
3단계: Annotation 생성 및 편집 (Annotation Creation & Editing)
자동으로 annotation을 생성하고 필요에 따라 수정합니다.
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
from src.core.user_annotations import UserAnnotationManager, UserField, FieldType, FieldImportance
from src.core.docjson import BoundingBox

async def step3_annotation_creation():
    print("=" * 70)
    print("📝 3단계: Annotation 생성 및 편집")
    print("=" * 70)

    document_path = "../기술기준_예시.docx"

    # 1. 기본 문서 처리로 DocJSON 생성
    print("📋 문서 처리 및 DocJSON 생성...")
    pipeline = EnhancedModernizedPipeline(
        output_dir="step3_annotation",
        templates_dir="templates/definitions"
    )

    config = PipelineConfig(
        processing_level=ProcessingLevel.COMPLETE,
        override_output_formats=['docjson', 'annotations']
    )

    result = await pipeline.process_document(document_path, config)

    if not result.success:
        print(f"❌ 문서 처리 실패: {result.error}")
        return None

    print("✅ 문서 처리 완료!")
    print(f"⏱️ 처리 시간: {result.processing_time:.3f}초")
    print()

    # 2. 자동 Annotation 생성
    print("🤖 자동 Annotation 생성...")
    annotation_manager = UserAnnotationManager("step3_annotations")

    # DocJSON에서 자동으로 필드 감지
    auto_annotation = annotation_manager.auto_detect_fields(
        result.docjson,
        document_path
    )

    print(f"✅ 자동 감지 완료! {len(auto_annotation.fields)}개 필드 발견")
    print()

    # 3. 자동 생성된 필드 분석
    print("🔍 자동 생성된 필드 분석:")

    # 중요도별 분류
    importance_counts = {}
    type_counts = {}

    for field in auto_annotation.fields:
        importance_counts[field.importance] = importance_counts.get(field.importance, 0) + 1
        type_counts[field.field_type] = type_counts.get(field.field_type, 0) + 1

    print("   📊 중요도별 분포:")
    for importance, count in importance_counts.items():
        emoji = {'critical': '🔴', 'high': '🟡', 'medium': '🔵', 'low': '⚪'}.get(importance.value, '⚫')
        print(f"     {emoji} {importance.value}: {count}개")

    print("\n   📈 필드 타입별 분포:")
    for field_type, count in type_counts.items():
        print(f"     • {field_type.value}: {count}개")
    print()

    # 4. 핵심 필드 상세 표시
    print("🎯 핵심 필드 상세:")
    critical_fields = [f for f in auto_annotation.fields if f.importance == FieldImportance.CRITICAL]

    for field in critical_fields[:5]:  # 상위 5개만 표시
        print(f"   🔴 {field.name} ({field.field_type.value})")
        if field.id in auto_annotation.extracted_values:
            value = auto_annotation.extracted_values[field.id]
            print(f"      값: \"{value[:50]}...\"")

        if field.bbox:
            print(f"      위치: x1={field.bbox.x1:.0f}, y1={field.bbox.y1:.0f}, "
                  f"x2={field.bbox.x2:.0f}, y2={field.bbox.y2:.0f}")
        else:
            print(f"      위치: 바운딩박스 없음")
        print()

    # 5. Annotation 저장
    print("💾 Annotation 저장...")
    annotation_manager.save_annotation(auto_annotation)
    print(f"✅ 저장 완료: annotations/{auto_annotation.document_id}.json")
    print()

    # 6. 수동 편집 데모
    await demonstrate_manual_editing(annotation_manager, auto_annotation)

    return {
        'annotation': auto_annotation,
        'annotation_manager': annotation_manager,
        'document_path': document_path,
        'fields_count': len(auto_annotation.fields),
        'critical_fields_count': len(critical_fields)
    }

async def demonstrate_manual_editing(annotation_manager, annotation):
    """수동 편집 데모"""
    print("🛠️ 수동 편집 데모:")
    print("   (실제 GUI는 향후 구현 예정, 현재는 프로그래밍 방식으로 편집)")
    print()

    # 1. 새 필드 추가 예시
    print("➕ 새 필드 추가 예시:")
    new_field = UserField(
        name="custom_department",
        field_type=FieldType.TEXT,
        importance=FieldImportance.HIGH,
        bbox=BoundingBox(x1=100, y1=200, x2=300, y2=220, page=1),
        description="사용자가 수동으로 추가한 부서 필드"
    )

    # 필드 추가
    success = annotation_manager.add_field_to_annotation(annotation.document_id, new_field)
    if success:
        print(f"   ✅ 새 필드 추가: {new_field.name}")
        print(f"      타입: {new_field.field_type.value}")
        print(f"      중요도: {new_field.importance.value}")
        print(f"      위치: x1={new_field.bbox.x1}, y1={new_field.bbox.y1}")
    print()

    # 2. 필드 값 수정 예시
    print("✏️ 필드 값 수정 예시:")
    if annotation.fields:
        first_field = annotation.fields[0]
        old_value = annotation.extracted_values.get(first_field.id, "없음")
        new_value = "사용자가 수정한 값"

        success = annotation_manager.update_field_value(
            annotation.document_id,
            first_field.id,
            new_value
        )

        if success:
            print(f"   ✅ 필드 값 수정: {first_field.name}")
            print(f"      이전 값: \"{old_value[:30]}...\"")
            print(f"      새 값: \"{new_value}\"")
    print()

    # 3. 바운딩박스 수정 예시
    print("📐 바운딩박스 수정 예시:")
    fields_with_bbox = [f for f in annotation.fields if f.bbox]
    if fields_with_bbox:
        field_to_modify = fields_with_bbox[0]
        print(f"   필드: {field_to_modify.name}")
        print(f"   기존 좌표: x1={field_to_modify.bbox.x1}, y1={field_to_modify.bbox.y1}")

        # 좌표 수정 (실제로는 GUI에서 드래그로 수정)
        field_to_modify.bbox.x1 += 10
        field_to_modify.bbox.y1 += 5
        field_to_modify.bbox.x2 += 10
        field_to_modify.bbox.y2 += 5

        print(f"   수정된 좌표: x1={field_to_modify.bbox.x1}, y1={field_to_modify.bbox.y1}")
        print("   💡 실제 사용시에는 시각적 인터페이스에서 드래그하여 수정")
    print()

    # 4. 검증 수행
    print("✅ Annotation 검증:")
    validation_result = annotation_manager.validate_annotation(annotation)

    if validation_result['valid']:
        print("   🟢 검증 통과!")
    else:
        print("   🔴 검증 실패:")
        for error in validation_result['errors']:
            print(f"      ❌ {error}")

    if validation_result['warnings']:
        print("   ⚠️ 경고사항:")
        for warning in validation_result['warnings']:
            print(f"      ⚠️ {warning}")
    print()

async def demonstrate_bbox_editing():
    """바운딩박스 편집 고급 예시"""
    print("🎨 바운딩박스 편집 고급 기능:")
    print("   (향후 구현될 GUI 기능들)")
    print()

    features = [
        "📱 시각적 문서 뷰어에서 필드 영역 표시",
        "🖱️ 마우스 드래그로 바운딩박스 크기/위치 조정",
        "🎯 자동 스냅-투-텍스트 (텍스트 경계에 자동 맞춤)",
        "📏 정밀 좌표 입력 (픽셀 단위 조정)",
        "🔄 다중 선택 및 일괄 편집",
        "📋 복사/붙여넣기로 바운딩박스 정보 공유",
        "🔍 확대/축소로 정밀 편집",
        "📐 가이드라인 및 격자 표시"
    ]

    for feature in features:
        print(f"   {feature}")
    print()

if __name__ == "__main__":
    annotation_info = asyncio.run(step3_annotation_creation())

    if annotation_info:
        print("\n" + "="*70)
        print("✅ Annotation 생성 완료! 이제 step4_template_save.py를 실행하세요.")
        print(f"생성된 필드: {annotation_info['fields_count']}개")
        print(f"핵심 필드: {annotation_info['critical_fields_count']}개")
        print("="*70)

        # 고급 편집 기능 데모
        print("\n🎨 고급 편집 기능 (향후 구현):")
        asyncio.run(demonstrate_bbox_editing())