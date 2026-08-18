# -*- coding: utf-8 -*-
CLIENT = 'public/index.html'

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

# ===== 0-40-A: "나의 대화목록" -> "채팅" 텍스트 변경 =====
c = must_replace(
    c,
    "else if (tab==='tab-chat'){ title.textContent='나의 대화목록'; filterBar.classList.add('hidden'); }",
    "else if (tab==='tab-chat'){ title.textContent='채팅'; filterBar.classList.add('hidden'); }",
    "탭 제목 채팅으로 변경"
)

# ===== 0-40-B: 설정 화면 우측 상단에 새로고침 버튼 추가 =====
old_settings_header = """  <div id="settingsScreen" class="full-screen-overlay">
    <div class="fs-header">
      <button class="back-btn" onclick="handleSettingsBack()"><i class="fa-solid fa-arrow-left"></i></button>
      <div class="fs-title">설정</div>
    </div>"""
new_settings_header = """  <div id="settingsScreen" class="full-screen-overlay">
    <div class="fs-header">
      <button class="back-btn" onclick="handleSettingsBack()"><i class="fa-solid fa-arrow-left"></i></button>
      <div class="fs-title">설정</div>
      <button class="back-btn" style="margin-left:auto;" onclick="refreshAppData()" title="새로고침"><i class="fa-solid fa-rotate-right"></i></button>
    </div>"""
c = must_replace(c, old_settings_header, new_settings_header, "설정화면 헤더에 새로고침 버튼 추가")

old_toggle_admin_fn = "function toggleAdminMode(){"
new_toggle_admin_fn = """// 0-40: 설정 화면 새로고침 버튼 - 데이터 꼬임 발생시 전체 페이지 새로고침
function refreshAppData(){
  location.reload();
}
function toggleAdminMode(){"""
c = must_replace(c, old_toggle_admin_fn, new_toggle_admin_fn, "refreshAppData 함수 추가")

# ===== 0-40-C: 방문자/좋아요 잠금화면에서 "확인" 눌러도 결제화면으로 안 넘어가던 버그 수정 =====
old_lock_confirm_btn = '<button class="btn btn-primary" style="flex:1;" onclick="closeModal(\'lockUpsellModal\');openSubscriptionScreen()">확인</button>'
new_lock_confirm_btn = '<button class="btn btn-primary" style="flex:1;" onclick="closeModal(\'lockUpsellModal\');closeFullScreen(\'photoLikersScreen\');closeFullScreen(\'profileVisitorsScreen\');openSubscriptionScreen()">확인</button>'
c = must_replace(c, old_lock_confirm_btn, new_lock_confirm_btn, "잠금화면 결제이동 버튼 - 뒤에 남은 화면 먼저 닫기")

write(CLIENT, c)
print("0-40 패치 적용 완료")
print("  A) 채팅 탭 제목: 나의 대화목록 -> 채팅")
print("  B) 설정 화면 우측 상단(헤더 우측 끝)에 새로고침 버튼 추가")
print("  C) 방문자/좋아요 잠금화면 확인버튼 - 결제화면으로 정상 이동하도록 수정")
