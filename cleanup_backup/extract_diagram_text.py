#!/usr/bin/env python3
"""
다이어그램 내부 텍스트 추출
"""

import zipfile
import xml.etree.ElementTree as ET
import re

def extract_diagram_texts(docx_path):
    """DOCX의 다이어그램에서 텍스트 추출"""
    print("🎨 다이어그램 텍스트 추출")
    print("=" * 60)

    with zipfile.ZipFile(docx_path, 'r') as docx:
        # document.xml에서 drawing 요소들 찾기
        if 'word/document.xml' in docx.namelist():
            document_xml = docx.read('word/document.xml')
            root = ET.fromstring(document_xml)

            # 네임스페이스 정의
            namespaces = {
                'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
                'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
                'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
                'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture',
                'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
                'wpg': 'http://schemas.microsoft.com/office/word/2010/wordprocessingGroup',
                'wps': 'http://schemas.microsoft.com/office/word/2010/wordprocessingShape'
            }

            # drawing 요소들 찾기
            drawings = root.findall('.//w:drawing', namespaces)
            print(f"📊 발견된 drawing 요소: {len(drawings)}개\n")

            diagram_texts = []

            for i, drawing in enumerate(drawings):
                print(f"🔍 Drawing {i+1} 분석:")
                print("-" * 30)

                # 모든 텍스트 요소 찾기
                texts_found = []

                # 다양한 텍스트 위치에서 검색
                text_paths = [
                    './/a:t',  # DrawingML 텍스트
                    './/w:t',  # Word 텍스트
                    './/wps:txBody//a:t',  # Shape 텍스트 바디
                    './/a:txBody//a:t',    # 텍스트 바디
                ]

                for path in text_paths:
                    text_elements = drawing.findall(path, namespaces)
                    for text_elem in text_elements:
                        if text_elem.text and text_elem.text.strip():
                            texts_found.append(text_elem.text.strip())

                if texts_found:
                    print("   📝 추출된 텍스트:")
                    for text in texts_found:
                        print(f"      • {text}")
                    diagram_texts.extend(texts_found)
                else:
                    print("   ❌ 텍스트를 찾을 수 없음")

                # shape 요소들 확인
                shapes = drawing.findall('.//wps:wsp', namespaces)
                if shapes:
                    print(f"   🔷 Shape 요소: {len(shapes)}개")

                print()

            # 프로세스 흐름 패턴 분석
            print("🔄 프로세스 흐름 분석")
            print("-" * 30)

            all_diagram_text = ' '.join(diagram_texts)
            print(f"전체 다이어그램 텍스트: {all_diagram_text}")

            # 프로세스 키워드 검색
            process_keywords = [
                "노열확보", "통기성확보", "풍량확보", "조업도상승", "조업도 상승",
                "증광", "증산", "연화융착대형성", "연화융착대 형성"
            ]

            found_processes = []
            for keyword in process_keywords:
                if keyword in all_diagram_text:
                    found_processes.append(keyword)

            if found_processes:
                print("\n✅ 다이어그램에서 발견된 프로세스:")
                for process in found_processes:
                    print(f"   • {process}")

            # 순서 패턴 검색
            sequence_patterns = [
                r'(\d+)[.)\s]*([^→\d]+?)(?:\s*→\s*(\d+)[.)\s]*([^→\d]+?))*',
                r'①([^②③④⑤]+)②([^③④⑤]+)③?([^④⑤]+)?④?([^⑤]+)?⑤?(.+)?',
                r'([^→]+)\s*→\s*([^→]+)(?:\s*→\s*([^→]+))*'
            ]

            for pattern in sequence_patterns:
                matches = re.finditer(pattern, all_diagram_text)
                for match in matches:
                    if match.groups():
                        steps = [step.strip() for step in match.groups() if step and step.strip()]
                        if len(steps) > 1:
                            print(f"\n🎯 발견된 프로세스 순서: {' → '.join(steps)}")

    return diagram_texts

if __name__ == "__main__":
    docx_path = "../기술기준_예시.docx"
    extract_diagram_texts(docx_path)