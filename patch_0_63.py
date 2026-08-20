import os

CANDIDATES = [
    os.path.join("malbeot-app", "public", "index.html"),
    os.path.join("public", "index.html"),
]
TARGET = next((p for p in CANDIDATES if os.path.exists(p)), None)

if not TARGET:
    print("❌ index.html을 찾을 수 없습니다.")
    print("현재 위치:", os.getcwd())
    print("→ C:\\malbeot 에서 실행 중인지 확인해주세요.")
    raise SystemExit(1)

with open(TARGET, "r", encoding="utf-8") as f:
    content = f.read()

edits = []

edits.append((
'''.photo-preview{width:100%;height:100%;object-fit:cover;}''',
'''.photo-preview{width:100%;height:100%;object-fit:cover;}
/* 0-63: 대표사진/추가사진 슬롯을 원형 하나로 통일 + 크기 확대 */
.unified-photo-row{flex-wrap:wrap;}
.unified-photo-row .photo-slot{flex:0 0 80px;width:80px;height:80px;border-radius:50%;overflow:visible;}
.unified-photo-row .photo-slot .photo-preview,.unified-photo-row .photo-slot img.photo-preview{border-radius:50%;overflow:hidden;}
.photo-slot-badge{position:absolute;top:-7px;left:-7px;background:var(--primary);color:#fff;border-radius:50%;width:22px;height:22px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:800;cursor:pointer;box-shadow:0 1px 4px rgba(0,0,0,.35);border:2px solid var(--bg-card);z-index:2;}'''
))

edits.append((
'''          <div class="form-group">
            <label>내 대표 사진 <span style="font-weight:400;color:var(--text-muted);">(클릭 후 드래그로 노출 위치 조절)</span></label>
            <div class="photo-slots"><div class="photo-slot" onclick="triggerEditPhotoInput()">
              <img id="editPhotoPreview" class="photo-preview hidden" alt="수정 사진" onclick="event.stopPropagation();reeditMainPhoto()">
              <span id="editPhotoPlaceholder"><i class="fa-solid fa-plus"></i></span>
              <span id="editPhotoBadgeMain" class="hidden" style="position:absolute;top:-7px;left:-7px;background:var(--primary);color:#fff;border-radius:50%;width:20px;height:20px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:800;box-shadow:0 1px 4px rgba(0,0,0,.35);border:2px solid var(--bg-card);">1</span>
            </div></div>
            <input type="file" id="editPhotoInput" accept="image/*" class="hidden" onchange="handleEditPhotoUpload(event)">
            <div id="editPhotoPositionWrap" class="hidden">
              <div class="photo-position-box" id="editPhotoPositionBox"><img id="editPhotoPositionImg" src="" alt=""></div>
              <div class="photo-position-hint">사진을 드래그해서 보여줄 위치를 맞춰주세요</div>
            </div>
          </div>
          <div class="form-group">
            <label>추가 사진 <span style="font-weight:400;color:var(--text-muted);">(최대 4장, 사진마다 좋아요를 받을 수 있어요)</span></label>
            <div class="photo-slots" id="editExtraPhotoSlots" style="flex-wrap:wrap;"></div>
            <input type="file" id="editExtraPhotoInput" accept="image/*" class="hidden" onchange="handleEditExtraPhotoUpload(event)">
          </div>''',
'''          <div class="form-group">
            <label>내 프로필 사진 <span style="font-weight:400;color:var(--text-muted);">(1번이 대표사진, 클릭 후 드래그로 노출 위치 조절 · 최대 5장, 사진마다 좋아요를 받을 수 있어요)</span></label>
            <div class="photo-slots unified-photo-row">
              <div class="photo-slot" onclick="triggerEditPhotoInput()">
                <img id="editPhotoPreview" class="photo-preview hidden" alt="수정 사진" onclick="event.stopPropagation();reeditMainPhoto()">
                <span id="editPhotoPlaceholder"><i class="fa-solid fa-plus"></i></span>
                <span id="editPhotoBadgeMain" class="hidden photo-slot-badge">1</span>
              </div>
              <div id="editExtraPhotoSlots" style="display:contents;"></div>
            </div>
            <input type="file" id="editPhotoInput" accept="image/*" class="hidden" onchange="handleEditPhotoUpload(event)">
            <input type="file" id="editExtraPhotoInput" accept="image/*" class="hidden" onchange="handleEditExtraPhotoUpload(event)">
            <div id="editPhotoPositionWrap" class="hidden">
              <div class="photo-position-box" id="editPhotoPositionBox"><img id="editPhotoPositionImg" src="" alt=""></div>
              <div class="photo-position-hint">사진을 드래그해서 보여줄 위치를 맞춰주세요</div>
            </div>
          </div>'''
))

edits.append((
'''  if (dx > THRESHOLD && Math.abs(dy) < 60) closeTopmostScreen();
  }, { passive: true });
})();''',
'''  if (dx > THRESHOLD && Math.abs(dy) < 60) closeTopmostScreen();
  }, { passive: true });
})();

/* 0-63: 프로필 상세 화면 사진 영역을 손가락으로 좌우로 밀어서 다음/이전 사진으로 넘기기.
   폰 갤러리처럼 왼쪽으로 밀면 다음 사진, 오른쪽으로 밀면 이전 사진이 나오게 함. */
(function initProfilePhotoSwipe(){
  const SWIPE_THRESHOLD = 40;
  let sx = 0, sy = 0, tracking = false;
  document.addEventListener('touchstart', (e)=>{
    const wrap = e.target.closest && e.target.closest('.profile-photo-wrap');
    if (!wrap) { tracking = false; return; }
    if (!e.touches || !e.touches.length) return;
    tracking = true;
    sx = e.touches[0].clientX; sy = e.touches[0].clientY;
  }, { passive: true });
  document.addEventListener('touchend', (e)=>{
    if (!tracking) return;
    tracking = false;
    const t = e.changedTouches && e.changedTouches[0];
    if (!t || !currentProfileUserCache) return;
    const dx = t.clientX - sx, dy = t.clientY - sy;
    if (Math.abs(dx) < SWIPE_THRESHOLD || Math.abs(dy) > 60) return;
    const photos = currentProfileUserCache.photos && currentProfileUserCache.photos.length ? currentProfileUserCache.photos : [null];
    if (dx < 0 && profilePhotoIndex < photos.length - 1) changeProfilePhoto(profilePhotoIndex + 1); // 왼쪽으로 밀면 다음 사진
    else if (dx > 0 && profilePhotoIndex > 0) changeProfilePhoto(profilePhotoIndex - 1); // 오른쪽으로 밀면 이전 사진
  }, { passive: true });
})();'''
))

edits.append((
'''function renderExtraPhotoSlots(){
  const wrap = document.getElementById('editExtraPhotoSlots');
  let html = editExtraPhotos.map((src,i)=>`
    <div class="photo-slot" style="flex:0 0 68px;width:68px;height:68px;overflow:visible;">
      <img src="${src}" class="photo-preview" onclick="event.stopPropagation();reeditExtraPhoto(${i})">
      <span onclick="event.stopPropagation();reorderExtraPhoto(${i})" title="누르면 순서를 맨 뒤로 보냅니다" style="position:absolute;top:-7px;left:-7px;background:var(--primary);color:#fff;border-radius:50%;width:20px;height:20px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:800;cursor:pointer;box-shadow:0 1px 4px rgba(0,0,0,.35);border:2px solid var(--bg-card);z-index:2;">${i+2}</span>
      <span onclick="event.stopPropagation();removeExtraPhoto(${i})" style="position:absolute;top:-7px;right:-7px;background:rgba(0,0,0,.65);color:#fff;border-radius:50%;width:20px;height:20px;display:flex;align-items:center;justify-content:center;font-size:11px;cursor:pointer;box-shadow:0 1px 4px rgba(0,0,0,.35);z-index:2;"><i class="fa-solid fa-xmark"></i></span>
    </div>`).join('');
  if (editExtraPhotos.length < EXTRA_PHOTO_MAX){
    html += `<div class="photo-slot" style="flex:0 0 68px;width:68px;height:68px;" onclick="document.getElementById('editExtraPhotoInput').click()"><span><i class="fa-solid fa-plus"></i></span></div>`;
  }
  wrap.innerHTML = html;
}''',
'''function renderExtraPhotoSlots(){
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
))

ok = True
for i, (old, new) in enumerate(edits, 1):
    count = content.count(old)
    if count != 1:
        print(f"❌ {i}번째 수정 실패: 원본 텍스트가 파일에서 {count}번 발견됨(1번이어야 함). 이미 패치가 적용됐거나 파일이 변경됐을 수 있어요.")
        ok = False
    else:
        content = content.replace(old, new)

if not ok:
    print("→ 아무 것도 저장하지 않았습니다. 위 메시지 그대로 알려주세요.")
    raise SystemExit(1)

with open(TARGET, "w", encoding="utf-8") as f:
    f.write(content)

print(f"✅ 0-63 완료: {TARGET} 에 사진 슬롯 통합 UI + 프로필 스와이프 넘기기 적용")