# -*- coding: utf-8 -*-
CLIENT = 'malbeot-app/public/index.html'

def read(p):
    with open(p, 'r', encoding='utf-8') as f:
        return f.read()

def write(p, s):
    with open(p, 'w', encoding='utf-8') as f:
        f.write(s)

def must_replace(text, old, new, label):
    cnt = text.count(old)
    if cnt != 1:
        raise SystemExit(f"[실패] {label}: old_str 매칭 개수={cnt} (1이어야 함) - 패치 중단")
    return text.replace(old, new)

c = read(CLIENT)

# ===== 0-39-A: 프로필 취미도 MBTI/목적처럼 아코디언으로 접고 펼 수 있게 =====
old_open = "const interestSubAccOpen = { mbti:false, purpose:false };"
new_open = "const interestSubAccOpen = { mbti:false, purpose:false, hobby:false };"
c = must_replace(c, old_open, new_open, "interestSubAccOpen에 hobby 추가")

old_hobby_html = """      <div class="settings-list-item" style="flex-direction:column;align-items:stretch;cursor:default;padding:8px 0;">
        <div class="sli-label" style="margin-bottom:8px;">취미 (여러 개 선택 가능)</div>
        <div id="myHobbyTagList" style="display:flex;flex-wrap:wrap;gap:6px;"></div>
      </div>"""

new_hobby_html = """      <div class="settings-list-item" style="flex-direction:column;align-items:stretch;cursor:default;padding:8px 0;">
        <div class="sli-label interest-subacc-header" onclick="toggleInterestSubAcc('hobby')">
          <span>취미<span class="interest-subacc-current" id="myHobbyCurrentLabel"></span></span>
          <i class="fa-solid fa-chevron-down interest-subacc-arrow" id="myHobbySubAccArrow"></i>
        </div>
        <div id="myHobbyTagList" style="display:none;flex-wrap:wrap;gap:6px;margin-top:8px;"></div>
      </div>"""

c = must_replace(c, old_hobby_html, new_hobby_html, "취미 섹션 아코디언 헤더로 변경")

old_hobby_render = """  document.getElementById('myHobbyTagList').innerHTML =
    `<span class="tag interest-select-tag ${!(interests.hobbies&&interests.hobbies.length)?'selected':''}" onclick="clearHobbyInterests()">선택 안 함</span>` +
    HOBBY_OPTIONS.map(o=>
      `<span class="tag interest-select-tag ${(interests.hobbies||[]).includes(o.key)?'selected':''}" onclick="toggleHobbyInterest('${o.key}')">${hobbyLabel(o,gender)}</span>`
    ).join('');
}"""

new_hobby_render = """  const selectedHobbies = interests.hobbies || [];
  document.getElementById('myHobbyCurrentLabel').textContent = selectedHobbies.length
    ? selectedHobbies.map(k=>{ const o=HOBBY_OPTIONS.find(h=>h.key===k); return o?hobbyLabel(o,gender):k; }).join(', ')
    : '선택 안 함';
  document.getElementById('myHobbyTagList').style.display = interestSubAccOpen.hobby ? 'flex' : 'none';
  document.getElementById('myHobbySubAccArrow').classList.toggle('open', interestSubAccOpen.hobby);
  document.getElementById('myHobbyTagList').innerHTML =
    `<span class="tag interest-select-tag ${!selectedHobbies.length?'selected':''}" onclick="clearHobbyInterests()">선택 안 함</span>` +
    HOBBY_OPTIONS.map(o=>
      `<span class="tag interest-select-tag ${selectedHobbies.includes(o.key)?'selected':''}" onclick="toggleHobbyInterest('${o.key}')">${hobbyLabel(o,gender)}</span>`
    ).join('');
}"""

c = must_replace(c, old_hobby_render, new_hobby_render, "취미 렌더링에 아코디언 열림상태/현재라벨 반영")

# ===== 0-39-B: 설명글(자기소개) 옆에 연필 아이콘 - 바로 인라인 수정 =====
old_bio_box = '<div class="profile-bio-box">${escapeHtml(user.bio||\'등록된 자기소개가 없습니다.\')}</div>'
new_bio_box = """<div class="profile-bio-box" id="profileBioBox" style="position:relative;">
        <span id="profileBioText">${escapeHtml(user.bio||'등록된 자기소개가 없습니다.')}</span>
        ${isMe?'<i class="fa-solid fa-pen" style="margin-left:8px;color:var(--text-muted);font-size:12px;cursor:pointer;" onclick="startInlineBioEdit()"></i>':''}
      </div>
      ${isMe?`<div id="profileBioEditBox" class="hidden" style="margin-top:-4px;margin-bottom:12px;">
        <textarea id="profileBioEditTextarea" rows="3" style="width:100%;padding:10px 12px;border:1px solid var(--border-color);border-radius:10px;background:var(--bg-input);color:var(--text-main);font-size:13px;box-sizing:border-box;" placeholder="자신만의 이야기를 편하게 소개해주세요."></textarea>
        <div style="display:flex;gap:8px;margin-top:6px;">
          <button class="btn btn-secondary btn-sm" style="flex:1;" onclick="cancelInlineBioEdit()">취소</button>
          <button class="btn btn-primary btn-sm" style="flex:1;" onclick="saveInlineBioEdit()">저장</button>
        </div>
      </div>`:''}"""

c = must_replace(c, old_bio_box, new_bio_box, "자기소개 옆 연필아이콘+인라인수정 UI 추가")

anchor2 = "// 관심사는 다른 알림 키워드처럼 선택 즉시 서버에 저장됨\nfunction saveInterestsField(next){"
new_anchor2 = """// 0-39: 자기소개 인라인 수정(연필 아이콘 클릭시 텍스트 대신 textarea로 바로 전환)
function startInlineBioEdit(){
  const box = document.getElementById('profileBioBox');
  const editBox = document.getElementById('profileBioEditBox');
  if (!box || !editBox) return;
  document.getElementById('profileBioEditTextarea').value = (currentUser && currentUser.bio) || '';
  box.classList.add('hidden');
  editBox.classList.remove('hidden');
  document.getElementById('profileBioEditTextarea').focus();
}
function cancelInlineBioEdit(){
  const box = document.getElementById('profileBioBox');
  const editBox = document.getElementById('profileBioEditBox');
  if (!box || !editBox) return;
  editBox.classList.add('hidden');
  box.classList.remove('hidden');
}
function saveInlineBioEdit(){
  const bio = (document.getElementById('profileBioEditTextarea').value || '').trim();
  socket.emit('profile:update', { bio }, (res)=>{
    if (res && res.success){
      currentUser = res.user; saveSession();
      document.getElementById('profileBioText').textContent = bio || '등록된 자기소개가 없습니다.';
      cancelInlineBioEdit();
    } else {
      showMiniAlert((res && res.message) || '저장 중 오류가 발생했습니다.', [{label:'확인', primary:true}]);
    }
  });
}
// 관심사는 다른 알림 키워드처럼 선택 즉시 서버에 저장됨
function saveInterestsField(next){"""

c = must_replace(c, anchor2, new_anchor2, "자기소개 인라인 수정 함수 3개 추가")

write(CLIENT, c)
print("✅ malbeot-app/public/index.html 패치 완료 (취미 아코디언 + 자기소개 인라인수정)")
