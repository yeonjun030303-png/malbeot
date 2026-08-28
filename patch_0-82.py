# -*- coding: utf-8 -*-
"""
0-82 패치: terms.html의 사업자정보 플레이스홀더 3곳을 실제 정보로 채워넣음
(홈택스 영문 사업자등록증명 기준)

사용법 (PowerShell, C:\\malbeot 에서):
  python3 patch_0-82.py
"""
import pathlib

FILE = pathlib.Path("malbeot-app/public/terms.html")
html = FILE.read_text(encoding="utf-8")

old = """        <tr><th>사업자명</th><td>[사업자등록증상 상호명 기재]</td></tr>
        <tr><th>대표자</th><td>[대표자명 기재]</td></tr>
        <tr><th>사업자등록번호</th><td>[사업자등록번호 기재]</td></tr>"""
assert html.count(old) == 1, "old 매칭 실패 - terms.html이 0-80 상태 그대로인지 확인 필요"
new = """        <tr><th>사업자명</th><td>씨앤에스 스튜디오(C&S)</td></tr>
        <tr><th>대표자</th><td>한경은</td></tr>
        <tr><th>사업자등록번호</th><td>246-01-04142</td></tr>"""
html = html.replace(old, new)

FILE.write_text(html, encoding="utf-8")
print("0-82 패치 완료 (사업자정보 반영됨)")