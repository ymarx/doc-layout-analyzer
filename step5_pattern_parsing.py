#!/usr/bin/env python3
"""
5단계: 패턴 인식 및 최종 파싱 (Pattern Recognition & Final Parsing)
생성된 템플릿과 패턴 인식을 결합하여 최종 파싱을 수행합니다.
"""

import asyncio
import sys
import json
import time
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.enhanced_modernized_pipeline import EnhancedModernizedPipeline
from src.core.simplified_config import PipelineConfig, ProcessingLevel
from src.core.user_annotations import UserAnnotationManager

async def step5_final_parsing():
    print("=" * 70)
    print("🎯 5단계: 패턴 인식 및 최종 파싱")
    print("=" * 70)

    document_path = "../기술기준_예시.docx"

    # 1. 모든 기능을 활성화한 완전 파싱
    print("🚀 완전 기능 파싱 시작...")
    start_time = time.time()

    pipeline = EnhancedModernizedPipeline(
        output_dir="step5_final_parsing",
        templates_dir="templates/definitions"
    )

    # 모든 기능 활성화
    config = PipelineConfig(
        processing_level=ProcessingLevel.COMPLETE,
        override_output_formats=['docjson', 'annotations', 'vectors']
    )

    result = await pipeline.process_document(document_path, config)
    processing_time = time.time() - start_time

    if not result.success:
        print(f"❌ 최종 파싱 실패: {result.error}")
        return None

    print(f"✅ 최종 파싱 완료!")
    print(f"⏱️ 전체 처리 시간: {processing_time:.3f}초")
    print(f"🔄 완료된 단계: {len(result.stages_completed)}개")
    print(f"📊 단계 목록: {', '.join(result.stages_completed)}")
    print()

    # 2. 템플릿 매칭 결과 분석
    await analyze_template_matching(result)

    # 3. 패턴 인식 결과 분석
    await analyze_pattern_recognition(result)

    # 4. 하이브리드 파싱 결과 분석
    await analyze_hybrid_parsing(result)

    # 5. 품질 평가 및 개선점
    await analyze_quality_assessment(result)

    # 6. 최종 결과 검증
    await verify_final_results(result)

    return {
        'result': result,
        'processing_time': processing_time,
        'template_confidence': result.template_match.confidence if result.template_match else 0,
        'extracted_fields': len(result.template_match.matched_fields) if result.template_match else 0
    }

async def analyze_template_matching(result):
    """템플릿 매칭 결과 분석"""
    print("📋 템플릿 매칭 결과 분석:")

    if result.template_match:
        tm = result.template_match
        print(f"   🎯 사용된 템플릿: {tm.template_id}")
        print(f"   📊 매칭 신뢰도: {tm.confidence:.1%}")
        print(f"   📏 바운딩박스 정확도: {tm.bbox_accuracy:.1%}")
        print(f"   🔧 매칭 전략: {tm.strategy_used.value}")
        print(f"   ✅ 성공 필드: {len(tm.matched_fields)}개")
        print(f"   ❌ 누락 필드: {len(tm.missing_fields)}개")
        print()

        # 매칭 방법별 분류
        method_counts = {}
        for field_data in tm.matched_fields.values():
            method = field_data.get('method', 'unknown')
            method_counts[method] = method_counts.get(method, 0) + 1

        print("   🔍 매칭 방법별 분포:")
        for method, count in method_counts.items():
            percentage = (count / len(tm.matched_fields)) * 100
            emoji = {
                'unknown': '📝',
                'docjson_metadata': '📊',
                'process_flow': '🔄',
                'template_pattern': '🎯'
            }.get(method, '❓')
            print(f"     {emoji} {method}: {count}개 ({percentage:.1f}%)")
        print()
    else:
        print("   ❌ 템플릿 매칭 실패")
        print()

async def analyze_pattern_recognition(result):
    """패턴 인식 결과 분석"""
    print("🔍 패턴 인식 결과 분석:")

    # DocJSON에서 패턴 분석
    docjson = result.docjson
    metadata = docjson.get('metadata', {})

    # 1. 메타데이터 패턴
    print("   📊 메타데이터 패턴 인식:")
    detected_patterns = []

    if metadata.get('document_number'):
        detected_patterns.append(f"문서번호: {metadata['document_number']}")
    if metadata.get('effective_date'):
        detected_patterns.append(f"효력발생일: {metadata['effective_date']}")
    if metadata.get('author'):
        detected_patterns.append(f"작성자: {metadata['author']}")

    for pattern in detected_patterns:
        print(f"     ✅ {pattern}")

    # 2. 프로세스 플로우 패턴
    process_flows = metadata.get('source', [])
    sequential_flows = [s for s in process_flows if s.get('type') == 'sequential']

    if sequential_flows:
        print(f"\n   🔄 프로세스 플로우 패턴: {len(sequential_flows)}개 감지")
        for flow in sequential_flows:
            steps = flow.get('steps', [])
            print(f"     순서도: {len(steps)}단계")
            for step in steps[:3]:
                print(f"       {step.get('marker', '')} {step.get('title', '')}")
            if len(steps) > 3:
                print(f"       ... 및 {len(steps) - 3}개 더")

    # 3. 구조적 패턴
    sections = docjson.get('sections', [])
    section_types = {}
    for section in sections:
        section_type = section.get('type', 'unknown')
        section_types[section_type] = section_types.get(section_type, 0) + 1

    print(f"\n   🏗️ 구조적 패턴: {len(sections)}개 섹션")
    for sec_type, count in section_types.items():
        print(f"     • {sec_type}: {count}개")
    print()

async def analyze_hybrid_parsing(result):
    """하이브리드 파싱 결과 분석"""
    print("🔀 하이브리드 파싱 결과 분석:")

    if result.template_match:
        tm = result.template_match

        # 템플릿 기반 vs 추론 기반 분류
        template_based = []
        inference_based = []

        for field_name, field_data in tm.matched_fields.items():
            method = field_data.get('method', 'unknown')
            if method in ['docjson_metadata', 'process_flow']:
                inference_based.append(field_name)
            else:
                template_based.append(field_name)

        print(f"   🎯 템플릿 기반 추출: {len(template_based)}개")
        for field in template_based[:5]:
            print(f"     • {field}")
        if len(template_based) > 5:
            print(f"     ... 및 {len(template_based) - 5}개 더")

        print(f"\n   🧠 추론 기반 추출: {len(inference_based)}개")
        for field in inference_based:
            print(f"     • {field}")

        # 하이브리드 효율성 계산
        total_fields = len(tm.matched_fields)
        template_ratio = len(template_based) / total_fields if total_fields > 0 else 0
        inference_ratio = len(inference_based) / total_fields if total_fields > 0 else 0

        print(f"\n   📈 하이브리드 비율:")
        print(f"     템플릿 기반: {template_ratio:.1%}")
        print(f"     추론 기반: {inference_ratio:.1%}")
        print()

async def analyze_quality_assessment(result):
    """품질 평가 및 개선점 분석"""
    print("📈 품질 평가 및 개선점:")

    # 기본 품질 지표
    if hasattr(result, 'field_extraction_accuracy'):
        print(f"   📊 필드 추출 정확도: {result.field_extraction_accuracy:.1%}")
    if hasattr(result, 'bbox_improvement_score'):
        print(f"   📏 바운딩박스 개선 점수: {result.bbox_improvement_score:.1%}")

    # 개선 분석
    if result.template_match:
        confidence = result.template_match.confidence

        print(f"\n   🎯 성능 분석:")
        if confidence >= 0.8:
            print(f"     🟢 우수 (신뢰도: {confidence:.1%})")
        elif confidence >= 0.6:
            print(f"     🟡 양호 (신뢰도: {confidence:.1%})")
        else:
            print(f"     🔴 개선 필요 (신뢰도: {confidence:.1%})")

        # 개선 제안
        print(f"\n   💡 개선 제안:")
        if len(result.template_match.missing_fields) > 0:
            print(f"     • 누락된 {len(result.template_match.missing_fields)}개 필드에 대한 패턴 추가")
        if result.template_match.bbox_accuracy < 0.7:
            print(f"     • 바운딩박스 정확도 개선 (현재: {result.template_match.bbox_accuracy:.1%})")
        if confidence < 0.8:
            print(f"     • 템플릿 패턴 정교화 필요")
    print()

async def verify_final_results(result):
    """최종 결과 검증"""
    print("✅ 최종 결과 검증:")

    # 1. 필수 정보 추출 검증
    essential_fields = ['document_number', 'effective_date', 'title']
    extracted_essential = []

    if result.template_match:
        for field in essential_fields:
            if field in result.template_match.matched_fields:
                value = result.template_match.matched_fields[field].get('value', '')
                if value.strip():
                    extracted_essential.append(field)

    print(f"   📋 필수 정보 추출: {len(extracted_essential)}/{len(essential_fields)}")
    for field in extracted_essential:
        print(f"     ✅ {field}")

    missing_essential = set(essential_fields) - set(extracted_essential)
    for field in missing_essential:
        print(f"     ❌ {field} (누락)")

    # 2. 파일 생성 검증
    output_files = result.output_files if hasattr(result, 'output_files') else {}
    print(f"\n   📁 생성된 파일: {len(output_files)}개")
    for file_type, file_path in output_files.items():
        if file_path.exists():
            size = file_path.stat().st_size
            print(f"     ✅ {file_type}: {file_path.name} ({size:,} bytes)")
        else:
            print(f"     ❌ {file_type}: 파일 없음")

    # 3. 종합 평가
    print(f"\n   🏆 종합 평가:")

    total_score = 0
    max_score = 0

    # 템플릿 매칭 점수 (40점)
    if result.template_match:
        template_score = result.template_match.confidence * 40
        total_score += template_score
        print(f"     템플릿 매칭: {template_score:.1f}/40점")
    max_score += 40

    # 필수 정보 추출 점수 (30점)
    essential_score = (len(extracted_essential) / len(essential_fields)) * 30
    total_score += essential_score
    print(f"     필수 정보 추출: {essential_score:.1f}/30점")
    max_score += 30

    # 파일 생성 점수 (20점)
    file_score = (len([f for f in output_files.values() if f.exists()]) / max(len(output_files), 1)) * 20
    total_score += file_score
    print(f"     파일 생성: {file_score:.1f}/20점")
    max_score += 20

    # 처리 속도 점수 (10점)
    processing_time = getattr(result, 'processing_time', 0)
    speed_score = max(0, min(10, 10 - processing_time)) if processing_time > 0 else 10
    total_score += speed_score
    print(f"     처리 속도: {speed_score:.1f}/10점")
    max_score += 10

    final_percentage = (total_score / max_score) * 100 if max_score > 0 else 0
    print(f"\n   🎯 최종 점수: {total_score:.1f}/{max_score}점 ({final_percentage:.1f}%)")

    if final_percentage >= 80:
        print("     🟢 우수 - 프로덕션 사용 가능")
    elif final_percentage >= 60:
        print("     🟡 양호 - 일부 개선 후 사용 권장")
    else:
        print("     🔴 개선 필요 - 추가 개발 필요")
    print()

async def demonstrate_advanced_features():
    """고급 기능 데모"""
    print("🚀 고급 기능 및 향후 계획:")
    print()

    advanced_features = [
        "🤖 머신러닝 기반 패턴 학습",
        "📊 템플릿 성능 분석 및 자동 최적화",
        "🌐 다국어 문서 지원 (영어, 중국어, 일본어)",
        "📱 웹 기반 시각적 편집 인터페이스",
        "🔄 실시간 문서 처리 API",
        "📈 배치 처리 및 대용량 문서 지원",
        "🧠 사용자 행동 학습 및 개인화",
        "🔐 보안 및 접근 권한 관리",
        "📋 워크플로우 자동화",
        "🎯 업계별 특화 템플릿 라이브러리"
    ]

    for feature in advanced_features:
        print(f"   {feature}")

    print("\n💡 최적화 팁:")
    tips = [
        "템플릿 패턴을 정교하게 작성할수록 정확도 향상",
        "바운딩박스 정보를 추가하면 추출 속도 개선",
        "문서별 특성에 맞는 전용 템플릿 생성 권장",
        "정기적인 템플릿 성능 모니터링 및 업데이트",
        "사용자 피드백을 통한 지속적 개선"
    ]

    for i, tip in enumerate(tips, 1):
        print(f"   {i}. {tip}")

if __name__ == "__main__":
    final_info = asyncio.run(step5_final_parsing())

    if final_info:
        print("\n" + "="*70)
        print("🎉 전체 워크플로우 완료!")
        print(f"⏱️ 총 처리 시간: {final_info['processing_time']:.3f}초")
        print(f"🎯 템플릿 신뢰도: {final_info['template_confidence']:.1%}")
        print(f"📊 추출된 필드: {final_info['extracted_fields']}개")
        print("="*70)

        # 고급 기능 데모
        print("\n🚀 시스템 고도화 방향:")
        asyncio.run(demonstrate_advanced_features())