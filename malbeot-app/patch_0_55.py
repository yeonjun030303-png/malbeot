# -*- coding: utf-8 -*-
# 0-55: 1:1 채팅방에 카톡식 정보 화면(☰ 메뉴 - 사진·동영상 갤러리 + 알림끄기 + 차단/신고 + 나가기) 신설
# 반드시 malbeot-app 폴더 안에서 실행하세요 (server.js, public/index.html 이 같은 폴더에 있어야 함)

import os

def apply(path, replacements):
    if not os.path.exists(path):
        print(f"❌ 파일을 찾을 수 없습니다: {path} (실행 위치를 확인하세요)")
        raise SystemExit(1)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    for old, new in replacements:
        cnt = content.count(old)
        if cnt != 1:
            print(f"❌ {path} 에서 패턴을 정확히 1곳에서 찾지 못했습니다(발견 {cnt}회). 이미 적용됐거나 코드가 변경되었을 수 있습니다.")
            print("---- 찾으려던 내용 ----")
            print(old[:200])
            raise SystemExit(1)
        content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

INDEX_HTML = "public/index.html"

index_replacements = [
    (
        '''      <div style="margin-left:auto;display:flex;gap:4px;">
        <button class="icon-round-btn" onclick="openChatSearchBar()"><i class="fa-solid fa-magnifying-glass"></i></button>
        <button class="icon-round-btn" onclick="openBlockReportModal('chat', activeRoomId)"><i class="fa-solid fa-ellipsis"></i></button>
        <button class="icon-round-btn" style="color:var(--danger);" onclick="triggerExitChat()"><i class="fa-solid fa-right-from-bracket"></i></button>
      </div>''',
        '''      <div style="margin-left:auto;display:flex;gap:4px;">
        <button class="icon-round-btn" onclick="openChatSearchBar()"><i class="fa-solid fa-magnifying-glass"></i></button>
        <button class="icon-round-btn" onclick="openChatInfoScreen()"><i class="fa-solid fa-bars"></i></button>
        <button class="icon-round-btn" onclick="openBlockReportModal('chat', activeRoomId)"><i class="fa-solid fa-ellipsis"></i></button>
        <button class="icon-round-btn" style="color:var(--danger);" onclick="triggerExitChat()"><i class="fa-solid fa-right-from-bracket"></i></button>
      </div>'''
    ),
    (
        '''  <div id="groupGalleryScreen" class="full-screen-overlay drawer-right">
    <div class="chat-header-row">
      <button class="back-btn" style="background:none;border:none;font-size:18px;cursor:pointer;" onclick="closeFullScreen('groupGalleryScreen')"><i class="fa-solid fa-arrow-left"></i></button>
      <div class="chat-header-nick" style="cursor:default;">사진/동영상</div>
    </div>
    <div id="groupGalleryFullGrid" style="padding:10px;overflow-y:auto;flex:1;display:grid;grid-template-columns:repeat(5,1fr);gap:4px;"></div>
  </div>

  <div id="imageLightboxOverlay"''',
        '''  <div id="groupGalleryScreen" class="full-screen-overlay drawer-right">
    <div class="chat-header-row">
      <button class="back-btn" style="background:none;border:none;font-size:18px;cursor:pointer;" onclick="closeFullScreen('groupGalleryScreen')"><i class="fa-solid fa-arrow-left"></i></button>
      <div class="chat-header-nick" style="cursor:default;">사진/동영상</div>
    </div>
    <div id="groupGalleryFullGrid" style="padding:10px;overflow-y:auto;flex:1;display:grid;grid-template-columns:repeat(5,1fr);gap:4px;"></div>
  </div>

  <!-- 0-55: 1:1 채팅방 정보 화면(그룹채팅 정보화면과 동일한 형태) -->
  <div id="chatInfoScreen" class="full-screen-overlay drawer-right">
    <div class="chat-header-row">
      <button class="back-btn" style="background:none;border:none;font-size:18px;cursor:pointer;" onclick="closeFullScreen('chatInfoScreen')"><i class="fa-solid fa-arrow-left"></i></button>
      <div class="chat-header-nick" style="cursor:default;">채팅방 정보</div>
    </div>
    <div style="padding:10px;overflow-y:auto;flex:1;">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:18px;cursor:pointer;" onclick="openProfileFromChatHeader()">
        <img id="chatInfoAvatar" class="avatar-sm" src="" alt="" style="display:none;width:44px;height:44px;border-radius:50%;object-fit:cover;">
        <span id="chatInfoAvatarDefault" class="avatar-sm" style="display:none;width:44px;height:44px;border-radius:50%;align-items:center;justify-content:center;"></span>
        <div style="font-size:15px;font-weight:700;" id="chatInfoNick"></div>
      </div>
      <div style="margin-bottom:18px;">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
          <div style="font-size:13px;font-weight:700;">사진/동영상</div>
          <span id="chatGalleryMoreBtn" style="font-size:12px;color:var(--text-muted);cursor:pointer;display:none;" onclick="openChatGalleryScreen()">더보기 ></span>
        </div>
        <div id="chatInfoGallery" style="display:grid;grid-template-columns:repeat(5,1fr);gap:4px;"></div>
      </div>
      <div style="display:flex;justify-content:space-around;padding:14px 0;border-top:1px solid var(--border-color);">
        <button type="button" style="background:none;border:none;display:flex;flex-direction:column;align-items:center;gap:4px;cursor:pointer;color:var(--text-main);" onclick="toggleChatMuteFromInfo()"><i id="chatInfoMuteIcon" class="fa-solid fa-bell" style="font-size:17px;"></i><span style="font-size:11px;">알림</span></button>
        <button type="button" style="background:none;border:none;display:flex;flex-direction:column;align-items:center;gap:4px;cursor:pointer;color:var(--text-main);" onclick="openBlockReportModal('chat', activeRoomId)"><i class="fa-solid fa-ban" style="font-size:17px;"></i><span style="font-size:11px;">차단/신고</span></button>
        <button type="button" style="background:none;border:none;display:flex;flex-direction:column;align-items:center;gap:4px;cursor:pointer;color:var(--danger);" onclick="closeFullScreen('chatInfoScreen');triggerExitChat();"><i class="fa-solid fa-right-from-bracket" style="font-size:17px;"></i><span style="font-size:11px;">나가기</span></button>
      </div>
    </div>
  </div>

  <div id="chatGalleryScreen" class="full-screen-overlay drawer-right">
    <div class="chat-header-row">
      <button class="back-btn" style="background:none;border:none;font-size:18px;cursor:pointer;" onclick="closeFullScreen('chatGalleryScreen')"><i class="fa-solid fa-arrow-left"></i></button>
      <div class="chat-header-nick" style="cursor:default;">사진/동영상</div>
    </div>
    <div id="chatGalleryFullGrid" style="padding:10px;overflow-y:auto;flex:1;display:grid;grid-template-columns:repeat(5,1fr);gap:4px;"></div>
  </div>

  <div id="imageLightboxOverlay"'''
    ),
    (
        '''function leaveGroupRoomFromInfo(){
  showMiniAlert('정말로 이 채팅방을 나가시겠어요?', [
    {label:'취소'},
    {label:'나가기', danger:true, onClick:()=>{ const rid=activeGroupRoomId; socket.emit('group:leave', {roomId:rid}, ()=>{ closeFullScreen('groupInfoScreen'); closeGroupChatModal(); }); }}
  ]);
}''',
        '''function leaveGroupRoomFromInfo(){
  showMiniAlert('정말로 이 채팅방을 나가시겠어요?', [
    {label:'취소'},
    {label:'나가기', danger:true, onClick:()=>{ const rid=activeGroupRoomId; socket.emit('group:leave', {roomId:rid}, ()=>{ closeFullScreen('groupInfoScreen'); closeGroupChatModal(); }); }}
  ]);
}

/* ===================== 0-55: 1:1 채팅방 정보 화면(카톡식 점3개/햄버거 메뉴) ===================== */
function openChatInfoScreen(){
  if (!activeRoomId) return;
  const headerAvatar = document.getElementById('chatHeaderAvatar');
  const headerAvatarDefault = document.getElementById('chatHeaderAvatarDefault');
  const infoAvatar = document.getElementById('chatInfoAvatar');
  const infoAvatarDefault = document.getElementById('chatInfoAvatarDefault');
  if (headerAvatar.style.display !== 'none'){
    infoAvatar.src = headerAvatar.src; infoAvatar.style.display = 'block';
    infoAvatarDefault.style.display = 'none';
  } else {
    infoAvatar.style.display = 'none';
    infoAvatarDefault.style.display = 'flex';
    infoAvatarDefault.innerHTML = headerAvatarDefault.innerHTML;
    infoAvatarDefault.style.background = headerAvatarDefault.style.background;
    infoAvatarDefault.style.color = headerAvatarDefault.style.color;
  }
  document.getElementById('chatInfoNick').textContent = document.getElementById('chatTargetName').textContent;
  const muteIcon = document.getElementById('chatInfoMuteIcon');
  if (muteIcon) muteIcon.className = mutedChatRoomIds.has(activeRoomId) ? 'fa-solid fa-bell-slash' : 'fa-solid fa-bell';
  renderChatInfoGallery();
  openFullScreen('chatInfoScreen');
}
function chatImageMessages(){
  return (currentChatMessages||[]).filter(m=> m.type==='image' && !m.deletedForEveryone);
}
function renderChatInfoGallery(){
  const imgs = chatImageMessages();
  const gallery = document.getElementById('chatInfoGallery');
  gallery.innerHTML = imgs.slice(-5).reverse().map(m=>`<div style="aspect-ratio:1;border-radius:8px;overflow:hidden;background:#eee;cursor:pointer;" onclick="openImageLightbox('${m.data}')"><img src="${m.data}" style="width:100%;height:100%;object-fit:cover;"></div>`).join('') || `<div style="grid-column:1/-1;color:var(--text-muted);font-size:12px;text-align:center;padding:10px 0;">등록된 사진/동영상이 없습니다.</div>`;
  document.getElementById('chatGalleryMoreBtn').style.display = imgs.length > 5 ? 'block' : 'none';
}
function openChatGalleryScreen(){
  const imgs = chatImageMessages().slice().reverse();
  const grid = document.getElementById('chatGalleryFullGrid');
  grid.innerHTML = imgs.map(m=>`<div style="aspect-ratio:1;border-radius:8px;overflow:hidden;background:#eee;cursor:pointer;" onclick="openImageLightbox('${m.data}')"><img src="${m.data}" style="width:100%;height:100%;object-fit:cover;"></div>`).join('') || `<div style="grid-column:1/-1;color:var(--text-muted);font-size:13px;text-align:center;padding:30px 0;">등록된 사진/동영상이 없습니다.</div>`;
  openFullScreen('chatGalleryScreen');
}
function toggleChatMuteFromInfo(){
  if (!activeRoomId) return;
  socket.emit('chat:toggle_mute', {roomId:activeRoomId}, (res)=>{
    if (!res || !res.success) return;
    if (res.muted) mutedChatRoomIds.add(activeRoomId); else mutedChatRoomIds.delete(activeRoomId);
    const muteIcon = document.getElementById('chatInfoMuteIcon');
    if (muteIcon) muteIcon.className = res.muted ? 'fa-solid fa-bell-slash' : 'fa-solid fa-bell';
  });
}'''
    ),
    (
        '''function closeChatModal(){
  closeModal('chatModal');
  activeRoomId = null;
  activeChatTargetId = null;
  closeChatSearchBar();
  clearTimeout(chatMarkReadTimer);
  chatMaxSeenTs = 0;
}''',
        '''function closeChatModal(){
  closeModal('chatModal');
  closeFullScreen('chatInfoScreen');
  closeFullScreen('chatGalleryScreen');
  activeRoomId = null;
  activeChatTargetId = null;
  closeChatSearchBar();
  clearTimeout(chatMarkReadTimer);
  chatMaxSeenTs = 0;
}'''
    ),
]

apply(INDEX_HTML, index_replacements)
print("✅ 0-55 완료: 1:1 채팅방 정보 화면(사진/동영상 갤러리 + 알림끄기 + 차단/신고 + 나가기) 추가됨")