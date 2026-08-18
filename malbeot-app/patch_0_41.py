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

old_block = """socket.on('connect', ()=>{
  if (currentUser && sessionToken){
    socket.emit('auth:session_resume', {token: sessionToken}, (res)=>{
      if (res.success){
        currentUser = res.user; saveSession(res.token);
        closeModal('landingScreen'); closeModal('authModal');
        initApp();
        if (res.rewardNotify){
          showMiniAlert(`어제의 인기 투표로 선정되셔서 포인트 ${res.rewardNotify.amount}개를 지급했어요!`, [{label:'확인', primary:true}]);
        }
        if (res.dailyRewardNotify){
          showMiniAlert(`오늘의 접속 보상으로 쌀 ${res.dailyRewardNotify.amount}개가 지급되었습니다!`, [{label:'확인', primary:true}]);
        }
        if (res.warningNotify){ showWarningModal(res.warningNotify.message); }
        if (res.repPhotoSuggestNotify){
          showMiniAlert('다른 사진이 대표사진보다 좋아요를 더 많이 받았어요! 대표사진을 바꿔보시겠어요?', [
            {label:'나중에', primary:false},
            {label:'프로필 편집하기', primary:true, onClick:()=>{ openSettingsScreen(); loadProfileToForm(); }}
          ]);
        }
        if (!currentUser.phone) openPhoneSetupModal();
      } else {
        clearSession();
        resetToLandingScreen();
      }
    });
  }
});"""

new_block = """// 0-41: 세션 복구 실패시 무조건 로그아웃하던 버그 수정.
// 진짜 로그인 만료(expired)/계정정지(banned)일 때만 로그아웃하고,
// 그 외(서버 일시적 불안정 등)는 세션을 유지한 채 잠시 후 자동 재시도함(최대 3회).
let sessionResumeRetryCount = 0;
function attemptSessionResume(){
  if (!(currentUser && sessionToken)) return;
  socket.emit('auth:session_resume', {token: sessionToken}, (res)=>{
    if (res.success){
      sessionResumeRetryCount = 0;
      currentUser = res.user; saveSession(res.token);
      closeModal('landingScreen'); closeModal('authModal');
      initApp();
      if (res.rewardNotify){
        showMiniAlert(`어제의 인기 투표로 선정되셔서 포인트 ${res.rewardNotify.amount}개를 지급했어요!`, [{label:'확인', primary:true}]);
      }
      if (res.dailyRewardNotify){
        showMiniAlert(`오늘의 접속 보상으로 쌀 ${res.dailyRewardNotify.amount}개가 지급되었습니다!`, [{label:'확인', primary:true}]);
      }
      if (res.warningNotify){ showWarningModal(res.warningNotify.message); }
      if (res.repPhotoSuggestNotify){
        showMiniAlert('다른 사진이 대표사진보다 좋아요를 더 많이 받았어요! 대표사진을 바꿔보시겠어요?', [
          {label:'나중에', primary:false},
          {label:'프로필 편집하기', primary:true, onClick:()=>{ openSettingsScreen(); loadProfileToForm(); }}
        ]);
      }
      if (!currentUser.phone) openPhoneSetupModal();
    } else if (res.expired || res.banned){
      sessionResumeRetryCount = 0;
      clearSession();
      resetToLandingScreen();
      if (res.banned) showWarningModal(res.message || '이용이 제한된 계정입니다.');
    } else {
      // 일시적 오류(서버 재시작 등으로 추정) - 로그아웃시키지 않고 잠시 후 재시도
      sessionResumeRetryCount++;
      if (sessionResumeRetryCount <= 3){
        setTimeout(attemptSessionResume, 2000);
      } else {
        sessionResumeRetryCount = 0;
        clearSession();
        resetToLandingScreen();
      }
    }
  });
}
socket.on('connect', ()=>{
  attemptSessionResume();
});"""

c = must_replace(c, old_block, new_block, "세션복구 실패시 무조건 로그아웃 버그 수정")
write(CLIENT, c)
print("0-41 패치 적용 완료")
print("  세션 복구(auth:session_resume)가 실패해도 진짜 만료/계정정지가 아니면")
print("  로그아웃시키지 않고 2초 간격으로 최대 3회 자동 재시도하도록 수정")
