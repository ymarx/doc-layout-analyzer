#!/usr/bin/env python3
"""
기술기준 문서 주석 편집기
사용자가 바운딩 박스와 필드를 직접 조정할 수 있는 대화형 인터페이스
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import asdict

from src.core.user_annotations import (
    UserAnnotationManager, UserField, FieldType, FieldImportance, DocumentAnnotation
)
from src.core.docjson import DocJSON, BoundingBox

class AnnotationEditor:
    """바운딩 박스 및 주석 편집기"""

    def __init__(self, output_dir: str = "pipeline_output"):
        self.output_dir = Path(output_dir)
        self.annotation_manager = UserAnnotationManager(self.output_dir / "annotations")
        self.current_docjson = None
        self.current_annotation = None

    def load_document(self, docjson_file: str) -> bool:
        """처리된 DocJSON 문서 로드"""
        try:
            docjson_path = Path(docjson_file)
            if not docjson_path.exists():
                print(f"❌ 파일을 찾을 수 없습니다: {docjson_file}")
                return False

            with open(docjson_path, 'r', encoding='utf-8') as f:
                docjson_data = json.load(f)

            # DocJSON 객체 직접 생성 (from_dict 메서드 대신)
            from src.core.docjson import DocumentMetadata

            # 기본 메타데이터 생성
            metadata = DocumentMetadata(
                title='',
                doc_type='',
                source={}
            )

            self.current_docjson = DocJSON(
                version=docjson_data.get('version', '2.0'),
                doc_id=docjson_data.get('doc_id', ''),
                metadata=metadata
            )

            # 메타데이터 설정
            if 'metadata' in docjson_data:
                metadata_data = docjson_data['metadata']
                self.current_docjson.metadata.title = metadata_data.get('title', '')
                self.current_docjson.metadata.doc_type = metadata_data.get('doc_type', '')
                if 'source' in metadata_data:
                    self.current_docjson.metadata.source = metadata_data['source']

            # 섹션 데이터 로드 (간단한 형태로)
            if 'sections' in docjson_data:
                from src.core.docjson import DocumentSection, ContentBlock
                for section_data in docjson_data['sections']:
                    section = DocumentSection(
                        id=section_data.get('id', ''),
                        path=section_data.get('path', []),
                        heading=section_data.get('heading', ''),
                        level=section_data.get('level', 1)
                    )

                    # 블록 데이터 로드
                    for block_data in section_data.get('blocks', []):
                        bbox = None
                        if 'bbox' in block_data and block_data['bbox']:
                            bbox_data = block_data['bbox']
                            bbox = BoundingBox(
                                bbox_data.get('x1', 0),
                                bbox_data.get('y1', 0),
                                bbox_data.get('x2', 0),
                                bbox_data.get('y2', 0),
                                bbox_data.get('page', 1)
                            )

                        from src.core.docjson import ContentBlockType

                        # 타입 변환
                        block_type_str = block_data.get('type', 'paragraph')
                        try:
                            block_type = ContentBlockType(block_type_str)
                        except ValueError:
                            block_type = ContentBlockType.PARAGRAPH

                        block = ContentBlock(
                            id=block_data.get('id', ''),
                            type=block_type,
                            page=block_data.get('page', 1),
                            bbox=bbox,
                            content=block_data.get('content', {})
                        )
                        section.blocks.append(block)

                    self.current_docjson.sections.append(section)

            # 기존 주석 로드 또는 새로 생성
            source_path = self.current_docjson.metadata.source.get('path', '') if self.current_docjson.metadata.source else ''
            self.current_annotation = self.annotation_manager.load_annotation_by_path(source_path)

            if not self.current_annotation:
                self.current_annotation = self.annotation_manager.create_annotation(
                    source_path, template_id=None
                )
                print(f"✅ 새 주석 생성: {self.current_annotation.document_id}")
            else:
                print(f"✅ 기존 주석 로드: {self.current_annotation.document_id}")

            return True

        except Exception as e:
            print(f"❌ 문서 로드 실패: {e}")
            return False

    def show_document_structure(self):
        """문서 구조 표시"""
        if not self.current_docjson:
            print("❌ 문서가 로드되지 않았습니다.")
            return

        print("\n📋 문서 구조:")
        print(f"   제목: {self.current_docjson.metadata.title}")
        print(f"   타입: {self.current_docjson.metadata.doc_type}")
        print(f"   섹션 수: {len(self.current_docjson.sections)}")

        for i, section in enumerate(self.current_docjson.sections):
            print(f"\n{i+1}. 섹션: {section.heading} (레벨 {section.level})")
            print(f"   블록 수: {len(section.blocks)}")

            # 각 블록의 간단한 미리보기
            for j, block in enumerate(section.blocks[:3]):  # 처음 3개만 표시
                content_preview = block.content.get('text', '')[:50]
                if len(content_preview) < len(block.content.get('text', '')):
                    content_preview += "..."
                print(f"   - 블록 {j+1}: {content_preview}")

            if len(section.blocks) > 3:
                print(f"   - ... 외 {len(section.blocks)-3}개 블록")

    def show_current_annotations(self):
        """현재 주석 표시"""
        if not self.current_annotation:
            print("❌ 주석이 로드되지 않았습니다.")
            return

        print(f"\n📍 현재 주석 (ID: {self.current_annotation.document_id})")
        print(f"   문서: {self.current_annotation.document_path}")
        print(f"   필드 수: {len(self.current_annotation.fields)}")

        if not self.current_annotation.fields:
            print("   ⚠️ 아직 정의된 필드가 없습니다.")
            return

        for i, field in enumerate(self.current_annotation.fields):
            bbox_info = ""
            if field.bbox:
                bbox_info = f" [{field.bbox.x1:.1f},{field.bbox.y1:.1f}-{field.bbox.x2:.1f},{field.bbox.y2:.1f}]"
            print(f"   {i+1}. {field.name} ({field.field_type.value}){bbox_info}")
            if field.description:
                print(f"      설명: {field.description}")

    def add_field_interactive(self):
        """대화형 필드 추가"""
        print("\n➕ 새 필드 추가")

        # 필드 기본 정보 입력
        name = input("필드 이름: ").strip()
        if not name:
            print("❌ 필드 이름은 필수입니다.")
            return

        print("\n사용 가능한 필드 타입:")
        field_types = list(FieldType)
        for i, ft in enumerate(field_types):
            print(f"  {i+1}. {ft.value}")

        try:
            type_idx = int(input("필드 타입 번호: ")) - 1
            if type_idx < 0 or type_idx >= len(field_types):
                raise ValueError()
            field_type = field_types[type_idx]
        except:
            print("❌ 올바른 번호를 입력하세요.")
            return

        description = input("설명 (선택사항): ").strip()

        print("\n중요도:")
        importance_levels = list(FieldImportance)
        for i, imp in enumerate(importance_levels):
            print(f"  {i+1}. {imp.value}")

        try:
            imp_idx = int(input("중요도 번호 (기본값: 2): ") or "2") - 1
            if imp_idx < 0 or imp_idx >= len(importance_levels):
                imp_idx = 1  # MEDIUM
            importance = importance_levels[imp_idx]
        except:
            importance = FieldImportance.MEDIUM

        # 바운딩 박스 입력
        print("\n바운딩 박스 좌표 입력 (선택사항):")
        print("  형식: x1,y1,x2,y2,page (예: 100,200,300,250,1)")
        bbox_input = input("바운딩 박스: ").strip()

        bbox = None
        if bbox_input:
            try:
                coords = [float(x.strip()) for x in bbox_input.split(',')]
                if len(coords) == 5:
                    x1, y1, x2, y2, page = coords
                    bbox = BoundingBox(x1, y1, x2, y2, int(page))
                elif len(coords) == 4:
                    x1, y1, x2, y2 = coords
                    bbox = BoundingBox(x1, y1, x2, y2, 1)
                else:
                    print("⚠️ 좌표 형식이 올바르지 않습니다. 바운딩 박스 없이 생성합니다.")
            except:
                print("⚠️ 좌표 파싱 실패. 바운딩 박스 없이 생성합니다.")

        # 필드 생성
        field = UserField(
            name=name,
            field_type=field_type,
            description=description,
            importance=importance,
            bbox=bbox
        )

        self.current_annotation.fields.append(field)
        self.annotation_manager.save_annotation(self.current_annotation)

        print(f"✅ 필드 '{name}' 추가 완료")

    def suggest_fields_from_document(self):
        """문서 내용에서 필드 자동 제안"""
        if not self.current_docjson:
            print("❌ 문서가 로드되지 않았습니다.")
            return

        print("\n🤖 문서 분석하여 필드 자동 제안 중...")

        suggested_fields = []

        # 1. 헤더에서 기본 필드들 추출
        for section in self.current_docjson.sections:
            for block in section.blocks:
                text = block.content.get('text', '').strip()

                # 문서 번호 패턴
                if 'TP-' in text and len(text) < 50:
                    field = UserField(
                        name="문서번호",
                        field_type=FieldType.CODE,
                        importance=FieldImportance.CRITICAL,
                        description=f"자동 감지: {text}",
                        bbox=block.bbox
                    )
                    suggested_fields.append(field)

                # 제목 패턴 (짧은 텍스트, 숫자로 시작하지 않음)
                elif len(text) < 100 and text and not text[0].isdigit() and '.' not in text[:10]:
                    if any(keyword in text for keyword in ['기준', '표준', '조치', '관리']):
                        field = UserField(
                            name="제목_또는_주요내용",
                            field_type=FieldType.TITLE,
                            importance=FieldImportance.HIGH,
                            description=f"자동 감지: {text}",
                            bbox=block.bbox
                        )
                        suggested_fields.append(field)

                # 번호 매겨진 항목들
                elif text.startswith(('1.', '2.', '3.', '4.', '5.')):
                    field = UserField(
                        name=f"항목_{text.split('.')[0]}",
                        field_type=FieldType.TEXT,
                        importance=FieldImportance.MEDIUM,
                        description=f"번호 매겨진 항목: {text[:50]}",
                        bbox=block.bbox
                    )
                    suggested_fields.append(field)

        if not suggested_fields:
            print("⚠️ 자동 제안할 필드를 찾을 수 없습니다.")
            return

        print(f"\n📋 {len(suggested_fields)}개 필드 제안:")
        for i, field in enumerate(suggested_fields):
            bbox_info = ""
            if field.bbox:
                bbox_info = f" [{field.bbox.x1:.0f},{field.bbox.y1:.0f}-{field.bbox.x2:.0f},{field.bbox.y2:.0f}]"
            print(f"  {i+1}. {field.name} ({field.field_type.value}){bbox_info}")
            print(f"     {field.description}")

        add_all = input("\n모든 제안 필드를 추가하시겠습니까? (y/N): ").strip().lower()
        if add_all in ['y', 'yes']:
            self.current_annotation.fields.extend(suggested_fields)
            self.annotation_manager.save_annotation(self.current_annotation)
            print(f"✅ {len(suggested_fields)}개 필드 추가 완료")
        else:
            print("개별 선택 기능은 추후 구현 예정입니다.")

    def edit_field(self):
        """기존 필드 편집"""
        if not self.current_annotation.fields:
            print("❌ 편집할 필드가 없습니다.")
            return

        print("\n✏️ 필드 편집")
        self.show_current_annotations()

        try:
            field_idx = int(input("\n편집할 필드 번호: ")) - 1
            if field_idx < 0 or field_idx >= len(self.current_annotation.fields):
                print("❌ 올바른 필드 번호를 입력하세요.")
                return
        except:
            print("❌ 올바른 번호를 입력하세요.")
            return

        field = self.current_annotation.fields[field_idx]
        print(f"\n현재 필드: {field.name}")

        # 바운딩 박스 편집
        if field.bbox:
            print(f"현재 바운딩 박스: [{field.bbox.x1},{field.bbox.y1},{field.bbox.x2},{field.bbox.y2},page{field.bbox.page}]")

        new_bbox = input("새 바운딩 박스 (x1,y1,x2,y2,page) 또는 Enter로 유지: ").strip()
        if new_bbox:
            try:
                coords = [float(x.strip()) for x in new_bbox.split(',')]
                if len(coords) >= 4:
                    page = int(coords[4]) if len(coords) == 5 else (field.bbox.page if field.bbox else 1)
                    field.bbox = BoundingBox(coords[0], coords[1], coords[2], coords[3], page)
                    print("✅ 바운딩 박스 업데이트됨")
            except:
                print("⚠️ 바운딩 박스 형식 오류")

        # 설명 편집
        new_desc = input(f"새 설명 (현재: {field.description}) 또는 Enter로 유지: ").strip()
        if new_desc:
            field.description = new_desc

        self.annotation_manager.save_annotation(self.current_annotation)
        print("✅ 필드 업데이트 완료")

    def export_annotation_summary(self):
        """주석 요약 내보내기"""
        if not self.current_annotation:
            print("❌ 주석이 로드되지 않았습니다.")
            return

        output_file = self.output_dir / f"annotation_summary_{self.current_annotation.document_id[:8]}.json"

        summary = {
            "annotation_id": self.current_annotation.document_id,
            "source_document": self.current_annotation.document_path,
            "created_at": self.current_annotation.created_at,
            "field_count": len(self.current_annotation.fields),
            "fields": []
        }

        for field in self.current_annotation.fields:
            field_summary = {
                "name": field.name,
                "type": field.field_type.value,
                "importance": field.importance.value,
                "description": field.description,
                "has_bbox": field.bbox is not None
            }

            if field.bbox:
                field_summary["bbox"] = {
                    "x1": field.bbox.x1,
                    "y1": field.bbox.y1,
                    "x2": field.bbox.x2,
                    "y2": field.bbox.y2,
                    "page": field.bbox.page
                }

            summary["fields"].append(field_summary)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        print(f"✅ 주석 요약 저장: {output_file}")

    def interactive_menu(self):
        """대화형 메뉴"""
        while True:
            print("\n" + "="*50)
            print("📝 기술기준 문서 주석 편집기")
            print("="*50)

            if self.current_docjson:
                print(f"현재 문서: {self.current_docjson.metadata.title}")
            else:
                print("현재 문서: 없음")

            if self.current_annotation:
                print(f"현재 주석: {len(self.current_annotation.fields)}개 필드")

            print("\n🔧 사용 가능한 작업:")
            print("  1. 문서 구조 보기")
            print("  2. 현재 주석 보기")
            print("  3. 필드 추가")
            print("  4. 필드 편집")
            print("  5. 자동 필드 제안")
            print("  6. 주석 요약 내보내기")
            print("  7. 다른 문서 로드")
            print("  0. 종료")

            try:
                choice = input("\n선택: ").strip()

                if choice == '0':
                    print("👋 편집기를 종료합니다.")
                    break
                elif choice == '1':
                    self.show_document_structure()
                elif choice == '2':
                    self.show_current_annotations()
                elif choice == '3':
                    self.add_field_interactive()
                elif choice == '4':
                    self.edit_field()
                elif choice == '5':
                    self.suggest_fields_from_document()
                elif choice == '6':
                    self.export_annotation_summary()
                elif choice == '7':
                    docjson_file = input("DocJSON 파일 경로: ").strip()
                    self.load_document(docjson_file)
                else:
                    print("❌ 올바른 번호를 선택하세요.")

            except KeyboardInterrupt:
                print("\n👋 편집기를 종료합니다.")
                break
            except Exception as e:
                print(f"❌ 오류 발생: {e}")

def main():
    parser = argparse.ArgumentParser(description="기술기준 문서 주석 편집기")
    parser.add_argument('docjson_file', nargs='?', help='편집할 DocJSON 파일')
    parser.add_argument('--output-dir', '-o', default='pipeline_output', help='출력 디렉토리')

    args = parser.parse_args()

    editor = AnnotationEditor(args.output_dir)

    if args.docjson_file:
        if editor.load_document(args.docjson_file):
            editor.interactive_menu()
    else:
        # 최근 처리된 파일 자동 감지
        output_dir = Path(args.output_dir)
        docjson_files = list(output_dir.glob("*.docjson"))

        if docjson_files:
            # 가장 최근 파일 선택
            latest_file = max(docjson_files, key=lambda f: f.stat().st_mtime)
            print(f"🔍 최근 파일 자동 감지: {latest_file.name}")

            if editor.load_document(str(latest_file)):
                editor.interactive_menu()
        else:
            print("❌ DocJSON 파일을 찾을 수 없습니다.")
            print("사용법: python annotation_editor.py <docjson_file>")

if __name__ == "__main__":
    main()