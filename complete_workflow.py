#!/usr/bin/env python3
"""
완전 워크플로우 실행 스크립트
문서 등재 → 템플릿 선택 → 어노테이션 → 템플릿 저장 → 패턴 인식 파싱
전체 과정을 순차적으로 실행합니다.
"""

import asyncio
import sys
import time
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def print_step_header(step_num: int, title: str):
    """단계별 헤더 출력"""
    print("\n" + "="*80)
    print(f"🔥 {step_num}단계: {title}")
    print("="*80)

def print_step_completion(step_num: int, title: str, duration: float):
    """단계 완료 메시지"""
    print(f"\n✅ {step_num}단계 완료: {title}")
    print(f"⏱️ 소요 시간: {duration:.3f}초")

async def run_complete_workflow():
    """완전 워크플로우 실행"""
    total_start = time.time()

    print("🚀 문서 파싱 완전 워크플로우 시작")
    print("=" * 80)
    print("📋 실행 단계:")
    print("   1️⃣ 문서 등재 및 기본 분석")
    print("   2️⃣ 템플릿 선택 및 적용")
    print("   3️⃣ Annotation 생성 및 편집")
    print("   4️⃣ 템플릿 저장 및 관리")
    print("   5️⃣ 패턴 인식 및 최종 파싱")
    print("=" * 80)

    # 1단계: 문서 등재
    print_step_header(1, "문서 등재 및 기본 분석")
    step1_start = time.time()

    # step1_document_registration.py 내용을 직접 실행
    from step1_document_registration import step1_register_document
    document_info = await step1_register_document()

    step1_duration = time.time() - step1_start
    if document_info:
        print_step_completion(1, "문서 등재", step1_duration)
    else:
        print("❌ 1단계 실패 - 워크플로우 중단")
        return False

    # 2단계: 템플릿 선택
    print_step_header(2, "템플릿 선택 및 적용")
    step2_start = time.time()

    from step2_template_selection import step2_template_selection
    template_info = await step2_template_selection()

    step2_duration = time.time() - step2_start
    if template_info:
        print_step_completion(2, "템플릿 선택", step2_duration)
    else:
        print("❌ 2단계 실패 - 워크플로우 중단")
        return False

    # 3단계: Annotation
    print_step_header(3, "Annotation 생성 및 편집")
    step3_start = time.time()

    from step3_annotation import step3_annotation_creation
    annotation_info = await step3_annotation_creation()

    step3_duration = time.time() - step3_start
    if annotation_info:
        print_step_completion(3, "Annotation 생성", step3_duration)
    else:
        print("❌ 3단계 실패 - 워크플로우 중단")
        return False

    # 4단계: 템플릿 저장
    print_step_header(4, "템플릿 저장 및 관리")
    step4_start = time.time()

    from step4_template_save import step4_template_creation
    template_save_info = await step4_template_creation()

    step4_duration = time.time() - step4_start
    if template_save_info:
        print_step_completion(4, "템플릿 저장", step4_duration)
    else:
        print("❌ 4단계 실패 - 워크플로우 중단")
        return False

    # 5단계: 최종 파싱
    print_step_header(5, "패턴 인식 및 최종 파싱")
    step5_start = time.time()

    from step5_pattern_parsing import step5_final_parsing
    final_info = await step5_final_parsing()

    step5_duration = time.time() - step5_start
    if final_info:
        print_step_completion(5, "최종 파싱", step5_duration)
    else:
        print("❌ 5단계 실패")
        return False

    # 전체 결과 요약
    total_duration = time.time() - total_start

    print("\n" + "🎉" * 25)
    print("🏆 전체 워크플로우 성공적 완료!")
    print("🎉" * 25)
    print()

    print("📊 최종 결과 요약:")
    print(f"   ⏱️ 전체 소요 시간: {total_duration:.3f}초")
    print(f"   📋 단계별 소요 시간:")
    print(f"      1단계 (문서 등재): {step1_duration:.3f}초")
    print(f"      2단계 (템플릿 선택): {step2_duration:.3f}초")
    print(f"      3단계 (Annotation): {step3_duration:.3f}초")
    print(f"      4단계 (템플릿 저장): {step4_duration:.3f}초")
    print(f"      5단계 (최종 파싱): {step5_duration:.3f}초")
    print()

    print("🎯 달성된 성과:")
    if final_info:
        print(f"   📈 템플릿 매칭 신뢰도: {final_info['template_confidence']:.1%}")
        print(f"   📊 추출된 필드 수: {final_info['extracted_fields']}개")
        print(f"   ⚡ 최종 처리 속도: {final_info['processing_time']:.3f}초")

    if template_save_info:
        print(f"   💾 생성된 템플릿 필드: {template_save_info['fields_count']}개")

    if annotation_info:
        print(f"   📝 자동 생성 annotation: {annotation_info['fields_count']}개 필드")

    print()
    print("📁 생성된 출력 디렉토리:")
    output_dirs = [
        "step1_analysis",
        "step2_template_test",
        "step3_annotation",
        "step4_template_creation",
        "step5_final_parsing"
    ]

    for output_dir in output_dirs:
        dir_path = Path(output_dir)
        if dir_path.exists():
            file_count = len(list(dir_path.glob("*")))
            print(f"   📂 {output_dir}: {file_count}개 파일")

    print()
    print("🔥 시스템 사용 준비 완료!")
    print("💡 이제 다른 문서들도 동일한 과정으로 처리할 수 있습니다.")

    return True

async def demonstrate_next_steps():
    """다음 단계 안내"""
    print("\n" + "🔮" * 25)
    print("🚀 다음 단계 가이드")
    print("🔮" * 25)
    print()

    print("1️⃣ 새로운 문서 처리:")
    print("   • 새 DOCX 파일을 프로젝트 디렉토리에 배치")
    print("   • complete_workflow.py 재실행")
    print("   • 자동으로 생성된 템플릿이 적용됨")
    print()

    print("2️⃣ 템플릿 개선:")
    print("   • templates/definitions/ 디렉토리의 JSON 파일 편집")
    print("   • 정규식 패턴 정교화")
    print("   • confidence_threshold 조정")
    print()

    print("3️⃣ Annotation 미세 조정:")
    print("   • step3_annotations/ 디렉토리의 annotation 파일 편집")
    print("   • 바운딩박스 좌표 수정")
    print("   • 필드 타입 및 중요도 조정")
    print()

    print("4️⃣ 배치 처리:")
    print("   • 여러 문서를 한 번에 처리하는 스크립트 작성")
    print("   • 성능 최적화 및 병렬 처리")
    print("   • 결과 통계 및 분석")
    print()

    print("5️⃣ 시스템 통합:")
    print("   • 웹 API 서버 구축")
    print("   • 데이터베이스 연동")
    print("   • 사용자 인터페이스 개발")

if __name__ == "__main__":
    print("🔥 문서 파싱 시스템 완전 워크플로우")
    print("📋 모든 단계를 순차적으로 실행합니다...")
    print()

    # 워크플로우 실행
    success = asyncio.run(run_complete_workflow())

    if success:
        # 다음 단계 안내
        asyncio.run(demonstrate_next_steps())
    else:
        print("\n❌ 워크플로우 실행 중 오류가 발생했습니다.")
        print("💡 각 단계별 스크립트를 개별적으로 실행하여 문제를 확인하세요.")