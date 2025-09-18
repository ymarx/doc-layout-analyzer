#!/usr/bin/env python3
"""
템플릿 관리 CLI 도구
기존 주석을 템플릿으로 변환하고 관리하는 도구
"""

import argparse
import json
from pathlib import Path
from typing import List, Dict, Any

from src.core.template_manager import TemplateManager
from src.core.user_annotations import UserAnnotationManager, DocumentAnnotation


class TemplateManagerCLI:
    """템플릿 관리 CLI"""

    def __init__(self, output_dir: str = "pipeline_output"):
        self.output_dir = Path(output_dir)
        self.annotation_manager = UserAnnotationManager(self.output_dir / "annotations" / "documents")
        self.template_manager = TemplateManager(self.output_dir / "annotations" / "templates")

    def list_annotations(self) -> List[Dict[str, Any]]:
        """사용 가능한 주석 목록 조회"""
        annotations_dir = self.output_dir / "annotations" / "documents"
        annotations = []

        if not annotations_dir.exists():
            return annotations

        for annotation_file in annotations_dir.glob("*.json"):
            try:
                with open(annotation_file, 'r', encoding='utf-8') as f:
                    annotation_data = json.load(f)

                annotations.append({
                    "id": annotation_data.get("document_id", ""),
                    "document_path": annotation_data.get("document_path", ""),
                    "field_count": len(annotation_data.get("fields", [])),
                    "created_at": annotation_data.get("created_at", ""),
                    "file_path": str(annotation_file)
                })
            except Exception as e:
                print(f"⚠️ 주석 파일 읽기 실패 {annotation_file}: {e}")

        return annotations

    def show_annotation_details(self, annotation_id: str):
        """주석 상세 정보 표시"""
        annotation = self.annotation_manager.load_annotation(annotation_id)
        if not annotation:
            print(f"❌ 주석을 찾을 수 없습니다: {annotation_id}")
            return

        print(f"\n📍 주석 상세 정보:")
        print(f"   ID: {annotation.document_id}")
        print(f"   문서: {annotation.document_path}")
        print(f"   필드 수: {len(annotation.fields)}")
        print(f"   생성일: {annotation.created_at}")

        if annotation.fields:
            print(f"\n📋 필드 목록:")
            for i, field in enumerate(annotation.fields, 1):
                bbox_info = ""
                if field.bbox:
                    bbox_info = f" [{field.bbox.x1:.0f},{field.bbox.y1:.0f}-{field.bbox.x2:.0f},{field.bbox.y2:.0f}]"

                print(f"   {i}. {field.name} ({field.field_type.value}){bbox_info}")
                print(f"      중요도: {field.importance.value}")
                if field.description:
                    print(f"      설명: {field.description}")
                print()

    def create_template_from_annotation(self,
                                       annotation_id: str,
                                       template_name: str,
                                       description: str = ""):
        """주석에서 템플릿 생성"""
        annotation = self.annotation_manager.load_annotation(annotation_id)
        if not annotation:
            print(f"❌ 주석을 찾을 수 없습니다: {annotation_id}")
            return None

        template = self.template_manager.create_template_from_annotation(
            annotation, template_name, description
        )

        print(f"✅ 템플릿 생성 완료: {template.name}")
        print(f"   ID: {template.id}")
        print(f"   문서 타입: {template.document_type}")
        print(f"   필드 수: {len(template.template_fields)}")

        return template

    def list_templates(self):
        """템플릿 목록 표시"""
        templates = self.template_manager.list_templates()

        if not templates:
            print("📋 등록된 템플릿이 없습니다.")
            return

        print(f"\n📋 등록된 템플릿 ({len(templates)}개):")
        for i, template in enumerate(templates, 1):
            print(f"   {i}. {template['name']} ({template['document_type']})")
            print(f"      ID: {template['id']}")
            print(f"      필드 수: {template['field_count']}")
            print(f"      사용 횟수: {template['usage_count']}")
            print(f"      성공률: {template['success_rate']:.1%}")
            print(f"      생성일: {template['created_at']}")
            print()

    def show_template_details(self, template_id: str):
        """템플릿 상세 정보 표시"""
        if template_id not in self.template_manager.templates:
            print(f"❌ 템플릿을 찾을 수 없습니다: {template_id}")
            return

        template = self.template_manager.templates[template_id]

        print(f"\n📋 템플릿 상세 정보:")
        print(f"   이름: {template.name}")
        print(f"   ID: {template.id}")
        print(f"   문서 타입: {template.document_type}")
        print(f"   설명: {template.description}")
        print(f"   필드 수: {len(template.template_fields)}")
        print(f"   사용 횟수: {template.usage_count}")
        print(f"   성공률: {template.success_rate:.1%}")

        if template.template_fields:
            print(f"\n📋 템플릿 필드:")
            for i, field in enumerate(template.template_fields, 1):
                bbox_info = ""
                if field.bbox:
                    bbox_info = f" [{field.bbox.x1:.0f},{field.bbox.y1:.0f}-{field.bbox.x2:.0f},{field.bbox.y2:.0f}]"

                print(f"   {i}. {field.name} ({field.field_type.value}){bbox_info}")
                print(f"      중요도: {field.importance.value}")
                if field.description:
                    print(f"      설명: {field.description}")

        if template.header_patterns:
            print(f"\n🔍 헤더 패턴:")
            for pattern in template.header_patterns:
                print(f"   - {pattern}")

        if template.section_patterns:
            print(f"\n📄 섹션 패턴:")
            for pattern in template.section_patterns:
                print(f"   - {pattern}")

        if template.identifier_patterns:
            print(f"\n🔖 식별자 패턴:")
            for pattern in template.identifier_patterns:
                print(f"   - {pattern}")

    def test_template_matching(self, template_id: str, docjson_file: str):
        """템플릿 매칭 테스트"""
        if template_id not in self.template_manager.templates:
            print(f"❌ 템플릿을 찾을 수 없습니다: {template_id}")
            return

        docjson_path = Path(docjson_file)
        if not docjson_path.exists():
            print(f"❌ DocJSON 파일을 찾을 수 없습니다: {docjson_file}")
            return

        try:
            with open(docjson_path, 'r', encoding='utf-8') as f:
                document_content = json.load(f)

            template = self.template_manager.templates[template_id]
            match_result = self.template_manager._match_template(template, document_content)

            print(f"\n🔍 템플릿 매칭 결과:")
            print(f"   템플릿: {match_result.template_name}")
            print(f"   신뢰도: {match_result.confidence:.2%}")
            print(f"   매칭된 필드: {len(match_result.matched_fields)}")
            print(f"   미매칭 필드: {len(match_result.unmatched_fields)}")

            if match_result.matched_fields:
                print(f"\n✅ 매칭된 필드:")
                for field_id, content, confidence in match_result.matched_fields:
                    field_name = next((f.name for f in template.template_fields if f.id == field_id), field_id)
                    print(f"   - {field_name}: {content[:50]}... (신뢰도: {confidence:.2%})")

            if match_result.unmatched_fields:
                print(f"\n❌ 미매칭 필드:")
                for field_id in match_result.unmatched_fields:
                    field_name = next((f.name for f in template.template_fields if f.id == field_id), field_id)
                    print(f"   - {field_name}")

        except Exception as e:
            print(f"❌ 템플릿 매칭 테스트 실패: {e}")

    def delete_template(self, template_id: str):
        """템플릿 삭제"""
        if template_id not in self.template_manager.templates:
            print(f"❌ 템플릿을 찾을 수 없습니다: {template_id}")
            return

        template_name = self.template_manager.templates[template_id].name
        confirm = input(f"정말로 템플릿 '{template_name}'을(를) 삭제하시겠습니까? (y/N): ").strip().lower()

        if confirm in ['y', 'yes']:
            if self.template_manager.delete_template(template_id):
                print(f"✅ 템플릿 삭제 완료: {template_name}")
            else:
                print(f"❌ 템플릿 삭제 실패")
        else:
            print("❌ 삭제가 취소되었습니다.")

    def show_stats(self):
        """통계 정보 표시"""
        stats = self.template_manager.get_template_stats()

        print(f"\n📊 템플릿 통계:")
        print(f"   총 템플릿 수: {stats['total_templates']}")

        if stats['total_templates'] > 0:
            print(f"   평균 성공률: {stats['avg_success_rate']:.1%}")

            if 'by_type' in stats:
                print(f"\n📋 문서 타입별:")
                for doc_type, count in stats['by_type'].items():
                    print(f"   - {doc_type}: {count}개")

            if 'most_used' in stats and stats['most_used']:
                most_used = stats['most_used']
                print(f"\n🏆 가장 많이 사용된 템플릿:")
                print(f"   - 이름: {most_used['name']}")
                print(f"   - 사용 횟수: {most_used['usage_count']}")
                print(f"   - 성공률: {most_used['success_rate']:.1%}")

    def interactive_menu(self):
        """대화형 메뉴"""
        while True:
            print("\n" + "="*60)
            print("🔧 템플릿 관리 도구")
            print("="*60)

            print("\n📋 사용 가능한 작업:")
            print("  1. 주석 목록 보기")
            print("  2. 주석 상세 정보")
            print("  3. 주석에서 템플릿 생성")
            print("  4. 템플릿 목록 보기")
            print("  5. 템플릿 상세 정보")
            print("  6. 템플릿 매칭 테스트")
            print("  7. 템플릿 삭제")
            print("  8. 통계 보기")
            print("  0. 종료")

            try:
                choice = input("\n선택: ").strip()

                if choice == '0':
                    print("👋 템플릿 관리 도구를 종료합니다.")
                    break
                elif choice == '1':
                    annotations = self.list_annotations()
                    if annotations:
                        print(f"\n📋 사용 가능한 주석 ({len(annotations)}개):")
                        for i, ann in enumerate(annotations, 1):
                            print(f"   {i}. {Path(ann['document_path']).name}")
                            print(f"      ID: {ann['id'][:8]}...")
                            print(f"      필드: {ann['field_count']}개")
                            print(f"      생성일: {ann['created_at']}")
                            print()
                    else:
                        print("📋 사용 가능한 주석이 없습니다.")

                elif choice == '2':
                    annotation_id = input("주석 ID: ").strip()
                    self.show_annotation_details(annotation_id)

                elif choice == '3':
                    annotation_id = input("주석 ID: ").strip()
                    template_name = input("템플릿 이름: ").strip()
                    description = input("설명 (선택사항): ").strip()

                    if annotation_id and template_name:
                        self.create_template_from_annotation(annotation_id, template_name, description)

                elif choice == '4':
                    self.list_templates()

                elif choice == '5':
                    template_id = input("템플릿 ID: ").strip()
                    self.show_template_details(template_id)

                elif choice == '6':
                    template_id = input("템플릿 ID: ").strip()
                    docjson_file = input("테스트할 DocJSON 파일 경로: ").strip()
                    self.test_template_matching(template_id, docjson_file)

                elif choice == '7':
                    template_id = input("삭제할 템플릿 ID: ").strip()
                    self.delete_template(template_id)

                elif choice == '8':
                    self.show_stats()

                else:
                    print("❌ 올바른 번호를 선택하세요.")

            except KeyboardInterrupt:
                print("\n👋 템플릿 관리 도구를 종료합니다.")
                break
            except Exception as e:
                print(f"❌ 오류 발생: {e}")


def main():
    parser = argparse.ArgumentParser(description="템플릿 관리 CLI 도구")
    parser.add_argument('--output-dir', '-o', default='pipeline_output', help='출력 디렉토리')

    # 개별 명령어들
    subparsers = parser.add_subparsers(dest='command', help='사용 가능한 명령어')

    # 템플릿 생성 명령
    create_parser = subparsers.add_parser('create', help='주석에서 템플릿 생성')
    create_parser.add_argument('annotation_id', help='주석 ID')
    create_parser.add_argument('template_name', help='템플릿 이름')
    create_parser.add_argument('--description', help='템플릿 설명')

    # 템플릿 목록 명령
    list_parser = subparsers.add_parser('list', help='템플릿 목록 보기')

    # 템플릿 상세 정보 명령
    show_parser = subparsers.add_parser('show', help='템플릿 상세 정보')
    show_parser.add_argument('template_id', help='템플릿 ID')

    # 매칭 테스트 명령
    test_parser = subparsers.add_parser('test', help='템플릿 매칭 테스트')
    test_parser.add_argument('template_id', help='템플릿 ID')
    test_parser.add_argument('docjson_file', help='테스트할 DocJSON 파일')

    # 템플릿 삭제 명령
    delete_parser = subparsers.add_parser('delete', help='템플릿 삭제')
    delete_parser.add_argument('template_id', help='삭제할 템플릿 ID')

    # 통계 명령
    stats_parser = subparsers.add_parser('stats', help='통계 정보')

    args = parser.parse_args()

    cli = TemplateManagerCLI(args.output_dir)

    if args.command == 'create':
        cli.create_template_from_annotation(
            args.annotation_id,
            args.template_name,
            args.description or ""
        )
    elif args.command == 'list':
        cli.list_templates()
    elif args.command == 'show':
        cli.show_template_details(args.template_id)
    elif args.command == 'test':
        cli.test_template_matching(args.template_id, args.docjson_file)
    elif args.command == 'delete':
        cli.delete_template(args.template_id)
    elif args.command == 'stats':
        cli.show_stats()
    else:
        # 대화형 모드
        cli.interactive_menu()


if __name__ == "__main__":
    main()