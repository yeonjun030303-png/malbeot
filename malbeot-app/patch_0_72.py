# -*- coding: utf-8 -*-
# 0-72: 사진 전체화면 뷰어 - PC 마우스휠 확대/축소, 좌우 화살표 버튼(+키보드 방향키) 넘기기 추가
import os, sys

path = os.path.join(os.getcwd(), "public", "index.html")
if not os.path.exists(path):
    print("!! public/index.html 을 못 찾았습니다. C:\\malbeot\\malbeot-app 에서 실행해주세요.")
    sys.exit(1)

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

orig_len = len(content)
edits_applied = []

def apply_edit(name, old, new, content):
    cnt = content.count(old)
    if cnt != 1:
        print(f"!! [{name}] 매칭 개수가 1이 아닙니다(찾은 개수: {cnt}). 패치를 중단합니다.")
        return content, False
    content = content.replace(old, new)
    edits_applied.append(name)
    return content, True

old_a = '<img id="photoViewerImg" src="" ontouchstart="pvTouchStart(event)" ontouchend="pvTouchEnd(event)" onclick="pvHandleTap(event)" style="max-width:100%;max-height:100%;object-fit:contain;touch-action:pan-y;">'
new_a = '''<div id="photoViewerPrevBtn" onclick="photoViewerPrev()" style="position:absolute;left:14px;top:50%;transform:translateY(-50%);z-index:2;color:#fff;font-size:18px;width:38px;height:38px;display:none;align-items:center;justify-content:center;background:rgba(0,0,0,.35);border-radius:50%;cursor:pointer;"><i class="fa-solid fa-chevron-left"></i></div>
    <div id="photoViewerNextBtn" onclick="photoViewerNext()" style="position:absolute;right:14px;top:50%;transform:translateY(-50%);z-index:2;color:#fff;font-size:18px;width:38px;height:38px;display:none;align-items:center;justify-content:center;background:rgba(0,0,0,.35);border-radius:50%;cursor:pointer;"><i class="fa-solid fa-chevron-right"></i></div>
    <img id="photoViewerImg" src="" ontouchstart="pvTouchStart(event)" ontouchend="pvTouchEnd(event)" onclick="pvHandleTap(event)" onwheel="pvHandleWheel(event)" style="max-width:100%;max-height:100%;object-fit:contain;touch-action:pan-y;transition:transform .08s ease-out;">'''
content, ok = apply_edit("A-화살표버튼+휠핸들러HTML", old_a, new_a, content)

old_b = '''function renderPhotoViewer(){
  if (!photoViewerState) return;
  document.getElementById('photoViewerImg').src = photoViewerState.images[photoViewerState.index];
  document.getElementById('photoViewerCounter').textContent = `${photoViewerState.index + 1}/${photoViewerState.images.length}`;
}'''
new_b = '''function renderPhotoViewer(){
  if (!photoViewerState) return;
  document.getElementById('photoViewerImg').src = photoViewerState.images[photoViewerState.index];
  document.getElementById('photoViewerCounter').textContent = `${photoViewerState.index + 1}/${photoViewerState.images.length}`;
  pvResetZoom();
  const isTouchDevice = window.matchMedia && window.matchMedia('(pointer: coarse)').matches;
  const prevBtn = document.getElementById('photoViewerPrevBtn');
  const nextBtn = document.getElementById('photoViewerNextBtn');
  const showArrows = !isTouchDevice && photoViewerState.images.length > 1;
  if (prevBtn) prevBtn.style.display = (showArrows && photoViewerState.index > 0) ? 'flex' : 'none';
  if (nextBtn) nextBtn.style.display = (showArrows && photoViewerState.index < photoViewerState.images.length - 1) ? 'flex' : 'none';
}
let pvZoom = 1;
function pvResetZoom(){
  pvZoom = 1;
  const img = document.getElementById('photoViewerImg');
  if (img) img.style.transform = 'scale(1)';
}
function pvHandleWheel(e){
  e.preventDefault();
  const delta = e.deltaY < 0 ? 0.15 : -0.15;
  pvZoom = Math.min(4, Math.max(1, pvZoom + delta));
  const img = document.getElementById('photoViewerImg');
  if (img) img.style.transform = `scale(${pvZoom})`;
}
function pvHandleKeydown(e){
  if (!photoViewerState) return;
  if (e.key === 'ArrowLeft') photoViewerPrev();
  else if (e.key === 'ArrowRight') photoViewerNext();
  else if (e.key === 'Escape') closePhotoViewer();
}
document.addEventListener('keydown', pvHandleKeydown);'''
content, ok = apply_edit("B-렌더함수확장+줌+키보드", old_b, new_b, content)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"완료: {len(edits_applied)}/2 항목 적용됨 -> {edits_applied}")
print(f"파일 크기 변화: {orig_len} -> {len(content)} bytes")
if len(edits_applied) < 2:
    print("!! 일부 항목이 적용되지 않았습니다. 커밋/푸시하지 마세요.")
    sys.exit(1)