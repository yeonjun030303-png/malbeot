# -*- coding: utf-8 -*-
"""
0-79 패치: 채팅탭 상단 아이콘 줄 재구성(사용자 손그림 지시대로)
1) 검색버튼/오픈채팅만들기 버튼을 상단 헤더(우측)로 이동
2) 채팅탭 아이콘 줄의 중복 설정(톱니바퀴) 버튼 삭제(상단 헤더 설정버튼과 중복이라 삭제)
3) 검색창("닉네임, 채팅방 이름, 대화 내용 검색")을 상시 노출로 변경(그 자리가 원래 아이콘줄 자리로 위로 올라옴)

사용법 (PowerShell, C:\\malbeot 에서):
  python3 patch_0-79.py
"""
import pathlib

FILE = pathlib.Path("malbeot-app/public/index.html")
html = FILE.read_text(encoding="utf-8")

# 1) 헤더 우측에 검색/오픈채팅만들기 버튼 추가(설정버튼 바로 앞)
old1 = """      <button class="icon-round-btn hidden" id="headerAdminModeBtn" onclick="toggleAdminModeView()" title="관리자 모드"><i class="fa-solid fa-user-shield"></i></button>
      <button class="icon-round-btn" id="headerSettingsBtn" onclick="openSettingsScreen()"><i class="fa-solid fa-gear"></i></button>"""
assert html.count(old1) == 1, "old1 매칭 실패"
new1 = """      <button class="icon-round-btn hidden" id="headerAdminModeBtn" onclick="toggleAdminModeView()" title="관리자 모드"><i class="fa-solid fa-user-shield"></i></button>
      <button type="button" class="icon-round-btn hidden" id="headerChatSearchBtn" onclick="document.getElementById('groupSearchInput').focus()"><i class="fa-solid fa-magnifying-glass"></i></button>
      <button type="button" class="icon-round-btn hidden" id="headerChatCreateBtn" onclick="openGroupCreateModal()" title="오픈채팅 만들기" style="position:relative;">
        <i class="fa-solid fa-comment" style="font-size:15px;"></i>
        <span style="position:absolute;right:2px;bottom:2px;width:12px;height:12px;border-radius:50%;background:var(--primary);color:#fff;font-size:8px;display:flex;align-items:center;justify-content:center;border:1.5px solid var(--bg-card);"><i class="fa-solid fa-plus" style="font-size:7px;"></i></span>
      </button>
      <button class="icon-round-btn" id="headerSettingsBtn" onclick="openSettingsScreen()"><i class="fa-solid fa-gear"></i></button>"""
html = html.replace(old1, new1)

# 2) updateHeaderForTab: 새 버튼 기본 숨김 + tab-chat일 때만 노출
old2 = """  const communitySearchRow = document.getElementById('communitySearchRow');
  ptsWrap.classList.add('hidden'); writeBtn.classList.add('hidden'); filterBar.classList.remove('hidden');
  homeSearchWrap.classList.add('hidden'); homeAdBannerRow.classList.add('hidden'); communitySearchRow.classList.add('hidden');
  document.getElementById('homeSearchDropdown').classList.add('hidden');
  if (tab==='tab-home'){ title.textContent='실시간 친구들'; ptsWrap.classList.remove('hidden'); homeSearchWrap.classList.remove('hidden'); homeAdBannerRow.classList.remove('hidden'); }
  else if (tab==='tab-community'){ title.textContent='일상 이야기'; writeBtn.classList.remove('hidden'); ptsWrap.classList.remove('hidden'); communitySearchRow.classList.remove('hidden'); }
  else if (tab==='tab-chat'){ title.textContent='채팅'; filterBar.classList.add('hidden'); }
  else { title.textContent='설정'; filterBar.classList.add('hidden'); }
}"""
assert html.count(old2) == 1, "old2 매칭 실패"
new2 = """  const communitySearchRow = document.getElementById('communitySearchRow');
  const chatSearchBtn = document.getElementById('headerChatSearchBtn');
  const chatCreateBtn = document.getElementById('headerChatCreateBtn');
  ptsWrap.classList.add('hidden'); writeBtn.classList.add('hidden'); filterBar.classList.remove('hidden');
  homeSearchWrap.classList.add('hidden'); homeAdBannerRow.classList.add('hidden'); communitySearchRow.classList.add('hidden');
  chatSearchBtn.classList.add('hidden'); chatCreateBtn.classList.add('hidden');
  document.getElementById('homeSearchDropdown').classList.add('hidden');
  if (tab==='tab-home'){ title.textContent='실시간 친구들'; ptsWrap.classList.remove('hidden'); homeSearchWrap.classList.remove('hidden'); homeAdBannerRow.classList.remove('hidden'); }
  else if (tab==='tab-community'){ title.textContent='일상 이야기'; writeBtn.classList.remove('hidden'); ptsWrap.classList.remove('hidden'); communitySearchRow.classList.remove('hidden'); }
  else if (tab==='tab-chat'){ title.textContent='채팅'; filterBar.classList.add('hidden'); chatSearchBtn.classList.remove('hidden'); chatCreateBtn.classList.remove('hidden'); }
  else { title.textContent='설정'; filterBar.classList.add('hidden'); }
}"""
html = html.replace(old2, new2)

# 3) 채팅탭 아이콘줄(chatListIconRow) 통째로 삭제 - 검색/오픈채팅만들기는 헤더로 이동, 설정버튼은 중복이라 삭제
old3 = """      <div id="chatListIconRow" style="display:flex;gap:8px;padding:10px 14px;align-items:center;">
        <button type="button" onclick="toggleChatListSearch()" style="flex-shrink:0;width:36px;height:36px;border-radius:50%;border:1px solid var(--border-color);background:var(--bg-card);color:inherit;font-size:14px;"><i class="fa-solid fa-magnifying-glass"></i></button>
        <div id="openChatCreateEntry" onclick="openGroupCreateModal()" title="오픈채팅 만들기" style="flex-shrink:0;width:36px;height:36px;border-radius:50%;border:1px solid var(--border-color);background:var(--bg-card);cursor:pointer;position:relative;display:flex;align-items:center;justify-content:center;">
          <i class="fa-solid fa-comment" style="font-size:15px;color:var(--primary);"></i>
          <span style="position:absolute;right:-2px;bottom:-2px;width:13px;height:13px;border-radius:50%;background:var(--primary);color:#fff;font-size:9px;display:flex;align-items:center;justify-content:center;border:1.5px solid var(--bg-card);"><i class="fa-solid fa-plus" style="font-size:8px;"></i></span>
        </div>
        <div style="flex:1;"></div>
        <button type="button" onclick="openSettingsScreen()" style="flex-shrink:0;width:36px;height:36px;border-radius:50%;border:1px solid var(--border-color);background:var(--bg-card);color:inherit;font-size:14px;"><i class="fa-solid fa-gear"></i></button>
      </div>
      <div id="chatListSearchRow" class="hidden" style="padding:0 14px 8px;">"""
assert html.count(old3) == 1, "old3 매칭 실패"
new3 = """      <div id="chatListSearchRow" style="padding:8px 14px 8px;">"""
html = html.replace(old3, new3)

# 4) 이제 안 쓰는 toggleChatListSearch 함수 삭제(검색창이 상시노출로 바뀌어 토글 불필요)
old4 = """// 채팅방 검색: 1:1 채팅 + 내가 이미 들어간 단체채팅방(로컬 필터) + 아직 안 들어간 공개 단체채팅방(서버 검색)을 한번에 보여줌
// 0-54: 돋보기 아이콘을 눌러야 검색창이 나타나게 함(평소엔 광고란+오픈채팅 만들기 칸이 그 자리를 대신함)
function toggleChatListSearch(){
  const row = document.getElementById('chatListSearchRow');
  const willShow = row.classList.contains('hidden');
  row.classList.toggle('hidden');
  if (willShow) {
    document.getElementById('groupSearchInput').focus();
  } else {
    document.getElementById('groupSearchInput').value = '';
    onGroupSearchInput('');
  }
}
"""
assert html.count(old4) == 1, "old4 매칭 실패"
html = html.replace(old4, "// 채팅방 검색: 1:1 채팅 + 내가 이미 들어간 단체채팅방(로컬 필터) + 아직 안 들어간 공개 단체채팅방(서버 검색)을 한번에 보여줌\n// 0-79: 검색창이 상시노출로 바뀌면서(예전엔 아이콘 눌러야 나타남) toggleChatListSearch는 더 이상 필요 없어 제거됨\n")

FILE.write_text(html, encoding="utf-8")
print("0-79 패치 완료")