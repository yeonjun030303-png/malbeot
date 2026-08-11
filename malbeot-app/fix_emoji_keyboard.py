#!/usr/bin/env python3
# 0-9: 이모지 키보드 추가
# - 1:1 채팅 + 단체채팅 입력창에 이모지 버튼 추가
# - 버튼 클릭 시 자주 쓰는 이모지 그리드 패널이 입력창 위에 뜨고, 탭하면 커서 위치에 삽입됨
# - 패널 바깥을 클릭하면 자동으로 닫힘
# 실행 위치: malbeot-app 폴더 안에서 python3 fix_emoji_keyboard.py

import sys

def patch(path, replacements):
    with open(path, encoding='utf-8') as f:
        content = f.read()
    for old, new in replacements:
        count = content.count(old)
        if count != 1:
            print(f"[실패] {path}: 패턴이 {count}번 발견됨 (1번이어야 함) -> {old[:60]!r}")
            sys.exit(1)
        content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"[성공] {path} 패치 완료")

replacements = [
(
""".chat-attach-btn,.chat-send-btn{background:none;border:none;color:var(--primary);font-size:19px;cursor:pointer;padding:4px 8px;}""",
""".chat-attach-btn,.chat-send-btn,.chat-emoji-btn{background:none;border:none;color:var(--primary);font-size:19px;cursor:pointer;padding:4px 8px;}
.emoji-panel{position:absolute;left:0;right:0;bottom:100%;max-height:220px;overflow-y:auto;background:var(--bg-card);border-top:1px solid var(--border-color);padding:8px;display:none;grid-template-columns:repeat(8,1fr);gap:2px;z-index:5;}
.emoji-panel.open{display:grid;}
.emoji-panel-item{font-size:22px;text-align:center;padding:6px 0;cursor:pointer;border-radius:8px;}
.emoji-panel-item:active{background:var(--bg-subtle);}"""
),
(
"""    <div class="chat-input-bar">
      <button class="chat-attach-btn" onclick="triggerChatImageInput()"><i class="fa-solid fa-image"></i></button>
      <input type="file" id="chatImageInput" accept="image/*" class="hidden" onchange="handleChatImageUpload(event)">
      <input type="text" id="chatInputText" placeholder="메시지를 입력하세요...">
      <button class="chat-send-btn" id="btnSendMsg"><i class="fa-solid fa-paper-plane"></i></button>
    </div>
  </div>""",
"""    <div class="chat-input-bar" style="position:relative;">
      <div id="chatEmojiPanel" class="emoji-panel"></div>
      <button class="chat-attach-btn" onclick="triggerChatImageInput()"><i class="fa-solid fa-image"></i></button>
      <input type="file" id="chatImageInput" accept="image/*" class="hidden" onchange="handleChatImageUpload(event)">
      <button class="chat-emoji-btn" onclick="toggleEmojiPanel('chatEmojiPanel','chatInputText')"><i class="fa-regular fa-face-smile"></i></button>
      <input type="text" id="chatInputText" placeholder="메시지를 입력하세요...">
      <button class="chat-send-btn" id="btnSendMsg"><i class="fa-solid fa-paper-plane"></i></button>
    </div>
  </div>"""
),
(
"""    <div class="chat-input-bar">
      <button class="chat-attach-btn" onclick="triggerGroupChatImageInput()"><i class="fa-solid fa-image"></i></button>
      <input type="file" id="groupChatImageInput" accept="image/*" class="hidden" onchange="handleGroupChatImageUpload(event)">
      <input type="text" id="groupChatInputText" placeholder="메시지를 입력하세요...">
      <button class="chat-send-btn" id="btnSendGroupMsg"><i class="fa-solid fa-paper-plane"></i></button>
    </div>
  </div>""",
"""    <div class="chat-input-bar" style="position:relative;">
      <div id="groupChatEmojiPanel" class="emoji-panel"></div>
      <button class="chat-attach-btn" onclick="triggerGroupChatImageInput()"><i class="fa-solid fa-image"></i></button>
      <input type="file" id="groupChatImageInput" accept="image/*" class="hidden" onchange="handleGroupChatImageUpload(event)">
      <button class="chat-emoji-btn" onclick="toggleEmojiPanel('groupChatEmojiPanel','groupChatInputText')"><i class="fa-regular fa-face-smile"></i></button>
      <input type="text" id="groupChatInputText" placeholder="메시지를 입력하세요...">
      <button class="chat-send-btn" id="btnSendGroupMsg"><i class="fa-solid fa-paper-plane"></i></button>
    </div>
  </div>"""
),
(
"""const chatInputTextEl = document.getElementById('chatInputText');""",
"""/* ===================== 이모지 키보드 ===================== */
const EMOJI_LIST = ['😀','😁','😂','🤣','😊','😍','😘','😉','😎','🤩','🥳','😇','🙂','😅','😢','😭','😡','🤬','😱','😴','🤔','🙄','😏','😜','🥰','😆','😳','🥺','😔','😤','👍','👎','👏','🙏','💪','🙌','👋','✌️','🤝','❤️','💕','💔','💯','🔥','✨','⭐','🎉','🎊','🎁','💰','⏰','📷','🍀','☀️','🌙','☕','🍔','🍕','🍺','🎵','⚽','😷','🤒','😪'];
let activeEmojiPanel = null;
function toggleEmojiPanel(panelId, inputId){
  const panel = document.getElementById(panelId);
  if (panel.classList.contains('open')){
    panel.classList.remove('open'); activeEmojiPanel = null; return;
  }
  document.querySelectorAll('.emoji-panel.open').forEach(p=>p.classList.remove('open'));
  if (!panel.dataset.built){
    panel.innerHTML = EMOJI_LIST.map(e=>`<div class="emoji-panel-item" onclick="insertEmoji('${inputId}','${e}')">${e}</div>`).join('');
    panel.dataset.built = '1';
  }
  panel.classList.add('open');
  activeEmojiPanel = panel;
}
function insertEmoji(inputId, emoji){
  const el = document.getElementById(inputId);
  const start = el.selectionStart ?? el.value.length;
  const end = el.selectionEnd ?? el.value.length;
  el.value = el.value.slice(0, start) + emoji + el.value.slice(end);
  const newPos = start + emoji.length;
  el.focus();
  el.setSelectionRange(newPos, newPos);
}
document.addEventListener('click', (e)=>{
  if (!activeEmojiPanel) return;
  if (activeEmojiPanel.contains(e.target)) return;
  if (e.target.closest('.chat-emoji-btn')) return;
  activeEmojiPanel.classList.remove('open');
  activeEmojiPanel = null;
});

const chatInputTextEl = document.getElementById('chatInputText');"""
),
]

patch('public/index.html', replacements)
print("\n패치 완료. 다음 순서로 진행하세요:")
print("1) node -c server.js   (변경 없지만 확인차)")
print("2) git add -A && git commit -m \"0-9: 이모지 키보드 추가 - 1:1/단체 채팅 입력창에 이모지 패널\"")
print("3) (모아뒀다가 원하실 때) git push")
