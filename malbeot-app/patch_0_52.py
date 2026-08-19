#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
0-52 패치: 프로필 사진 대표순번 숫자 배지를 원 밖으로 이동 + 프로필 사진 등록시
채팅과 동일한 편집화면(회전/펜/블러/지우개) 적용 + 하단 카톡식 미리보기 스트립 +
가운데 실제 프로필 반영 미리보기 + "n/전체" 카운터 표시.

실행 위치: 반드시 저장소 루트(C:\\malbeot)에서 실행할 것.
대상 파일: malbeot-app/public/index.html
"""
import pathlib, sys

TARGET = pathlib.Path("malbeot-app/public/index.html")

def main():
    if not TARGET.exists():
        print(f"❌ 파일을 찾을 수 없습니다: {TARGET.resolve()}")
        print("   → 반드시 저장소 루트(C:\\malbeot)에서 실행하세요. (지금 위치: %s)" % pathlib.Path.cwd())
        sys.exit(1)

    text = TARGET.read_text(encoding="utf-8")
    original_len = len(text)
    applied = []

    def replace_once(old, new, label):
        nonlocal text
        count = text.count(old)
        if count != 1:
            print(f"❌ [{label}] old_str가 파일에서 {count}번 발견됨(1번이어야 함). 패치를 중단합니다.")
            sys.exit(1)
        text = text.replace(old, new)
        applied.append(label)

    # ------------------------------------------------------------------
    # 1) 대표사진(메인) 순번 배지를 사진 원(사각) 안쪽에서 바깥쪽으로 이동
    # ------------------------------------------------------------------
    old1 = '''<span id="editPhotoBadgeMain" class="hidden" style="position:absolute;top:2px;left:2px;background:var(--primary);color:#fff;border-radius:50%;width:18px;height:18px;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:800;">1</span>'''
    new1 = '''<span id="editPhotoBadgeMain" class="hidden" style="position:absolute;top:-7px;left:-7px;background:var(--primary);color:#fff;border-radius:50%;width:20px;height:20px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:800;box-shadow:0 1px 4px rgba(0,0,0,.35);border:2px solid var(--bg-card);">1</span>'''
    replace_once(old1, new1, "메인 사진 순번 배지 위치(원 밖으로)")

    # editPhotoPreview 이미지 클릭 시 "새 사진 선택"이 아니라 "기존 사진 재편집"으로 진입하도록 분리
    old1b = '''<img id="editPhotoPreview" class="photo-preview hidden" alt="수정 사진">'''
    new1b = '''<img id="editPhotoPreview" class="photo-preview hidden" alt="수정 사진" onclick="event.stopPropagation();reeditMainPhoto()">'''
    replace_once(old1b, new1b, "메인 사진 클릭시 재편집 진입")

    # ------------------------------------------------------------------
    # 2) 추가사진 순번 배지도 원 밖으로 이동 + 사진 자체 클릭 시 재편집 진입
    # ------------------------------------------------------------------
    old2 = '''  let html = editExtraPhotos.map((src,i)=>`
    <div class="photo-slot" style="flex:0 0 68px;width:68px;height:68px;">
      <img src="${src}" class="photo-preview">
      <span onclick="event.stopPropagation();reorderExtraPhoto(${i})" title="누르면 순서를 맨 뒤로 보냅니다" style="position:absolute;top:2px;left:2px;background:var(--primary);color:#fff;border-radius:50%;width:18px;height:18px;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:800;cursor:pointer;">${i+2}</span>
      <span onclick="event.stopPropagation();removeExtraPhoto(${i})" style="position:absolute;top:2px;right:2px;background:rgba(0,0,0,.55);color:#fff;border-radius:50%;width:18px;height:18px;display:flex;align-items:center;justify-content:center;font-size:10px;cursor:pointer;"><i class="fa-solid fa-xmark"></i></span>
    </div>`).join('');'''
    new2 = '''  let html = editExtraPhotos.map((src,i)=>`
    <div class="photo-slot" style="flex:0 0 68px;width:68px;height:68px;overflow:visible;">
      <img src="${src}" class="photo-preview" onclick="event.stopPropagation();reeditExtraPhoto(${i})">
      <span onclick="event.stopPropagation();reorderExtraPhoto(${i})" title="누르면 순서를 맨 뒤로 보냅니다" style="position:absolute;top:-7px;left:-7px;background:var(--primary);color:#fff;border-radius:50%;width:20px;height:20px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:800;cursor:pointer;box-shadow:0 1px 4px rgba(0,0,0,.35);border:2px solid var(--bg-card);z-index:2;">${i+2}</span>
      <span onclick="event.stopPropagation();removeExtraPhoto(${i})" style="position:absolute;top:-7px;right:-7px;background:rgba(0,0,0,.65);color:#fff;border-radius:50%;width:20px;height:20px;display:flex;align-items:center;justify-content:center;font-size:11px;cursor:pointer;box-shadow:0 1px 4px rgba(0,0,0,.35);z-index:2;"><i class="fa-solid fa-xmark"></i></span>
    </div>`).join('');'''
    replace_once(old2, new2, "추가사진 순번/삭제 배지 위치(원 밖으로) + 재편집 진입")

    # ------------------------------------------------------------------
    # 3) photoPreviewScreen 헤더/버튼에 id 부여 + 프로필 전용 상단바(실시간 미리보기+카운터) 삽입
    # ------------------------------------------------------------------
    old3 = '''  <!-- 0-40: 채팅 사진 전송 전 미리보기 + 편집(회전/블러/펜/지우개) 화면 -->
  <div id="photoPreviewScreen" class="full-screen-overlay" style="background:#000;z-index:300;">
    <div class="chat-header-row" style="background:#000;border:none;">
      <button class="back-btn" style="background:none;border:none;font-size:18px;cursor:pointer;color:#fff;" onclick="closePhotoPreview()"><i class="fa-solid fa-arrow-left"></i></button>
      <div style="margin-left:auto;">
        <button class="btn btn-primary btn-sm" onclick="sendPreviewedPhoto()">전송</button>
      </div>
    </div>
    <div style="flex:1;display:flex;align-items:center;justify-content:center;overflow:hidden;position:relative;">
      <canvas id="photoPreviewCanvas"></canvas>
    </div>
    <div style="display:flex;justify-content:center;padding:14px;">
      <button type="button" style="background:rgba(255,255,255,.15);border:none;color:#fff;border-radius:20px;padding:9px 20px;display:flex;align-items:center;gap:6px;cursor:pointer;font-size:13px;" onclick="enterPhotoEditMode()"><i class="fa-solid fa-pen"></i> 편집</button>
    </div>'''
    new3 = '''  <!-- 0-40: 채팅 사진 전송 전 미리보기 + 편집(회전/블러/펜/지우개) 화면 -->
  <!-- 0-52: 프로필 사진 등록시에도 동일 화면 재사용(mode=profile) -->
  <div id="photoPreviewScreen" class="full-screen-overlay" style="background:#000;z-index:300;">
    <div class="chat-header-row" style="background:#000;border:none;">
      <button class="back-btn" style="background:none;border:none;font-size:18px;cursor:pointer;color:#fff;" onclick="closePhotoPreview()"><i class="fa-solid fa-arrow-left"></i></button>
      <div style="margin-left:auto;">
        <button id="photoPreviewSendBtn" class="btn btn-primary btn-sm" onclick="sendPreviewedPhoto()">전송</button>
      </div>
    </div>
    <div id="profilePreviewMetaBar" class="hidden" style="display:none;align-items:center;justify-content:space-between;padding:6px 16px 10px;">
      <div style="display:flex;align-items:center;gap:9px;min-width:0;">
        <div style="width:38px;height:38px;border-radius:50%;overflow:hidden;background:#333;flex-shrink:0;border:1px solid rgba(255,255,255,.25);"><img id="profilePreviewAvatarImg" src="" style="width:100%;height:100%;object-fit:cover;"></div>
        <div style="min-width:0;">
          <div id="profilePreviewNickname" style="font-size:13px;font-weight:700;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"></div>
          <div style="font-size:10.5px;color:rgba(255,255,255,.55);">실제 프로필에 이렇게 표시돼요</div>
        </div>
      </div>
      <div id="photoPreviewCounter" style="font-size:11px;color:rgba(255,255,255,.85);background:rgba(255,255,255,.14);padding:3px 10px;border-radius:12px;flex-shrink:0;margin-left:8px;"></div>
    </div>
    <div style="flex:1;display:flex;align-items:center;justify-content:center;overflow:hidden;position:relative;">
      <canvas id="photoPreviewCanvas"></canvas>
    </div>
    <div id="profilePreviewThumbStrip" class="hidden" style="display:none;gap:7px;padding:0 14px 10px;overflow-x:auto;"></div>
    <div style="display:flex;justify-content:center;padding:14px;">
      <button type="button" style="background:rgba(255,255,255,.15);border:none;color:#fff;border-radius:20px;padding:9px 20px;display:flex;align-items:center;gap:6px;cursor:pointer;font-size:13px;" onclick="enterPhotoEditMode()"><i class="fa-solid fa-pen"></i> 편집</button>
    </div>'''
    replace_once(old3, new3, "photoPreviewScreen에 프로필 전용 상단바/썸네일스트립 마크업 삽입")

    # ------------------------------------------------------------------
    # 4) openPhotoPreview / closePhotoPreview / sendPreviewedPhoto 로직 확장 + 프로필 전용 함수 추가
    # ------------------------------------------------------------------
    old4 = '''function openPhotoPreview(dataUrl, isGroup, roomId){
  photoPreviewMeta = {isGroup, roomId, currentDataUrl: dataUrl};
  const img = new Image();
  img.onload = ()=>{
    previewCanvas = document.getElementById('photoPreviewCanvas');
    const maxW = Math.min(window.innerWidth, 520), maxH = window.innerHeight * 0.62;
    const scale = Math.min(maxW / img.width, maxH / img.height, 1);
    previewCanvas.width = Math.round(img.width * scale);
    previewCanvas.height = Math.round(img.height * scale);
    previewCtx = previewCanvas.getContext('2d');
    previewCtx.drawImage(img, 0, 0, previewCanvas.width, previewCanvas.height);
  };
  img.src = dataUrl;
  document.getElementById('photoEditBar').classList.add('hidden');
  openFullScreen('photoPreviewScreen');
}
function closePhotoPreview(){
  closeFullScreen('photoPreviewScreen');
  photoPreviewMeta = null;
}
function sendPreviewedPhoto(){
  if (!photoPreviewMeta) return;
  const meta = photoPreviewMeta;
  closeFullScreen('photoPreviewScreen');
  photoPreviewMeta = null;
  const onResult = (res)=>{
    if (!res) { showMiniAlert('사진 전송에 실패했어요. 잠시 후 다시 시도해주세요.', [{label:'확인', primary:true}]); return; }
    if (res.blocked) showMiniAlert(res.message || '부적절한 사진으로 감지되어 전송할 수 없습니다.', [{label:'확인', primary:true}]);
    else if (!res.success) showMiniAlert(res.message || '사진 전송에 실패했어요. 잠시 후 다시 시도해주세요.', [{label:'확인', primary:true}]);
  };
  if (meta.isGroup) socket.emit('group:send_image', {roomId: meta.roomId, image: meta.currentDataUrl}, onResult);
  else socket.emit('chat:send_image', {roomId: meta.roomId, image: meta.currentDataUrl}, onResult);
}'''
    new4 = '''function loadPreviewImageToCanvas(dataUrl){
  const img = new Image();
  img.onload = ()=>{
    previewCanvas = document.getElementById('photoPreviewCanvas');
    const maxW = Math.min(window.innerWidth, 520), maxH = window.innerHeight * 0.62;
    const scale = Math.min(maxW / img.width, maxH / img.height, 1);
    previewCanvas.width = Math.round(img.width * scale);
    previewCanvas.height = Math.round(img.height * scale);
    previewCtx = previewCanvas.getContext('2d');
    previewCtx.drawImage(img, 0, 0, previewCanvas.width, previewCanvas.height);
  };
  img.src = dataUrl;
}
function openPhotoPreview(dataUrl, isGroup, roomId){
  photoPreviewMeta = {mode:'chat', isGroup, roomId, currentDataUrl: dataUrl};
  loadPreviewImageToCanvas(dataUrl);
  document.getElementById('photoEditBar').classList.add('hidden');
  document.getElementById('profilePreviewMetaBar').classList.add('hidden');
  document.getElementById('profilePreviewMetaBar').style.display = 'none';
  document.getElementById('profilePreviewThumbStrip').classList.add('hidden');
  document.getElementById('profilePreviewThumbStrip').style.display = 'none';
  document.getElementById('photoPreviewSendBtn').textContent = '전송';
  openFullScreen('photoPreviewScreen');
}
// 0-52: 프로필 사진(대표/추가) 등록·재편집도 동일한 미리보기+편집 화면을 재사용
// slotIndex: 0=대표사진, 1~4=추가사진(1번째 추가사진=slotIndex 1)
function openProfilePhotoPreview(dataUrl, slotIndex){
  photoPreviewMeta = {mode:'profile', slotIndex, currentDataUrl: dataUrl};
  loadPreviewImageToCanvas(dataUrl);
  document.getElementById('photoEditBar').classList.add('hidden');
  document.getElementById('profilePreviewMetaBar').classList.remove('hidden');
  document.getElementById('profilePreviewMetaBar').style.display = 'flex';
  document.getElementById('profilePreviewThumbStrip').classList.remove('hidden');
  document.getElementById('profilePreviewThumbStrip').style.display = 'flex';
  document.getElementById('photoPreviewSendBtn').textContent = '저장';
  renderProfilePreviewMeta();
  renderProfilePreviewThumbStrip();
  openFullScreen('photoPreviewScreen');
}
function reeditMainPhoto(){
  if (!editPhotoBase64) return;
  openProfilePhotoPreview(editPhotoBase64, 0);
}
function reeditExtraPhoto(i){
  if (!editExtraPhotos[i]) return;
  openProfilePhotoPreview(editExtraPhotos[i], i + 1);
}
function renderProfilePreviewMeta(){
  if (!photoPreviewMeta || photoPreviewMeta.mode !== 'profile') return;
  const avatarImg = document.getElementById('profilePreviewAvatarImg');
  if (avatarImg) avatarImg.src = photoPreviewMeta.currentDataUrl;
  const nickEl = document.getElementById('profilePreviewNickname');
  if (nickEl){
    const nickInput = document.getElementById('editNickname');
    nickEl.textContent = (nickInput && nickInput.value.trim()) || (currentUser && currentUser.nickname) || '내 프로필';
  }
  const totalCount = Math.max(1 + editExtraPhotos.length, photoPreviewMeta.slotIndex + 1);
  const counterEl = document.getElementById('photoPreviewCounter');
  if (counterEl) counterEl.textContent = `${photoPreviewMeta.slotIndex + 1}/${totalCount}`;
}
function renderProfilePreviewThumbStrip(){
  if (!photoPreviewMeta || photoPreviewMeta.mode !== 'profile') return;
  const wrap = document.getElementById('profilePreviewThumbStrip');
  if (!wrap) return;
  const slots = [editPhotoBase64 || null, ...editExtraPhotos];
  const display = slots.map((src,i)=> i===photoPreviewMeta.slotIndex ? photoPreviewMeta.currentDataUrl : src);
  wrap.innerHTML = display.map((src,i)=> src ? `
    <div onclick="switchProfilePreviewSlot(${i})" style="width:52px;height:52px;border-radius:9px;overflow:hidden;flex-shrink:0;cursor:pointer;border:2px solid ${i===photoPreviewMeta.slotIndex?'#fff':'transparent'};position:relative;">
      <img src="${src}" style="width:100%;height:100%;object-fit:cover;display:block;">
      ${i===0?'<span style="position:absolute;bottom:1px;left:1px;background:rgba(0,0,0,.55);color:#fff;font-size:9px;padding:1px 4px;border-radius:4px;">대표</span>':''}
    </div>` : '').join('');
}
function switchProfilePreviewSlot(i){
  if (!photoPreviewMeta || photoPreviewMeta.mode !== 'profile') return;
  if (i === photoPreviewMeta.slotIndex) return;
  const slots = [editPhotoBase64 || null, ...editExtraPhotos];
  const src = slots[i];
  if (!src) return;
  photoPreviewMeta.slotIndex = i;
  photoPreviewMeta.currentDataUrl = src;
  document.getElementById('photoEditBar').classList.add('hidden');
  loadPreviewImageToCanvas(src);
  renderProfilePreviewMeta();
  renderProfilePreviewThumbStrip();
}
function applyProfilePreviewPhoto(slotIndex, dataUrl){
  if (slotIndex === 0){
    editPhotoBase64 = dataUrl;
    const p = document.getElementById('editPhotoPreview');
    p.src = editPhotoBase64; p.classList.remove('hidden');
    document.getElementById('editPhotoPlaceholder').classList.add('hidden');
    document.getElementById('editPhotoBadgeMain').classList.remove('hidden');
    editPhotoPosition = {x:50, y:50};
    const posImg = document.getElementById('editPhotoPositionImg');
    posImg.src = editPhotoBase64; posImg.style.objectPosition = '50% 50%';
    document.getElementById('editPhotoPositionWrap').classList.remove('hidden');
  } else {
    const idx = slotIndex - 1;
    if (idx < editExtraPhotos.length) editExtraPhotos[idx] = dataUrl;
    else if (editExtraPhotos.length < EXTRA_PHOTO_MAX) editExtraPhotos.push(dataUrl);
    renderExtraPhotoSlots();
  }
}
function closePhotoPreview(){
  closeFullScreen('photoPreviewScreen');
  photoPreviewMeta = null;
}
function sendPreviewedPhoto(){
  if (!photoPreviewMeta) return;
  const meta = photoPreviewMeta;
  if (meta.mode === 'profile'){
    applyProfilePreviewPhoto(meta.slotIndex, meta.currentDataUrl);
    closeFullScreen('photoPreviewScreen');
    photoPreviewMeta = null;
    return;
  }
  closeFullScreen('photoPreviewScreen');
  photoPreviewMeta = null;
  const onResult = (res)=>{
    if (!res) { showMiniAlert('사진 전송에 실패했어요. 잠시 후 다시 시도해주세요.', [{label:'확인', primary:true}]); return; }
    if (res.blocked) showMiniAlert(res.message || '부적절한 사진으로 감지되어 전송할 수 없습니다.', [{label:'확인', primary:true}]);
    else if (!res.success) showMiniAlert(res.message || '사진 전송에 실패했어요. 잠시 후 다시 시도해주세요.', [{label:'확인', primary:true}]);
  };
  if (meta.isGroup) socket.emit('group:send_image', {roomId: meta.roomId, image: meta.currentDataUrl}, onResult);
  else socket.emit('chat:send_image', {roomId: meta.roomId, image: meta.currentDataUrl}, onResult);
}'''
    replace_once(old4, new4, "openPhotoPreview/closePhotoPreview/sendPreviewedPhoto 로직 확장 + 프로필 전용 함수 신설")

    # ------------------------------------------------------------------
    # 5) savePhotoEdit(펜/블러 편집화면 내부 저장)에서도 프로필 실시간 미리보기 갱신
    # ------------------------------------------------------------------
    old5 = '''function savePhotoEdit(){
  if (!peCanvas || !photoPreviewMeta) return;
  photoPreviewMeta.currentDataUrl = peCanvas.toDataURL('image/jpeg', 0.85);
  document.getElementById('photoEditBar').classList.add('hidden');
  const img = new Image();
  img.onload = ()=>{
    previewCtx.clearRect(0, 0, previewCanvas.width, previewCanvas.height);
    previewCtx.drawImage(img, 0, 0, previewCanvas.width, previewCanvas.height);
  };
  img.src = photoPreviewMeta.currentDataUrl;
}'''
    new5 = '''function savePhotoEdit(){
  if (!peCanvas || !photoPreviewMeta) return;
  photoPreviewMeta.currentDataUrl = peCanvas.toDataURL('image/jpeg', 0.85);
  document.getElementById('photoEditBar').classList.add('hidden');
  const img = new Image();
  img.onload = ()=>{
    previewCtx.clearRect(0, 0, previewCanvas.width, previewCanvas.height);
    previewCtx.drawImage(img, 0, 0, previewCanvas.width, previewCanvas.height);
  };
  img.src = photoPreviewMeta.currentDataUrl;
  if (photoPreviewMeta.mode === 'profile'){
    renderProfilePreviewMeta();
    renderProfilePreviewThumbStrip();
  }
}'''
    replace_once(old5, new5, "savePhotoEdit에서 프로필 실시간 미리보기/썸네일스트립 갱신")

    # ------------------------------------------------------------------
    # 6) 대표사진 업로드 핸들러: 압축 후 바로 반영하지 않고 편집화면으로 진입
    # ------------------------------------------------------------------
    old6 = '''async function handleEditPhotoUpload(e){
  const file=e.target.files[0]; if(!file) return;
  editPhotoBase64 = await compressImageFile(file);
  const p=document.getElementById('editPhotoPreview'); p.src=editPhotoBase64; p.classList.remove('hidden'); document.getElementById('editPhotoPlaceholder').classList.add('hidden'); document.getElementById('editPhotoBadgeMain').classList.remove('hidden');
  editPhotoPosition = {x:50, y:50};
  const posImg = document.getElementById('editPhotoPositionImg');
  posImg.src = editPhotoBase64; posImg.style.objectPosition = '50% 50%';
  document.getElementById('editPhotoPositionWrap').classList.remove('hidden');
}'''
    new6 = '''async function handleEditPhotoUpload(e){
  const file=e.target.files[0]; if(!file) return;
  let image;
  try { image = await compressImageFile(file); }
  catch(err){
    console.error('사진 처리 실패:', err);
    showMiniAlert('이 사진은 불러올 수 없어요. 다른 사진으로 다시 시도해주세요.', [{label:'확인', primary:true}]);
    e.target.value = '';
    return;
  }
  e.target.value = '';
  openProfilePhotoPreview(image, 0);
}'''
    replace_once(old6, new6, "대표사진 업로드시 편집화면 진입(handleEditPhotoUpload)")

    # ------------------------------------------------------------------
    # 7) 추가사진 업로드 핸들러: 압축 후 바로 반영하지 않고 편집화면으로 진입
    # ------------------------------------------------------------------
    old7 = '''async function handleEditExtraPhotoUpload(e){
  const file = e.target.files[0]; if (!file) return;
  if (editExtraPhotos.length >= EXTRA_PHOTO_MAX) { e.target.value=''; return; }
  const b64 = await compressImageFile(file);
  editExtraPhotos.push(b64);
  renderExtraPhotoSlots();
  e.target.value = '';
}'''
    new7 = '''async function handleEditExtraPhotoUpload(e){
  const file = e.target.files[0]; if (!file) return;
  if (editExtraPhotos.length >= EXTRA_PHOTO_MAX) { e.target.value=''; return; }
  let image;
  try { image = await compressImageFile(file); }
  catch(err){
    console.error('사진 처리 실패:', err);
    showMiniAlert('이 사진은 불러올 수 없어요. 다른 사진으로 다시 시도해주세요.', [{label:'확인', primary:true}]);
    e.target.value = '';
    return;
  }
  const nextSlotIndex = editExtraPhotos.length + 1;
  e.target.value = '';
  openProfilePhotoPreview(image, nextSlotIndex);
}'''
    replace_once(old7, new7, "추가사진 업로드시 편집화면 진입(handleEditExtraPhotoUpload)")

    TARGET.write_text(text, encoding="utf-8")
    print(f"✅ 0-52 패치 완료: {len(applied)}개 항목 적용됨 (파일 크기 {original_len} → {len(text)} bytes)")
    for a in applied:
        print(f"   - {a}")

if __name__ == "__main__":
    main()