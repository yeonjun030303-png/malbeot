#!/usr/bin/env python3
# 0-7(초대링크 라우트 중복 버그 수정) + 0-9(이모지 키보드 추가) 통합 스크립트
#
# ⚠️ 0-7은 이미 GitHub(커밋 1e34c91)에 적용·push까지 완료되어 있는 상태입니다.
#    이 스크립트는 만약 지금 작업 중인 폴더가 그 커밋을 반영하지 않은 옛날 사본이라면 0-7도 마저 적용하고,
#    이미 최신 상태라면 "이미 적용됨" 메시지만 출력하고 자동으로 건너뜁니다(에러로 멈추지 않음).
#    0-9(이모지 키보드)는 아직 GitHub에 없으므로 이 스크립트로 새로 적용됩니다.
#
# 실행 위치: malbeot-app 폴더 안에서 python3 fix_join_route_and_emoji.py

import sys

def patch(path, replacements, allow_skip_ok=None):
    """
    replacements: [(old, new, label), ...]
    allow_skip_ok: set of label 중 '이미 적용되어 있으면 건너뛰어도 되는' 것들
    """
    with open(path, encoding='utf-8') as f:
        content = f.read()
    for old, new, label in replacements:
        count = content.count(old)
        if count == 1:
            content = content.replace(old, new)
            print(f"[적용] {path} - {label}")
        elif count == 0 and allow_skip_ok and label in allow_skip_ok:
            print(f"[건너뜀] {path} - {label} (이미 적용되어 있거나 대상 없음)")
        else:
            print(f"[실패] {path}: '{label}' 패턴이 {count}번 발견됨 (1번이어야 함) -> {old[:60]!r}")
            sys.exit(1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"[완료] {path} 저장")

# ── 1) 0-7: 초대링크 라우트 중복 버그 수정 (이미 적용돼 있으면 건너뜀) ──
server_replacements = [
(
"""// 단체채팅방 초대링크(실제 URL) 진입점: /join/코드 로 접속하면 프론트가 그 코드를 읽어 자동 입장 처리함
// (지금은 웹앱뿐이라 그냥 앱 페이지로 리다이렉트하지만, 나중에 네이티브 앱이 생기면
//  여기서 미설치 기기를 감지해 스토어로 보내는 분기를 추가할 것)
app.get('/join/:code', (req, res) => {
  res.redirect('/?joinCode=' + encodeURIComponent(req.params.code));
});

// 단체채팅방 초대링크 (카카오 오픈채팅처럼 실제 URL로 들어오면 앱 내 페이지로 바로 진입)
// 지금은 웹뷰만 있어서 index.html을 그대로 내려주고, 클라이언트가 경로의 코드를 읽어 로그인 후 자동 입장시킴.
// TODO: 나중에 네이티브 앱이 생기면 여기서 User-Agent를 보고 앱 미설치 기기는 스토어로 리다이렉트하도록 확장할 것.
app.get('/join/:code', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});""",
"""// 단체채팅방 초대링크 (카카오 오픈채팅처럼 실제 URL로 들어오면 앱 내 페이지로 바로 진입)
// 지금은 웹뷰만 있어서 index.html을 그대로 내려주고, 클라이언트가 경로(/join/코드)를 그대로 읽어 로그인 후 자동 입장시킴.
// 주의: 절대 여기서 redirect하지 말 것 - 클라이언트가 location.pathname에서 '/join/코드' 패턴을 직접 파싱하기 때문에,
//       경로가 바뀌면(redirect로 '/?joinCode=...' 등으로) 클라이언트가 코드를 못 읽어 자동입장이 깨짐.
// TODO: 나중에 네이티브 앱이 생기면 여기서 User-Agent를 보고 앱 미설치 기기는 스토어로 리다이렉트하도록 확장할 것.
app.get('/join/:code', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});""",
"0-7 초대링크 라우트 중복 제거"
),
]

# ── 2) 0-9: 이모지 키보드 추가 ──
html_replacements = [
(
""".chat-attach-btn,.chat-send-btn{background:none;border:none;color:var(--primary);font-size:19px;cursor:pointer;padding:4px 8px;}""",
""".chat-attach-btn,.chat-send-btn{background:none;border:none;color:var(--primary);font-size:19px;cursor:pointer;padding:4px 8px;}
.chat-attach-btn.emoji-btn.active{color:var(--text-main);}
.emoji-panel{position:absolute;left:0;right:0;bottom:0;z-index:220;background:#fff;border-top:1px solid var(--border-color);box-shadow:0 -2px 10px rgba(0,0,0,.08);display:none;flex-direction:column;}
.emoji-panel.open{display:flex;}
.emoji-panel-tabs{display:flex;border-bottom:1px solid var(--border-color);flex-shrink:0;}
.emoji-panel-tab{flex:1;text-align:center;padding:9px 0;font-size:16px;cursor:pointer;color:var(--text-muted);}
.emoji-panel-tab.active{color:var(--primary);border-bottom:2px solid var(--primary);}
.emoji-panel-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:2px;padding:8px;height:190px;overflow-y:auto;font-size:22px;}
.emoji-panel-grid span{display:flex;align-items:center;justify-content:center;aspect-ratio:1;cursor:pointer;border-radius:8px;}
.emoji-panel-grid span:active{background:var(--bg-subtle);}""",
"0-9 이모지 패널 CSS 추가"
),
(
"""      <button class="chat-attach-btn" onclick="triggerChatImageInput()"><i class="fa-solid fa-image"></i></button>
      <input type="file" id="chatImageInput" accept="image/*" class="hidden" onchange="handleChatImageUpload(event)">
      <input type="text" id="chatInputText" placeholder="메시지를 입력하세요...">""",
"""      <button class="chat-attach-btn" onclick="triggerChatImageInput()"><i class="fa-solid fa-image"></i></button>
      <input type="file" id="chatImageInput" accept="image/*" class="hidden" onchange="handleChatImageUpload(event)">
      <button class="chat-attach-btn emoji-btn" id="btnEmojiChat" onclick="toggleEmojiPanel('chatInputText', 'btnEmojiChat')"><i class="fa-regular fa-face-smile"></i></button>
      <input type="text" id="chatInputText" placeholder="메시지를 입력하세요..." onfocus="closeEmojiPanel()">""",
"0-9 1:1채팅 이모지 버튼 추가"
),
(
"""      <button class="chat-attach-btn" onclick="triggerGroupChatImageInput()"><i class="fa-solid fa-image"></i></button>
      <input type="file" id="groupChatImageInput" accept="image/*" class="hidden" onchange="handleGroupChatImageUpload(event)">
      <input type="text" id="groupChatInputText" placeholder="메시지를 입력하세요...">""",
"""      <button class="chat-attach-btn" onclick="triggerGroupChatImageInput()"><i class="fa-solid fa-image"></i></button>
      <input type="file" id="groupChatImageInput" accept="image/*" class="hidden" onchange="handleGroupChatImageUpload(event)">
      <button class="chat-attach-btn emoji-btn" id="btnEmojiGroupChat" onclick="toggleEmojiPanel('groupChatInputText', 'btnEmojiGroupChat')"><i class="fa-regular fa-face-smile"></i></button>
      <input type="text" id="groupChatInputText" placeholder="메시지를 입력하세요..." onfocus="closeEmojiPanel()">""",
"0-9 단체채팅 이모지 버튼 추가"
),
(
"""  <div id="drawerBackdrop" onclick="closeFullScreen('groupInfoScreen')"></div>
  <div id="groupInfoScreen" class="full-screen-overlay drawer-right">""",
"""  <div id="emojiPanel" class="emoji-panel">
    <div class="emoji-panel-tabs">
      <div class="emoji-panel-tab active" data-cat="smileys" onclick="switchEmojiTab('smileys', this)">😀</div>
      <div class="emoji-panel-tab" data-cat="gestures" onclick="switchEmojiTab('gestures', this)">👍</div>
      <div class="emoji-panel-tab" data-cat="hearts" onclick="switchEmojiTab('hearts', this)">❤️</div>
      <div class="emoji-panel-tab" data-cat="animals" onclick="switchEmojiTab('animals', this)">🐶</div>
      <div class="emoji-panel-tab" data-cat="food" onclick="switchEmojiTab('food', this)">🍔</div>
      <div class="emoji-panel-tab" data-cat="etc" onclick="switchEmojiTab('etc', this)">✨</div>
    </div>
    <div id="emojiPanelGrid" class="emoji-panel-grid"></div>
  </div>

  <div id="drawerBackdrop" onclick="closeFullScreen('groupInfoScreen')"></div>
  <div id="groupInfoScreen" class="full-screen-overlay drawer-right">""",
"0-9 이모지 패널 마크업 추가"
),
(
"""// 버튼을 탭하면 입력창(input)이 포커스를 잃으면서(blur) 모바일 키보드가 내려가는 것이 기본 동작이라,
// mousedown/touchstart 시점에 preventDefault로 포커스 이동 자체를 막아 카톡처럼 키보드가 유지되도록 함.
const btnSendMsgEl = document.getElementById('btnSendMsg');""",
"""// 이모지 키보드 (0-9): 두 채팅 입력창(1:1/단체) 공용 패널
const EMOJI_SETS = {
  smileys: ['😀','😁','😂','🤣','😊','😇','🙂','🙃','😉','😍','🥰','😘','😋','😜','🤪','😎','🥳','😢','😭','😤','😡','🥺','😴','🤔','😅','😳','🤗','😏','🙄','😬'],
  gestures: ['👍','👎','👏','🙌','🙏','💪','🤝','👋','✌️','🤞','🤙','👌','✋','🫶','🤟','👊','🫡'],
  hearts: ['❤️','🧡','💛','💚','💙','💜','🖤','🤍','🤎','💕','💞','💓','💗','💖','💘','💝','💔'],
  animals: ['🐶','🐱','🐭','🐹','🐰','🦊','🐻','🐼','🐨','🐯','🦁','🐮','🐷','🐸','🐵','🐔','🐧','🦄','🐢'],
  food: ['🍎','🍊','🍉','🍇','🍓','🍑','🍒','🍕','🍔','🍟','🌭','🍿','🍩','🍰','🎂','🍫','🍪','☕','🍺','🍻'],
  etc: ['✨','🎉','🎈','🔥','💯','⭐','🌟','💤','💦','💥','☀️','🌈','🌙','⚡','🎁','⏰','📌','✅','❌','❓','❗']
};
let emojiTargetInputId = null;
function renderEmojiGrid(cat){
  const grid = document.getElementById('emojiPanelGrid');
  grid.innerHTML = (EMOJI_SETS[cat]||[]).map(e=>`<span onclick="insertEmoji('${e}')">${e}</span>`).join('');
}
function switchEmojiTab(cat, el){
  document.querySelectorAll('.emoji-panel-tab').forEach(t=>t.classList.remove('active'));
  el.classList.add('active');
  renderEmojiGrid(cat);
}
function toggleEmojiPanel(inputId, btnId){
  const panel = document.getElementById('emojiPanel');
  const isOpenForSame = panel.classList.contains('open') && emojiTargetInputId === inputId;
  document.querySelectorAll('.emoji-btn').forEach(b=>b.classList.remove('active'));
  if (isOpenForSame){
    panel.classList.remove('open');
    emojiTargetInputId = null;
    return;
  }
  emojiTargetInputId = inputId;
  document.getElementById(btnId).classList.add('active');
  if (!document.getElementById('emojiPanelGrid').innerHTML) renderEmojiGrid('smileys');
  panel.classList.add('open');
}
function closeEmojiPanel(){
  document.getElementById('emojiPanel').classList.remove('open');
  document.querySelectorAll('.emoji-btn').forEach(b=>b.classList.remove('active'));
  emojiTargetInputId = null;
}
function insertEmoji(emoji){
  if (!emojiTargetInputId) return;
  const input = document.getElementById(emojiTargetInputId);
  if (!input) return;
  const start = input.selectionStart ?? input.value.length;
  const end = input.selectionEnd ?? input.value.length;
  input.value = input.value.slice(0, start) + emoji + input.value.slice(end);
  const newPos = start + emoji.length;
  input.focus();
  input.setSelectionRange(newPos, newPos);
}

// 버튼을 탭하면 입력창(input)이 포커스를 잃으면서(blur) 모바일 키보드가 내려가는 것이 기본 동작이라,
// mousedown/touchstart 시점에 preventDefault로 포커스 이동 자체를 막아 카톡처럼 키보드가 유지되도록 함.
const btnSendMsgEl = document.getElementById('btnSendMsg');""",
"0-9 이모지 JS 로직 추가"
),
]

patch('server.js', server_replacements, allow_skip_ok={"0-7 초대링크 라우트 중복 제거"})
patch('public/index.html', html_replacements)

print("\n패치 완료. 다음 순서로 진행하세요:")
print("1) node -c server.js")
print("2) git add -A && git commit -m \"0-9: 이모지 키보드 추가 (1:1 채팅 + 단체채팅방 공용)\"")
print("3) (모아뒀다가 원하실 때) git push")