# -*- coding: utf-8 -*-
# 0-75: 채팅탭 상단 "오픈채팅 만들기" 칸을 돋보기/설정과 같은 작은 원형 아이콘 버튼으로 통일
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

old_a = '''<div id="openChatCreateEntry" onclick="openGroupCreateModal()" style="flex:1;position:relative;display:flex;align-items:center;gap:8px;border:1px solid var(--border-color);border-radius:20px;padding:8px 14px;background:var(--bg-card);cursor:pointer;">
          <span style="position:relative;display:inline-flex;">
            <i class="fa-solid fa-comment" style="font-size:15px;color:var(--primary);"></i>
            <span style="position:absolute;right:-6px;bottom:-5px;width:13px;height:13px;border-radius:50%;background:var(--primary);color:#fff;font-size:9px;display:flex;align-items:center;justify-content:center;"><i class="fa-solid fa-plus" style="font-size:8px;"></i></span>
          </span>
          <span style="font-size:13px;font-weight:600;">오픈채팅 만들기</span>
        </div>'''
new_a = '''<div id="openChatCreateEntry" onclick="openGroupCreateModal()" title="오픈채팅 만들기" style="flex-shrink:0;width:36px;height:36px;border-radius:50%;border:1px solid var(--border-color);background:var(--bg-card);cursor:pointer;position:relative;display:flex;align-items:center;justify-content:center;">
          <i class="fa-solid fa-comment" style="font-size:15px;color:var(--primary);"></i>
          <span style="position:absolute;right:-2px;bottom:-2px;width:13px;height:13px;border-radius:50%;background:var(--primary);color:#fff;font-size:9px;display:flex;align-items:center;justify-content:center;border:1.5px solid var(--bg-card);"><i class="fa-solid fa-plus" style="font-size:8px;"></i></span>
        </div>
        <div style="flex:1;"></div>'''
content, ok = apply_edit("A-채팅구름아이콘컴팩트화", old_a, new_a, content)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"완료: {len(edits_applied)}/1 항목 적용됨 -> {edits_applied}")
print(f"파일 크기 변화: {orig_len} -> {len(content)} bytes")
if len(edits_applied) < 1:
    print("!! 적용 실패. 커밋/푸시하지 마세요.")
    sys.exit(1)