# -*- coding: utf-8 -*-
# 0-90: 추천코드(친구 초대) 기능
#  - 내 프로필(마이페이지)에 "내 추천코드" 카드 + 복사 버튼(누르면 즉시 복사)
#  - 카카오 가입 2단계에 "회원 소개로 오셨나요?" 추천코드 입력칸 (선택)
#  - 추천코드로 가입하면 가입자/추천인 모두 쌀 200개 지급 (같은 기기 재가입, 추천인 30명 초과는 지급 제외)
#  - 초대링크 ?ref=코드 로 들어오면 입력칸 자동 채움

import io

def read(p):
    with io.open(p, "r", encoding="utf-8") as f:
        return f.read()

def write(p, s):
    with io.open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(s)

def rep(s, old, new, label):
    n = s.count(old)
    if n != 1:
        raise SystemExit("[실패] %s : 매칭 %d곳(1곳이어야 함). 수정 없이 중단." % (label, n))
    return s.replace(old, new, 1)

# ======================= server.js =======================
sp = "server.js"
s = read(sp)

s = rep(s, "async function getGroupRoom(roomId) {",
"""// 0-90: 추천코드(친구 초대) - 가입 시 코드를 입력하면 가입자/추천인 모두 쌀 지급
const REFERRAL_REWARD_POINTS = 200;
const REFERRAL_MAX_PER_USER = 30;
function generateReferralCode() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  let code = '';
  for (let i = 0; i < 6; i++) code += chars[Math.floor(Math.random() * chars.length)];
  return code;
}
async function ensureReferralCode(user) {
  if (user.referralCode) return user.referralCode;
  let code;
  do { code = generateReferralCode(); } while ((await db.ref(`referralCodes/${code}`).once('value')).exists());
  await db.ref(`referralCodes/${code}`).set(user.id);
  user.referralCode = code;
  return code;
}
async function getGroupRoom(roomId) {""", "server: 추천코드 헬퍼")

s = rep(s, "  // 회원가입 전 번호 중복 체크\n  socket.on('auth:check_phone'",
"""  // 0-90: 내 추천코드 조회(없으면 생성) + 지금까지 추천으로 가입한 인원 수
  socket.on('referral:get_my_code', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      if (!userId) return cb && cb({ success: false });
      const user = await getUser(userId);
      if (!user) return cb && cb({ success: false });
      const had = !!user.referralCode;
      const code = await ensureReferralCode(user);
      if (!had) await saveUser(user);
      cb && cb({ success: true, code, count: user.referralCount || 0, reward: REFERRAL_REWARD_POINTS });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 회원가입 전 번호 중복 체크
  socket.on('auth:check_phone'""", "server: 추천코드 조회 핸들러")

s = rep(s, "      const user = {\n        id: genId('u'), phone: '', kakaoId: payload.kakaoId,",
"""      // 0-90: 추천코드 확인 (입력한 경우에만)
      let referrer = null;
      let referralRewarded = false;
      let referralNote = null;
      const inputReferralCode = String(data.referralCode || '').trim().toUpperCase();
      if (inputReferralCode) {
        const refSnap = await db.ref(`referralCodes/${inputReferralCode}`).once('value');
        const referrerId = refSnap.val();
        referrer = referrerId ? await getUser(referrerId) : null;
        if (!referrer) return cb({ success: false, referralInvalid: true, message: '추천 코드를 찾을 수 없어요. 코드를 다시 확인하거나 비워두고 가입해주세요.' });
        if (referrer.isBanned) referralNote = '추천인 계정 상태로 인해 추천 보상은 지급되지 않았어요.';
        else if ((referrer.referralCount || 0) >= REFERRAL_MAX_PER_USER) referralNote = '이 추천코드는 보상 지급 한도에 도달해 보상이 지급되지 않았어요.';
        else if (deviceDupUsers && deviceDupUsers.length) referralNote = '이미 가입 이력이 있는 기기라 추천 보상은 지급되지 않았어요.';
        else referralRewarded = true;
      }
      const user = {
        id: genId('u'), phone: '', kakaoId: payload.kakaoId,""", "server: 카카오 가입 추천코드 확인")

s = rep(s, """      await saveUser(user);
      socketToUser[socket.id] = user.id;
      userToSocket[user.id] = socket.id;
      const token = issueSessionToken(user.id);
      cb({ success: true, user: { ...user, isAdmin: false }, token });
      broadcastUsers();""",
"""      if (referralRewarded) { user.points = (user.points || 0) + REFERRAL_REWARD_POINTS; user.referredBy = referrer.id; }
      await saveUser(user);
      socketToUser[socket.id] = user.id;
      userToSocket[user.id] = socket.id;
      const token = issueSessionToken(user.id);
      let referralResult = null;
      if (referrer) {
        referralResult = referralRewarded ? { rewarded: true, amount: REFERRAL_REWARD_POINTS } : { rewarded: false, note: referralNote };
      }
      cb({ success: true, user: { ...user, isAdmin: false }, token, referralResult });
      if (referralRewarded) {
        try {
          const freshReferrer = await getUser(referrer.id);
          if (freshReferrer) {
            freshReferrer.points = (freshReferrer.points || 0) + REFERRAL_REWARD_POINTS;
            freshReferrer.referralCount = (freshReferrer.referralCount || 0) + 1;
            await saveUser(freshReferrer);
            notifyUser(freshReferrer.id, { type: 'referral_reward', title: '초대 보상 도착', body: `${user.nickname}님이 내 추천코드로 가입해서 쌀 ${REFERRAL_REWARD_POINTS}개가 지급되었어요.` });
          }
        } catch (e) { console.error('[추천 보상 지급 오류]', e); }
      }
      broadcastUsers();""", "server: 카카오 가입 보상 지급")
write(sp, s)
print("[적용됨] server.js :: 추천코드 생성/조회/가입 보상")

# ======================= public/index.html =======================
hp = "public/index.html"
h = read(hp)

# 1) 가입 2단계 입력칸
h = rep(h, """        <div style="background:var(--bg-subtle);border:1px solid var(--border-color);border-radius:8px;padding:12px;margin-bottom:14px;">
          <label style="font-size:11px;cursor:pointer;display:flex;gap:8px;align-items:flex-start;">
            <input type="checkbox" id="agreeLegal" style="margin-top:2px;">""",
"""        <div class="form-group">
          <label>회원 소개로 오셨나요? <span style="font-weight:400;color:var(--text-muted);">(선택 · 추천코드를 입력하면 쌀 200개!)</span></label>
          <input type="text" id="regReferralCode" placeholder="추천코드 6자리 (없으면 비워두세요)" maxlength="8" autocapitalize="characters" autocomplete="off" style="text-transform:uppercase;">
        </div>
        <div style="background:var(--bg-subtle);border:1px solid var(--border-color);border-radius:8px;padding:12px;margin-bottom:14px;">
          <label style="font-size:11px;cursor:pointer;display:flex;gap:8px;align-items:flex-start;">
            <input type="checkbox" id="agreeLegal" style="margin-top:2px;">""", "html: 가입 추천코드 입력칸")

# 2) 마이페이지 추천코드 카드
h = rep(h, """        <div class="settings-card" style="background:var(--bg-card);border:1px solid var(--border-color);border-radius:16px;padding:16px;">
          <div style="margin-bottom:6px;">
            <h2 style="font-size:16px;margin:0;"><i class="fa-solid fa-id-card"></i> 내 프로필 편집</h2>""",
"""        <div style="background:var(--bg-card);border:1px solid var(--border-color);border-radius:16px;padding:14px 16px;display:flex;align-items:center;justify-content:space-between;gap:10px;">
          <div style="min-width:0;">
            <div class="sli-label"><i class="fa-solid fa-gift"></i> 내 추천코드</div>
            <div class="sli-sub" id="myReferralSub">친구가 이 코드로 가입하면 서로 쌀 200개!</div>
          </div>
          <button type="button" id="btnCopyReferral" onclick="copyMyReferralCode()" style="flex-shrink:0;display:flex;align-items:center;gap:8px;border:1px dashed var(--border-color);background:var(--bg-subtle);border-radius:12px;padding:10px 14px;font-weight:800;letter-spacing:2px;font-size:16px;cursor:pointer;color:var(--text-main);">
            <span id="myReferralCode">------</span><i class="fa-regular fa-copy"></i>
          </button>
        </div>
        <div class="settings-card" style="background:var(--bg-card);border:1px solid var(--border-color);border-radius:16px;padding:16px;">
          <div style="margin-bottom:6px;">
            <h2 style="font-size:16px;margin:0;"><i class="fa-solid fa-id-card"></i> 내 프로필 편집</h2>""", "html: 마이페이지 추천코드 카드")

# 3) 가입 단계 진입 시 ?ref= 코드 자동 채움
h = rep(h, "function setAuthStep(n){\n",
"""function setAuthStep(n){
  if (n===2){ try{ const refEl=document.getElementById('regReferralCode'); const savedRef=localStorage.getItem('pendingReferralCode'); if (refEl && !refEl.value && savedRef) refEl.value=savedRef; }catch(e){} }
""", "html: setAuthStep 자동채움")

# 4) 가입 제출 시 추천코드 전송
h = rep(h, "    deviceId: getDeviceId(),\n    deviceConfirmed\n  };\n  socket.emit('auth:kakao_complete_profile'",
"    deviceId: getDeviceId(),\n    deviceConfirmed,\n    referralCode: ((document.getElementById('regReferralCode')||{}).value || '').trim().toUpperCase()\n  };\n  socket.emit('auth:kakao_complete_profile'", "html: 가입 제출 추천코드")

# 5) 가입 결과 처리 (보상 안내 + 잘못된 코드 안내)
h = rep(h, "    if (res.success){ currentUser = res.user; saveSession(res.token); closeModal('authModal'); initApp(); if (!currentUser.onboardingSeen) setTimeout(showOnboardingTutorial, 400); }\n    else if (res.needsConfirm){",
"""    if (res.success){ currentUser = res.user; saveSession(res.token); closeModal('authModal'); initApp(); if (!currentUser.onboardingSeen) setTimeout(showOnboardingTutorial, 400);
      try{ localStorage.removeItem('pendingReferralCode'); }catch(e){}
      if (res.referralResult){ setTimeout(()=>showMiniAlert(res.referralResult.rewarded ? ('추천 보상으로 쌀 '+res.referralResult.amount+'개가 지급되었어요!') : (res.referralResult.note || '추천 보상이 지급되지 않았어요.'), [{label:'확인', primary:true}]), 900); }
    }
    else if (res.referralInvalid){ showMiniAlert(res.message, [{label:'확인', primary:true}]); }
    else if (res.needsConfirm){""", "html: 가입 결과 처리")

# 6) 내 프로필 폼 로드 시 추천코드 조회
h = rep(h, "function loadProfileToForm(){\n", "function loadProfileToForm(){\n  try{ loadMyReferralCode(); }catch(e){}\n", "html: loadProfileToForm 훅")

# 7) 추천코드 함수 + ?ref= 링크 저장
h = rep(h, "function copyMsgText(m){",
"""/* ===== 0-90: 추천코드 ===== */
(function(){ try { const ref = new URLSearchParams(location.search).get('ref'); if (ref) localStorage.setItem('pendingReferralCode', ref.trim().toUpperCase().slice(0,8)); } catch(e){} })();
let myReferralCodeValue = '';
function loadMyReferralCode(){
  if (!currentUser) return;
  socket.emit('referral:get_my_code', {}, (res)=>{
    if (!res || !res.success) return;
    myReferralCodeValue = res.code;
    const el = document.getElementById('myReferralCode'); if (el) el.textContent = res.code;
    const sub = document.getElementById('myReferralSub');
    if (sub) sub.textContent = '친구가 이 코드로 가입하면 서로 쌀 ' + res.reward + '개! (지금까지 ' + res.count + '명 초대)';
  });
}
function copyMyReferralCode(){
  if (!myReferralCodeValue) return;
  const btn = document.getElementById('btnCopyReferral');
  const icon = btn ? btn.querySelector('i') : null;
  const done = ()=>{
    if (!icon) return;
    icon.className = 'fa-solid fa-check';
    setTimeout(()=>{ icon.className = 'fa-regular fa-copy'; }, 1500);
  };
  if (navigator.clipboard && navigator.clipboard.writeText){
    navigator.clipboard.writeText(myReferralCodeValue).then(done).catch(()=>{ fallbackCopyReferral(); done(); });
  } else { fallbackCopyReferral(); done(); }
}
function fallbackCopyReferral(){
  const ta = document.createElement('textarea'); ta.value = myReferralCodeValue;
  document.body.appendChild(ta); ta.select(); try{ document.execCommand('copy'); }catch(e){} ta.remove();
}
function copyMsgText(m){""", "html: 추천코드 함수")
write(hp, h)
print("[적용됨] public/index.html :: 가입 입력칸 / 마이페이지 카드 / 복사 버튼 / ?ref= 자동채움")
print("0-90 패치 완료.")