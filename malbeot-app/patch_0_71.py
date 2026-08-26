# -*- coding: utf-8 -*-
# 0-71: photoViewerOverlay 인라인 display:none 제거 (풀스크린 사진뷰어 영구 안 열리던 버그 근본수정)
# - 0-70 직후 검은화면 버그 수정 패치가 style 속성에 display:none을 인라인으로 박아넣었는데,
#   인라인 style은 CSS class(.modal-overlay.active{display:flex})보다 우선순위가 높아서
#   openModal()이 'active' 클래스를 넣어도 인라인 display:none이 계속 이겨 영원히 안 열리던 것.
#   기본 상태는 CSS(.modal-overlay{display:none;})가 이미 처리하므로 인라인 display:none만 제거하면 됨.
import os, sys

path = os.path.join(os.getcwd(), "public", "index.html")
if not os.path.exists(path):
    print("!! public/index.html 을 못 찾았습니다. C:\\malbeot\\malbeot-app 에서 실행해주세요.")
    sys.exit(1)

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

orig_len = len(content)

old = 'id="photoViewerOverlay" class="modal-overlay" style="position:fixed;inset:0;background:#000;z-index:10000;display:none;align-items:center;justify-content:center;overflow:hidden;"'
new = 'id="photoViewerOverlay" class="modal-overlay" style="position:fixed;inset:0;background:#000;z-index:10000;align-items:center;justify-content:center;overflow:hidden;"'

cnt = content.count(old)
if cnt != 1:
    print(f"!! [photoViewerOverlay] 매칭 개수가 1이 아닙니다(찾은 개수: {cnt}). 패치를 중단합니다. 이미 반영됐거나 코드가 달라졌을 수 있습니다.")
    sys.exit(1)

content = content.replace(old, new)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("완료: photoViewerOverlay 인라인 display:none 제거")
print(f"파일 크기 변화: {orig_len} -> {len(content)} bytes")
