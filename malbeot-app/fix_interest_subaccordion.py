#!/usr/bin/env python3
# 0-14: 관심사 - MBTI/목적을 하위 아코디언(평소엔 접혀있고, 누르면 펼쳐지고, 고르면 자동으로 다시 접힘)으로 변경
#        + 각 항목(MBTI/목적/취미)에 "선택 안 함" 옵션 추가
#
# 구현 범위:
#  A) MBTI/목적 항목이 지금까지는 16개/3개가 항상 다 펼쳐져 있었는데, 이제 평소엔 "MBTI  현재값 ▾" 처럼
#     한 줄로 접혀있다가, 그 줄을 누르면 선택지가 펼쳐지고, 그중 하나를 고르면 저장과 동시에 자동으로 다시 접힘
#     (수동으로 접었다 펴는 게 아니라 선택하면 알아서 접힘)
#  B) MBTI/목적/취미 각각에 "선택 안 함" 칩을 추가해서 한 번에 초기화(선택 해제) 가능하게 함
#  C) 프로필 화면 표기 방식은 기존 그대로 유지(설정한 항목만 태그로 표시, 대문자 MBTI 그대로 - 예: ENTJ)
#
# 실행 위치: malbeot-app 폴더 안에서 python3 fix_interest_subaccordion.py

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

# ── 1) CSS: 하위 아코디언(MBTI/목적) 화살표 회전 애니메이션 ──
(
""".interest-select-tag.selected{background:var(--primary);color:#fff;font-weight:700;}""",
""".interest-select-tag.selected{background:var(--primary);color:#fff;font-weight:700;}
.interest-subacc-header{display:flex;justify-content:space-between;align-items:center;cursor:pointer;-webkit-tap-highlight-color:transparent;}
.interest-subacc-header .interest-subacc-arrow{font-size:11px;color:var(--text-muted);transition:transform .2s;}
.interest-subacc-header .interest-subacc-arrow.open{transform:rotate(180deg);}
.interest-subacc-current{color:var(--primary);font-weight:700;font-size:12px;margin-left:4px;}""",
"관심사 하위 아코디언(MBTI/목적) CSS 추가"
),

# ── 2) 설정화면 마크업: MBTI/목적 항목을 하위 아코디언 헤더+접히는 바디 구조로 변경 ──
(
"""      <div class="settings-list-item" style="flex-direction:column;align-items:stretch;cursor:default;">
        <div class="sli-label" style="margin-bottom:8px;">MBTI</div>
        <div id="mbtiTagList" style="display:flex;flex-wrap:wrap;gap:6px;"></div>
      </div>
      <div class="settings-list-item" style="flex-direction:column;align-items:stretch;cursor:default;">
        <div class="sli-label" style="margin-bottom:8px;">목적</div>
        <div id="purposeTagList" style="display:flex;flex-wrap:wrap;gap:6px;"></div>
      </div>""",
"""      <div class="settings-list-item" style="flex-direction:column;align-items:stretch;cursor:default;">
        <div class="sli-label interest-subacc-header" onclick="toggleInterestSubAcc('mbti')">
          <span>MBTI<span class="interest-subacc-current" id="mbtiCurrentLabel"></span></span>
          <i class="fa-solid fa-chevron-down interest-subacc-arrow" id="mbtiSubAccArrow"></i>
        </div>
        <div id="mbtiTagList" style="display:none;flex-wrap:wrap;gap:6px;margin-top:8px;"></div>
      </div>
      <div class="settings-list-item" style="flex-direction:column;align-items:stretch;cursor:default;">
        <div class="sli-label interest-subacc-header" onclick="toggleInterestSubAcc('purpose')">
          <span>목적<span class="interest-subacc-current" id="purposeCurrentLabel"></span></span>
          <i class="fa-solid fa-chevron-down interest-subacc-arrow" id="purposeSubAccArrow"></i>
        </div>
        <div id="purposeTagList" style="display:none;flex-wrap:wrap;gap:6px;margin-top:8px;"></div>
      </div>""",
"MBTI/목적 항목을 하위 아코디언 헤더+바디 구조로 변경"
),

# ── 3) JS: 하위 아코디언 열림 상태 + 렌더 함수 전면 교체(선택 안 함 옵션 포함) ──
(
"""function hobbyLabel(opt, gender){ return typeof opt.label==='object' ? (opt.label[gender==='male'?'male':'female']) : opt.label; }
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
}""",
"""function hobbyLabel(opt, gender){ return typeof opt.label==='object' ? (opt.label[gender==='male'?'male':'female']) : opt.label; }
// MBTI/목적 하위 아코디언은 기본으로 접혀있고, 항목을 고르면 자동으로 다시 접힘(수동으로 접는 게 아님)
const interestSubAccOpen = { mbti:false, purpose:false };
function toggleInterestSubAcc(cat){
  interestSubAccOpen[cat] = !interestSubAccOpen[cat];
  renderInterestSettingsUI();
}
// 설정화면의 관심사 아코디언(MBTI/목적/취미) 태그를 현재 내 선택 상태 + 하위 아코디언 열림 상태에 맞춰 다시 그림
function renderInterestSettingsUI(){
  if (!currentUser) return;
  const interests = currentUser.interests || {};
  const gender = currentUser.gender || 'female';

  document.getElementById('mbtiCurrentLabel').textContent = interests.mbti || '선택 안 함';
  document.getElementById('mbtiTagList').style.display = interestSubAccOpen.mbti ? 'flex' : 'none';
  document.getElementById('mbtiSubAccArrow').classList.toggle('open', interestSubAccOpen.mbti);
  document.getElementById('mbtiTagList').innerHTML =
    `<span class="tag interest-select-tag ${!interests.mbti?'selected':''}" onclick="toggleMbtiInterest(null)">선택 안 함</span>` +
    MBTI_TYPES.map(t=>
      `<span class="tag interest-select-tag ${interests.mbti===t?'selected':''}" onclick="toggleMbtiInterest('${t}')">${t}</span>`
    ).join('');

  const purposeLabel = PURPOSE_OPTIONS.find(o=>o.key===interests.purpose);
  document.getElementById('purposeCurrentLabel').textContent = purposeLabel ? purposeLabel.label : '선택 안 함';
  document.getElementById('purposeTagList').style.display = interestSubAccOpen.purpose ? 'flex' : 'none';
  document.getElementById('purposeSubAccArrow').classList.toggle('open', interestSubAccOpen.purpose);
  document.getElementById('purposeTagList').innerHTML =
    `<span class="tag interest-select-tag ${!interests.purpose?'selected':''}" onclick="togglePurposeInterest(null)">선택 안 함</span>` +
    PURPOSE_OPTIONS.map(o=>
      `<span class="tag interest-select-tag ${interests.purpose===o.key?'selected':''}" onclick="togglePurposeInterest('${o.key}')">${o.label}</span>`
    ).join('');

  document.getElementById('hobbyTagList').innerHTML =
    `<span class="tag interest-select-tag ${!(interests.hobbies&&interests.hobbies.length)?'selected':''}" onclick="clearHobbyInterests()">선택 안 함</span>` +
    HOBBY_OPTIONS.map(o=>
      `<span class="tag interest-select-tag ${(interests.hobbies||[]).includes(o.key)?'selected':''}" onclick="toggleHobbyInterest('${o.key}')">${hobbyLabel(o,gender)}</span>`
    ).join('');
}
// 관심사는 다른 알림 키워드처럼 선택 즉시 서버에 저장됨(설정화면의 '저장' 버튼과 무관)
function saveInterestsField(next){
  socket.emit('profile:update', { interests: next }, (res)=>{
    if (res && res.success){ currentUser = res.user; saveSession(); renderInterestSettingsUI(); }
  });
}
// MBTI/목적은 단일 선택 - 고르면 저장과 동시에 하위 아코디언이 자동으로 닫힘
function toggleMbtiInterest(t){
  const cur = currentUser.interests || {};
  interestSubAccOpen.mbti = false;
  saveInterestsField({ ...cur, mbti: t });
}
function togglePurposeInterest(k){
  const cur = currentUser.interests || {};
  interestSubAccOpen.purpose = false;
  saveInterestsField({ ...cur, purpose: k });
}
function toggleHobbyInterest(k){
  const cur = currentUser.interests || {};
  const hobbies = cur.hobbies || [];
  const nextHobbies = hobbies.includes(k) ? hobbies.filter(h=>h!==k) : [...hobbies, k];
  saveInterestsField({ ...cur, hobbies: nextHobbies });
}
function clearHobbyInterests(){
  const cur = currentUser.interests || {};
  saveInterestsField({ ...cur, hobbies: [] });
}""",
"MBTI/목적 선택 안 함 옵션 + 하위 아코디언 자동닫힘 로직으로 렌더/저장 함수 전면 교체"
),
]

patch('public/index.html', replacements)

print("다음 순서로 진행하세요:")
print("1) node -c server.js   (서버는 이번 패치에서 변경 없음 - 확인용)")
print("2) git add -A && git commit -m \"0-14: 관심사 MBTI/목적 하위아코디언(선택시 자동닫힘) + 선택 안 함 옵션 추가\"")
print("3) (모아뒀다가 원하실 때) git push")
