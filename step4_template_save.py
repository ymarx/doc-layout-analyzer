#!/usr/bin/env python3
"""
4단계: 템플릿 저장 및 관리 (Template Save & Management)
생성된 annotation을 바탕으로 새로운 템플릿을 생성하고 저장합니다.
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.enhanced_modernized_pipeline import EnhancedModernizedPipeline
from src.core.simplified_config import PipelineConfig, ProcessingLevel
from src.core.user_annotations import UserAnnotationManager, DocumentTemplate, UserField, FieldType

async def step4_template_creation():
    print("=" * 70)
    print("💾 4단계: 템플릿 저장 및 관리")
    print("=" * 70)

    document_path = "../기술기준_예시.docx"

    # 1. 이전 단계에서 생성된 annotation 로드
    print("📂 이전 단계의 annotation 로드...")
    annotation_manager = UserAnnotationManager("step3_annotations")

    # 문서 경로로 annotation 찾기
    annotation = annotation_manager.load_annotation_by_path(document_path)

    if not annotation:
        print("❌ 이전 단계의 annotation을 찾을 수 없습니다.")
        print("💡 step3_annotation.py를 먼저 실행하세요.")
        return None

    print(f"✅ Annotation 로드 완료: {len(annotation.fields)}개 필드")
    print()

    # 2. 자동 생성된 사용자 템플릿 확인
    print("🤖 자동 생성된 사용자 템플릿 확인...")
    pipeline = EnhancedModernizedPipeline(
        output_dir="step4_template_creation",
        templates_dir="templates/definitions"
    )

    config = PipelineConfig(
        processing_level=ProcessingLevel.COMPLETE,
        override_output_formats=['docjson']
    )

    result = await pipeline.process_document(document_path, config)

    if result.success and result.user_template:
        user_template = result.user_template
        print(f"✅ 자동 템플릿 생성 완료!")
        print(f"   템플릿 이름: {user_template.name}")
        print(f"   문서 타입: {user_template.document_type}")
        print(f"   필드 수: {len(user_template.fields)}개")
        print()

        # 필드 상세 정보
        print("🔍 템플릿 필드 상세:")
        field_types = {}
        importance_types = {}

        for field in user_template.fields[:10]:  # 처음 10개만 표시
            field_types[field.field_type] = field_types.get(field.field_type, 0) + 1
            importance_types[field.importance] = importance_types.get(field.importance, 0) + 1

            emoji = {'critical': '🔴', 'high': '🟡', 'medium': '🔵', 'low': '⚪'}.get(field.importance.value, '⚫')
            print(f"   {emoji} {field.name} ({field.field_type.value})")

        if len(user_template.fields) > 10:
            print(f"   ... 및 {len(user_template.fields) - 10}개 더")
        print()

        # 3. 템플릿 JSON 형식으로 변환 및 저장
        await save_user_template_as_json(user_template, annotation)

        # 4. 기존 템플릿과 비교
        await compare_with_existing_templates(user_template)

        return {
            'user_template': user_template,
            'annotation': annotation,
            'fields_count': len(user_template.fields)
        }
    else:
        print("❌ 자동 템플릿 생성 실패")
        return None

async def save_user_template_as_json(user_template, annotation):
    """사용자 템플릿을 JSON 형식으로 저장"""
    print("💾 템플릿을 JSON 형식으로 저장...")

    # JSON 템플릿 구조 생성
    json_template = {
        "template_id": f"user_generated_{user_template.name.lower().replace(' ', '_')}",
        "name": f"{user_template.name} (사용자 생성)",
        "description": f"사용자가 생성한 템플릿 - {datetime.now().strftime('%Y-%m-%d %H:%M')}에 생성",
        "document_type": user_template.document_type,
        "version": "1.0",
        "created_by": "user_annotation_system",
        "created_at": datetime.now().isoformat(),
        "elements": []
    }

    # 필드를 JSON 요소로 변환
    for field in user_template.fields:
        element = {
            "name": field.name,
            "element_type": _map_field_type_to_element_type(field.field_type),
            "extraction_method": "regex",
            "patterns": _generate_patterns_for_field(field, annotation),
            "required": field.importance.value in ['critical', 'high'],
            "confidence_threshold": _get_confidence_threshold(field.importance),
            "description": field.description or f"Auto-generated for {field.name}"
        }

        # 바운딩박스 정보 추가
        if field.bbox:
            element["position_hints"] = {
                "typical_location": _infer_location_from_bbox(field.bbox),
                "y_range": [field.bbox.y1, field.bbox.y2],
                "x_range": [field.bbox.x1, field.bbox.x2],
                "page": field.bbox.page
            }

        json_template["elements"].append(element)

    # 파일로 저장
    templates_dir = Path("templates/definitions")
    templates_dir.mkdir(exist_ok=True)

    template_file = templates_dir / f"{json_template['template_id']}.json"
    with open(template_file, 'w', encoding='utf-8') as f:
        json.dump(json_template, f, ensure_ascii=False, indent=2)

    print(f"✅ 템플릿 저장 완료: {template_file.name}")
    print(f"   파일 크기: {template_file.stat().st_size:,} bytes")
    print(f"   요소 수: {len(json_template['elements'])}개")
    print()

def _map_field_type_to_element_type(field_type):
    """필드 타입을 JSON 템플릿 요소 타입으로 매핑"""
    mapping = {
        FieldType.TEXT: "fixed",
        FieldType.TITLE: "fixed",
        FieldType.CODE: "fixed",
        FieldType.DATE: "fixed",
        FieldType.NUMBER: "variable",
        FieldType.HEADER: "structural",
        FieldType.FOOTER: "structural",
        FieldType.DIAGRAM: "diagram"
    }
    return mapping.get(field_type, "content")

def _generate_patterns_for_field(field, annotation):
    """필드에 대한 정규식 패턴 생성"""
    field_value = annotation.extracted_values.get(field.id, "")

    if not field_value:
        return [f".*{field.name}.*"]

    patterns = []

    # 필드 타입별 패턴 생성
    if field.field_type == FieldType.DATE:
        patterns.extend([
            r"\d{2,4}[-/.]\d{1,2}[-/.]\d{1,4}",
            r"시행일[:\s]*(\d{2}\.\d{2}\.\d{2})",
            r"효력발생일[:\s]*(\d{2}\.\d{2}\.\d{2})"
        ])
    elif field.field_type == FieldType.CODE:
        patterns.extend([
            r"[A-Z]{2,4}-\d{3}-\d{3}-\d{3}",
            r"문서번호[:\s]*([A-Z0-9-]+)",
            r"(?:문서|Document)\s*(?:번호|No)[:\s]*([A-Z0-9-]+)"
        ])
    elif field.field_type == FieldType.TITLE:
        # 실제 값에서 키워드 추출
        words = field_value.split()[:5]  # 처음 5단어
        pattern = ".*".join(words[:3]) if len(words) >= 3 else field_value[:20]
        patterns.append(pattern)
    else:
        # 기본 패턴: 필드 이름과 관련된 패턴
        patterns.append(f".*{field.name}.*")

    return patterns

def _get_confidence_threshold(importance):
    """중요도별 신뢰도 임계값 반환"""
    thresholds = {
        'critical': 0.95,
        'high': 0.8,
        'medium': 0.7,
        'low': 0.6
    }
    return thresholds.get(importance.value, 0.7)

def _infer_location_from_bbox(bbox):
    """바운딩박스에서 위치 추론"""
    if bbox.y1 < 150:
        return "header"
    elif bbox.y1 > 600:
        return "footer"
    elif bbox.x1 < 200:
        return "left"
    elif bbox.x1 > 400:
        return "right"
    else:
        return "center"

async def compare_with_existing_templates(user_template):
    """기존 템플릿과 비교"""
    print("🔍 기존 템플릿과 비교...")

    templates_dir = Path("templates/definitions")
    existing_templates = []

    for template_file in templates_dir.glob("*.json"):
        if "user_generated" not in template_file.name:  # 기존 템플릿만
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)
                existing_templates.append({
                    'file': template_file.name,
                    'name': template_data.get('name', 'Unknown'),
                    'elements_count': len(template_data.get('elements', []))
                })
            except Exception:
                continue

    print(f"📊 비교 결과:")
    print(f"   새 템플릿 필드 수: {len(user_template.fields)}개")

    for template in existing_templates:
        similarity = _calculate_similarity(len(user_template.fields), template['elements_count'])
        print(f"   vs {template['name']}: {template['elements_count']}개 (유사도: {similarity:.1%})")

    print()

def _calculate_similarity(new_count, existing_count):
    """필드 수 기반 유사도 계산"""
    if new_count == 0 or existing_count == 0:
        return 0.0

    smaller = min(new_count, existing_count)
    larger = max(new_count, existing_count)
    return smaller / larger

async def demonstrate_template_management():
    """템플릿 관리 기능 데모"""
    print("🗂️ 템플릿 관리 기능:")
    print()

    templates_dir = Path("templates/definitions")
    template_files = list(templates_dir.glob("*.json"))

    print(f"📚 현재 저장된 템플릿: {len(template_files)}개")

    for i, template_file in enumerate(template_files[:5], 1):
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                template_data = json.load(f)

            print(f"   {i}. {template_data.get('name', 'Unknown')}")
            print(f"      파일: {template_file.name}")
            print(f"      요소: {len(template_data.get('elements', []))}개")
            print(f"      생성일: {template_data.get('created_at', 'N/A')}")
            print()
        except Exception as e:
            print(f"   {i}. 오류: {template_file.name} - {e}")

    if len(template_files) > 5:
        print(f"   ... 및 {len(template_files) - 5}개 더")

    print("\n🔧 관리 기능:")
    features = [
        "📝 템플릿 편집 및 필드 추가/삭제",
        "🔄 템플릿 버전 관리",
        "📊 템플릿 성능 통계",
        "🎯 템플릿 최적화 제안",
        "📋 템플릿 백업 및 복원",
        "🔍 템플릿 검색 및 필터링",
        "📈 사용 빈도 분석",
        "🏷️ 태그 및 카테고리 관리"
    ]

    for feature in features:
        print(f"   {feature}")

if __name__ == "__main__":
    template_info = asyncio.run(step4_template_creation())

    if template_info:
        print("\n" + "="*70)
        print("✅ 템플릿 저장 완료! 이제 step5_pattern_parsing.py를 실행하세요.")
        print(f"생성된 템플릿 필드: {template_info['fields_count']}개")
        print("="*70)

        # 템플릿 관리 기능 데모
        print("\n🗂️ 템플릿 관리 시스템:")
        asyncio.run(demonstrate_template_management())