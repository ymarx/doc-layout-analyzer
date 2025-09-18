#!/usr/bin/env python3
"""
Document Layout Analyzer - Main Application
CPU/GPU 듀얼 모드 지원 문서 분석 시스템
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path
from typing import Optional, List

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'src'))

from src.core.config import ConfigManager, init_config
from src.core.device_manager import DeviceManager
from src.parsers import DocumentParserFactory, ProcessingOptions
from src.analyzers import LayoutAnalyzer
from src.extractors.content_extractor import ContentExtractor
from src.core.docjson import DocJSONConverter

import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DocumentAnalyzer:
    """문서 분석 메인 클래스"""

    def __init__(self, config_path: Optional[str] = None):
        """초기화"""
        # 설정 로드
        self.config = init_config(config_path)

        # 디바이스 매니저 초기화
        self.device_manager = DeviceManager()

        # 컴포넌트 초기화
        self.parser_factory = DocumentParserFactory(self.device_manager, self.config)
        self.layout_analyzer = LayoutAnalyzer(self.device_manager, self.config)
        self.content_extractor = ContentExtractor(self.device_manager, self.config)
        self.docjson_converter = DocJSONConverter()

        logger.info("Document Analyzer 초기화 완료")

    async def process_document(self,
                              file_path: str,
                              output_dir: str = "./output",
                              options: Optional[ProcessingOptions] = None) -> bool:
        """문서 처리 파이프라인"""

        try:
            file_path = Path(file_path)
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            logger.info(f"문서 처리 시작: {file_path}")

            # 1. 문서 파싱
            logger.info("1. 문서 파싱 중...")
            parser = self.parser_factory.get_parser(file_path)
            if not parser:
                logger.error(f"지원하지 않는 파일 형식: {file_path}")
                return False

            parse_result = await parser.parse(file_path, options)
            if not parse_result.success:
                logger.error(f"문서 파싱 실패: {parse_result.error}")
                return False

            logger.info(f"파싱 완료: {parse_result.processing_time:.2f}초")

            # 2. 레이아웃 분석
            logger.info("2. 레이아웃 분석 중...")
            layout_result = await self.layout_analyzer.analyze_document(file_path)
            if not layout_result.success:
                logger.error(f"레이아웃 분석 실패: {layout_result.error}")
                return False

            logger.info(f"레이아웃 분석 완료: {len(layout_result.elements)}개 요소, "
                       f"{layout_result.processing_time:.2f}초")

            # 3. 콘텐츠 추출
            logger.info("3. 콘텐츠 추출 중...")
            extraction_result = await self.content_extractor.extract_from_layout(
                layout_result.elements, file_path
            )
            if not extraction_result.success:
                logger.error(f"콘텐츠 추출 실패: {extraction_result.error}")
                return False

            logger.info(f"콘텐츠 추출 완료: {len(extraction_result.content)}개 콘텐츠, "
                       f"{extraction_result.processing_time:.2f}초")

            # 4. DocJSON 변환
            logger.info("4. DocJSON 변환 중...")
            docjson = self.docjson_converter.convert_to_docjson(
                layout_elements=layout_result.elements,
                extracted_content=extraction_result.content,
                document_metadata=parse_result.metadata or {},
                file_path=file_path
            )

            # 5. 결과 저장
            output_filename = file_path.stem + ".docjson"
            output_path = output_dir / output_filename

            if self.docjson_converter.save_docjson(docjson, output_path):
                logger.info(f"DocJSON 저장 완료: {output_path}")
            else:
                logger.error("DocJSON 저장 실패")
                return False

            # 통계 출력
            self._print_processing_stats(parse_result, layout_result, extraction_result)

            return True

        except Exception as e:
            logger.error(f"문서 처리 중 오류: {e}")
            return False

    def _print_processing_stats(self, parse_result, layout_result, extraction_result):
        """처리 통계 출력"""
        print("\n" + "="*50)
        print("📊 처리 결과 요약")
        print("="*50)

        print(f"📄 파싱 결과:")
        print(f"  - 성공: {parse_result.success}")
        print(f"  - 페이지 수: {parse_result.pages}")
        print(f"  - 파일 크기: {parse_result.file_size:,} bytes")
        print(f"  - 처리 시간: {parse_result.processing_time:.2f}초")

        print(f"\n🔍 레이아웃 분석:")
        print(f"  - 감지된 요소: {len(layout_result.elements)}개")
        print(f"  - 분석 방법: {layout_result.method_used}")
        print(f"  - 처리 시간: {layout_result.processing_time:.2f}초")

        print(f"\n📝 콘텐츠 추출:")
        print(f"  - 추출된 콘텐츠: {len(extraction_result.content)}개")
        print(f"  - 처리 시간: {extraction_result.processing_time:.2f}초")

        # 콘텐츠 타입별 통계
        content_types = {}
        for content in extraction_result.content:
            content_type = content.content_type
            content_types[content_type] = content_types.get(content_type, 0) + 1

        if content_types:
            print(f"\n📊 콘텐츠 타입별 분포:")
            for content_type, count in content_types.items():
                print(f"  - {content_type}: {count}개")

        total_time = (parse_result.processing_time +
                     layout_result.processing_time +
                     extraction_result.processing_time)
        print(f"\n⏱️ 전체 처리 시간: {total_time:.2f}초")
        print("="*50)

    def print_system_info(self):
        """시스템 정보 출력"""
        print("🖥️ 시스템 정보")
        print("="*40)
        self.config.print_system_info()
        print()
        self.device_manager.print_device_info()
        print()


async def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="Document Layout Analyzer - CPU/GPU 듀얼 모드")

    parser.add_argument(
        "input_file",
        nargs="?",
        help="분석할 문서 파일 경로"
    )

    parser.add_argument(
        "-o", "--output",
        default="./output",
        help="출력 디렉토리 (기본: ./output)"
    )

    parser.add_argument(
        "-c", "--config",
        help="설정 파일 경로"
    )

    parser.add_argument(
        "--gpu",
        action="store_true",
        help="GPU 사용 강제 (사용 가능한 경우)"
    )

    parser.add_argument(
        "--cpu-only",
        action="store_true",
        help="CPU만 사용"
    )

    parser.add_argument(
        "--info",
        action="store_true",
        help="시스템 정보만 출력"
    )

    parser.add_argument(
        "--batch",
        nargs="+",
        help="배치 처리할 파일들"
    )

    args = parser.parse_args()

    try:
        # 분석기 초기화
        analyzer = DocumentAnalyzer(args.config)

        # 시스템 정보 출력
        if args.info:
            analyzer.print_system_info()
            return

        # GPU/CPU 설정 조정
        if args.gpu:
            analyzer.config.system.processing_mode = "gpu"
            analyzer.config.ocr.use_gpu = True
            analyzer.config.embedding.device = "cuda" if analyzer.device_manager.is_gpu_available() else "cpu"
        elif args.cpu_only:
            analyzer.config.system.processing_mode = "cpu"
            analyzer.config.ocr.use_gpu = False
            analyzer.config.embedding.device = "cpu"

        # 시스템 정보 출력
        analyzer.print_system_info()

        # 배치 처리
        if args.batch:
            success_count = 0
            total_count = len(args.batch)

            print(f"\n📁 배치 처리 시작: {total_count}개 파일")
            print("-" * 40)

            for i, file_path in enumerate(args.batch, 1):
                print(f"\n[{i}/{total_count}] 처리 중: {file_path}")
                success = await analyzer.process_document(file_path, args.output)
                if success:
                    success_count += 1
                    print(f"✅ 성공: {file_path}")
                else:
                    print(f"❌ 실패: {file_path}")

            print(f"\n📊 배치 처리 완료: {success_count}/{total_count} 성공")
            return

        # 단일 파일 처리
        if not args.input_file:
            # 대화형 모드
            print("🤖 Document Layout Analyzer")
            print("파일 경로를 입력하세요 (종료: quit)")

            while True:
                try:
                    file_path = input("\n📄 파일 경로: ").strip()
                    if file_path.lower() in ['quit', 'exit', 'q']:
                        break

                    if not file_path:
                        continue

                    if not Path(file_path).exists():
                        print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
                        continue

                    success = await analyzer.process_document(file_path, args.output)
                    if success:
                        print("✅ 처리 완료!")
                    else:
                        print("❌ 처리 실패!")

                except KeyboardInterrupt:
                    print("\n종료합니다.")
                    break
                except Exception as e:
                    print(f"❌ 오류: {e}")
        else:
            # 단일 파일 처리
            if not Path(args.input_file).exists():
                print(f"❌ 파일을 찾을 수 없습니다: {args.input_file}")
                return

            success = await analyzer.process_document(args.input_file, args.output)
            if success:
                print("✅ 처리 완료!")
            else:
                print("❌ 처리 실패!")
                sys.exit(1)

    except KeyboardInterrupt:
        print("\n사용자에 의해 중단되었습니다.")
    except Exception as e:
        logger.error(f"실행 중 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # 이벤트 루프 실행
    if sys.platform == "win32":
        # Windows에서 ProactorEventLoop 사용
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(main())