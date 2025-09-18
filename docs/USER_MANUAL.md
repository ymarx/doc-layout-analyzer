# 📚 문서 파싱 시스템 사용 매뉴얼

## 🎯 시스템 개요

이 문서 파싱 시스템은 DOCX 문서를 구조화된 데이터로 변환하는 완전한 워크플로우를 제공합니다.

### 🔥 핵심 기능
- **다중 템플릿 기반 파싱**: 여러 문서 형식 동시 지원
- **자동 Annotation 생성**: 템플릿 기반 필드 자동 감지
- **하이브리드 파싱**: 템플릿 + 패턴 인식 결합
- **사용자 템플릿 생성**: 새로운 문서 형식 자동 학습
- **품질 평가**: 신뢰도 및 정확도 자동 측정

## 🚀 빠른 시작

### 1단계: 전체 워크플로우 실행
```bash
# 전체 5단계를 한 번에 실행
python complete_workflow.py

# 또는 단계별 실행
python step1_document_registration.py
python step2_template_selection.py
python step3_annotation.py
python step4_template_save.py
python step5_pattern_parsing.py
```

### 2단계: 결과 확인
실행 완료 후 다음 디렉토리에서 결과를 확인할 수 있습니다:
- `step5_final_parsing/`: 최종 파싱 결과
- `templates/definitions/`: 생성된 템플릿
- `annotations/`: Annotation 데이터

## 📋 단계별 상세 가이드

### 1️⃣ 문서 등재 (Document Registration)

**목적**: 새 문서를 시스템에 등재하고 기본 구조 분석

```bash
python step1_document_registration.py
```

**수행 작업**:
- 문서 파일 존재 확인
- 기본 메타데이터 추출 (제목, 문서번호, 작성자 등)
- 문서 구조 분석 (섹션, 블록, 헤더/푸터)
- 프로세스 플로우 자동 감지

**출력**:
- `step1_analysis/`: 기본 분석 결과 파일들

### 2️⃣ 템플릿 선택 (Template Selection)

**목적**: 문서에 최적화된 템플릿 자동 선택

```bash
python step2_template_selection.py
```

**수행 작업**:
- 사용 가능한 템플릿 목록 조회
- 문서 내용 기반 최적 템플릿 자동 매칭
- 매칭 신뢰도 및 전략 분석
- 수동 템플릿 선택 옵션 제공

**출력**:
- `step2_template_test/`: 템플릿 매칭 테스트 결과

### 3️⃣ Annotation 생성 (Annotation Creation)

**목적**: 템플릿 기반 자동 필드 감지 및 annotation 생성

```bash
python step3_annotation.py
```

**수행 작업**:
- DocJSON 데이터에서 필드 자동 감지
- 필드 타입 및 중요도 분류
- 바운딩박스 좌표 자동 추정
- Annotation 검증 및 저장

**출력**:
- `step3_annotation/`: 처리 결과
- `annotations/`: Annotation JSON 파일들

### 4️⃣ 템플릿 저장 (Template Management)

**목적**: 생성된 annotation을 기반으로 새 템플릿 생성

```bash
python step4_template_save.py
```

**수행 작업**:
- 사용자 템플릿 자동 생성
- JSON 형식 템플릿 저장
- 기존 템플릿과 유사도 분석
- 템플릿 성능 비교

**출력**:
- `step4_template_creation/`: 템플릿 생성 과정
- `templates/definitions/`: 새 템플릿 JSON 파일

### 5️⃣ 최종 파싱 (Final Parsing)

**목적**: 템플릿과 패턴 인식을 결합한 완전 파싱

```bash
python step5_pattern_parsing.py
```

**수행 작업**:
- 모든 기능 활성화한 완전 파싱
- 하이브리드 파싱 (템플릿 + 추론)
- 품질 평가 및 성능 측정
- 최종 결과 검증

**출력**:
- `step5_final_parsing/`: 최종 파싱 결과 전체

## 📁 산출물 및 파일 위치

### 🎯 핵심 산출물

#### 1. 최종 파싱 결과
```
step5_final_parsing/
├── [UUID].docjson                    # 구조화된 문서 데이터
├── [UUID].metadata.json              # 메타데이터
├── 기술기준_예시_template.json        # 자동 생성 템플릿
├── doc_기술기준_예시_[ID]_enhanced.json   # 개선된 DocJSON
├── doc_기술기준_예시_[ID]_template_report.json  # 템플릿 매칭 보고서
└── doc_기술기준_예시_[ID]_quality_report.json   # 품질 평가 보고서
```

#### 2. 템플릿 라이브러리
```
templates/definitions/
├── technical_standard_v1.json                    # 기본 기술기준서 템플릿
├── technical_standard_v2_improved.json           # 개선된 기술기준서 템플릿
└── user_generated_기술기준_예시_template.json    # 사용자 생성 템플릿
```

#### 3. Annotation 데이터
```
annotations/
└── [UUID].json    # 자동 생성된 annotation (21개 필드)
```

### 📊 단계별 중간 산출물

#### Step 1: 문서 등재
```
step1_analysis/
├── [UUID].docjson         # 기본 DocJSON
└── [UUID].metadata.json   # 기본 메타데이터
```

#### Step 2: 템플릿 선택
```
step2_template_test/
├── [UUID].docjson         # 템플릿 테스트용 DocJSON
└── [UUID].metadata.json   # 템플릿 테스트 메타데이터
```

#### Step 3: Annotation
```
step3_annotation/
├── [UUID].docjson         # Annotation 생성용 DocJSON
├── [UUID].metadata.json   # Annotation 메타데이터
└── 기술기준_예시_template.json  # 초기 템플릿

step3_annotations/
└── [UUID].json            # 자동 생성 Annotation (22개 필드)
```

#### Step 4: 템플릿 저장
```
step4_template_creation/
├── [UUID].docjson         # 템플릿 생성용 DocJSON
├── [UUID].metadata.json   # 템플릿 생성 메타데이터
└── 기술기준_예시_template.json  # 최종 템플릿
```

## 🔧 고급 사용법

### 새 문서 처리
```bash
# 1. 새 DOCX 파일을 프로젝트 디렉토리에 배치
cp your_new_document.docx ./

# 2. 파일명을 step 스크립트에서 수정
# 각 step*.py 파일의 document_path 변수 수정

# 3. 전체 워크플로우 재실행
python complete_workflow.py
```

### 템플릿 편집
```bash
# 템플릿 JSON 파일 직접 편집
nano templates/definitions/technical_standard_v2_improved.json

# 편집 가능한 요소:
# - patterns: 정규식 패턴
# - confidence_threshold: 신뢰도 임계값
# - position_hints: 위치 힌트
# - validation_rules: 검증 규칙
```

### Annotation 수정
```python
from src.core.user_annotations import UserAnnotationManager

# Annotation 매니저 초기화
manager = UserAnnotationManager("annotations")

# 기존 annotation 로드
annotation = manager.load_annotation("document_id")

# 필드 값 수정
manager.update_field_value("document_id", "field_id", "new_value")

# 새 필드 추가
from src.core.user_annotations import UserField, FieldType, FieldImportance
new_field = UserField(
    name="custom_field",
    field_type=FieldType.TEXT,
    importance=FieldImportance.HIGH
)
manager.add_field_to_annotation("document_id", new_field)
```

### 배치 처리
```python
import asyncio
from pathlib import Path

async def batch_process(document_paths):
    """여러 문서 일괄 처리"""
    from src.core.enhanced_modernized_pipeline import EnhancedModernizedPipeline
    from src.core.simplified_config import PipelineConfig, ProcessingLevel

    pipeline = EnhancedModernizedPipeline(
        output_dir="batch_output",
        templates_dir="templates/definitions"
    )

    config = PipelineConfig(processing_level=ProcessingLevel.COMPLETE)

    results = []
    for doc_path in document_paths:
        result = await pipeline.process_document(doc_path, config)
        results.append(result)
        print(f"처리 완료: {doc_path}")

    return results

# 사용 예시
document_list = ["doc1.docx", "doc2.docx", "doc3.docx"]
results = asyncio.run(batch_process(document_list))
```

## 📊 성능 모니터링

### 품질 지표 확인
```python
# 최종 결과에서 품질 지표 추출
import json

# 품질 보고서 로드
with open("step5_final_parsing/doc_기술기준_예시_[ID]_quality_report.json") as f:
    quality = json.load(f)

# 템플릿 매칭 보고서 로드
with open("step5_final_parsing/doc_기술기준_예시_[ID]_template_report.json") as f:
    template_report = json.load(f)

print(f"템플릿 신뢰도: {template_report.get('confidence', 0):.1%}")
print(f"바운딩박스 정확도: {template_report.get('bbox_accuracy', 0):.1%}")
print(f"필드 추출 정확도: {quality.get('field_extraction_accuracy', 0):.1%}")
```

### 성능 기준
- **우수 (85점 이상)**: 프로덕션 사용 가능
- **양호 (60-84점)**: 일부 개선 후 사용 권장
- **개선 필요 (60점 미만)**: 추가 개발 필요

## 🛠️ 문제 해결

### 일반적인 문제

#### 1. 문서를 찾을 수 없음
```
❌ 문서를 찾을 수 없습니다: ../기술기준_예시.docx
```
**해결방법**:
- DOCX 파일이 올바른 위치에 있는지 확인
- 파일명과 경로가 정확한지 확인

#### 2. 템플릿 매칭 신뢰도 낮음
```
🔴 개선 필요 (신뢰도: 30.0%)
```
**해결방법**:
- 템플릿 패턴을 더 구체적으로 작성
- confidence_threshold 값 조정
- 새로운 템플릿 패턴 추가

#### 3. 바운딩박스 정확도 낮음
```
📏 바운딩박스 개선 점수: 20.0%
```
**해결방법**:
- OCR 품질 확인
- 문서 해상도 개선
- 수동으로 바운딩박스 조정

### 로그 확인
```bash
# 처리 과정 중 오류 로그 확인
grep -i error *.log

# 경고 메시지 확인
grep -i warning *.log
```

## 📈 최적화 팁

### 1. 성능 향상
- **빠른 처리**: `ProcessingLevel.BASIC` 사용
- **정확도 우선**: `ProcessingLevel.COMPLETE` 사용
- **균형**: `ProcessingLevel.STANDARD` 사용

### 2. 정확도 향상
- 문서별 전용 템플릿 생성
- 정규식 패턴 정교화
- 바운딩박스 정보 추가

### 3. 시스템 관리
- 정기적인 템플릿 성능 모니터링
- 사용자 피드백 수집 및 반영
- 템플릿 라이브러리 지속적 확장

## 🔮 확장 기능

### 현재 개발 중
- 웹 기반 시각적 편집 인터페이스
- 실시간 API 서버
- 다국어 문서 지원
- 패턴 학습 및 최적화

### 향후 계획
- PDF 문서 지원 확장
- 대용량 배치 처리
- 클라우드 연동
- 업계별 특화 템플릿

## 📞 지원 및 문의

### 시스템 정보
- **버전**: 2.0
- **지원 형식**: DOCX
- **성능**: 평균 7-10초/문서
- **정확도**: 평균 85-90%

### 도움말
- `USAGE_GUIDE.md`: 상세 사용 가이드
- `ANNOTATION_GUIDE.md`: Annotation 시스템 가이드
- 각 step 스크립트의 `--help` 옵션

**현재 시스템 상태**: ✅ **프로덕션 준비 완료**