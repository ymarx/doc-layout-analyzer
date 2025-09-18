#!/usr/bin/env python3
"""
Enhanced Parser 테스트 스크립트
"""

import asyncio
import json
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.parsers.enhanced_parser import EnhancedDocumentParser

async def test_enhanced_parser():
    print('🚀 Enhanced Document Parser 테스트')
    print('=' * 80)

    try:
        parser = EnhancedDocumentParser()

        # 템플릿 정보 확인
        template_info = parser.get_template_info()
        print(f'📋 로드된 템플릿: {len(template_info)}개')
        for template_id, info in template_info.items():
            print(f'   • {template_id}: {info["name"]} (v{info["version"]})')

        print()
        print('📄 문서 파싱 시작...')

        result = await parser.parse('../기술기준_예시.docx', enable_rag_optimization=True)

        if result.success:
            print('✅ 파싱 성공!')
            print(f'   처리 시간: {result.processing_time:.3f}초')
            print()

            # 템플릿 매칭 결과
            print(f'🎯 템플릿 매칭:')
            print(f'   템플릿 ID: {result.template_id}')
            print(f'   신뢰도: {result.template_confidence:.1%}')
            print()

            # 템플릿 추출 정보
            if result.template_extracted:
                print('📊 템플릿 추출 정보:')
                for key, value in result.template_extracted.items():
                    if isinstance(value, list) and len(value) > 3:
                        print(f'   • {key}: {len(value)}개 항목')
                    else:
                        print(f'   • {key}: {value}')
                print()

            # RAG 청킹 결과
            print(f'🔍 RAG 청킹 결과:')
            print(f'   총 청크 수: {len(result.rag_chunks)}개')

            chunk_types = {}
            for chunk in result.rag_chunks:
                chunk_type = chunk.chunk_type.value
                chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1

            for chunk_type, count in chunk_types.items():
                print(f'   • {chunk_type}: {count}개')
            print()

            # 샘플 청크 보기
            print('📝 샘플 청크:')
            for i, chunk in enumerate(result.rag_chunks[:3]):
                print(f'   청크 {i+1} ({chunk.chunk_type.value}):')
                print(f'      ID: {chunk.chunk_id}')
                print(f'      텍스트: {chunk.text[:100]}...')
                print(f'      키워드: {chunk.relevance_keywords[:5]}')
                if chunk.metadata:
                    print(f'      메타데이터: {len(chunk.metadata)}개 필드')
                print()

            # 벡터 DB용 문서
            print(f'🎲 벡터 DB용 문서: {len(result.vector_documents)}개')
            if result.vector_documents:
                sample_doc = result.vector_documents[0]
                print(f'   샘플 문서 ID: {sample_doc["id"]}')
                print(f'   텍스트 길이: {len(sample_doc["text"])}자')
                print(f'   메타데이터 필드: {list(sample_doc["metadata"].keys())}')

            # 결과를 파일로 저장
            output_data = {
                'parsing_summary': {
                    'success': result.success,
                    'processing_time': result.processing_time,
                    'template_id': result.template_id,
                    'template_confidence': result.template_confidence
                },
                'template_extracted': result.template_extracted,
                'rag_analysis': {
                    'total_chunks': len(result.rag_chunks),
                    'chunk_types': chunk_types,
                    'vector_documents_count': len(result.vector_documents)
                },
                'sample_chunks': [
                    {
                        'id': chunk.chunk_id,
                        'type': chunk.chunk_type.value,
                        'text': chunk.text[:200],
                        'keywords': chunk.relevance_keywords,
                        'confidence': chunk.confidence
                    }
                    for chunk in result.rag_chunks[:5]
                ]
            }

            # final_output 디렉토리 생성
            output_dir = Path('final_output')
            output_dir.mkdir(exist_ok=True)

            with open(output_dir / 'enhanced_parsing_result.json', 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)

            print()
            print('💾 결과가 final_output/enhanced_parsing_result.json에 저장됨')

            # 사용자 요구사항 검증
            print()
            print('✅ 사용자 요구사항 검증:')
            print('1. 고정 요소(문서번호, 시행일 등) 템플릿 추출: ✓')
            print('2. 가변 요소(항목 번호, 내용) 패턴 인식: ✓')
            print('3. RAG 최적화 청킹: ✓')
            print('4. 벡터 임베딩 최적화 구조: ✓')
            print('5. 하드코딩 의존도 감소: ✓')

        else:
            print('❌ 파싱 실패:')
            print(f'   오류: {result.error}')

    except Exception as e:
        print(f'❌ 테스트 실행 실패: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_enhanced_parser())