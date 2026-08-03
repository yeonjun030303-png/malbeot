import re

with open('public/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = """  <div id="chatModal" class="modal-overlay">
    <div class="modal-card chat-window-card" style="height:88vh;">
      <div class="chat-header-row">
        <button class="back-btn" style="background:none;border:none;font-size:18px;cursor:pointer;" onclick="closeChatModal()"><i class="fa-solid fa-arrow-left"></i></button>
        <img id="chatHeaderAvatar" class="chat-header-avatar" src="" alt="" style="cursor:pointer;" onclick="openProfileFromChatHeader()">
        <div class="chat-header-nick" id="chatTargetName" style="cursor:pointer;" onclick="openProfileFromChatHeader()">말벗</div>
        <div style="margin-left:auto;display:flex;gap:4px;">
          <button class="icon-round-btn" onclick="openBlockReportModal('chat')"><i class="fa-solid fa-ellipsis"></i></button>
          <button class="icon-round-btn" style="color:var(--danger);" onclick="triggerExitChat()"><i class="fa-solid fa-right-from-bracket"></i></button>
        </div>
      </div>
      <div class="chat-warning-banner">
        <b>성매매·성추행·성희롱</b> 등 범죄 관련 대화, <b>아동 대상 간음·성적 알선</b> 발생 시 수사기관에 신고될 수 있습니다. 사진 전송, 외부 링크 클릭, 카톡 아이디·전화번호 등 <b>개인정보 유출을 미끼로 금전을 요구</b>하는 피싱 범죄에 주의하세요.
      </div>
      <div id="chatMessageArea" class="chat-messages-area"></div>
      <div class="chat-input-bar">
        <button class="chat-attach-btn" onclick="triggerChatImageInput()"><i class="fa-solid fa-image"></i></button>
        <input type="file" id="chatImageInput" accept="image/*" class="hidden" onchange="handleChatImageUpload(event)">
        <input type="text" id="chatInputText" placeholder="메시지를 입력하세요...">
        <button class="chat-send-btn" id="btnSendMsg"><i class="fa-solid fa-paper-plane"></i></button>
      </div>
    </div>
  </div>"""

new = """  <div id="chatModal" class="full-screen-overlay chat-window-card">
    <div class="chat-header-row">
      <button class="back-btn" style="background:none;border:none;font-size:18px;cursor:pointer;" onclick="closeChatModal()"><i class="fa-solid fa-arrow-left"></i></button>
      <img id="chatHeaderAvatar" class="chat-header-avatar" src="" alt="" style="cursor:pointer;" onclick="openProfileFromChatHeader()">
      <div class="chat-header-nick" id="chatTargetName" style="cursor:pointer;" onclick="openProfileFromChatHeader()">말벗</div>
      <div style="margin-left:auto;display:flex;gap:4px;">
        <button class="icon-round-btn" onclick="openBlockReportModal('chat')"><i class="fa-solid fa-ellipsis"></i></button>
        <button class="icon-round-btn" style="color:var(--danger);" onclick="triggerExitChat()"><i class="fa-solid fa-right-from-bracket"></i></button>
      </div>
    </div>
    <div class="chat-warning-banner">
      <b>성매매·성추행·성희롱</b> 등 범죄 관련 대화, <b>아동 대상 간음·성적 알선</b> 발생 시 수사기관에 신고될 수 있습니다. 사진 전송, 외부 링크 클릭, 카톡 아이디·전화번호 등 <b>개인정보 유출을 미끼로 금전을 요구</b>하는 피싱 범죄에 주의하세요.
    </div>
    <div id="chatMessageArea" class="chat-messages-area"></div>
    <div class="chat-input-bar">
      <button class="chat-attach-btn" onclick="triggerChatImageInput()"><i class="fa-solid fa-image"></i></button>
      <input type="file" id="chatImageInput" accept="image/*" class="hidden" onchange="handleChatImageUpload(event)">
      <input type="text" id="chatInputText" placeholder="메시지를 입력하세요...">
      <button class="chat-send-btn" id="btnSendMsg"><i class="fa-solid fa-paper-plane"></i></button>
    </div>
  </div>"""

count = content.count(old)
if count != 1:
    print(f'[경고] chatModal 구조 변경: 매치 {count}개 (1개여야 정상) - 수동 확인 필요')
else:
    content = content.replace(old, new)
    print('[완료] chatModal → full-screen-overlay 전환')

with open('public/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('저장 완료')