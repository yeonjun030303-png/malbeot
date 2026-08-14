# 0-41: 프로필 화면에서 전화번호 표시 제거(본인이 봐도 안 보임) + 설정화면 "계정" 항목의
#       로그아웃/회원탈퇴 버튼 바로 밑에만 전화번호를 읽기전용으로 표시

path_h = "public/index.html"
with open(path_h, "r", encoding="utf-8") as f:
    h = f.read()

# 1) 프로필 화면에서 전화번호 줄 제거
old = '''      ${isMe?`<div style="font-size:12px;color:var(--text-muted);margin:2px 0 6px 0;"><i class="fa-solid fa-phone" style="margin-right:4px;"></i>${user.phone?formatPhoneDisplay(user.phone):'전화번호 미등록'}</div>`:''}
      <div class="profile-tags"><span class="tag">${user.region}</span><span class="tag">${user.gender==='female'?'여성':'남성'}</span><span class="tag">${user.age}세</span></div>'''
assert old in h, "프로필 전화번호 표시 줄을 찾을 수 없습니다"
h = h.replace(old, '''      <div class="profile-tags"><span class="tag">${user.region}</span><span class="tag">${user.gender==='female'?'여성':'남성'}</span><span class="tag">${user.age}세</span></div>''')
print("✅ [1/3] 프로필 화면 전화번호 표시 제거 완료")

# 2) 설정 > 계정 - 로그아웃/회원탈퇴 버튼 바로 밑에 전화번호(읽기전용) 항목 추가
old = '''      <div class="settings-list-item" style="flex-direction:column;align-items:stretch;cursor:default;gap:8px;">
        <button type="button" class="btn btn-secondary btn-block" style="color:var(--danger);" onclick="triggerLogout()"><i class="fa-solid fa-right-from-bracket"></i> 로그아웃</button>
        <button type="button" class="btn btn-secondary btn-block" style="color:var(--danger);" onclick="triggerWithdraw()"><i class="fa-solid fa-user-slash"></i> 회원탈퇴</button>
      </div>'''
assert old in h, "로그아웃/회원탈퇴 버튼 블록을 찾을 수 없습니다"
new = old + '''
      <div class="settings-list-item" style="cursor:default;">
        <div class="sli-label">전화번호</div>
        <div class="sli-right" id="settingsPhoneLabel"></div>
      </div>'''
h = h.replace(old, new)
print("✅ [2/3] 설정화면 로그아웃 밑에 전화번호 항목 추가 완료")

# 3) openSettingsScreen()에서 전화번호 값 채워넣기
old = '''  document.getElementById('blockedCountLabel').textContent = (currentUser && currentUser.blockedUserIds ? currentUser.blockedUserIds.length : 0) + '명';'''
assert old in h, "openSettingsScreen 초기화 로직을 찾을 수 없습니다"
new = old + '''
  document.getElementById('settingsPhoneLabel').textContent = (currentUser && currentUser.phone) ? formatPhoneDisplay(currentUser.phone) : '미등록';'''
h = h.replace(old, new)
print("✅ [3/3] 설정화면 오픈 시 전화번호 값 채우기 완료")

with open(path_h, "w", encoding="utf-8") as f:
    f.write(h)
print("0-41 패치 전체 완료")