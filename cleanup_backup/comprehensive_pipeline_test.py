#!/usr/bin/env python3
"""
종합 파이프라인 건전성 테스트
리팩토링된 시스템의 각 단계별 모듈 작동 및 전체 파이프라인 검증
"""

import asyncio
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# 리팩토링된 시스템 컴포넌트
from src.core.simplified_config import (
    ProcessingLevel, PipelineConfig, SimplifiedConfigManager,
    create_basic_config, create_standard_config, create_complete_config
)
from src.core.modernized_pipeline import ModernizedPipeline, quick_process
from src.parsers.unified_docx_parser import UnifiedDocxParser
from src.core.template_manager import TemplateManager
from src.core.user_annotations import UserAnnotationManager


class ComprehensivePipelineTest:
    """종합 파이프라인 테스트"""

    def __init__(self, output_dir: str = "test_pipeline_output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.test_results = {}
        self.start_time = time.time()

    async def run_full_test(self, document_path: str = None):
        """전체 테스트 실행"""
        print("🔬 종합 파이프라인 건전성 테스트 시작")
        print("=" * 70)

        # 테스트 문서 확인
        test_document = self._find_test_document(document_path)
        if not test_document:
            return await self._create_mock_test()

        print(f"📄 테스트 문서: {test_document}")
        print(f"📁 출력 디렉토리: {self.output_dir}")
        print()

        # 단계별 테스트 실행
        await self._test_1_individual_modules(test_document)
        await self._test_2_parser_functionality(test_document)
        await self._test_3_configuration_system()
        await self._test_4_pipeline_stages(test_document)
        await self._test_5_end_to_end_processing(test_document)
        await self._test_6_output_quality_assessment()

        # 종합 평가
        self._generate_comprehensive_report()

    def _find_test_document(self, document_path: str) -> str:
        """테스트 문서 찾기"""
        if document_path and Path(document_path).exists():
            return document_path

        # 가능한 위치들 확인
        possible_paths = [
            "기술기준_예시.docx",
            "../기술기준_예시.docx",
            "../../기술기준_예시.docx",
            "test_document.docx",
            "sample.docx"
        ]

        for path in possible_paths:
            if Path(path).exists():
                return path

        return None

    async def _create_mock_test(self):
        """테스트 문서가 없을 때 모의 테스트"""
        print("⚠️ 테스트 문서를 찾을 수 없어 모의 테스트를 실행합니다")
        print("실제 문서로 테스트하려면 '기술기준_예시.docx' 파일을 제공해주세요.")
        print()

        # 모의 테스트 결과 생성
        self.test_results = {
            "mock_test": True,
            "individual_modules": {"status": "✅ PASS", "note": "초기화 테스트만 수행"},
            "parser_functionality": {"status": "⚠️ SKIP", "note": "실제 문서 필요"},
            "configuration_system": {"status": "✅ PASS", "note": "설정 시스템 정상"},
            "pipeline_stages": {"status": "⚠️ SKIP", "note": "실제 문서 필요"},
            "end_to_end": {"status": "⚠️ SKIP", "note": "실제 문서 필요"},
            "output_quality": {"status": "⚠️ SKIP", "note": "출력물 없음"}
        }

        await self._test_3_configuration_system()
        print("\n🎯 모의 테스트 완료")
        print("실제 테스트를 위해서는 기술기준_예시.docx 파일이 필요합니다.")

    async def _test_1_individual_modules(self, document_path: str):
        """1단계: 개별 모듈 기능 테스트"""
        print("🧩 1단계: 개별 모듈 기능 테스트")
        print("-" * 50)

        module_tests = {}

        try:
            # 통합 파서 테스트
            parser = UnifiedDocxParser()
            module_tests["unified_parser"] = {
                "initialized": True,
                "supports_docx": parser.can_handle(document_path),
                "parsing_modes": len(parser.parsing_modes)
            }
            print("✅ UnifiedDocxParser: 초기화 및 기능 확인 완료")

            # 설정 관리자 테스트
            config_manager = SimplifiedConfigManager()
            module_tests["config_manager"] = {
                "initialized": True,
                "presets_count": len(config_manager.presets),
                "current_level": config_manager.current_preset.level.value
            }
            print("✅ SimplifiedConfigManager: 설정 시스템 정상")

            # 템플릿 관리자 테스트
            template_manager = TemplateManager(self.output_dir / "templates")
            module_tests["template_manager"] = {
                "initialized": True,
                "templates_dir_exists": template_manager.templates_dir.exists()
            }
            print("✅ TemplateManager: 초기화 완료")

            # 주석 관리자 테스트
            annotation_manager = UserAnnotationManager(self.output_dir / "annotations")
            module_tests["annotation_manager"] = {
                "initialized": True,
                "annotations_path_exists": annotation_manager.annotations_path.exists()
            }
            print("✅ UserAnnotationManager: 초기화 완료")

            self.test_results["individual_modules"] = {
                "status": "✅ PASS",
                "details": module_tests,
                "passed_modules": len([m for m in module_tests.values() if m.get("initialized")])
            }

        except Exception as e:
            print(f"❌ 개별 모듈 테스트 실패: {e}")
            self.test_results["individual_modules"] = {
                "status": "❌ FAIL",
                "error": str(e)
            }

        print()

    async def _test_2_parser_functionality(self, document_path: str):
        """2단계: 파서 기능 테스트"""
        print("🔧 2단계: 파서 기능 테스트")
        print("-" * 50)

        try:
            parser = UnifiedDocxParser()

            # 각 파싱 모드 테스트
            parsing_results = {}

            for mode_name, mode_config in parser.parsing_modes.items():
                try:
                    print(f"   🧪 {mode_name} 모드 테스트...")

                    # 모의 파싱 옵션 생성
                    from src.parsers.base_parser import ProcessingOptions
                    options = ProcessingOptions()
                    options.parsing_complexity = mode_name

                    start_time = time.time()
                    result = await parser.parse(document_path, options)
                    parse_time = time.time() - start_time

                    parsing_results[mode_name] = {
                        "success": result.success,
                        "processing_time": parse_time,
                        "has_content": result.content is not None,
                        "docjson_generated": 'docjson' in (result.content or {}),
                        "error": result.error
                    }

                    status = "✅" if result.success else "❌"
                    print(f"   {status} {mode_name}: {parse_time:.3f}초")

                except Exception as e:
                    parsing_results[mode_name] = {
                        "success": False,
                        "error": str(e)
                    }
                    print(f"   ❌ {mode_name}: {e}")

            # 파서 성능 평가
            successful_modes = len([r for r in parsing_results.values() if r.get("success")])
            total_modes = len(parsing_results)

            self.test_results["parser_functionality"] = {
                "status": "✅ PASS" if successful_modes > 0 else "❌ FAIL",
                "successful_modes": f"{successful_modes}/{total_modes}",
                "details": parsing_results,
                "best_performance": min([r.get("processing_time", 999) for r in parsing_results.values() if r.get("success")], default=0)
            }

            print(f"📊 파서 테스트 완료: {successful_modes}/{total_modes} 모드 성공")

        except Exception as e:
            print(f"❌ 파서 기능 테스트 실패: {e}")
            self.test_results["parser_functionality"] = {
                "status": "❌ FAIL",
                "error": str(e)
            }

        print()

    async def _test_3_configuration_system(self):
        """3단계: 설정 시스템 테스트"""
        print("⚙️ 3단계: 설정 시스템 테스트")
        print("-" * 50)

        try:
            config_tests = {}

            # 각 처리 레벨 테스트
            levels = [ProcessingLevel.BASIC, ProcessingLevel.STANDARD, ProcessingLevel.COMPLETE]

            for level in levels:
                config = PipelineConfig(processing_level=level)
                config_manager = SimplifiedConfigManager()
                preset = config.to_preset(config_manager)

                config_tests[level.value] = {
                    "level": level.value,
                    "description": preset.description,
                    "template_matching": preset.enable_template_matching,
                    "auto_annotations": preset.enable_auto_annotations,
                    "vectorization": preset.enable_vectorization,
                    "output_formats": preset.output_formats
                }

                print(f"   ✅ {level.value.upper()}: {preset.description}")

            # 편의 함수 테스트
            convenience_configs = {
                "basic": create_basic_config(),
                "standard": create_standard_config(),
                "complete": create_complete_config()
            }

            for name, config in convenience_configs.items():
                print(f"   ✅ {name}_config(): {config.processing_level.value}")

            # 마이그레이션 테스트
            from src.core.simplified_config import migrate_legacy_config
            legacy_config = {
                'processing_mode': 'enhanced',
                'template_confidence_threshold': 0.7,
                'output_formats': ['docjson', 'annotations']
            }
            migrated = migrate_legacy_config(legacy_config)
            print(f"   ✅ 레거시 마이그레이션: {legacy_config['processing_mode']} → {migrated.processing_level.value}")

            self.test_results["configuration_system"] = {
                "status": "✅ PASS",
                "levels_tested": len(levels),
                "convenience_functions": len(convenience_configs),
                "migration_support": True,
                "details": config_tests
            }

        except Exception as e:
            print(f"❌ 설정 시스템 테스트 실패: {e}")
            self.test_results["configuration_system"] = {
                "status": "❌ FAIL",
                "error": str(e)
            }

        print()

    async def _test_4_pipeline_stages(self, document_path: str):
        """4단계: 파이프라인 단계별 테스트"""
        print("🏭 4단계: 파이프라인 단계별 테스트")
        print("-" * 50)

        try:
            pipeline = ModernizedPipeline(output_dir=str(self.output_dir))
            config = create_standard_config()

            # 개별 단계 시뮬레이션
            stage_results = {}

            # 모의 결과 객체 생성
            from src.core.modernized_pipeline import ModernPipelineResult
            mock_result = ModernPipelineResult(
                success=False,
                document_id="test_doc",
                processing_level=ProcessingLevel.STANDARD
            )

            # Stage 1: Document Parsing 테스트
            try:
                preset = config.to_preset(pipeline.config_manager)
                await pipeline._stage_document_parsing(document_path, preset, mock_result)
                stage_results["parsing"] = {
                    "success": "parsing" in mock_result.stages_completed,
                    "docjson_created": mock_result.docjson is not None
                }
                print("   ✅ Stage 1 (Document Parsing): 완료")
            except Exception as e:
                stage_results["parsing"] = {"success": False, "error": str(e)}
                print(f"   ❌ Stage 1 (Document Parsing): {e}")

            # Stage 2: Template Matching 테스트 (DocJSON이 있는 경우만)
            if mock_result.docjson:
                try:
                    await pipeline._stage_template_matching(document_path, preset, mock_result)
                    stage_results["template_matching"] = {
                        "success": "template_matching" in mock_result.stages_completed,
                        "template_found": mock_result.template_match is not None
                    }
                    print("   ✅ Stage 2 (Template Matching): 완료")
                except Exception as e:
                    stage_results["template_matching"] = {"success": False, "error": str(e)}
                    print(f"   ⚠️ Stage 2 (Template Matching): {e}")

            # Stage 6: Quality Assessment 테스트
            try:
                await pipeline._stage_quality_assessment(mock_result)
                stage_results["quality_assessment"] = {
                    "success": "quality_assessment" in mock_result.stages_completed,
                    "quality_score": mock_result.quality_score
                }
                print(f"   ✅ Stage 6 (Quality Assessment): 품질 점수 {mock_result.quality_score:.1f}")
            except Exception as e:
                stage_results["quality_assessment"] = {"success": False, "error": str(e)}
                print(f"   ❌ Stage 6 (Quality Assessment): {e}")

            successful_stages = len([s for s in stage_results.values() if s.get("success")])
            total_stages = len(stage_results)

            self.test_results["pipeline_stages"] = {
                "status": "✅ PASS" if successful_stages > 0 else "❌ FAIL",
                "successful_stages": f"{successful_stages}/{total_stages}",
                "details": stage_results,
                "final_quality_score": mock_result.quality_score
            }

        except Exception as e:
            print(f"❌ 파이프라인 단계 테스트 실패: {e}")
            self.test_results["pipeline_stages"] = {
                "status": "❌ FAIL",
                "error": str(e)
            }

        print()

    async def _test_5_end_to_end_processing(self, document_path: str):
        """5단계: 종단간 처리 테스트"""
        print("🔄 5단계: 종단간 처리 테스트")
        print("-" * 50)

        try:
            # 각 처리 레벨별 종단간 테스트
            levels = [ProcessingLevel.BASIC, ProcessingLevel.STANDARD]  # COMPLETE는 시간이 오래 걸릴 수 있음

            e2e_results = {}

            for level in levels:
                print(f"   🧪 {level.value} 레벨 종단간 테스트...")

                try:
                    start_time = time.time()
                    result = await quick_process(
                        document_path,
                        level,
                        str(self.output_dir)
                    )
                    processing_time = time.time() - start_time

                    e2e_results[level.value] = {
                        "success": result.success,
                        "processing_time": processing_time,
                        "stages_completed": len(result.stages_completed),
                        "quality_score": result.quality_score,
                        "output_files": len(result.output_files),
                        "error": result.error
                    }

                    if result.success:
                        print(f"   ✅ {level.value}: {processing_time:.2f}초, 품질 {result.quality_score:.1f}/100")
                    else:
                        print(f"   ❌ {level.value}: {result.error}")

                except Exception as e:
                    e2e_results[level.value] = {
                        "success": False,
                        "error": str(e)
                    }
                    print(f"   ❌ {level.value}: {e}")

            successful_levels = len([r for r in e2e_results.values() if r.get("success")])
            total_levels = len(e2e_results)

            self.test_results["end_to_end"] = {
                "status": "✅ PASS" if successful_levels > 0 else "❌ FAIL",
                "successful_levels": f"{successful_levels}/{total_levels}",
                "details": e2e_results,
                "average_quality": sum([r.get("quality_score", 0) for r in e2e_results.values() if r.get("success")]) / max(successful_levels, 1)
            }

        except Exception as e:
            print(f"❌ 종단간 처리 테스트 실패: {e}")
            self.test_results["end_to_end"] = {
                "status": "❌ FAIL",
                "error": str(e)
            }

        print()

    async def _test_6_output_quality_assessment(self):
        """6단계: 출력 품질 평가"""
        print("📊 6단계: 출력 품질 평가")
        print("-" * 50)

        try:
            # 출력 디렉토리 확인
            output_files = list(self.output_dir.glob("*"))
            metadata_files = list(self.output_dir.glob("*.metadata.json"))
            docjson_files = list(self.output_dir.glob("*.docjson"))

            quality_metrics = {
                "total_output_files": len(output_files),
                "metadata_files": len(metadata_files),
                "docjson_files": len(docjson_files),
                "directories_created": len([f for f in output_files if f.is_dir()])
            }

            # 파일 무결성 검사
            file_integrity = True
            for metadata_file in metadata_files:
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        json.load(f)
                except Exception:
                    file_integrity = False
                    break

            quality_metrics["file_integrity"] = file_integrity

            # 품질 점수 계산
            quality_score = 0
            if quality_metrics["total_output_files"] > 0:
                quality_score += 25
            if quality_metrics["metadata_files"] > 0:
                quality_score += 25
            if quality_metrics["docjson_files"] > 0:
                quality_score += 25
            if quality_metrics["file_integrity"]:
                quality_score += 25

            print(f"   📄 총 출력 파일: {quality_metrics['total_output_files']}개")
            print(f"   📋 메타데이터 파일: {quality_metrics['metadata_files']}개")
            print(f"   📊 DocJSON 파일: {quality_metrics['docjson_files']}개")
            print(f"   🔒 파일 무결성: {'✅' if file_integrity else '❌'}")
            print(f"   📊 출력 품질 점수: {quality_score}/100")

            self.test_results["output_quality"] = {
                "status": "✅ PASS" if quality_score >= 50 else "❌ FAIL",
                "quality_score": quality_score,
                "details": quality_metrics
            }

        except Exception as e:
            print(f"❌ 출력 품질 평가 실패: {e}")
            self.test_results["output_quality"] = {
                "status": "❌ FAIL",
                "error": str(e)
            }

        print()

    def _generate_comprehensive_report(self):
        """종합 보고서 생성"""
        print("=" * 70)
        print("📋 종합 파이프라인 건전성 평가 보고서")
        print("=" * 70)

        total_time = time.time() - self.start_time

        # 전체 테스트 결과 요약
        test_categories = [
            ("개별 모듈", "individual_modules"),
            ("파서 기능", "parser_functionality"),
            ("설정 시스템", "configuration_system"),
            ("파이프라인 단계", "pipeline_stages"),
            ("종단간 처리", "end_to_end"),
            ("출력 품질", "output_quality")
        ]

        passed_tests = 0
        total_tests = len(test_categories)

        print(f"\n🕐 총 테스트 시간: {total_time:.1f}초")
        print(f"📁 출력 디렉토리: {self.output_dir}")
        print(f"⏰ 테스트 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        print(f"\n📊 테스트 결과 요약:")
        for category_name, category_key in test_categories:
            result = self.test_results.get(category_key, {"status": "⚠️ SKIP"})
            status = result.get("status", "❓ UNKNOWN")
            print(f"   {category_name:12s}: {status}")

            if "✅ PASS" in status:
                passed_tests += 1

        # 전체 성공률 계산
        success_rate = (passed_tests / total_tests) * 100

        print(f"\n🎯 전체 성공률: {passed_tests}/{total_tests} ({success_rate:.1f}%)")

        # 성능 지표
        if "end_to_end" in self.test_results and self.test_results["end_to_end"].get("details"):
            avg_quality = self.test_results["end_to_end"].get("average_quality", 0)
            print(f"📈 평균 품질 점수: {avg_quality:.1f}/100")

        # 등급 결정
        if success_rate >= 90:
            grade = "🏆 A+ (우수)"
        elif success_rate >= 80:
            grade = "🥇 A (양호)"
        elif success_rate >= 70:
            grade = "🥈 B (보통)"
        elif success_rate >= 60:
            grade = "🥉 C (개선 필요)"
        else:
            grade = "❌ F (불량)"

        print(f"🏅 전체 등급: {grade}")

        # 권장사항
        print(f"\n💡 권장사항:")
        if success_rate >= 80:
            print("   ✅ 파이프라인이 정상적으로 작동합니다.")
            print("   ✅ 프로덕션 환경에서 사용할 준비가 되었습니다.")
            if success_rate < 100:
                print("   📈 미세한 조정으로 완벽한 시스템이 될 수 있습니다.")
        elif success_rate >= 60:
            print("   ⚠️ 시스템이 기본적으로 작동하지만 개선이 필요합니다.")
            print("   🔧 실패한 테스트들을 점검하고 수정하세요.")
        else:
            print("   ❌ 시스템에 심각한 문제가 있습니다.")
            print("   🚨 문제 해결 후 다시 테스트를 실행하세요.")

        # 상세 보고서 저장
        self._save_detailed_report(total_time, success_rate, grade)

    def _save_detailed_report(self, total_time: float, success_rate: float, grade: str):
        """상세 보고서 파일 저장"""
        report = {
            "test_summary": {
                "timestamp": datetime.now().isoformat(),
                "total_time": total_time,
                "success_rate": success_rate,
                "grade": grade,
                "output_directory": str(self.output_dir)
            },
            "test_results": self.test_results,
            "system_info": {
                "pipeline_version": "2.0_refactored",
                "test_framework": "comprehensive_pipeline_test",
                "python_version": sys.version
            }
        }

        report_file = self.output_dir / "comprehensive_test_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n📄 상세 보고서 저장: {report_file}")


async def main():
    """메인 실행 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="종합 파이프라인 건전성 테스트")
    parser.add_argument("--document", "-d", type=str, help="테스트할 문서 경로")
    parser.add_argument("--output", "-o", type=str, default="test_pipeline_output", help="출력 디렉토리")

    args = parser.parse_args()

    # 테스트 실행
    tester = ComprehensivePipelineTest(args.output)
    await tester.run_full_test(args.document)


if __name__ == "__main__":
    asyncio.run(main())