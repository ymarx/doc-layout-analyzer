#!/usr/bin/env python3
"""
간단한 템플릿 생성 스크립트
"""
import json
from pathlib import Path
from src.core.template_manager import TemplateManager

def create_template_from_annotation():
    """주석에서 템플릿 생성"""
    # 주석 파일 직접 로드
    annotation_file = Path("pipeline_output/annotations/documents/8cfe9966-72ba-4716-a333-c5659bc1a8d2.json")

    with open(annotation_file, 'r', encoding='utf-8') as f:
        annotation_data = json.load(f)

    print(f"✅ 주석 데이터 로드: {annotation_data['document_id']}")
    print(f"📄 문서: {annotation_data['document_path']}")
    print(f"📊 필드 수: {len(annotation_data['fields'])}")

    # 템플릿 매니저 초기화
    template_manager = TemplateManager(Path("pipeline_output/annotations/templates"))

    # 템플릿 생성
    template = template_manager.create_template_from_annotation_data(
        annotation_data,
        "기술기준_표준템플릿",
        "기술기준 문서의 표준 템플릿"
    )

    if template:
        print(f"✅ 템플릿 생성 성공: {template.id}")
        print(f"📝 템플릿 이름: {template.name}")
        print(f"📊 필드 수: {len(template.template_fields)}")

        # 템플릿 저장
        template_manager.save_template(template)
        print(f"💾 템플릿 저장 완료")

        return template
    else:
        print("❌ 템플릿 생성 실패")
        return None

if __name__ == "__main__":
    create_template_from_annotation()