# -*- coding: utf-8 -*-
# 0-73: 추가사진을 "대표사진으로 지정하기" 즉시반영 기능 추가 (0-52 미구현분)
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

old_a = '''function renderExtraPhotoSlots(){
  const wrap = document.getElementById('editExtraPhotoSlots');
  let html = editExtraPhotos.map((src,i)=>`
    <div class="photo-slot">
      <img src="${src}" class="photo-preview" onclick="event.stopPropagation();reeditExtraPhoto(${i})">
      <span class="photo-slot-badge" onclick="event.stopPropagation();reorderExtraPhoto(${i})" title="누르면 순서를 맨 뒤로 보냅니다">${i+2}</span>
      <span onclick="event.stopPropagation();removeExtraPhoto(${i})" style="position:absolute;top:-7px;right:-7px;background:rgba(0,0,0,.65);color:#fff;border-radius:50%;width:20px;height:20px;display:flex;align-items:center;justify-content:center;font-size:11px;cursor:pointer;box-shadow:0 1px 4px rgba(0,0,0,.35);z-index:2;"><i class="fa-solid fa-xmark"></i></span>
    </div>`).join('');
  if (editExtraPhotos.length < EXTRA_PHOTO_MAX){
    html += `<div class="photo-slot" onclick="document.getElementById('editExtraPhotoInput').click()"><span><i class="fa-solid fa-plus"></i></span></div>`;
  }
  wrap.innerHTML = html;
}'''
new_a = '''function renderExtraPhotoSlots(){
  const wrap = document.getElementById('editExtraPhotoSlots');
  let html = editExtraPhotos.map((src,i)=>`
    <div class="photo-slot">
      <img src="${src}" class="photo-preview" onclick="event.stopPropagation();reeditExtraPhoto(${i})">
      <span class="photo-slot-badge" onclick="event.stopPropagation();reorderExtraPhoto(${i})" title="누르면 순서를 맨 뒤로 보냅니다">${i+2}</span>
      <span onclick="event.stopPropagation();setAsMainPhoto(${i})" style="position:absolute;bottom:-6px;left:-6px;background:rgba(0,0,0,.65);color:#ffd76b;border-radius:50%;width:20px;height:20px;display:flex;align-items:center;justify-content:center;font-size:10px;cursor:pointer;box-shadow:0 1px 4px rgba(0,0,0,.35);z-index:2;" title="대표사진으로 지정"><i class="fa-solid fa-star"></i></span>
      <span onclick="event.stopPropagation();removeExtraPhoto(${i})" style="position:absolute;top:-7px;right:-7px;background:rgba(0,0,0,.65);color:#fff;border-radius:50%;width:20px;height:20px;display:flex;align-items:center;justify-content:center;font-size:11px;cursor:pointer;box-shadow:0 1px 4px rgba(0,0,0,.35);z-index:2;"><i class="fa-solid fa-xmark"></i></span>
    </div>`).join('');
  if (editExtraPhotos.length < EXTRA_PHOTO_MAX){
    html += `<div class="photo-slot" onclick="document.getElementById('editExtraPhotoInput').click()"><span><i class="fa-solid fa-plus"></i></span></div>`;
  }
  wrap.innerHTML = html;
}
// 0-73: 추가사진을 대표사진 자리로 승격(기존 대표사진은 해당 추가사진 자리로 내려감), 위치조절값은 초기화
function setAsMainPhoto(i){
  if (!editExtraPhotos[i]) return;
  const newMain = editExtraPhotos[i];
  const oldMain = editPhotoBase64;
  if (oldMain){ editExtraPhotos[i] = oldMain; } else { editExtraPhotos.splice(i,1); }
  editPhotoBase64 = newMain;
  const preview = document.getElementById('editPhotoPreview');
  preview.src = editPhotoBase64; preview.classList.remove('hidden');
  document.getElementById('editPhotoPlaceholder').classList.add('hidden');
  document.getElementById('editPhotoBadgeMain').classList.remove('hidden');
  editPhotoPosition = {x:50, y:50};
  const posImg = document.getElementById('editPhotoPositionImg');
  posImg.src = editPhotoBase64; posImg.style.objectPosition = '50% 50%';
  document.getElementById('editPhotoPositionWrap').classList.remove('hidden');
  renderExtraPhotoSlots();
}'''
content, ok = apply_edit("A-대표사진지정버튼", old_a, new_a, content)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"완료: {len(edits_applied)}/1 항목 적용됨 -> {edits_applied}")
print(f"파일 크기 변화: {orig_len} -> {len(content)} bytes")
if len(edits_applied) < 1:
    print("!! 적용 실패. 커밋/푸시하지 마세요.")
    sys.exit(1)