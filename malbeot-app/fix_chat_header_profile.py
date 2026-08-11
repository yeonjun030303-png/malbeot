#!/usr/bin/env python3
# 고객센터(챗봇/메일 문의) 기능 추가
# - 설정 화면 > 정보 섹션에 "고객센터" 진입점 추가
# - customerServiceScreen: 챗봇/메일 두 가지 선택 화면
# - supportChatScreen: 카테고리 클릭형 챗봇 대화 UI (봇=상대방쪽/왼쪽, 나=내쪽/오른쪽, 기존 채팅 말풍선 스타일 재사용)
# 실행 위치: malbeot-app 폴더 안에서 python3 fix_customer_service.py

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

html_replacements = [
(
""".msg-bubble.msg-deleted{color:var(--text-muted);font-style:italic;background:var(--bg-subtle)!important;}""",
""".msg-bubble.msg-deleted{color:var(--text-muted);font-style:italic;background:var(--bg-subtle)!important;}
.support-chip-wrap{display:flex;flex-direction:column;gap:6px;margin-top:8px;}
.support-chip{padding:9px 12px;border:1px solid var(--border-color);border-radius:10px;background:var(--bg-app);color:var(--text-main);font-size:13px;text-align:left;cursor:pointer;}
.support-chip:active{background:var(--bg-subtle);}"""
),
(
"""      <div class="settings-accordion-body" id="acc-info">
      <div class="settings-list-item" style="cursor:default;">
        <div class="sli-label">버전 정보</div>
        <div class="sli-right" id="appVersionLabel">v1.0.0</div>
      </div>
      </div>
    </div>""",
"""      <div class="settings-accordion-body" id="acc-info">
      <div class="settings-list-item" onclick="openCustomerServiceScreen()">
        <div class="sli-label">고객센터</div>
        <div class="sli-right"><i class="fa-solid fa-chevron-right"></i></div>
      </div>
      <div class="settings-list-item" style="cursor:default;">
        <div class="sli-label">버전 정보</div>
        <div class="sli-right" id="appVersionLabel">v1.0.0</div>
      </div>
      </div>
    </div>"""
),
(
"""  <div id="adminScreen" class="full-screen-overlay">""",
"""  <div id="customerServiceScreen" class="full-screen-overlay">
    <div class="fs-header">
      <button class="back-btn" onclick="closeFullScreen('customerServiceScreen')"><i class="fa-solid fa-arrow-left"></i></button>
      <div class="fs-title">고객센터</div>
    </div>
    <div class="fs-body" style="padding:18px;">
      <div class="settings-list-item" onclick="openSupportChatScreen()" style="border:1px solid var(--border-color);border-radius:12px;padding:16px;margin-bottom:12px;">
        <div style="display:flex;align-items:center;gap:12px;">
          <div style="width:40px;height:40px;border-radius:50%;background:var(--primary,#4a90e2);color:#fff;display:flex;align-items:center;justify-content:center;font-size:18px;"><i class="fa-solid fa-robot"></i></div>
          <div><div class="sli-label">챗봇 고객센터</div><div class="sli-sub">자주 묻는 질문을 바로 확인해보세요</div></div>
        </div>
        <div class="sli-right"><i class="fa-solid fa-chevron-right"></i></div>
      </div>
      <div class="settings-list-item" onclick="openSupportMailCompose()" style="border:1px solid var(--border-color);border-radius:12px;padding:16px;">
        <div style="display:flex;align-items:center;gap:12px;">
          <div style="width:40px;height:40px;border-radius:50%;background:var(--bg-subtle);display:flex;align-items:center;justify-content:center;font-size:18px;"><i class="fa-solid fa-envelope"></i></div>
          <div><div class="sli-label">1:1 메일 문의</div><div class="sli-sub">kickoff030303@gmail.com</div></div>
        </div>
        <div class="sli-right"><i class="fa-solid fa-chevron-right"></i></div>
      </div>
    </div>
  </div>

  <div id="supportChatScreen" class="full-screen-overlay">
    <div class="fs-header">
      <button class="back-btn" onclick="closeFullScreen('supportChatScreen')"><i class="fa-solid fa-arrow-left"></i></button>
      <div class="fs-title">챗봇 고객센터</div>
    </div>
    <div class="fs-body" id="supportChatArea" style="padding:14px 14px 100px 14px;display:flex;flex-direction:column;gap:10px;overflow-y:auto;"></div>
  </div>

  <div id="adminScreen" class="full-screen-overlay">"""
),
(
"""/* ===================== 차단한 회원 목록 ===================== */
function openBlockedListScreen(){""",
"""/* ===================== 고객센터 챗봇 ===================== */
const SUPPORT_TOPICS = [
  { id:'account', label:'계정 · 로그인 문제', answer:'로그인이 안 되시나요? 카카오 계정 연결 상태를 확인해주시고, 그래도 안 되면 앱을 완전히 종료 후 다시 실행해보세요. 계속 문제가 있으면 1:1 메일 문의로 카카오 닉네임과 상황을 알려주세요.' },
  { id:'report', label:'신고 · 차단 문의', answer:'신고하신 내용은 관리자가 순차적으로 확인하고 있습니다. 처리 결과는 별도 알림으로 안내드리지 않으니, 급한 건은 1:1 메일 문의로 신고 대상과 사유를 함께 보내주세요.' },
  { id:'payment', label:'결제 · 환불 문의', answer:'결제(쌀 충전 등)는 결제 즉시 적용되며, 서비스 이용약관에 따라 원칙적으로 환불이 불가합니다. 결제 오류(중복 결제 등)가 의심되면 1:1 메일 문의로 결제 일시와 내역을 알려주세요.' },
  { id:'bug', label:'버그 · 오류 신고', answer:'불편을 드려 죄송합니다. 어떤 화면에서 어떤 동작을 했을 때 문제가 발생했는지 최대한 자세히 1:1 메일 문의로 보내주시면 빠르게 확인하겠습니다.' },
  { id:'etc', label:'기타 문의', answer:'그 밖의 문의사항은 1:1 메일 문의로 편하게 남겨주세요. 확인 후 답변드리겠습니다.' }
];
function openCustomerServiceScreen(){ openFullScreen('customerServiceScreen'); }
function openSupportMailCompose(subject){
  const s = encodeURIComponent(subject ? `[말벗 문의] ${subject}` : '[말벗 문의]');
  window.location.href = `mailto:kickoff030303@gmail.com?subject=${s}`;
}
function openSupportChatScreen(){
  const area = document.getElementById('supportChatArea');
  area.innerHTML = '';
  openFullScreen('supportChatScreen');
  supportBotSay('안녕하세요! 말벗 챗봇 고객센터입니다. 아래에서 궁금하신 항목을 선택해주세요.');
  supportShowTopicChips();
}
function supportScrollToBottom(){
  const area = document.getElementById('supportChatArea');
  area.scrollTop = area.scrollHeight;
}
function supportBotSay(text){
  const area = document.getElementById('supportChatArea');
  const row = document.createElement('div'); row.className = 'msg-row other';
  const bubble = document.createElement('div'); bubble.className = 'msg-bubble';
  bubble.textContent = text;
  row.appendChild(bubble); area.appendChild(row);
  supportScrollToBottom();
}
function supportUserSay(text){
  const area = document.getElementById('supportChatArea');
  const row = document.createElement('div'); row.className = 'msg-row mine';
  const bubble = document.createElement('div'); bubble.className = 'msg-bubble';
  bubble.textContent = text;
  row.appendChild(bubble); area.appendChild(row);
  supportScrollToBottom();
}
function supportShowTopicChips(){
  const area = document.getElementById('supportChatArea');
  const wrap = document.createElement('div'); wrap.className = 'support-chip-wrap';
  SUPPORT_TOPICS.forEach(t=>{
    const btn = document.createElement('button');
    btn.className = 'support-chip'; btn.type = 'button'; btn.textContent = t.label;
    btn.onclick = ()=> supportSelectTopic(t.id);
    wrap.appendChild(btn);
  });
  const mailBtn = document.createElement('button');
  mailBtn.className = 'support-chip'; mailBtn.type = 'button';
  mailBtn.innerHTML = '<i class="fa-solid fa-envelope"></i> 1:1 메일로 문의하기';
  mailBtn.onclick = ()=> openSupportMailCompose();
  wrap.appendChild(mailBtn);
  area.appendChild(wrap);
  supportScrollToBottom();
}
function supportSelectTopic(topicId){
  const topic = SUPPORT_TOPICS.find(t=>t.id===topicId);
  if (!topic) return;
  document.querySelectorAll('#supportChatArea .support-chip-wrap').forEach(w=>w.remove());
  supportUserSay(topic.label);
  setTimeout(()=>{
    supportBotSay(topic.answer);
    setTimeout(()=>{
      supportBotSay('다른 궁금하신 내용이 있으신가요?');
      supportShowTopicChips();
    }, 300);
  }, 350);
}

/* ===================== 차단한 회원 목록 ===================== */
function openBlockedListScreen(){"""
),
]

patch('public/index.html', html_replacements)
print("\n패치 완료. 다음 순서로 진행하세요:")
print("1) node -c server.js   (변경 없지만 확인차)")
print("2) git add -A && git commit -m \"0-5: 고객센터(챗봇/메일) 화면 추가\"")
print("3) (모아뒀다가 원하실 때) git push")