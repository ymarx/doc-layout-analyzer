#!/usr/bin/env python3
"""
파이프라인 품질 평가 도구
처리 결과물의 품질을 종합적으로 평가
"""
import json
import asyncio
from pathlib import Path
from datetime import datetime
from src.core.integrated_pipeline import IntegratedPipeline, PipelineConfig, ProcessingMode

class PipelineQualityAssessment:
    """파이프라인 품질 평가기"""

    def __init__(self, output_dir: str = "pipeline_output"):
        self.output_dir = Path(output_dir)
        self.assessment_report = {}

    async def comprehensive_assessment(self, document_path: str):
        """종합 품질 평가"""
        print("=" * 60)
        print("🔍 파이프라인 품질 평가 시작")
        print("=" * 60)

        document_name = Path(document_path).name
        self.assessment_report = {
            "document": document_name,
            "timestamp": datetime.now().isoformat(),
            "assessments": {}
        }

        # 1. 기본 처리 성능 평가
        await self._assess_basic_processing(document_path)

        # 2. 템플릿 시스템 평가
        await self._assess_template_system(document_path)

        # 3. 하이브리드 시스템 평가
        await self._assess_hybrid_system(document_path)

        # 4. 출력 품질 평가
        self._assess_output_quality()

        # 5. 전체 점수 계산
        self._calculate_overall_score()

        # 6. 보고서 출력
        self._print_assessment_report()

        return self.assessment_report

    async def _assess_basic_processing(self, document_path: str):
        """기본 처리 성능 평가"""
        print("\n📊 1. 기본 처리 성능 평가")
        print("-" * 40)

        pipeline = IntegratedPipeline(str(self.output_dir))
        config = PipelineConfig(
            processing_mode=ProcessingMode.FAST,
            enable_template_matching=False,
            enable_user_annotations=False,
            output_formats=[]
        )

        try:
            start_time = datetime.now()
            result = await pipeline.process_document(document_path, config)
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            basic_assessment = {
                "processing_time": processing_time,
                "success": True,
                "docjson_generated": result.docjson is not None,
                "sections_count": len(result.docjson.sections) if result.docjson else 0,
                "total_blocks": 0
            }

            # 블록 수 계산
            if result.docjson and result.docjson.sections:
                total_blocks = sum(len(section.blocks) for section in result.docjson.sections)
                basic_assessment["total_blocks"] = total_blocks

            # 성능 점수 계산
            performance_score = min(100, max(0, 100 - processing_time * 10))  # 10초 = 0점
            structure_score = min(100, basic_assessment["sections_count"] * 10)  # 10섹션 = 100점

            basic_assessment["performance_score"] = performance_score
            basic_assessment["structure_score"] = structure_score
            basic_assessment["overall_score"] = (performance_score + structure_score) / 2

            print(f"   ⏱️ 처리 시간: {processing_time:.2f}초")
            print(f"   📋 섹션 수: {basic_assessment['sections_count']}개")
            print(f"   📦 총 블록 수: {basic_assessment['total_blocks']}개")
            print(f"   🎯 성능 점수: {performance_score:.1f}/100")
            print(f"   🏗️ 구조 점수: {structure_score:.1f}/100")
            print(f"   📊 전체 점수: {basic_assessment['overall_score']:.1f}/100")

            self.assessment_report["assessments"]["basic_processing"] = basic_assessment

        except Exception as e:
            print(f"   ❌ 기본 처리 실패: {e}")
            self.assessment_report["assessments"]["basic_processing"] = {
                "success": False,
                "error": str(e),
                "overall_score": 0
            }

    async def _assess_template_system(self, document_path: str):
        """템플릿 시스템 평가"""
        print("\n🎯 2. 템플릿 시스템 평가")
        print("-" * 40)

        pipeline = IntegratedPipeline(str(self.output_dir))
        config = PipelineConfig(
            processing_mode=ProcessingMode.FAST,
            enable_template_matching=True,
            auto_apply_template=True,
            template_confidence_threshold=0.6,
            enable_user_annotations=False,
            output_formats=[]
        )

        try:
            result = await pipeline.process_document(document_path, config)

            template_assessment = {
                "template_matched": result.template_match is not None,
                "template_name": result.template_match.template_name if result.template_match else None,
                "confidence": result.template_match.confidence if result.template_match else 0,
                "auto_applied": result.metadata.get('template_applied', False),
                "matched_fields": len(result.template_match.matched_fields) if result.template_match else 0
            }

            # 템플릿 점수 계산
            if template_assessment["template_matched"]:
                confidence_score = template_assessment["confidence"] * 100
                application_score = 100 if template_assessment["auto_applied"] else 50
                field_score = min(100, template_assessment["matched_fields"] * 10)
                template_score = (confidence_score + application_score + field_score) / 3
            else:
                template_score = 0

            template_assessment["overall_score"] = template_score

            print(f"   🎯 템플릿 매칭: {'✅' if template_assessment['template_matched'] else '❌'}")
            if template_assessment["template_matched"]:
                print(f"   📝 템플릿 이름: {template_assessment['template_name']}")
                print(f"   📊 신뢰도: {template_assessment['confidence']:.1%}")
                print(f"   🤖 자동 적용: {'✅' if template_assessment['auto_applied'] else '❌'}")
                print(f"   🔍 매칭 필드: {template_assessment['matched_fields']}개")
            print(f"   📊 템플릿 점수: {template_score:.1f}/100")

            self.assessment_report["assessments"]["template_system"] = template_assessment

        except Exception as e:
            print(f"   ❌ 템플릿 평가 실패: {e}")
            self.assessment_report["assessments"]["template_system"] = {
                "success": False,
                "error": str(e),
                "overall_score": 0
            }

    async def _assess_hybrid_system(self, document_path: str):
        """하이브리드 시스템 평가"""
        print("\n🎭 3. 하이브리드 시스템 평가")
        print("-" * 40)

        pipeline = IntegratedPipeline(str(self.output_dir))
        config = PipelineConfig(
            processing_mode=ProcessingMode.ENHANCED,
            enable_template_matching=True,
            auto_apply_template=True,
            template_confidence_threshold=0.6,
            enable_user_annotations=True,
            enable_diagrams=True,
            output_formats=[]
        )

        try:
            result = await pipeline.process_document(document_path, config)

            hybrid_assessment = {
                "annotation_generated": result.annotation is not None,
                "total_fields": len(result.annotation.fields) if result.annotation else 0,
                "extracted_values": 0,
                "template_fields": 0,
                "auto_detected_fields": 0
            }

            if result.annotation:
                # 추출된 값 계산
                extracted_values = len([v for v in result.annotation.extracted_values.values() if v])
                hybrid_assessment["extracted_values"] = extracted_values

                # 필드 소스 분석
                template_fields = len([f for f in result.annotation.fields
                                     if f.metadata.get('source') == 'template'])
                auto_fields = len([f for f in result.annotation.fields
                                 if f.metadata.get('source') == 'auto_detection'])

                hybrid_assessment["template_fields"] = template_fields
                hybrid_assessment["auto_detected_fields"] = auto_fields

            # 하이브리드 점수 계산
            field_coverage_score = min(100, hybrid_assessment["total_fields"] * 10)  # 10필드 = 100점
            extraction_rate = (hybrid_assessment["extracted_values"] / max(1, hybrid_assessment["total_fields"])) * 100
            hybrid_balance_score = 100 if (hybrid_assessment["template_fields"] > 0 and
                                         hybrid_assessment["auto_detected_fields"] > 0) else 75

            hybrid_score = (field_coverage_score + extraction_rate + hybrid_balance_score) / 3
            hybrid_assessment["overall_score"] = hybrid_score

            print(f"   📝 주석 생성: {'✅' if hybrid_assessment['annotation_generated'] else '❌'}")
            print(f"   📋 총 필드: {hybrid_assessment['total_fields']}개")
            print(f"   ✅ 추출 값: {hybrid_assessment['extracted_values']}개")
            print(f"   🎯 템플릿 필드: {hybrid_assessment['template_fields']}개")
            print(f"   🤖 자동감지 필드: {hybrid_assessment['auto_detected_fields']}개")
            print(f"   📊 추출률: {extraction_rate:.1f}%")
            print(f"   📊 하이브리드 점수: {hybrid_score:.1f}/100")

            self.assessment_report["assessments"]["hybrid_system"] = hybrid_assessment

        except Exception as e:
            print(f"   ❌ 하이브리드 평가 실패: {e}")
            self.assessment_report["assessments"]["hybrid_system"] = {
                "success": False,
                "error": str(e),
                "overall_score": 0
            }

    def _assess_output_quality(self):
        """출력 품질 평가"""
        print("\n📁 4. 출력 품질 평가")
        print("-" * 40)

        output_assessment = {
            "metadata_files": 0,
            "docjson_files": 0,
            "annotation_files": 0,
            "template_files": 0,
            "file_integrity": True
        }

        try:
            # 메타데이터 파일 확인
            metadata_files = list(self.output_dir.glob("*.metadata.json"))
            output_assessment["metadata_files"] = len(metadata_files)

            # DocJSON 파일 확인
            docjson_files = list(self.output_dir.glob("*.docjson"))
            output_assessment["docjson_files"] = len(docjson_files)

            # 주석 파일 확인
            annotation_dir = self.output_dir / "annotations" / "documents"
            if annotation_dir.exists():
                annotation_files = list(annotation_dir.glob("*.json"))
                output_assessment["annotation_files"] = len(annotation_files)

            # 템플릿 파일 확인
            template_dir = self.output_dir / "annotations" / "templates"
            if template_dir.exists():
                template_files = list(template_dir.glob("*.json"))
                output_assessment["template_files"] = len(template_files)

            # 파일 무결성 확인
            for metadata_file in metadata_files[:3]:  # 최근 3개 파일만 체크
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        json.load(f)
                except Exception:
                    output_assessment["file_integrity"] = False
                    break

            # 출력 점수 계산
            file_diversity_score = min(100, (
                (25 if output_assessment["metadata_files"] > 0 else 0) +
                (25 if output_assessment["docjson_files"] > 0 else 0) +
                (25 if output_assessment["annotation_files"] > 0 else 0) +
                (25 if output_assessment["template_files"] > 0 else 0)
            ))
            integrity_score = 100 if output_assessment["file_integrity"] else 0
            output_score = (file_diversity_score + integrity_score) / 2

            output_assessment["overall_score"] = output_score

            print(f"   📄 메타데이터 파일: {output_assessment['metadata_files']}개")
            print(f"   📋 DocJSON 파일: {output_assessment['docjson_files']}개")
            print(f"   📝 주석 파일: {output_assessment['annotation_files']}개")
            print(f"   🎯 템플릿 파일: {output_assessment['template_files']}개")
            print(f"   🔒 파일 무결성: {'✅' if output_assessment['file_integrity'] else '❌'}")
            print(f"   📊 출력 품질 점수: {output_score:.1f}/100")

            self.assessment_report["assessments"]["output_quality"] = output_assessment

        except Exception as e:
            print(f"   ❌ 출력 평가 실패: {e}")
            self.assessment_report["assessments"]["output_quality"] = {
                "success": False,
                "error": str(e),
                "overall_score": 0
            }

    def _calculate_overall_score(self):
        """전체 점수 계산"""
        assessments = self.assessment_report["assessments"]

        scores = []
        weights = {
            "basic_processing": 0.25,
            "template_system": 0.35,
            "hybrid_system": 0.30,
            "output_quality": 0.10
        }

        total_weight = 0
        weighted_sum = 0

        for component, weight in weights.items():
            if component in assessments and "overall_score" in assessments[component]:
                score = assessments[component]["overall_score"]
                weighted_sum += score * weight
                total_weight += weight

        overall_score = weighted_sum / total_weight if total_weight > 0 else 0
        self.assessment_report["overall_score"] = overall_score

    def _print_assessment_report(self):
        """평가 보고서 출력"""
        print("\n" + "=" * 60)
        print("📊 파이프라인 품질 평가 결과")
        print("=" * 60)

        overall_score = self.assessment_report.get("overall_score", 0)

        # 등급 결정
        if overall_score >= 90:
            grade = "🏆 A+ (우수)"
        elif overall_score >= 80:
            grade = "🥇 A (양호)"
        elif overall_score >= 70:
            grade = "🥈 B (보통)"
        elif overall_score >= 60:
            grade = "🥉 C (개선 필요)"
        else:
            grade = "❌ F (불량)"

        print(f"\n🎯 전체 점수: {overall_score:.1f}/100")
        print(f"🏅 등급: {grade}")

        # 컴포넌트별 점수
        print(f"\n📋 컴포넌트별 점수:")
        assessments = self.assessment_report["assessments"]
        for component, data in assessments.items():
            score = data.get("overall_score", 0)
            component_name = {
                "basic_processing": "기본 처리",
                "template_system": "템플릿 시스템",
                "hybrid_system": "하이브리드 시스템",
                "output_quality": "출력 품질"
            }.get(component, component)

            print(f"   {component_name}: {score:.1f}/100")

        # 결과 해석
        print(f"\n💬 평가 결과:")
        if overall_score >= 80:
            print("   ✅ 파이프라인이 우수한 성능을 보입니다.")
            print("   ✅ 템플릿 기반 하이브리드 시스템이 정상 작동합니다.")
            print("   ✅ 문서 처리 품질이 실용적 수준에 도달했습니다.")
        elif overall_score >= 60:
            print("   ⚠️ 파이프라인이 기본적으로 작동하지만 개선 여지가 있습니다.")
            print("   📈 템플릿 시스템 최적화가 필요할 수 있습니다.")
        else:
            print("   ❌ 파이프라인에 심각한 문제가 있습니다.")
            print("   🔧 시스템 점검과 수정이 필요합니다.")

async def main():
    """메인 실행"""
    assessor = PipelineQualityAssessment()
    document_path = "../기술기준_예시.docx"

    if not Path(document_path).exists():
        print(f"❌ 테스트 문서를 찾을 수 없습니다: {document_path}")
        return

    report = await assessor.comprehensive_assessment(document_path)

    # 보고서 저장
    report_file = Path("pipeline_quality_report.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n📁 상세 보고서 저장: {report_file}")

if __name__ == "__main__":
    asyncio.run(main())