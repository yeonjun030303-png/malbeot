path = "public/index.html"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

patches = []

patches.append((
"""    <div class="chat-input-bar" style="position:relative;">
      <div id="chatEmojiPanel" class="emoji-panel"></div>
      <button class="chat-attach-btn" onclick="triggerChatImageInput()"><i class="fa-solid fa-image"></i></button>
      <input type="file" id="chatImageInput" accept="image/*" class="hidden" onchange="handleChatImageUpload(event)">
      <button class="chat-emoji-btn" onclick="toggleEmojiPanel('chatEmojiPanel','chatInputText')"><i class="fa-regular fa-face-smile"></i></button>
      <input type="text" id="chatInputText" placeholder="메시지를 입력하세요...">
      <button class="chat-send-btn" id="btnSendMsg"><i class="fa-solid fa-paper-plane"></i></button>
    </div>""",
"""    <div class="chat-input-bar" style="position:relative;">
      <button class="chat-attach-btn" onclick="triggerChatImageInput()"><i class="fa-solid fa-image"></i></button>
      <input type="file" id="chatImageInput" accept="image/*" class="hidden" onchange="handleChatImageUpload(event)">
      <input type="text" id="chatInputText" placeholder="메시지를 입력하세요...">
      <button class="chat-send-btn" id="btnSendMsg"><i class="fa-solid fa-paper-plane"></i></button>
    </div>"""
))

patches.append((
"""    <div class="chat-input-bar" style="position:relative;">
      <div id="groupChatEmojiPanel" class="emoji-panel"></div>
      <button class="chat-attach-btn" onclick="triggerGroupChatImageInput()"><i class="fa-solid fa-image"></i></button>
      <input type="file" id="groupChatImageInput" accept="image/*" class="hidden" onchange="handleGroupChatImageUpload(event)">
      <button class="chat-emoji-btn" onclick="toggleEmojiPanel('groupChatEmojiPanel','groupChatInputText')"><i class="fa-regular fa-face-smile"></i></button>
      <input type="text" id="groupChatInputText" placeholder="메시지를 입력하세요...">
      <button class="chat-send-btn" id="btnSendGroupMsg"><i class="fa-solid fa-paper-plane"></i></button>
    </div>""",
"""    <div class="chat-input-bar" style="position:relative;">
      <button class="chat-attach-btn" onclick="triggerGroupChatImageInput()"><i class="fa-solid fa-image"></i></button>
      <input type="file" id="groupChatImageInput" accept="image/*" class="hidden" onchange="handleGroupChatImageUpload(event)">
      <input type="text" id="groupChatInputText" placeholder="메시지를 입력하세요...">
      <button class="chat-send-btn" id="btnSendGroupMsg"><i class="fa-solid fa-paper-plane"></i></button>
    </div>"""
))

patches.append((
"""    if (!inGracePeriod && Math.abs(newHeight - prev) < 20) return;
    container.style.height = newHeight + 'px';
  }""",
"""    if (!inGracePeriod && Math.abs(newHeight - prev) < 20) return;
    container.style.height = newHeight + 'px';
    ['chatModal','groupChatModal'].forEach(function(id){
      var el = document.getElementById(id);
      if (el) el.style.height = newHeight + 'px';
    });
  }"""
))

results = []
for i, (old, new) in enumerate(patches, 1):
    count = content.count(old)
    if count != 1:
        results.append(f"[오류] 패치 {i}: 패턴이 {count}개 발견됨(1개여야 함) - 건너뜀")
        continue
    content = content.replace(old, new, 1)
    results.append(f"[완료] 패치 {i} 적용됨")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

for r in results:
    print(r)
