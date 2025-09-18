# 📊 모듈 사용 분석 보고서

## 🎯 분석 목적
step1-5 워크플로우에서 extractors, parsers, templates 폴더의 실제 사용 여부 확인

---

## 📁 폴더별 사용 현황

### 1️⃣ extractors 폴더
```
src/extractors/
├── __init__.py
└── content_extractor.py
```

#### 사용 현황
- **직접 사용**: ❌ step1-5에서 직접 import 없음
- **간접 사용**: ✅ 다음 모듈을 통해 사용
  - `main.py`: 직접 import
  - `src/core/docjson.py`: ExtractedContent 클래스 사용
- **상태**: ⚠️ **레거시 모듈** (main.py 호환용)

### 2️⃣ parsers 폴더
```
src/parsers/
├── __init__.py
├── base_parser.py
├── diagram_flow_analyzer.py      # 사용됨 ✅
├── document_analyzer.py          # 사용됨 ✅
├── docx_enhanced_parser.py
├── docx_parser.py
├── enhanced_parser.py
├── pdf_parser.py
├── unified_docx_parser.py        # 사용됨 ✅
```

#### 사용 현황
- **직접 사용**: ❌ step1-5에서 직접 import 없음
- **간접 사용**: ✅ 다음 모듈을 통해 사용
  - `src/core/modernized_pipeline.py`:
    - `UnifiedDocxParser`
    - `PDFParser`
  - `main.py`: DocumentParserFactory 사용
- **상태**: ✅ **핵심 모듈** (파이프라인에서 활용)

### 3️⃣ analyzers 폴더
```
src/analyzers/
├── __init__.py
└── layout_analyzer.py
```

#### 사용 현황
- **직접 사용**: ❌ step1-5에서 직접 import 없음
- **간접 사용**: ✅ 다음 모듈을 통해 사용
  - `src/core/modernized_pipeline.py`: LayoutAnalyzer 사용
  - `src/core/docjson.py`: LayoutElement, LayoutElementType 사용
  - `main.py`: LayoutAnalyzer 직접 사용
- **상태**: ✅ **핵심 모듈** (레이아웃 분석용)

### 4️⃣ templates 폴더
```
templates/
└── definitions/
    ├── technical_standard_v1.json
    ├── technical_standard_v2_improved.json
    └── user_generated_기술기준_예시_template.json
```

#### 사용 현황
- **직접 사용**: ✅ step1-5 모든 단계에서 활용
  - EnhancedModernizedPipeline 초기화 시 `templates_dir="templates/definitions"` 지정
  - IntegratedTemplateSystem에서 템플릿 로드
- **상태**: ✅ **필수 데이터** (템플릿 정의 파일들)

---

## 🔗 Step1-5 모듈 의존성 매핑

### Step 스크립트별 직접 Import
```
step1_document_registration.py:
├── src.core.enhanced_modernized_pipeline
└── src.core.simplified_config

step2_template_selection.py:
├── src.core.enhanced_modernized_pipeline
├── src.core.simplified_config
└── src.core.integrated_template_system

step3_annotation.py:
├── src.core.enhanced_modernized_pipeline
├── src.core.simplified_config
├── src.core.user_annotations
└── src.core.docjson (BoundingBox만)

step4_template_save.py:
├── src.core.enhanced_modernized_pipeline
├── src.core.simplified_config
└── src.core.user_annotations

step5_pattern_parsing.py:
├── src.core.enhanced_modernized_pipeline
├── src.core.simplified_config
└── src.core.user_annotations
```

### 간접 의존성 체인
```
Step Scripts
    ↓ import
EnhancedModernizedPipeline
    ↓ 상속
ModernizedPipeline
    ↓ import
└── src.parsers.unified_docx_parser ✅
└── src.parsers.pdf_parser ✅
└── src.analyzers.layout_analyzer ✅

DocJSON
    ↓ import
└── src.analyzers.layout_analyzer ✅
└── src.extractors.content_extractor ⚠️
```

---

## 📊 사용 빈도 분석

### 🟢 핵심 사용 모듈 (step1-5에서 활용)
1. **templates/definitions/** - 템플릿 정의 파일들
2. **src/parsers/unified_docx_parser.py** - 주요 DOCX 파서
3. **src/parsers/diagram_flow_analyzer.py** - 다이어그램 분석
4. **src/parsers/document_analyzer.py** - 문서 분석
5. **src/analyzers/layout_analyzer.py** - 레이아웃 분석

### 🟡 부분 사용 모듈 (간접 사용)
1. **src/parsers/pdf_parser.py** - PDF 지원 (미래용)
2. **src/parsers/enhanced_parser.py** - 고급 파서
3. **src/parsers/base_parser.py** - 파서 기반 클래스

### 🔴 미사용/레거시 모듈
1. **src/extractors/content_extractor.py** - main.py에서만 사용
2. **src/parsers/docx_enhanced_parser.py** - 구버전 파서
3. **src/parsers/docx_parser.py** - 구버전 파서

---

## 🎯 결론 및 권장사항

### ✅ 유지해야 할 폴더/파일
```
✅ templates/ - 전체 유지 (필수 데이터)
✅ src/parsers/ - 대부분 유지 (핵심 기능)
  ├── unified_docx_parser.py (핵심)
  ├── diagram_flow_analyzer.py (핵심)
  ├── document_analyzer.py (핵심)
  ├── pdf_parser.py (미래용)
  └── base_parser.py (기반)
✅ src/analyzers/ - 전체 유지 (핵심 기능)
```

### ⚠️ 검토 대상
```
⚠️ src/extractors/ - 레거시 호환용
  └── content_extractor.py (main.py에서만 사용)

⚠️ src/parsers/ - 일부 구버전 파일
  ├── docx_enhanced_parser.py (구버전)
  └── docx_parser.py (구버전)
```

### 📈 사용 패턴
1. **Step1-5**: core 모듈만 직접 사용
2. **Core 모듈**: parsers/analyzers를 간접 활용
3. **Templates**: 모든 단계에서 데이터로 활용
4. **Extractors**: 현재 워크플로우에서 미사용

### 🚀 최적화 제안
1. **즉시 가능**: 구버전 파서 파일들을 cleanup_backup으로 이동
2. **향후 검토**: extractors 폴더의 필요성 재평가
3. **유지 권장**: templates, 핵심 parsers, analyzers 전체 유지

---

**📅 분석일**: 2025-09-18
**🎯 결론**: templates과 핵심 parsers/analyzers는 필수, extractors는 레거시 호환용