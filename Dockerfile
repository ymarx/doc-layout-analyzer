# Document Layout Analyzer - Multi-stage Docker Build
# CPU/GPU 듀얼 모드 지원 with 최적화된 빌드

# =============================================================================
# Base 이미지 - 공통 시스템 의존성
# =============================================================================
FROM python:3.11-slim as system-base

# 환경 변수 설정
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성을 한 번에 설치 (레이어 최적화)
RUN apt-get update && apt-get install -y --no-install-recommends \
    # 기본 도구
    wget curl unzip \
    # 이미지 처리 라이브러리
    libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 \
    # PDF 처리
    poppler-utils \
    # OCR 엔진
    tesseract-ocr tesseract-ocr-kor tesseract-ocr-eng \
    # LibreOffice (headless)
    libreoffice --no-install-recommends \
    # Python 빌드 도구
    build-essential python3-dev pkg-config \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# =============================================================================
# CPU 버전 빌드
# =============================================================================
FROM system-base as cpu-deps

# requirements 파일들 복사 (캐시 최적화)
COPY doc_layout_analyzer/requirements.txt ./requirements-base.txt
COPY doc_layout_analyzer/requirements-optional.txt ./requirements-optional.txt

# CPU 버전 PyTorch 설치 (가장 큰 패키지부터)
RUN pip install --no-cache-dir \
    torch==2.1.1+cpu torchvision==0.16.1+cpu \
    --index-url https://download.pytorch.org/whl/cpu

# PaddlePaddle CPU 버전 설치
RUN pip install --no-cache-dir paddlepaddle==2.5.2

# OCRmyPDF (시스템 의존성 필요)
RUN pip install --no-cache-dir ocrmypdf

# 기본 의존성 설치
RUN pip install --no-cache-dir -r requirements-base.txt

# 선택적 의존성 설치 (GPU 제외)
RUN pip install --no-cache-dir \
    paddleocr==2.7.3 \
    pytesseract==0.3.10 \
    easyocr==1.7.0 \
    opencv-python==4.8.1.78 \
    scikit-image==0.22.0 \
    sentence-transformers==2.2.2 \
    transformers==4.36.0 \
    onnxruntime==1.16.3 \
    qdrant-client==1.7.0 \
    spacy==3.7.2

FROM cpu-deps as base

# 애플리케이션 코드 복사 (레이어 최적화 순서)
COPY src/ ./src/
COPY config/ ./config/
COPY main.py test_system.py setup.py ./

# 스크립트 파일들 복사
COPY step*.py template_manager_cli.py annotation_editor.py ./

# 디렉토리 구조 생성
RUN mkdir -p \
    data/{input,output,models} \
    logs \
    annotations \
    templates/{definitions} \
    tests \
    && chmod +x *.py

# 포트 노출
EXPOSE 8000

# 헬스체크 개선
HEALTHCHECK --interval=30s --timeout=30s --start-period=10s --retries=3 \
    CMD python -c "import sys; sys.path.insert(0, '/app/src'); from src.core.config import ConfigManager; print('OK')" || exit 1

# 엔트리포인트 설정
ENTRYPOINT ["python", "main.py"]
CMD ["--info"]

# =============================================================================
# GPU 지원 빌드 (NVIDIA CUDA 기반)
# =============================================================================
FROM nvidia/cuda:11.8-runtime-ubuntu22.04 as gpu-system-base

# 환경 변수 설정
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CUDA_VISIBLE_DEVICES=0

WORKDIR /app

# Python 3.11 및 시스템 의존성 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3.11-dev python3.11-distutils python3-pip \
    # 기본 도구
    wget curl unzip \
    # 이미지 처리
    libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 \
    # PDF 처리
    poppler-utils \
    # OCR
    tesseract-ocr tesseract-ocr-kor tesseract-ocr-eng \
    # LibreOffice
    libreoffice --no-install-recommends \
    # 빌드 도구
    build-essential pkg-config \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Python 심볼릭 링크 및 pip 업그레이드
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 \
    && python3 -m pip install --upgrade pip

FROM gpu-system-base as gpu-deps

# requirements 파일들 복사
COPY doc_layout_analyzer/requirements.txt ./requirements-base.txt
COPY doc_layout_analyzer/requirements-optional.txt ./requirements-optional.txt

# GPU 버전 PyTorch 설치
RUN pip install --no-cache-dir \
    torch==2.1.1+cu118 torchvision==0.16.1+cu118 \
    --index-url https://download.pytorch.org/whl/cu118

# PaddlePaddle GPU 버전 설치
RUN pip install --no-cache-dir paddlepaddle-gpu==2.5.2

# OCRmyPDF
RUN pip install --no-cache-dir ocrmypdf

# 기본 의존성 설치
RUN pip install --no-cache-dir -r requirements-base.txt

# GPU 최적화된 선택적 의존성 설치
RUN pip install --no-cache-dir \
    paddleocr==2.7.3 \
    pytesseract==0.3.10 \
    easyocr==1.7.0 \
    opencv-python==4.8.1.78 \
    scikit-image==0.22.0 \
    sentence-transformers==2.2.2 \
    transformers==4.36.0 \
    onnxruntime-gpu==1.16.3 \
    qdrant-client==1.7.0 \
    spacy==3.7.2

FROM gpu-deps as gpu-base

# 애플리케이션 코드 복사
COPY src/ ./src/
COPY config/ ./config/
COPY main.py test_system.py setup.py ./
COPY step*.py template_manager_cli.py annotation_editor.py ./

# 디렉토리 구조 생성
RUN mkdir -p \
    data/{input,output,models} \
    logs \
    annotations \
    templates/{definitions} \
    tests \
    && chmod +x *.py

# GPU 설정 템플릿 생성 (런타임에 환경변수로 덮어쓸 수 있도록)
RUN echo 'system:\n  processing_mode: "gpu"\n  device: "cuda"\nocr:\n  paddleocr:\n    use_gpu: true\n  tesseract:\n    enabled: true\nembeddings:\n  device: "cuda"' > config/gpu_override.yaml

# 포트 노출
EXPOSE 8000

# GPU 헬스체크
HEALTHCHECK --interval=30s --timeout=30s --start-period=15s --retries=3 \
    CMD python -c "import torch; print('GPU available:', torch.cuda.is_available()); assert torch.cuda.is_available()" || exit 1

# 엔트리포인트 설정
ENTRYPOINT ["python", "main.py"]
CMD ["--gpu"]