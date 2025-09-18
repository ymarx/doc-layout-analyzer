#!/usr/bin/env python3
"""
DOCX 파일의 모든 영역을 깊이 검사
헤더, 푸터, 텍스트박스 등에서 누락된 정보 찾기
"""

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import re

def inspect_docx_deeply(file_path):
    """DOCX의 모든 XML 파일 검사"""
    print(f"🔍 {file_path} 전체 검사")
    print("=" * 60)

    # 찾고자 하는 패턴들
    patterns = {
        'document_number': re.compile(r'TP-\d{3}-\d{3}-\d{3}'),
        'date': re.compile(r"(?:'?\d{2}[.\-/]\d{1,2}[.\-/]\d{1,2})|(?:\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2})"),
        'revision': re.compile(r'Rev[\.\s]*:\s*\d+'),
        'author': re.compile(r'진\s*다\s*훈'),
        'effective': re.compile(r'시행일'),
    }

    found_items = {}

    with zipfile.ZipFile(file_path, 'r') as docx:
        # 모든 XML 파일 나열
        xml_files = [f for f in docx.namelist() if f.endswith('.xml') or f.endswith('.rels')]

        print(f"📦 총 {len(xml_files)}개의 XML 파일 발견\n")

        for xml_file in xml_files:
            try:
                # XML 읽기
                xml_content = docx.read(xml_file)
                xml_text = xml_content.decode('utf-8', errors='ignore')

                # 패턴 검색
                matches = {}
                for name, pattern in patterns.items():
                    if found := pattern.findall(xml_text):
                        matches[name] = found

                if matches:
                    print(f"📄 {xml_file}:")
                    for name, values in matches.items():
                        print(f"   ✅ {name}: {values}")
                        if name not in found_items:
                            found_items[name] = []
                        found_items[name].extend(values)

                    # 특정 파일에 대한 상세 분석
                    if 'header' in xml_file.lower() or 'footer' in xml_file.lower():
                        print(f"   📋 헤더/푸터 파일 - 상세 분석:")
                        # XML 파싱
                        try:
                            root = ET.fromstring(xml_content)
                            # 모든 텍스트 요소 추출
                            texts = []
                            for elem in root.iter():
                                if elem.text:
                                    texts.append(elem.text.strip())

                            if texts:
                                print(f"      텍스트 내용: {' | '.join(texts[:5])}")
                        except:
                            pass

            except Exception as e:
                if 'header' in xml_file or 'footer' in xml_file or 'document' in xml_file:
                    print(f"⚠️ {xml_file} 읽기 실패: {e}")

    print("\n" + "=" * 60)
    print("📊 전체 검색 결과 요약:")
    print("-" * 40)

    for name, values in found_items.items():
        unique_values = list(set(values))
        print(f"✅ {name}: {unique_values}")

    # 특정 패턴이 없다면 추가 검색
    if 'document_number' not in found_items:
        print("\n⚠️ 문서번호(TP-XXX-XXX-XXX)를 찾지 못했습니다.")
        print("   → 헤더/푸터 또는 이미지에 포함되어 있을 가능성")

    if 'revision' not in found_items:
        print("\n⚠️ 개정번호(Rev.)를 찾지 못했습니다.")
        print("   → 다른 형식으로 표시되었을 가능성")

    # document.xml의 전체 텍스트 확인
    print("\n📝 document.xml 전체 텍스트 (처음 500자):")
    print("-" * 40)

    with zipfile.ZipFile(file_path, 'r') as docx:
        if 'word/document.xml' in docx.namelist():
            doc_xml = docx.read('word/document.xml')
            root = ET.fromstring(doc_xml)

            # 네임스페이스
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

            # 모든 텍스트 수집
            all_texts = []
            for t in root.findall('.//w:t', ns):
                if t.text:
                    all_texts.append(t.text)

            full_text = ''.join(all_texts)
            print(full_text[:500])

            # 패턴 재검색
            print("\n🔍 document.xml에서 패턴 재검색:")
            for name, pattern in patterns.items():
                if found := pattern.findall(full_text):
                    print(f"   {name}: {found}")

if __name__ == "__main__":
    docx_path = "../기술기준_예시.docx"
    inspect_docx_deeply(docx_path)