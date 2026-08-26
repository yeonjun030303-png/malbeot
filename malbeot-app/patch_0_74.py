# -*- coding: utf-8 -*-
# 0-74: 프로필 사진 위치조절 드래그 Y축 반전 + 대표사진(1번) 슬롯에 별표 표시 + 성별 표기에서 색상 괄호 제거
import os, sys

path = os.path.join(os.getcwd(), "public", "index.html")
if not os.path.exists(path):
    print("!! public/index.html 을 못 찾았습니다. C:\\malbeot\\malbeot-app 에서 실행해주세요.")
    sys.exit(1)

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

orig_len = len(content)
edits_applied = []

def apply_edit(name, old, new, content, expect=1):
    cnt = content.count(old)
    if cnt != expect:
        print(f"!! [{name}] 매칭 개수가 예상({expect})과 다릅니다(찾은 개수: {cnt}). 패치를 중단합니다.")
        return content, False
    content = content.replace(old, new)
    edits_applied.append(name)
    return content, True

old_a = "    let y = ((clientY-rect.top)/rect.height)*100;"
new_a = "    let y = 100 - ((clientY-rect.top)/rect.height)*100;"
content, ok = apply_edit("A-드래그Y축반전", old_a, new_a, content)

old_b = '<span id="editPhotoBadgeMain" class="hidden photo-slot-badge">1</span>'
new_b = '<span id="editPhotoBadgeMain" class="hidden photo-slot-badge" style="color:#ffd76b;"><i class="fa-solid fa-star"></i></span>'
content, ok = apply_edit("B-대표사진별표배지", old_b, new_b, content)

old_c = '<option value="female">여성 (핑크)</option><option value="male">남성 (파란색)</option>'
new_c = '<option value="female">여성</option><option value="male">남성</option>'
content, ok = apply_edit("C-성별표기색상괄호제거", old_c, new_c, content, expect=2)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"완료: {len(edits_applied)}/3 항목 적용됨 -> {edits_applied}")
print(f"파일 크기 변화: {orig_len} -> {len(content)} bytes")
if len(edits_applied) < 3:
    print("!! 일부 항목이 적용되지 않았습니다. 절대 부분반영된 채로 커밋/푸시하지 마세요.")
    sys.exit(1)