# 파이프라인 분석 보고서

## 현재 파이프라인 구조

### 🔍 파이프라인 계층 구조

```
EnhancedModernizedPipeline (최상위 - 현재 사용 중) ✅
    ↑ 상속
ModernizedPipeline (중간 계층)
    ↑ 사용
IntegratedPipeline (독립적 - 병렬 개발)
```

### 📊 파이프라인별 사용 현황

#### 1. **EnhancedModernizedPipeline** ✅ (메인 - 유지)
- **위치**: `src/core/enhanced_modernized_pipeline.py`
- **사용처**:
  - step1~5 모든 워크플로우 스크립트
  - complete_workflow.py
- **특징**:
  - ModernizedPipeline을 상속받아 확장
  - IntegratedTemplateSystem 통합
  - UserAnnotations 지원
- **상태**: **핵심 파일 - 반드시 유지**

#### 2. **ModernizedPipeline** ⚠️ (기반 클래스 - 유지)
- **위치**: `src/core/modernized_pipeline.py`
- **사용처**:
  - EnhancedModernizedPipeline의 부모 클래스
  - cleanup_backup의 테스트 파일들 (삭제됨)
- **특징**:
  - 기본 파이프라인 기능 제공
  - SimplifiedConfig 사용
- **상태**: **의존성 - 유지 필요** (EnhancedModernizedPipeline이 상속)

#### 3. **IntegratedPipeline** ❌ (대체됨 - 제거 가능)
- **위치**: `src/core/integrated_pipeline.py`
- **사용처**:
  - enhanced_main.py
  - simple_hybrid_usage.py
  - cleanup_backup의 일부 테스트
- **특징**:
  - 독립적으로 개발된 병렬 파이프라인
  - PDF 지원 포함 (미완성)
- **상태**: **제거 가능** (EnhancedModernizedPipeline로 대체됨)

### 📁 기타 Core 파일 분석

#### 필수 유지 파일 ✅
1. **docjson.py** - DocJSON 데이터 구조 (모든 파이프라인이 사용)
2. **user_annotations.py** - Annotation 시스템 (step3, step4 사용)
3. **integrated_template_system.py** - 템플릿 매칭 시스템 (EnhancedModernizedPipeline 사용)
4. **simplified_config.py** - 설정 관리 (현재 파이프라인 사용)
5. **vectorization_engine.py** - RAG 벡터화 (선택적 사용)

#### 중복/대체 가능 파일 ⚠️
1. **config.py** vs **simplified_config.py**
   - config.py: 구 설정 시스템
   - simplified_config.py: 새 설정 시스템 (현재 사용)
   - **판단**: config.py 제거 가능

2. **template_manager.py** vs **integrated_template_system.py**
   - template_manager.py: 구 템플릿 시스템
   - integrated_template_system.py: 새 통합 템플릿 시스템
   - **판단**: template_manager.py 제거 가능

3. **device_manager.py**
   - GPU/CPU 관리 (현재 미사용)
   - **판단**: 향후 GPU 지원 시 필요, 당장은 제거 가능

## Config 디렉토리 분석

### config/config.yaml
- **상태**: 유지 (시스템 전체 설정)
- **용도**: OCR, 파서, 벡터DB 설정
- **참고**: 현재 CPU 모드로 설정됨

### src/core/config.py vs src/core/simplified_config.py
- **현재 사용**: simplified_config.py
- **config.py**: 구 버전, IntegratedPipeline에서만 사용
- **판단**: config.py 제거 가능

## 정리 권장사항

### 🗑️ 제거 가능 파일
```bash
# Core 디렉토리
src/core/integrated_pipeline.py     # EnhancedModernizedPipeline로 대체
src/core/config.py                  # simplified_config.py로 대체
src/core/template_manager.py        # integrated_template_system.py로 대체
src/core/device_manager.py          # 현재 미사용 (GPU 미지원)
```

### ⚠️ 주의사항
- enhanced_main.py와 simple_hybrid_usage.py가 IntegratedPipeline을 사용 중
- 이 파일들을 EnhancedModernizedPipeline로 마이그레이션 필요

### ✅ 반드시 유지해야 할 파일
```bash
# Core 필수 파일
src/core/enhanced_modernized_pipeline.py  # 메인 파이프라인
src/core/modernized_pipeline.py          # 기반 클래스
src/core/docjson.py                      # 데이터 구조
src/core/user_annotations.py             # Annotation 시스템
src/core/integrated_template_system.py   # 템플릿 시스템
src/core/simplified_config.py            # 설정 관리
src/core/vectorization_engine.py         # 벡터화 (선택적)
```

## 마이그레이션 필요 파일

### enhanced_main.py
- IntegratedPipeline → EnhancedModernizedPipeline
- 기존 호환성 유지 필요

### simple_hybrid_usage.py
- IntegratedPipeline → EnhancedModernizedPipeline
- 하이브리드 사용 예제 업데이트