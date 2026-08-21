import io

with open("public/index.html", "r", encoding="utf-8") as f:
    html = f.read()

# 1) 채팅방 헤더에서 "설정(더보기->차단/신고)"와 "나가기" 버튼 제거
#    -> 이미 3개선(정보) 메뉴 안에 알림/차단신고/나가기가 전부 들어있어 중복이었음
old_header_btns = """      <div style="margin-left:auto;display:flex;gap:4px;">
        <button class="icon-round-btn" onclick="openChatSearchBar()"><i class="fa-solid fa-magnifying-glass"></i></button>
        <button class="icon-round-btn" onclick="openChatInfoScreen()"><i class="fa-solid fa-bars"></i></button>
        <button class="icon-round-btn" onclick="openBlockReportModal('chat', activeRoomId)"><i class="fa-solid fa-ellipsis"></i></button>
        <button class="icon-round-btn" style="color:var(--danger);" onclick="triggerExitChat()"><i class="fa-solid fa-right-from-bracket"></i></button>
      </div>"""
assert html.count(old_header_btns) == 1, "old_header_btns 매칭 실패"
new_header_btns = """      <div style="margin-left:auto;display:flex;gap:4px;">
        <button class="icon-round-btn" onclick="openChatSearchBar()"><i class="fa-solid fa-magnifying-glass"></i></button>
        <button class="icon-round-btn" onclick="openChatInfoScreen()"><i class="fa-solid fa-bars"></i></button>
      </div>"""
html = html.replace(old_header_btns, new_header_btns)

# 2) CSS: 채팅방이 열려있는 상태에서 프로필화면을 그 위에 겹쳐 띄울 때만 z-index를 올림
old_css = """.full-screen-overlay.active{display:flex;}"""
assert html.count(old_css) == 1, "old_css 매칭 실패"
new_css = """.full-screen-overlay.active{display:flex;}
/* 0-69: 채팅방 위에 프로필 화면을 겹쳐 띄울 때만(chatModal이 함께 열려있을 때) profileDetailScreen을 그 위로 올림 */
#profileDetailScreen.active:has(~ #chatModal.active){z-index:200;}"""
html = html.replace(old_css, new_css)

# 3) 채팅방 상대이름/프로필사진 클릭 -> 채팅방을 완전히 닫지 않고 프로필을 그 위에 겹쳐서 띄움
#    (기존엔 closeChatModal()로 채팅방 자체를 닫아버려서, 뒤로가기 누르면 채팅방이 아니라 채팅목록으로 나가버렸음)
old_openprofile = """function openProfileFromChatHeader(){
  if (!activeChatTargetId) return;
  const targetId = activeChatTargetId; // closeChatModal()이 activeChatTargetId를 null로 초기화하므로 미리 저장해둬야 함
  closeChatModal();
  openProfileDetailScreen(targetId);
}"""
assert html.count(old_openprofile) == 1, "old_openprofile 매칭 실패"
new_openprofile = """function openProfileFromChatHeader(){
  if (!activeChatTargetId) return;
  // 0-69: 채팅방을 닫지 않고 그대로 둔 채 프로필 화면만 위에 겹쳐서 띄움(위 CSS의 :has() 규칙이 z-index를 자동으로 올려줌).
  // 프로필에서 뒤로가기를 누르면 프로필만 닫히고 채팅방이 그대로 남아있게 됨.
  openProfileDetailScreen(activeChatTargetId);
}"""
html = html.replace(old_openprofile, new_openprofile)

# 4) 사진 확대보기(라이트박스)가 뒤로가기 스택에 전혀 포함되지 않던 문제 수정
#    (style.display만 직접 바꿔서 열고 닫았기 때문에, 라이트박스를 보다가 뒤로가기를 누르면
#     라이트박스는 안 닫히고 그 아래 채팅방만 닫혀버려 "화면이 어두워지며 먹통"인 것처럼 보이던 버그의 원인이었음)
old_lightbox_html = """  <div id="imageLightboxOverlay" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.92);z-index:9999;align-items:center;justify-content:center;" onclick="closeImageLightbox()">
    <img id="imageLightboxImg" src="" style="max-width:94%;max-height:88%;object-fit:contain;">
  </div>"""
assert html.count(old_lightbox_html) == 1, "old_lightbox_html 매칭 실패"
new_lightbox_html = """  <div id="imageLightboxOverlay" class="modal-overlay" style="position:fixed;inset:0;background:rgba(0,0,0,.92);z-index:9999;" onclick="closeImageLightbox()">
    <img id="imageLightboxImg" src="" style="max-width:94%;max-height:88%;object-fit:contain;">
  </div>"""
html = html.replace(old_lightbox_html, new_lightbox_html)

old_lightbox_js = """function openImageLightbox(url){
  document.getElementById('imageLightboxImg').src = url;
  document.getElementById('imageLightboxOverlay').style.display = 'flex';
}
function closeImageLightbox(){
  document.getElementById('imageLightboxOverlay').style.display = 'none';
  document.getElementById('imageLightboxImg').src = '';
}"""
assert html.count(old_lightbox_js) == 1, "old_lightbox_js 매칭 실패"
new_lightbox_js = """function openImageLightbox(url){
  document.getElementById('imageLightboxImg').src = url;
  // 0-69: openModal(클래스 기반)로 열어서 다른 화면들처럼 뒤로가기 스택에 자동으로 포함되게 함
  openModal('imageLightboxOverlay');
}
function closeImageLightbox(){
  closeModal('imageLightboxOverlay');
  document.getElementById('imageLightboxImg').src = '';
}"""
html = html.replace(old_lightbox_js, new_lightbox_js)

# 5) 프로필 사진 "추가" 등록 시 하단 미리보기 스트립에 새로 추가 중인 사진이 즉시 나타나지 않던 버그 수정
#    (slots 배열이 기존 등록된 사진 개수만큼만 있어서, 새로 추가하는 사진의 slotIndex가 배열 범위를 벗어나
#     .map()에서 아예 건너뛰어졌던 것이 원인)
old_thumbstrip = """function renderProfilePreviewThumbStrip(){
  if (!photoPreviewMeta || photoPreviewMeta.mode !== 'profile') return;
  const wrap = document.getElementById('profilePreviewThumbStrip');
  if (!wrap) return;
  const slots = [editPhotoBase64 || null, ...editExtraPhotos];
  const display = slots.map((src,i)=> i===photoPreviewMeta.slotIndex ? photoPreviewMeta.currentDataUrl : src);"""
assert html.count(old_thumbstrip) == 1, "old_thumbstrip 매칭 실패"
new_thumbstrip = """function renderProfilePreviewThumbStrip(){
  if (!photoPreviewMeta || photoPreviewMeta.mode !== 'profile') return;
  const wrap = document.getElementById('profilePreviewThumbStrip');
  if (!wrap) return;
  const slots = [editPhotoBase64 || null, ...editExtraPhotos];
  // 0-69: 새로 추가 중인 사진의 slotIndex가 기존 배열 길이보다 클 수 있으므로(아직 저장 전) 그만큼 자리를 늘려줌
  while (slots.length <= photoPreviewMeta.slotIndex) slots.push(null);
  const display = slots.map((src,i)=> i===photoPreviewMeta.slotIndex ? photoPreviewMeta.currentDataUrl : src);"""
html = html.replace(old_thumbstrip, new_thumbstrip)

# 6) 휴대폰 번호 옆에 "상대방에게 표기되지 않아요" 안내문구 추가
old_phone = """            <div class="form-group"><label>가입한 휴대폰 번호</label><input type="text" id="editPhoneReadonly" readonly disabled style="opacity:.7;"></div>"""
assert html.count(old_phone) == 1, "old_phone 매칭 실패"
new_phone = """            <div class="form-group"><label>가입한 휴대폰 번호 <span style="font-weight:400;color:var(--text-muted);font-size:11px;">(상대방에게 표기되지 않아요)</span></label><input type="text" id="editPhoneReadonly" readonly disabled style="opacity:.7;"></div>"""
html = html.replace(old_phone, new_phone)

with open("public/index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("0-69 패치 완료")