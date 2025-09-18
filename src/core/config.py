"""
Configuration Management System
CPU/GPU 듀얼 모드 지원을 위한 설정 관리
"""

import os
import yaml
import torch
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum


class ProcessingMode(Enum):
    """처리 모드"""
    CPU = "cpu"
    GPU = "gpu"
    AUTO = "auto"


@dataclass
class SystemConfig:
    """시스템 설정"""
    processing_mode: ProcessingMode = ProcessingMode.CPU
    max_workers: int = 8
    chunk_size: int = 1024
    memory_limit: str = "8GB"
    use_multiprocessing: bool = True
    temp_dir: str = "./data/temp"
    log_level: str = "INFO"
    max_file_size: str = "100MB"


@dataclass
class GPUConfig:
    """GPU 설정"""
    enabled: bool = False
    device_ids: list = field(default_factory=lambda: [0])
    batch_size: int = 32
    memory_fraction: float = 0.8
    fallback_to_cpu: bool = True


@dataclass
class OCRConfig:
    """OCR 설정"""
    use_gpu: bool = False
    lang: list = field(default_factory=lambda: ["ko", "en"])
    det_model: str = "ch_PP-OCRv4_det"
    rec_model: str = "ch_PP-OCRv4_rec"
    cls_model: str = "ch_ppocr_mobile_v2.0_cls"


@dataclass
class EmbeddingConfig:
    """임베딩 설정"""
    model: str = "BAAI/bge-m3"
    device: str = "cpu"
    max_length: int = 512
    normalize: bool = True
    batch_size: int = 16


class ConfigManager:
    """설정 관리자 - CPU/GPU 자동 감지 및 설정"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._find_config_file()
        self._config_data = self._load_config()
        self._system_info = self._detect_system_capabilities()

        # 설정 객체 생성
        self.system = self._create_system_config()
        self.gpu = self._create_gpu_config()
        self.ocr = self._create_ocr_config()
        self.embedding = self._create_embedding_config()

        # 환경에 따른 자동 조정
        self._auto_adjust_config()

    def _find_config_file(self) -> str:
        """설정 파일 자동 탐지"""
        possible_paths = [
            "./config/config.yaml",
            "../config/config.yaml",
            "./config.yaml",
            os.path.expanduser("~/.doc_analyzer/config.yaml")
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        # 기본 설정 파일이 없으면 생성
        return self._create_default_config()

    def _create_default_config(self) -> str:
        """기본 설정 파일 생성"""
        config_dir = Path("./config")
        config_dir.mkdir(exist_ok=True)

        default_config = {
            "system": {
                "processing_mode": "cpu",
                "cpu": {
                    "max_workers": 8,
                    "chunk_size": 1024,
                    "memory_limit": "8GB",
                    "use_multiprocessing": True
                },
                "gpu": {
                    "enabled": False,
                    "device_ids": [0],
                    "batch_size": 32,
                    "fallback_to_cpu": True
                }
            },
            "ocr": {
                "paddleocr": {
                    "use_gpu": False,
                    "lang": ["ko", "en"]
                }
            },
            "embeddings": {
                "text": {
                    "model": "BAAI/bge-m3",
                    "device": "cpu",
                    "batch_size": 16
                }
            }
        }

        config_path = config_dir / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)

        return str(config_path)

    def _load_config(self) -> Dict[str, Any]:
        """설정 파일 로드"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"설정 파일 로드 실패: {e}")
            return {}

    def _detect_system_capabilities(self) -> Dict[str, Any]:
        """시스템 능력 감지"""
        capabilities = {
            "cpu_count": os.cpu_count(),
            "has_cuda": torch.cuda.is_available() if 'torch' in globals() else False,
            "cuda_devices": 0,
            "total_memory": 0
        }

        try:
            import psutil
            capabilities["total_memory"] = psutil.virtual_memory().total // (1024**3)  # GB
        except ImportError:
            pass

        if capabilities["has_cuda"]:
            try:
                capabilities["cuda_devices"] = torch.cuda.device_count()
                capabilities["cuda_memory"] = [
                    torch.cuda.get_device_properties(i).total_memory // (1024**3)
                    for i in range(capabilities["cuda_devices"])
                ]
            except Exception:
                capabilities["has_cuda"] = False

        return capabilities

    def _create_system_config(self) -> SystemConfig:
        """시스템 설정 생성"""
        sys_config = self._config_data.get("system", {})

        # 처리 모드 결정
        mode = sys_config.get("processing_mode", "cpu")
        if mode == "auto":
            mode = "gpu" if self._system_info["has_cuda"] else "cpu"

        return SystemConfig(
            processing_mode=ProcessingMode(mode),
            max_workers=min(sys_config.get("cpu", {}).get("max_workers", 8),
                           self._system_info["cpu_count"]),
            chunk_size=sys_config.get("cpu", {}).get("chunk_size", 1024),
            memory_limit=sys_config.get("cpu", {}).get("memory_limit", "8GB"),
            use_multiprocessing=sys_config.get("cpu", {}).get("use_multiprocessing", True),
            temp_dir=sys_config.get("temp_dir", "./data/temp"),
            log_level=sys_config.get("log_level", "INFO"),
            max_file_size=sys_config.get("max_file_size", "100MB")
        )

    def _create_gpu_config(self) -> GPUConfig:
        """GPU 설정 생성"""
        gpu_config = self._config_data.get("system", {}).get("gpu", {})

        return GPUConfig(
            enabled=gpu_config.get("enabled", False) and self._system_info["has_cuda"],
            device_ids=gpu_config.get("device_ids", [0])[:self._system_info["cuda_devices"]],
            batch_size=gpu_config.get("batch_size", 32),
            memory_fraction=gpu_config.get("memory_fraction", 0.8),
            fallback_to_cpu=gpu_config.get("fallback_to_cpu", True)
        )

    def _create_ocr_config(self) -> OCRConfig:
        """OCR 설정 생성"""
        ocr_config = self._config_data.get("ocr", {}).get("paddleocr", {})

        return OCRConfig(
            use_gpu=ocr_config.get("use_gpu", False) and self._system_info["has_cuda"],
            lang=ocr_config.get("lang", ["ko", "en"]),
            det_model=ocr_config.get("det_model", "ch_PP-OCRv4_det"),
            rec_model=ocr_config.get("rec_model", "ch_PP-OCRv4_rec"),
            cls_model=ocr_config.get("cls_model", "ch_ppocr_mobile_v2.0_cls")
        )

    def _create_embedding_config(self) -> EmbeddingConfig:
        """임베딩 설정 생성"""
        emb_config = self._config_data.get("embeddings", {}).get("text", {})

        # 자동 디바이스 선택
        device = emb_config.get("device", "cpu")
        if device == "auto":
            device = "cuda" if self._system_info["has_cuda"] else "cpu"

        return EmbeddingConfig(
            model=emb_config.get("model", "BAAI/bge-m3"),
            device=device,
            max_length=emb_config.get("max_length", 512),
            normalize=emb_config.get("normalize", True),
            batch_size=emb_config.get("batch_size", 16)
        )

    def _auto_adjust_config(self):
        """환경에 따른 설정 자동 조정"""
        # 메모리 기반 배치 크기 조정
        if self._system_info["total_memory"] < 8:
            self.embedding.batch_size = min(self.embedding.batch_size, 8)
            self.system.max_workers = min(self.system.max_workers, 4)

        # GPU 메모리 부족 시 CPU로 폴백
        if self.gpu.enabled and hasattr(self._system_info, "cuda_memory"):
            if any(mem < 4 for mem in self._system_info.get("cuda_memory", [])):
                print("Warning: GPU 메모리 부족, CPU 모드로 전환")
                self.gpu.enabled = False
                self.ocr.use_gpu = False
                self.embedding.device = "cpu"

    def get_device(self, prefer_gpu: bool = False) -> str:
        """적절한 디바이스 반환"""
        if prefer_gpu and self.gpu.enabled:
            return f"cuda:{self.gpu.device_ids[0]}"
        return "cpu"

    def is_gpu_available(self) -> bool:
        """GPU 사용 가능 여부"""
        return self.gpu.enabled and self._system_info["has_cuda"]

    def get_optimal_batch_size(self, task_type: str = "embedding") -> int:
        """작업 유형별 최적 배치 크기"""
        if task_type == "embedding":
            return self.embedding.batch_size
        elif task_type == "ocr":
            return self.gpu.batch_size if self.ocr.use_gpu else 1
        else:
            return self.gpu.batch_size if self.gpu.enabled else 8

    def print_system_info(self):
        """시스템 정보 출력"""
        print("=== 시스템 환경 정보 ===")
        print(f"CPU 코어: {self._system_info['cpu_count']}")
        print(f"메모리: {self._system_info['total_memory']}GB")
        print(f"CUDA 사용 가능: {self._system_info['has_cuda']}")

        if self._system_info['has_cuda']:
            print(f"CUDA 디바이스: {self._system_info['cuda_devices']}")
            if 'cuda_memory' in self._system_info:
                for i, mem in enumerate(self._system_info['cuda_memory']):
                    print(f"  GPU {i}: {mem}GB")

        print("\n=== 설정된 처리 모드 ===")
        print(f"시스템 모드: {self.system.processing_mode.value if hasattr(self.system.processing_mode, 'value') else str(self.system.processing_mode)}")
        print(f"OCR GPU 사용: {self.ocr.use_gpu}")
        print(f"임베딩 디바이스: {self.embedding.device}")
        print(f"최대 워커: {self.system.max_workers}")

    def save_config(self, path: Optional[str] = None):
        """현재 설정을 파일로 저장"""
        save_path = path or self.config_path

        config_dict = {
            "system": {
                "processing_mode": self.system.processing_mode.value if hasattr(self.system.processing_mode, 'value') else str(self.system.processing_mode),
                "cpu": {
                    "max_workers": self.system.max_workers,
                    "chunk_size": self.system.chunk_size,
                    "memory_limit": self.system.memory_limit,
                    "use_multiprocessing": self.system.use_multiprocessing
                },
                "gpu": {
                    "enabled": self.gpu.enabled,
                    "device_ids": self.gpu.device_ids,
                    "batch_size": self.gpu.batch_size,
                    "fallback_to_cpu": self.gpu.fallback_to_cpu
                },
                "temp_dir": self.system.temp_dir,
                "log_level": self.system.log_level
            },
            "ocr": {
                "paddleocr": {
                    "use_gpu": self.ocr.use_gpu,
                    "lang": self.ocr.lang,
                    "det_model": self.ocr.det_model,
                    "rec_model": self.ocr.rec_model
                }
            },
            "embeddings": {
                "text": {
                    "model": self.embedding.model,
                    "device": self.embedding.device,
                    "max_length": self.embedding.max_length,
                    "batch_size": self.embedding.batch_size
                }
            }
        }

        with open(save_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)


# 전역 설정 인스턴스
config = ConfigManager()


def get_config() -> ConfigManager:
    """설정 매니저 인스턴스 반환"""
    return config


def init_config(config_path: Optional[str] = None) -> ConfigManager:
    """설정 초기화"""
    global config
    config = ConfigManager(config_path)
    return config


if __name__ == "__main__":
    # 설정 테스트
    cfg = ConfigManager()
    cfg.print_system_info()