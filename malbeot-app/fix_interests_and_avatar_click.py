#!/usr/bin/env python3
# 0-13: 관심사(MBTI/목적/취미) 기능 추가 + 채팅목록 사진 클릭 시 프로필로 이동하도록 수정
#
# 구현 범위:
#  A) 설정화면 맨 아래에 "관심사" 아코디언 섹션 신설
#     - MBTI 16개 중 1개 선택
#     - 목적(가볍게 만날 사람 / 연락만 할 사람 / 진지하게 만날 사람) 중 1개 선택
#     - 취미(스포츠/액티비티/집순이·집돌이(성별에 따라 자동 표기)/넷플 몰아보기/게임/여행/맛집탐방/카페투어/독서/반려동물/헬스운동/음악감상/요리/사진영상) 다중 선택
#     - 선택 즉시 서버에 저장(키워드 알림 추가/삭제와 동일한 방식, 별도 "저장" 버튼 없음)
#  B) 프로필 화면(별명 밑 지역/성별/나이 태그 바로 아래)에 본인이 설정한 관심사만 같은 스타일 태그로 표시
#     - 보고 있는 사람(나)과 겹치는 항목은 진하게/강조색으로 표시
#  C) 버그 수정: 채팅목록(1:1)에서 사진(아바타)을 클릭하면 지금까지는 무조건 그 채팅방으로 들어갔는데,
#     이제 사진을 클릭하면 프로필로, 그 외(닉네임/마지막 메시지 영역)를 클릭하면 기존처럼 채팅방으로 들어가도록 분리함
#     (채팅목록 검색결과의 1:1 채팅 매칭 항목도 동일하게 수정)
#
# 실행 위치: malbeot-app 폴더 안에서 python3 fix_interests_and_avatar_click.py

import sys

def patch(path, replacements):
    with open(path, encoding='utf-8') as f:
        content = f.read()
    for old, new, label in replacements:
        count = content.count(old)
        if count != 1:
            print(f"[실패] {path}: '{label}' 패턴이 {count}번 발견됨 (1번이어야 함) -> {old[:60]!r}")
            sys.exit(1)
        content = content.replace(old, new)
        print(f"[적용] {path} - {label}")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"[완료] {path} 저장\n")

replacements = [

# ── 1) CSS: 관심사 선택 태그 + 겹침 강조 태그 스타일 ──
(
""".tag{font-size:11px;padding:2px 7px;border-radius:var(--radius-sm);background:var(--bg-subtle);color:var(--text-muted);font-weight:600;}""",
""".tag{font-size:11px;padding:2px 7px;border-radius:var(--radius-sm);background:var(--bg-subtle);color:var(--text-muted);font-weight:600;}
.tag-match{background:var(--primary)!important;color:#fff!important;font-weight:800;}
.interest-select-tag{cursor:pointer;-webkit-tap-highlight-color:transparent;}
.interest-select-tag.selected{background:var(--primary);color:#fff;font-weight:700;}""",
"관심사 태그(선택/겹침강조) CSS 추가"
),

# ── 2) 설정화면 맨 아래에 "관심사" 아코디언 섹션 신설 ──
(
"""      <div class="settings-list-item" style="cursor:default;">
        <div class="sli-label">버전 정보</div>
        <div class="sli-right" id="appVersionLabel">v1.0.0</div>
      </div>
      </div>
    </div>
    <div style="position:absolute;left:0;right:0;bottom:0;padding:14px 18px;background:var(--bg-app);border-top:1px solid var(--border-color);">""",
"""      <div class="settings-list-item" style="cursor:default;">
        <div class="sli-label">버전 정보</div>
        <div class="sli-right" id="appVersionLabel">v1.0.0</div>
      </div>
      </div>

      <div class="settings-section-title settings-accordion-header" id="accHeader-acc-interest" onclick="toggleSettingsAccordion('acc-interest')">
        <span>관심사</span><i class="fa-solid fa-chevron-down accordion-arrow"></i>
      </div>
      <div class="settings-accordion-body" id="acc-interest">
      <div class="settings-list-item" style="flex-direction:column;align-items:stretch;cursor:default;">
        <div class="sli-label" style="margin-bottom:8px;">MBTI</div>
        <div id="mbtiTagList" style="display:flex;flex-wrap:wrap;gap:6px;"></div>
      </div>
      <div class="settings-list-item" style="flex-direction:column;align-items:stretch;cursor:default;">
        <div class="sli-label" style="margin-bottom:8px;">목적</div>
        <div id="purposeTagList" style="display:flex;flex-wrap:wrap;gap:6px;"></div>
      </div>
      <div class="settings-list-item" style="flex-direction:column;align-items:stretch;cursor:default;">
        <div class="sli-label" style="margin-bottom:8px;">취미 (여러 개 선택 가능)</div>
        <div id="hobbyTagList" style="display:flex;flex-wrap:wrap;gap:6px;"></div>
      </div>
      </div>
    </div>
    <div style="position:absolute;left:0;right:0;bottom:0;padding:14px 18px;background:var(--bg-app);border-top:1px solid var(--border-color);">""",
"설정화면 맨 아래 '관심사' 아코디언 섹션 추가"
),

# ── 3) 아코디언 접힘/펼침 대상 목록에 acc-interest 추가 ──
(
"""  const allIds = ['acc-notify','acc-account','acc-display','acc-info'];""",
"""  const allIds = ['acc-notify','acc-account','acc-display','acc-info','acc-interest'];""",
"toggleSettingsAccordion 대상 목록에 acc-interest 추가"
),

# ── 4) 관심사 선택 데이터/렌더/저장 함수 신설 + 설정화면 진입 시 렌더 호출 ──
(
"""/* ===================== 설정 화면 ===================== */
function openSettingsScreen(){""",
"""/* ===================== 관심사(MBTI/목적/취미) ===================== */
const MBTI_TYPES = ['INTJ','INTP','ENTJ','ENTP','INFJ','INFP','ENFJ','ENFP','ISTJ','ISFJ','ESTJ','ESFJ','ISTP','ISFP','ESTP','ESFP'];
const PURPOSE_OPTIONS = [
  {key:'light', label:'가볍게 만날 사람'},
  {key:'contact', label:'연락만 할 사람'},
  {key:'serious', label:'진지하게 만날 사람'}
];
const HOBBY_OPTIONS = [
  {key:'sports', label:'스포츠'},
  {key:'activity', label:'액티비티'},
  {key:'homebody', label:{female:'집순이', male:'집돌이'}},
  {key:'netflix', label:'넷플 몰아보기'},
  {key:'game', label:'게임'},
  {key:'travel', label:'여행'},
  {key:'food', label:'맛집 탐방'},
  {key:'cafe', label:'카페 투어'},
  {key:'reading', label:'독서'},
  {key:'pet', label:'반려동물'},
  {key:'fitness', label:'헬스/운동'},
  {key:'music', label:'음악감상'},
  {key:'cooking', label:'요리'},
  {key:'photo', label:'사진/영상'}
];
function hobbyLabel(opt, gender){ return typeof opt.label==='object' ? (opt.label[gender==='male'?'male':'female']) : opt.label; }
// 설정화면의 관심사 아코디언(MBTI/목적/취미) 태그를 현재 내 선택 상태에 맞춰 다시 그림
function renderInterestSettingsUI(){
  if (!currentUser) return;
  const interests = currentUser.interests || {};
  const gender = currentUser.gender || 'female';
  document.getElementById('mbtiTagList').innerHTML = MBTI_TYPES.map(t=>
    `<span class="tag interest-select-tag ${interests.mbti===t?'selected':''}" onclick="toggleMbtiInterest('${t}')">${t}</span>`
  ).join('');
  document.getElementById('purposeTagList').innerHTML = PURPOSE_OPTIONS.map(o=>
    `<span class="tag interest-select-tag ${interests.purpose===o.key?'selected':''}" onclick="togglePurposeInterest('${o.key}')">${o.label}</span>`
  ).join('');
  document.getElementById('hobbyTagList').innerHTML = HOBBY_OPTIONS.map(o=>
    `<span class="tag interest-select-tag ${(interests.hobbies||[]).includes(o.key)?'selected':''}" onclick="toggleHobbyInterest('${o.key}')">${hobbyLabel(o,gender)}</span>`
  ).join('');
}
// 관심사는 다른 알림 키워드처럼 선택 즉시 서버에 저장됨(설정화면의 '저장' 버튼과 무관)
function saveInterestsField(next){
  socket.emit('profile:update', { interests: next }, (res)=>{
    if (res && res.success){ currentUser = res.user; saveSession(); renderInterestSettingsUI(); }
  });
}
function toggleMbtiInterest(t){
  const cur = currentUser.interests || {};
  saveInterestsField({ ...cur, mbti: cur.mbti===t ? null : t });
}
function togglePurposeInterest(k){
  const cur = currentUser.interests || {};
  saveInterestsField({ ...cur, purpose: cur.purpose===k ? null : k });
}
function toggleHobbyInterest(k){
  const cur = currentUser.interests || {};
  const hobbies = cur.hobbies || [];
  const nextHobbies = hobbies.includes(k) ? hobbies.filter(h=>h!==k) : [...hobbies, k];
  saveInterestsField({ ...cur, hobbies: nextHobbies });
}
/* ===================== 설정 화면 ===================== */
function openSettingsScreen(){""",
"관심사 데이터/렌더/저장 함수 신설"
),
(
"""  renderKeywordTags();
  document.getElementById('adminModeRow').style.display = (currentUser && currentUser.isAdmin) ? 'flex' : 'none';""",
"""  renderKeywordTags();
  renderInterestSettingsUI();
  document.getElementById('adminModeRow').style.display = (currentUser && currentUser.isAdmin) ? 'flex' : 'none';""",
"설정화면 진입 시 관심사 태그 렌더 호출 추가"
),

# ── 5) 프로필 화면: 지역/성별/나이 태그 바로 밑에 본인이 설정한 관심사만 태그로 표시(겹치면 강조) ──
(
"""      <div class="profile-tags"><span class="tag">${user.region}</span><span class="tag">${user.gender==='female'?'여성':'남성'}</span><span class="tag">${user.age}세</span></div>
      <div class="profile-bio-box">${escapeHtml(user.bio||'등록된 자기소개가 없습니다.')}</div>""",
"""      <div class="profile-tags"><span class="tag">${user.region}</span><span class="tag">${user.gender==='female'?'여성':'남성'}</span><span class="tag">${user.age}세</span></div>
      ${buildInterestTagsHtml(user)}
      <div class="profile-bio-box">${escapeHtml(user.bio||'등록된 자기소개가 없습니다.')}</div>""",
"프로필 화면 지역/성별/나이 태그 밑에 관심사 태그 표시 추가"
),
(
"""function renderProfileDetail(user){""",
"""// 프로필 대상자가 설정한 관심사(MBTI/목적/취미)만 태그로 만들어줌.
// 보고 있는 사람(나)의 관심사와 겹치는 항목은 tag-match 클래스로 강조 표시함(본인 프로필에서는 강조 안 함)
function buildInterestTagsHtml(user){
  const interests = user.interests || {};
  const myInterests = (currentUser && currentUser.interests) || {};
  const isMe = currentUser && user.id===currentUser.id;
  const gender = user.gender || 'female';
  const parts = [];
  if (interests.mbti){
    const match = !isMe && myInterests.mbti && myInterests.mbti===interests.mbti;
    parts.push(`<span class="tag ${match?'tag-match':''}">${interests.mbti}</span>`);
  }
  if (interests.purpose){
    const po = PURPOSE_OPTIONS.find(o=>o.key===interests.purpose);
    if (po){
      const match = !isMe && myInterests.purpose && myInterests.purpose===interests.purpose;
      parts.push(`<span class="tag ${match?'tag-match':''}">${po.label}</span>`);
    }
  }
  (interests.hobbies||[]).forEach(h=>{
    const ho = HOBBY_OPTIONS.find(o=>o.key===h);
    if (!ho) return;
    const match = !isMe && (myInterests.hobbies||[]).includes(h);
    parts.push(`<span class="tag ${match?'tag-match':''}">${hobbyLabel(ho,gender)}</span>`);
  });
  if (!parts.length) return '';
  return `<div class="profile-tags" style="flex-wrap:wrap;margin-top:0;">${parts.join('')}</div>`;
}
function renderProfileDetail(user){""",
"관심사 태그 HTML 생성 함수(buildInterestTagsHtml) 신설"
),

# ── 6) 버그 수정: 채팅목록 1:1 행에서 사진(아바타) 클릭 시 채팅방이 아니라 프로필로 이동 ──
(
"""      <div class="chat-row-fg" data-roomid="${room.roomId}">
        ${avatarHtmlFor(target,'avatar-sm')}
        <div class="chat-row-text">
          <div class="chat-row-nick">${escapeHtml(target.nickname||'')}</div>
          <div class="chat-row-last">${escapeHtml(lastPreview)}</div>
        </div>
        <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px;">
          <div class="chat-row-time">${lastMsg.timestamp?formatRelativeTime(lastMsg.timestamp):''}</div>
          ${unread>0?`<div class="unread-badge">${unread>99?'99+':unread}</div>`:''}
        </div>
      </div>`;
    const fg = wrap.querySelector('.chat-row-fg');
    attachSwipe(fg);
    fg.addEventListener('click', ()=>{ if (fg.dataset.swiped==='1') return; openChatModal(room.roomId, target, room.messages); });""",
"""      <div class="chat-row-fg" data-roomid="${room.roomId}">
        <span onclick="event.stopPropagation();openProfileDetailScreen('${target.id}')" style="cursor:pointer;display:inline-block;">${avatarHtmlFor(target,'avatar-sm')}</span>
        <div class="chat-row-text">
          <div class="chat-row-nick">${escapeHtml(target.nickname||'')}</div>
          <div class="chat-row-last">${escapeHtml(lastPreview)}</div>
        </div>
        <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px;">
          <div class="chat-row-time">${lastMsg.timestamp?formatRelativeTime(lastMsg.timestamp):''}</div>
          ${unread>0?`<div class="unread-badge">${unread>99?'99+':unread}</div>`:''}
        </div>
      </div>`;
    const fg = wrap.querySelector('.chat-row-fg');
    attachSwipe(fg);
    fg.addEventListener('click', ()=>{ if (fg.dataset.swiped==='1') return; openChatModal(room.roomId, target, room.messages); });""",
"채팅목록 1:1 행 사진 클릭 시 프로필로 이동(기존엔 채팅방으로 이동하던 버그)"
),

# ── 7) 버그 수정: 채팅목록 검색결과의 1:1 채팅 매칭 행도 사진 클릭 시 프로필로 이동 ──
(
"""        wrap.innerHTML = `<div class="chat-row-fg">
          ${avatarHtmlFor(target,'avatar-sm')}
          <div class="chat-row-text"><div class="chat-row-nick">${escapeHtml(target.nickname||'')}</div></div>
        </div>`;
        wrap.querySelector('.chat-row-fg').addEventListener('click', ()=>{ clearGroupSearch(); openChatModal(r.roomId, target, r.messages); });""",
"""        wrap.innerHTML = `<div class="chat-row-fg">
          <span onclick="event.stopPropagation();openProfileDetailScreen('${target.id}')" style="cursor:pointer;display:inline-block;">${avatarHtmlFor(target,'avatar-sm')}</span>
          <div class="chat-row-text"><div class="chat-row-nick">${escapeHtml(target.nickname||'')}</div></div>
        </div>`;
        wrap.querySelector('.chat-row-fg').addEventListener('click', ()=>{ clearGroupSearch(); openChatModal(r.roomId, target, r.messages); });""",
"채팅목록 검색결과 1:1 매칭 행도 사진 클릭 시 프로필로 이동하도록 수정"
),
]

patch('public/index.html', replacements)

print("다음 순서로 진행하세요:")
print("1) node -c server.js   (서버는 이번 패치에서 변경 없음 - 확인용)")
print("2) git add -A && git commit -m \"0-13: 관심사(MBTI/목적/취미) 기능 추가 + 채팅목록 사진클릭시 프로필 이동 버그 수정\"")
print("3) (모아뒀다가 원하실 때) git push")
