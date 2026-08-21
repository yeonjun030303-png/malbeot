# -*- coding: utf-8 -*-
# 0-70: 사진 전체화면 뷰어 (프로필/1:1채팅/단체채팅/커뮤니티 공용)
# - 하단 "n/N" 카운터, 좌/우 스와이프 넘기기(마지막장 이상 못 넘어감), 좌측 나가기버튼
# - 상대 프로필 사진 뷰어에서만 더블탭시 하트 좋아요 토글 + 화면 중앙 하트 팝업 페이드 연출
import os, sys

path = os.path.join(os.getcwd(), "public", "index.html")
if not os.path.exists(path):
    print("!! public/index.html 을 찾을 수 없습니다. C:\\malbeot\\malbeot-app 위치에서 실행했는지 확인하세요.")
    sys.exit(1)

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

orig_len = len(content)
edits_applied = []

def apply_edit(name, old, new, content):
    cnt = content.count(old)
    if cnt != 1:
        print(f"!! [{name}] 패치 대상 문자열을 정확히 1곳에서 찾지 못했습니다(발견 {cnt}회). 코드가 이미 변경되었을 수 있습니다. 건너뜁니다.")
        return content, False
    content = content.replace(old, new)
    edits_applied.append(name)
    return content, True

# EDIT A: 뷰어 오버레이 HTML 추가
old_a = '''  <div id="imageLightboxOverlay" class="modal-overlay" style="position:fixed;inset:0;background:rgba(0,0,0,.92);z-index:9999;" onclick="closeImageLightbox()">
    <img id="imageLightboxImg" src="" style="max-width:94%;max-height:88%;object-fit:contain;">
  </div>'''
new_a = old_a + '''

  <div id="photoViewerOverlay" class="modal-overlay" style="position:fixed;inset:0;background:#000;z-index:10000;display:flex;align-items:center;justify-content:center;overflow:hidden;">
    <div onclick="closePhotoViewer()" style="position:absolute;top:16px;left:16px;z-index:2;color:#fff;font-size:22px;width:38px;height:38px;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.35);border-radius:50%;cursor:pointer;"><i class="fa-solid fa-xmark"></i></div>
    <div id="photoViewerCounter" style="position:absolute;bottom:22px;left:50%;transform:translateX(-50%);color:#fff;font-size:13px;background:rgba(0,0,0,.45);padding:5px 14px;border-radius:14px;z-index:2;"></div>
    <img id="photoViewerImg" src="" ontouchstart="pvTouchStart(event)" ontouchend="pvTouchEnd(event)" onclick="pvHandleTap(event)" style="max-width:100%;max-height:100%;object-fit:contain;touch-action:pan-y;">
    <div id="photoViewerHeartPop" style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);font-size:88px;color:#ff4d6d;pointer-events:none;opacity:0;z-index:2;"><i class="fa-regular fa-heart"></i></div>
  </div>'''
content, ok = apply_edit("A-오버레이HTML", old_a, new_a, content)

# EDIT B: JS 함수 추가
old_b = '''function openImageLightbox(url){
  document.getElementById('imageLightboxImg').src = url;
  // 0-69: openModal(클래스 기반)로 열어서 다른 화면들처럼 뒤로가기 스택에 자동으로 포함되게 함
  openModal('imageLightboxOverlay');
}
function closeImageLightbox(){
  closeModal('imageLightboxOverlay');
  document.getElementById('imageLightboxImg').src = '';
}'''
new_b = old_b + '''
/* ===== 0-70: 사진 전체화면 뷰어 (프로필/채팅/커뮤니티 공용) - 스와이프+카운터+더블탭 좋아요 ===== */
let photoViewerState = null;
let pvTouchStartX = null;
let pvLastTapTime = 0;
function openPhotoViewer(images, startIndex, opts){
  opts = opts || {};
  images = (images||[]).filter(Boolean);
  if (!images.length) return;
  photoViewerState = {
    images,
    index: Math.min(Math.max(startIndex||0, 0), images.length - 1),
    likable: !!opts.likable,
    isLiked: opts.isLiked || function(){ return false; },
    onToggleLike: opts.onToggleLike || function(){}
  };
  renderPhotoViewer();
  openModal('photoViewerOverlay');
}
function closePhotoViewer(){
  closeModal('photoViewerOverlay');
  photoViewerState = null;
}
function renderPhotoViewer(){
  if (!photoViewerState) return;
  document.getElementById('photoViewerImg').src = photoViewerState.images[photoViewerState.index];
  document.getElementById('photoViewerCounter').textContent = `${photoViewerState.index + 1}/${photoViewerState.images.length}`;
}
function photoViewerNext(){
  if (!photoViewerState) return;
  if (photoViewerState.index < photoViewerState.images.length - 1){ photoViewerState.index++; renderPhotoViewer(); }
}
function photoViewerPrev(){
  if (!photoViewerState) return;
  if (photoViewerState.index > 0){ photoViewerState.index--; renderPhotoViewer(); }
}
function pvTouchStart(e){ pvTouchStartX = e.touches[0].clientX; }
function pvTouchEnd(e){
  if (pvTouchStartX===null) return;
  const dx = e.changedTouches[0].clientX - pvTouchStartX;
  pvTouchStartX = null;
  if (Math.abs(dx) < 40) return;
  if (dx < 0) photoViewerNext(); else photoViewerPrev();
}
function pvHandleTap(e){
  e.stopPropagation();
  const now = Date.now();
  if (now - pvLastTapTime < 300){ pvToggleLike(); }
  pvLastTapTime = now;
}
function pvToggleLike(){
  if (!photoViewerState || !photoViewerState.likable) return;
  const liked = photoViewerState.isLiked(photoViewerState.index);
  photoViewerState.onToggleLike(photoViewerState.index);
  showPhotoViewerHeartPop(!liked);
}
function showPhotoViewerHeartPop(liked){
  const el = document.getElementById('photoViewerHeartPop');
  if (!el) return;
  el.querySelector('i').className = liked ? 'fa-solid fa-heart' : 'fa-regular fa-heart';
  el.style.transition = 'none';
  el.style.opacity = '1';
  el.style.transform = 'translate(-50%,-50%) scale(1.2)';
  void el.offsetWidth;
  requestAnimationFrame(()=>{
    el.style.transition = 'opacity 0.7s ease, transform 0.7s ease';
    el.style.opacity = '0';
    el.style.transform = 'translate(-50%,-50%) scale(0.85)';
  });
}
function openProfilePhotoViewer(){
  const user = currentProfileUserCache;
  if (!user || !user.photos || !user.photos.length) return;
  const isMe = currentUser && user.id === currentUser.id;
  openPhotoViewer(user.photos, profilePhotoIndex, {
    likable: !isMe,
    isLiked: (i)=> !!(((user.photoLikes && user.photoLikes[i]) || {})[currentUser && currentUser.id]),
    onToggleLike: (i)=> toggleProfilePhotoLike(user.id, i)
  });
}
function openChatAreaImageViewer(containerId, clickedImg){
  const container = document.getElementById(containerId);
  if (!container) return;
  const imgs = Array.from(container.querySelectorAll('.msg-bubble img'));
  const srcs = imgs.map(im=>im.src);
  const idx = imgs.indexOf(clickedImg);
  if (idx < 0) return;
  openPhotoViewer(srcs, idx, {});
}'''
content, ok = apply_edit("B-JS함수", old_b, new_b, content)

# EDIT C: 프로필 사진 클릭시 뷰어 열기
old_c = '''  const photoContent = photos[profilePhotoIndex]
    ? `<img src="${photos[profilePhotoIndex]}" style="${user.photoPosition ? photoPosStyle(user.photoPosition) : 'object-position:50% 38%;'}">`
    : `<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;padding-top:52px;">${defaultAvatarHtml(user.gender,'avatar-large')}</div>`;'''
new_c = '''  const photoContent = photos[profilePhotoIndex]
    ? `<img src="${photos[profilePhotoIndex]}" onclick="openProfilePhotoViewer()" style="cursor:pointer;${user.photoPosition ? photoPosStyle(user.photoPosition) : 'object-position:50% 38%;'}">`
    : `<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;padding-top:52px;">${defaultAvatarHtml(user.gender,'avatar-large')}</div>`;'''
content, ok = apply_edit("C-프로필사진클릭", old_c, new_c, content)

# EDIT D: 1:1 채팅 사진 클릭시 뷰어 열기 (기존엔 클릭해도 아무 반응 없었음)
old_d = '''  } else if (m.type==='image') {
    bubble.innerHTML = quoteHtml + `<img src="${m.data}">`;
  } else {'''
new_d = '''  } else if (m.type==='image') {
    bubble.innerHTML = quoteHtml + `<img src="${m.data}" style="cursor:pointer;" onclick="openChatAreaImageViewer('chatMessageArea', this)">`;
  } else {'''
content, ok = apply_edit("D-1:1채팅사진클릭", old_d, new_d, content)

# EDIT E: 단체채팅 사진 클릭시 뷰어 열기
old_e = '''  } else if (m.type==='image') { bubble.innerHTML = `<img src="${m.data}" style="cursor:pointer;" onclick="openImageLightbox('${m.data}')">`; }'''
new_e = '''  } else if (m.type==='image') { bubble.innerHTML = `<img src="${m.data}" style="cursor:pointer;" onclick="openChatAreaImageViewer('groupChatMessageArea', this)">`; }'''
content, ok = apply_edit("E-단체채팅사진클릭", old_e, new_e, content)

# EDIT F: 게시글 상세화면 사진 클릭시 뷰어 열기
old_f = '''  const mediaHtml = (p.photo && !isFiltered && !isDeleted) ? (p.mediaType==='video'?`<video src="${p.photo}" controls muted style="width:100%;border-radius:10px;margin-bottom:12px;"></video>`:`<img src="${p.photo}" style="width:100%;border-radius:10px;margin-bottom:12px;">`) : '';'''
new_f = '''  const mediaHtml = (p.photo && !isFiltered && !isDeleted) ? (p.mediaType==='video'?`<video src="${p.photo}" controls muted style="width:100%;border-radius:10px;margin-bottom:12px;"></video>`:`<img src="${p.photo}" onclick="openPhotoViewer(['${p.photo}'], 0, {})" style="width:100%;border-radius:10px;margin-bottom:12px;cursor:pointer;">`) : '';'''
content, ok = apply_edit("F-게시글상세사진클릭", old_f, new_f, content)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"완료: {len(edits_applied)}/6 항목 적용됨 -> {edits_applied}")
print(f"파일 크기 변화: {orig_len} -> {len(content)} bytes")
if len(edits_applied) < 6:
    print("!! 일부 항목이 적용되지 않았습니다. 위 로그를 확인하고 클로드에게 전달해주세요.")
    sys.exit(1)
