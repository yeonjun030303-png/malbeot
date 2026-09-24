# 0-90: 메시지 롱프레스 시 해당 말풍선 강조(카톡식 살짝 커짐)
# 0-91: 채팅방 나갈 때 정보/갤러리 드로어 같이 닫기 + 드로어 열린 채 뒤로가기/스와이프 시 드로어만 먼저 닫기
import sys, io
p = 'public/index.html'
s = io.open(p, encoding='utf-8').read()

def rep(old, new, label):
    global s
    n = s.count(old)
    if n != 1:
        print('FAIL', label, 'count=', n); sys.exit(1)
    s = s.replace(old, new)
    print('OK  ', label)

# --- CSS ---
rep(".msg-bubble.msg-deleted{",
""".msg-bubble.msg-pressed{position:relative;z-index:5;transform:scale(1.07);box-shadow:0 6px 18px rgba(0,0,0,.22);animation:msgPop .22s ease-out;}
.msg-row.mine .msg-bubble.msg-pressed{transform-origin:right center;}
.msg-row.other .msg-bubble.msg-pressed{transform-origin:left center;}
@keyframes msgPop{0%{transform:scale(1);}55%{transform:scale(1.11);}100%{transform:scale(1.07);}}
.msg-bubble.msg-deleted{""", '0-90 css')

# --- 하이라이트 헬퍼 + 메뉴 닫힐 때 해제 ---
rep("function closeMsgContextMenu(){\n  if (msgContextMenuEl){",
"""let msgHighlightedEl = null;
function setMsgHighlight(el){ clearMsgHighlight(); if (!el) return; el.classList.add('msg-pressed'); msgHighlightedEl = el; }
function clearMsgHighlight(){ if (msgHighlightedEl){ msgHighlightedEl.classList.remove('msg-pressed'); msgHighlightedEl = null; } }
function closeMsgContextMenu(){
  clearMsgHighlight();
  if (msgContextMenuEl){""", '0-90 helper')

# --- 1:1 / 그룹 롱프레스에서 강조 호출 ---
rep("openMsgContextMenuAt(sx, sy, m); }, 450);",
    "openMsgContextMenuAt(sx, sy, m); setMsgHighlight(bubbleEl); }, 450);", '0-90 dm touch')
rep("openMsgContextMenuAt(e.clientX, e.clientY, m); });",
    "openMsgContextMenuAt(e.clientX, e.clientY, m); setMsgHighlight(bubbleEl); });", '0-90 dm ctx')
rep("openGroupMsgContextMenuAt(sx, sy, m); }, 450);",
    "openGroupMsgContextMenuAt(sx, sy, m); setMsgHighlight(bubbleEl); }, 450);", '0-90 group touch')
rep("openGroupMsgContextMenuAt(e.clientX, e.clientY, m); });",
    "openGroupMsgContextMenuAt(e.clientX, e.clientY, m); setMsgHighlight(bubbleEl); });", '0-90 group ctx')

# --- 0-91: 그룹채팅방 닫을 때 정보/갤러리 드로어도 같이 닫기 ---
rep("function closeGroupChatModal(){\n  closeFullScreen('groupChatModal');",
"""function closeGroupChatModal(){
  closeFullScreen('groupGalleryScreen');
  closeFullScreen('groupInfoScreen');
  closeFullScreen('groupChatModal');""", '0-91 group close')

# --- 0-91: 뒤로가기/엣지스와이프/ESC 시 드로어가 열려있으면 드로어만 먼저 닫기 ---
rep("  if (isActive('chatModal')) return closeChatModal();\n  if (isActive('authModal'))",
"""  if (isActive('groupGalleryScreen')) return closeFullScreen('groupGalleryScreen');
  if (isActive('chatGalleryScreen')) return closeFullScreen('chatGalleryScreen');
  if (isActive('groupInfoScreen')) return closeFullScreen('groupInfoScreen');
  if (isActive('chatInfoScreen')) return closeFullScreen('chatInfoScreen');
  if (isActive('chatModal')) return closeChatModal();
  if (isActive('groupChatModal')) return closeGroupChatModal();
  if (isActive('authModal'))""", '0-91 topmost')

# --- 0-91: 하단 탭 이동 시 그룹채팅방도 정리 ---
rep("  if (activeRoomId) closeChatModal();\n  document.querySelectorAll('.bottom-nav",
    "  if (activeRoomId) closeChatModal();\n  if (activeGroupRoomId) closeGroupChatModal();\n  document.querySelectorAll('.bottom-nav", '0-91 switchTab')

io.open(p, 'w', encoding='utf-8', newline='').write(s)

# JS 문법 검사(inline script 전부)
import re, subprocess, tempfile, os
ok = True
for i, b in enumerate(re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', s, re.S)):
    f = os.path.join(tempfile.gettempdir(), 'chk_%d.js' % i)
    io.open(f, 'w', encoding='utf-8').write(b)
    r = subprocess.run(['node', '--check', f], capture_output=True, text=True, shell=(os.name == 'nt'))
    if r.returncode != 0:
        ok = False; print('SYNTAX ERROR in script', i); print(r.stderr)
print('SYNTAX OK' if ok else 'SYNTAX FAIL - git checkout public/index.html 로 되돌리세요')
print('DONE')