# -*- coding: utf-8 -*-
"""
0-16: 그룹채팅방(단체채팅방) 내 대화 검색 기능 추가 (1:1 채팅 검색과 동일한 스펙)
실행 위치: malbeot 저장소 루트 (malbeot-app 폴더가 보이는 곳)
사용법: python3 patch_0_16_group_chat_search.py
"""
import os, sys

ROOT = os.getcwd()
APP = os.path.join(ROOT, "malbeot-app")
if not os.path.isdir(APP):
    print("!! malbeot-app 폴더를 찾을 수 없습니다. 저장소 루트에서 실행하세요."); sys.exit(1)

INDEX = os.path.join(APP, "public", "index.html")

def read(p):
    with open(p, encoding="utf-8") as f: return f.read()

def write(p, s):
    with open(p, "w", encoding="utf-8") as f: f.write(s)

def replace_once(content, old, new, label, path):
    if new in content:
        print(f"   (건너뜀-이미적용됨) {label}")
        return content
    if old not in content:
        print(f"!! 패치 실패: {label} ({path}) — 원본 텍스트 못찾음"); sys.exit(1)
    if content.count(old) != 1:
        print(f"!! 패치실패 1개 아님({content.count(old)}개): {label} ({path})"); sys.exit(1)
    print(f"   적용: {label}")
    return content.replace(old, new)

h = read(INDEX)

# 1) 그룹채팅 헤더에 검색 버튼 추가 + 검색바 HTML 삽입
h = replace_once(h,
"""      <div style="margin-left:auto;display:flex;gap:4px;">
        <button class="icon-round-btn" onclick="openGroupInfoScreen()"><i class="fa-solid fa-bars"></i></button>
      </div>
    </div>
    <div id="groupChatMessageArea" class="chat-messages-area"></div>""",
"""      <div style="margin-left:auto;display:flex;gap:4px;">
        <button class="icon-round-btn" onclick="openGroupChatSearchBar()"><i class="fa-solid fa-magnifying-glass"></i></button>
        <button class="icon-round-btn" onclick="openGroupInfoScreen()"><i class="fa-solid fa-bars"></i></button>
      </div>
    </div>
    <div id="groupChatSearchBar" class="chat-search-bar hidden">
      <i class="fa-solid fa-magnifying-glass" style="color:var(--text-muted);font-size:13px;"></i>
      <input type="text" id="groupChatSearchInput" placeholder="대화 내용 검색" oninput="onGroupChatSearchInput()">
      <span id="groupChatSearchCounter" class="chat-search-counter">0/0</span>
      <button class="chat-search-nav-btn" onclick="navigateGroupChatSearch(1)"><i class="fa-solid fa-chevron-up"></i></button>
      <button class="chat-search-nav-btn" onclick="navigateGroupChatSearch(-1)"><i class="fa-solid fa-chevron-down"></i></button>
      <button class="chat-search-nav-btn" onclick="closeGroupChatSearchBar()"><i class="fa-solid fa-xmark"></i></button>
    </div>
    <div id="groupChatMessageArea" class="chat-messages-area"></div>""",
    "그룹채팅 헤더 검색버튼+검색바 HTML", INDEX)

# 2) closeGroupChatModal에 검색바 정리 로직 추가
h = replace_once(h,
"""function closeGroupChatModal(){
  closeFullScreen('groupChatModal');
  activeGroupRoomId = null;
  activeGroupRoomMeta = null;
  loadChatRoomList();
}""",
"""function closeGroupChatModal(){
  closeFullScreen('groupChatModal');
  activeGroupRoomId = null;
  activeGroupRoomMeta = null;
  closeGroupChatSearchBar();
  loadChatRoomList();
}""",
    "closeGroupChatModal 검색바 정리", INDEX)

# 3) 그룹채팅 검색 함수 세트 추가 (1:1 검색 로직과 동일한 방식, findCachedGroupRoom(activeGroupRoomId).messages 사용)
h = replace_once(h,
"""/* ===================== 단체채팅방 정보 화면 ===================== */""",
"""/* ===================== 단체채팅방 내 대화 검색 =====================
   1:1 채팅 검색과 동일한 방식: 돋보기로 검색바를 열고, 최신 메시지부터 1/N 순번을 매김.
   위쪽 화살표=더 과거 매치로, 아래쪽 화살표=더 최신 매치로 이동(끝에서 순환).
   매치로 이동하면 해당 메시지 말풍선을 파란 박스(.search-hl)로 강조, X는 강조만 제거하고 스크롤 위치 유지 */
let groupChatSearchQuery = '';
let groupChatSearchMatches = [];
let groupChatSearchIndex = -1;
let groupChatSearchHighlightEl = null;
let groupChatSearchHighlightOriginalHtml = null;
function openGroupChatSearchBar(){
  const bar = document.getElementById('groupChatSearchBar');
  if (!bar) return;
  bar.classList.remove('hidden');
  const input = document.getElementById('groupChatSearchInput');
  input.value = '';
  input.focus();
  groupChatSearchQuery = ''; groupChatSearchMatches = []; groupChatSearchIndex = -1;
  document.getElementById('groupChatSearchCounter').textContent = '0/0';
}
function closeGroupChatSearchBar(){
  const bar = document.getElementById('groupChatSearchBar');
  if (bar) bar.classList.add('hidden');
  restoreGroupChatSearchHighlight();
  groupChatSearchQuery = ''; groupChatSearchMatches = []; groupChatSearchIndex = -1;
  const input = document.getElementById('groupChatSearchInput');
  if (input) input.value = '';
  const counter = document.getElementById('groupChatSearchCounter');
  if (counter) counter.textContent = '0/0';
}
function restoreGroupChatSearchHighlight(){
  if (groupChatSearchHighlightEl && groupChatSearchHighlightOriginalHtml !== null){
    groupChatSearchHighlightEl.innerHTML = groupChatSearchHighlightOriginalHtml;
  }
  groupChatSearchHighlightEl = null;
  groupChatSearchHighlightOriginalHtml = null;
}
function onGroupChatSearchInput(){
  const q = document.getElementById('groupChatSearchInput').value.trim();
  groupChatSearchQuery = q;
  restoreGroupChatSearchHighlight();
  if (!q){
    groupChatSearchMatches = []; groupChatSearchIndex = -1;
    document.getElementById('groupChatSearchCounter').textContent = '0/0';
    return;
  }
  const cached = findCachedGroupRoom(activeGroupRoomId);
  const messages = (cached && cached.messages) || [];
  // 오래된 순으로 저장돼있어서, 뒤집으면 배열 0번=가장 최신 매치가 됨(=1/N)
  groupChatSearchMatches = messages
    .filter(m => m.id && !m.deletedForEveryone && m.type!=='image' && m.text && m.text.includes(q))
    .slice().reverse();
  if (!groupChatSearchMatches.length){
    groupChatSearchIndex = -1;
    document.getElementById('groupChatSearchCounter').textContent = '0/0';
    return;
  }
  groupChatSearchIndex = 0;
  goToGroupChatSearchMatch();
}
// dir=1(위 화살표)=더 과거 매치로 다음칸 이동, dir=-1(아래 화살표)=더 최신 매치로 이동. 끝에서 순환됨
function navigateGroupChatSearch(dir){
  if (!groupChatSearchMatches.length) return;
  groupChatSearchIndex = (groupChatSearchIndex + dir + groupChatSearchMatches.length) % groupChatSearchMatches.length;
  goToGroupChatSearchMatch();
}
function goToGroupChatSearchMatch(){
  restoreGroupChatSearchHighlight();
  const m = groupChatSearchMatches[groupChatSearchIndex];
  document.getElementById('groupChatSearchCounter').textContent = `${groupChatSearchIndex+1}/${groupChatSearchMatches.length}`;
  if (!m) return;
  const row = document.querySelector(`#groupChatMessageArea .msg-row[data-msgid="${m.id}"]`);
  if (!row) return;
  row.scrollIntoView({block:'center', behavior:'smooth'});
  const bubble = row.querySelector('.msg-bubble');
  if (bubble){
    groupChatSearchHighlightEl = bubble;
    groupChatSearchHighlightOriginalHtml = bubble.innerHTML;
    const quoteHtml = m.replyTo ? `<div class="msg-reply-quote">${escapeHtml(m.replyTo.preview||'')}</div>` : '';
    bubble.innerHTML = quoteHtml + highlightMatch(m.text, groupChatSearchQuery);
  }
}

/* ===================== 단체채팅방 정보 화면 ===================== */""",
    "그룹채팅 검색 함수 세트(open/close/input/navigate/goTo)", INDEX)

write(INDEX, h)
print("\n✅ 0-16 패치 적용 완료 (public/index.html).")
print("다음: 브라우저에서 그룹채팅방 열어 돋보기 버튼 테스트 후 git add -A && git commit && git push")