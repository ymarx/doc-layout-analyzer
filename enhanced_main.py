#!/usr/bin/env python3
"""
Enhanced Main - 고급 DOCX 문서 처리 메인 스크립트
기술기준 문서의 완전한 분석 및 벡터화 처리
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

# 프로젝트 모듈 임포트
from src.core.enhanced_modernized_pipeline import EnhancedModernizedPipeline
from src.core.simplified_config import PipelineConfig, ProcessingLevel


def setup_logging(verbose: bool = False):
    """로깅 설정"""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('enhanced_processing.log', encoding='utf-8')
        ]
    )

    # 외부 라이브러리 로그 레벨 조정
    logging.getLogger('paddlex').setLevel(logging.WARNING)
    logging.getLogger('paddle').setLevel(logging.WARNING)


async def process_single_document(pipeline: EnhancedModernizedPipeline,
                                 file_path: Path,
                                 config: PipelineConfig) -> bool:
    """단일 문서 처리"""
    print(f"\n📄 문서 처리 시작: {file_path}")
    print(f"   처리 레벨: {config.processing_level.value}")
    print(f"   출력 형식: {', '.join(config.get_output_formats())}")

    result = await pipeline.process_document(file_path, config)

    if result.success:
        print(f"✅ 처리 성공! ({result.processing_time:.2f}초)")
        print(f"   문서 ID: {result.document_id}")
        print(f"   섹션 수: {len(result.docjson.sections) if result.docjson else 0}")

        if result.vector_document:
            print(f"   벡터 청크: {len(result.vector_document.chunks)}")
            print(f"   핵심 개념: {len(result.vector_document.key_concepts)}")

        if result.metadata.get('diagrams_count', 0) > 0:
            print(f"   다이어그램: {result.metadata['diagrams_count']}개")

        # 출력 파일 정보
        print("\n📁 생성된 파일:")
        for file_type, file_path in result.intermediate_files.items():
            print(f"   {file_type}: {file_path}")

        return True
    else:
        print(f"❌ 처리 실패: {result.error}")
        return False


async def process_batch_documents(pipeline: IntegratedPipeline,
                                 file_paths: List[Path],
                                 config: PipelineConfig) -> None:
    """배치 문서 처리"""
    print(f"\n📚 배치 처리 시작: {len(file_paths)}개 문서")

    results = await pipeline.batch_process_documents(file_paths, config)

    success_count = sum(1 for r in results if r.success)
    print(f"\n📊 배치 처리 결과:")
    print(f"   전체: {len(results)}개")
    print(f"   성공: {success_count}개")
    print(f"   실패: {len(results) - success_count}개")

    # 실패한 문서들 표시
    failed_docs = [r for r in results if not r.success]
    if failed_docs:
        print(f"\n❌ 실패한 문서들:")
        for result in failed_docs:
            print(f"   {result.document_id}: {result.error}")


async def create_template_interactive(pipeline: IntegratedPipeline) -> Optional[str]:
    """대화형 템플릿 생성"""
    print("\n🎨 사용자 정의 템플릿 생성")

    name = input("템플릿 이름: ").strip()
    if not name:
        print("템플릿 이름이 필요합니다.")
        return None

    print("\n문서 타입 선택:")
    print("1. 기술기준")
    print("2. 작업표준")
    print("3. 기타")

    choice = input("선택 (1-3): ").strip()
    doc_types = {"1": "기술기준", "2": "작업표준", "3": "기타"}
    doc_type = doc_types.get(choice, "기타")

    sample_file = input("샘플 파일 경로 (선택사항): ").strip()
    sample_path = Path(sample_file) if sample_file and Path(sample_file).exists() else None

    template_id = await pipeline.create_custom_template(name, doc_type, sample_path)

    print(f"✅ 템플릿 생성 완료!")
    print(f"   템플릿 ID: {template_id}")
    print(f"   이름: {name}")
    print(f"   문서 타입: {doc_type}")

    return template_id


async def show_statistics(pipeline: IntegratedPipeline) -> None:
    """처리 통계 표시"""
    stats = await pipeline.get_processing_statistics()

    print("\n📊 처리 통계:")
    print(f"   전체 문서: {stats['total_documents']}")
    print(f"   성공 문서: {stats['successful_documents']}")
    print(f"   벡터화 문서: {stats['vectorized_documents']}")
    print(f"   주석 문서: {stats['annotated_documents']}")

    if stats['document_types']:
        print("\n📄 문서 타입별 분포:")
        for doc_type, count in stats['document_types'].items():
            print(f"   {doc_type}: {count}개")


def create_pipeline_config(args) -> PipelineConfig:
    """명령행 인수로부터 파이프라인 설정 생성"""
    # 처리 모드 결정
    if args.vectorize:
        mode = ProcessingMode.VECTORIZE
    elif args.complete:
        mode = ProcessingMode.COMPLETE
    elif args.enhanced:
        mode = ProcessingMode.ENHANCED
    else:
        mode = ProcessingMode.FAST

    # 문서 타입 결정
    if args.pdf:
        doc_type = DocumentType.PDF
    elif args.docx:
        doc_type = DocumentType.DOCX
    else:
        doc_type = DocumentType.AUTO

    # 출력 형식
    output_formats = ["docjson"]
    if args.xml:
        output_formats.append("xml")

    return PipelineConfig(
        processing_mode=mode,
        document_type=doc_type,
        enable_ocr=not args.no_ocr,
        enable_diagrams=not args.no_diagrams,
        enable_vectorization=args.vectorize or args.complete,
        enable_user_annotations=args.annotations or args.complete,
        output_formats=output_formats,
        custom_template_id=args.template
    )


async def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="고급 문서 처리 시스템 - 기술기준 문서 전문 분석",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # DOCX 기술기준 문서 완전 분석 (다이어그램 + 벡터화)
  python enhanced_main.py document.docx --complete

  # PDF 문서 빠른 OCR 처리
  python enhanced_main.py document.pdf --fast

  # 여러 문서 배치 처리
  python enhanced_main.py docs/*.docx --enhanced --vectorize

  # 사용자 정의 템플릿으로 처리
  python enhanced_main.py document.docx --template template_id

  # XML 중간 형식으로도 출력
  python enhanced_main.py document.docx --enhanced --xml
        """
    )

    # 파일 인수
    parser.add_argument('files', nargs='*', help='처리할 파일 경로')

    # 처리 모드
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--fast', action='store_true', help='빠른 처리 모드')
    mode_group.add_argument('--enhanced', action='store_true', help='고급 처리 모드 (기본값)')
    mode_group.add_argument('--vectorize', action='store_true', help='벡터화 포함 처리')
    mode_group.add_argument('--complete', action='store_true', help='완전 처리 (벡터화 + 주석)')

    # 문서 타입
    type_group = parser.add_mutually_exclusive_group()
    type_group.add_argument('--pdf', action='store_true', help='PDF 문서로 강제 처리')
    type_group.add_argument('--docx', action='store_true', help='DOCX 문서로 강제 처리')

    # 기능 옵션
    parser.add_argument('--no-ocr', action='store_true', help='OCR 비활성화')
    parser.add_argument('--no-diagrams', action='store_true', help='다이어그램 분석 비활성화')
    parser.add_argument('--annotations', action='store_true', help='사용자 주석 시스템 활성화')
    parser.add_argument('--xml', action='store_true', help='XML 중간 형식으로도 출력')
    parser.add_argument('--template', help='사용자 정의 템플릿 ID')

    # 출력 및 기타
    parser.add_argument('--output', '-o', help='출력 디렉토리')
    parser.add_argument('--verbose', '-v', action='store_true', help='상세 로그 출력')

    # 특수 명령
    parser.add_argument('--create-template', action='store_true', help='대화형 템플릿 생성')
    parser.add_argument('--stats', action='store_true', help='처리 통계 표시')

    args = parser.parse_args()

    # 로깅 설정
    setup_logging(args.verbose)

    print("🚀 고급 문서 처리 시스템 시작")
    print("=" * 50)

    try:
        # 시스템 초기화
        device_manager = DeviceManager()
        config_manager = ConfigManager()

        pipeline = IntegratedPipeline(
            device_manager=device_manager,
            config_manager=config_manager,
            output_dir=args.output
        )

        print(f"💾 디바이스: {device_manager.get_optimal_device()}")
        print(f"📁 출력 디렉토리: {pipeline.output_dir}")

        # 특수 명령 처리
        if args.create_template:
            await create_template_interactive(pipeline)
            return

        if args.stats:
            await show_statistics(pipeline)
            return

        # 파일 처리
        if not args.files:
            print("❌ 처리할 파일을 지정해주세요.")
            parser.print_help()
            return

        # 파일 경로 준비
        file_paths = []
        for file_pattern in args.files:
            if '*' in file_pattern or '?' in file_pattern:
                # 글롭 패턴 처리
                from glob import glob
                matched_files = glob(file_pattern)
                file_paths.extend([Path(f) for f in matched_files])
            else:
                file_path = Path(file_pattern)
                if file_path.exists():
                    file_paths.append(file_path)
                else:
                    print(f"⚠️  파일을 찾을 수 없습니다: {file_path}")

        if not file_paths:
            print("❌ 처리할 유효한 파일이 없습니다.")
            return

        # 파이프라인 설정 생성
        config = create_pipeline_config(args)

        # 문서 처리
        if len(file_paths) == 1:
            success = await process_single_document(pipeline, file_paths[0], config)
            sys.exit(0 if success else 1)
        else:
            await process_batch_documents(pipeline, file_paths, config)

    except KeyboardInterrupt:
        print("\n⏹️  사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 시스템 오류: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    print("\n✅ 처리 완료!")


if __name__ == "__main__":
    # Windows에서 asyncio 이벤트 루프 정책 설정
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(main())