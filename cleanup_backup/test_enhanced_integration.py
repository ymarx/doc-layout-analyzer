#!/usr/bin/env python3
"""
Enhanced Integration Test
통합 개선된 시스템 테스트
"""

import asyncio
import sys
from pathlib import Path
import json

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.enhanced_modernized_pipeline import EnhancedModernizedPipeline
from src.core.simplified_config import PipelineConfig, ProcessingLevel

async def test_enhanced_integration():
    print('🚀 Enhanced Integration System 테스트')
    print('=' * 90)

    try:
        # 1. 파이프라인 초기화
        print('1. 🏗️ Enhanced Pipeline 초기화')
        pipeline = EnhancedModernizedPipeline(
            output_dir="enhanced_pipeline_output",
            templates_dir="templates/definitions"
        )

        print(f'   ✅ 파이프라인 초기화 완료')
        print(f'   📁 출력 디렉토리: enhanced_pipeline_output')
        print(f'   🗂️ 템플릿 디렉토리: templates/definitions')
        print()

        # 2. 설정 구성
        config = PipelineConfig(
            processing_level=ProcessingLevel.COMPLETE,
            override_output_formats=['docjson', 'vector']
        )

        print('2. ⚙️ 처리 설정')
        print(f'   처리 레벨: {config.processing_level.value}')
        print(f'   출력 형식: {config.override_output_formats}')
        print()

        # 3. 문서 처리 실행
        print('3. 📄 문서 처리 실행')
        print('   대상 문서: 기술기준_예시.docx')
        print('   처리 시작...')

        result = await pipeline.process_document('../기술기준_예시.docx', config)

        if result.success:
            print('   ✅ 처리 성공!')
            print(f'   ⏱️ 처리 시간: {result.processing_time:.3f}초')
            print(f'   🔄 완료된 단계: {len(result.stages_completed)}개')
            print(f'   📊 단계 목록: {", ".join(result.stages_completed)}')
            print()

            # 4. 템플릿 매칭 결과
            print('4. 🎯 템플릿 매칭 결과')
            if result.template_match:
                tm = result.template_match
                print(f'   템플릿 ID: {tm.template_id}')
                print(f'   🎯 신뢰도: {tm.confidence:.1%}')
                print(f'   📏 바운딩박스 정확도: {tm.bbox_accuracy:.1%}')
                print(f'   🔧 사용된 전략: {tm.strategy_used.value}')
                print(f'   ✅ 매칭된 필드: {len(tm.matched_fields)}개')
                print(f'   ❌ 누락된 필드: {len(tm.missing_fields)}개')
                print()

                # 매칭된 필드 상세
                print('   🔍 매칭된 필드 상세:')
                for field_name, field_data in tm.matched_fields.items():
                    value = field_data.get('value', '')[:50]
                    confidence = field_data.get('confidence', 0)
                    method = field_data.get('method', 'unknown')
                    has_bbox = 'bbox' in field_data and field_data['bbox'] is not None

                    print(f'     • {field_name}: "{value}..." '
                          f'(신뢰도: {confidence:.2f}, 방법: {method}, bbox: {"✓" if has_bbox else "✗"})')
                print()

                if tm.missing_fields:
                    print(f'   ⚠️ 누락된 필드: {", ".join(tm.missing_fields)}')
                    print()
            else:
                print('   ❌ 템플릿 매칭 실패')
                print()

            # 5. 품질 평가
            print('5. 📈 품질 평가 결과')
            print(f'   필드 추출 정확도: {result.field_extraction_accuracy:.1%}')
            print(f'   바운딩박스 개선 점수: {result.bbox_improvement_score:.1%}')

            if result.template_match:
                original_confidence = 0.13  # 이전 테스트 결과
                improved_confidence = result.template_match.confidence
                improvement = ((improved_confidence - original_confidence) / original_confidence) * 100

                print(f'   📊 개선 분석:')
                print(f'     - 이전 신뢰도: {original_confidence:.1%}')
                print(f'     - 현재 신뢰도: {improved_confidence:.1%}')
                print(f'     - 개선률: {improvement:+.1f}%')
            print()

            # 6. 생성된 파일들
            print('6. 📁 생성된 출력 파일들')
            for file_type, file_path in result.output_files.items():
                file_size = file_path.stat().st_size if file_path.exists() else 0
                print(f'   📄 {file_type}: {file_path.name} ({file_size:,} bytes)')
            print()

            # 7. 사용자 템플릿 생성 결과
            if result.user_template:
                print('7. 👤 생성된 사용자 템플릿')
                ut = result.user_template
                print(f'   템플릿 이름: {ut.name}')
                print(f'   문서 타입: {ut.document_type}')
                print(f'   필드 수: {len(ut.fields)}개')
                print()

                print('   🏷️ 템플릿 필드들:')
                for field in ut.fields[:5]:  # 처음 5개만 표시
                    importance_emoji = {
                        'critical': '🔴',
                        'high': '🟡',
                        'medium': '🔵',
                        'low': '⚪'
                    }.get(field.importance.value, '⚫')

                    print(f'     {importance_emoji} {field.name} ({field.field_type.value})')
                    if len(ut.fields) > 5:
                        print(f'     ... 및 {len(ut.fields) - 5}개 더')
                print()

            # 8. 종합 성과 요약
            print('8. 🎉 종합 성과 요약')
            print('   ✅ 달성한 목표:')

            if result.template_match and result.template_match.confidence > 0.5:
                print('     • 템플릿 매칭 신뢰도 50% 이상 달성 ✓')
            else:
                print('     • 템플릿 매칭 신뢰도 향상 필요 ⚠️')

            if result.bbox_improvement_score > 0.3:
                print('     • 바운딩 박스 정확도 개선 ✓')
            else:
                print('     • 바운딩 박스 정확도 개선 필요 ⚠️')

            if len(result.stages_completed) >= 5:
                print('     • 통합 파이프라인 다단계 처리 ✓')
            else:
                print('     • 파이프라인 통합도 개선 필요 ⚠️')

            if result.user_template and len(result.user_template.fields) >= 5:
                print('     • 자동 사용자 템플릿 생성 ✓')
            else:
                print('     • 템플릿 생성 품질 개선 필요 ⚠️')

            # 9. 실용성 검증
            print()
            print('9. 🔬 실용성 검증')

            # 핵심 필드 추출 검증
            core_fields = ['document_number', 'auto_code', 'effective_date', 'auto_date']
            extracted_core = []

            if result.template_match:
                for core_field in core_fields:
                    if core_field in result.template_match.matched_fields:
                        value = result.template_match.matched_fields[core_field].get('value', '')
                        if value.strip():
                            extracted_core.append(f'{core_field}: {value}')

            if extracted_core:
                print('   📋 추출된 핵심 정보:')
                for info in extracted_core:
                    print(f'     • {info}')
            else:
                print('   ⚠️ 핵심 정보 추출 실패')

            print()
            print('=' * 90)
            print('🎯 단기 개선 목표 달성도 평가:')

            # 목표별 평가
            goals = [
                ("템플릿 매칭 신뢰도 80% 달성",
                 result.template_match.confidence if result.template_match else 0, 0.8),
                ("바운딩 박스 정확도 70% 달성",
                 result.bbox_improvement_score, 0.7),
                ("핵심 필드 추출률 90% 달성",
                 len(extracted_core) / 4, 0.9),  # 4개 핵심 필드 기준
                ("사용자 템플릿 자동 생성",
                 1.0 if result.user_template else 0.0, 1.0)
            ]

            total_score = 0
            for goal_name, achieved, target in goals:
                success_rate = achieved / target if target > 0 else achieved
                success_rate = min(1.0, success_rate)  # 100% 초과 방지
                status = "✅" if success_rate >= 1.0 else "🔄" if success_rate >= 0.7 else "❌"
                print(f'{status} {goal_name}: {achieved:.1%} / {target:.0%} ({success_rate:.1%})')
                total_score += success_rate

            overall_score = total_score / len(goals)
            print(f'\n🏆 전체 달성도: {overall_score:.1%}')

            if overall_score >= 0.8:
                print('🎉 단기 개선 목표 성공적 달성!')
            elif overall_score >= 0.6:
                print('👍 상당한 개선 달성, 추가 최적화 권장')
            else:
                print('⚠️ 추가 개발 필요')

        else:
            print('   ❌ 처리 실패')
            print(f'   오류: {result.error}')

    except Exception as e:
        print(f'❌ 테스트 실행 중 오류 발생: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_enhanced_integration())