#!/usr/bin/env python3
# 0-6: 일일 접속 보상(쌀50개, 자동지급) + 정렬모달 인기순 강조 + 프로필 오늘 방문자수/목록(본인전용) 추가
# 실행 위치: malbeot-app 폴더 안에서 python3 fix_batch_features.py

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

server_replacements = [
(
"""function kstDateStr(d) {
  return new Date(d.getTime() + 9 * 60 * 60 * 1000).toISOString().slice(0, 10);
}""",
"""function kstDateStr(d) {
  return new Date(d.getTime() + 9 * 60 * 60 * 1000).toISOString().slice(0, 10);
}
// 일일 접속 보상: 하루(KST 기준) 최초 로그인/세션복구 시 쌀 50개 자동 지급 (스위치 없이 항상 지급).
// user 객체를 직접 변형만 하고 저장은 호출부의 saveUser(user)가 한 번에 처리함.
function grantDailyLoginRewardIfNeeded(user) {
  const today = kstDateStr(new Date());
  if (user.lastDailyRewardDate === today) return null;
  user.points = (user.points || 0) + 50;
  user.lastDailyRewardDate = today;
  return 50;
}"""
),
(
"""      user.isOnline = true;
      user.lastSeen = Date.now();
      await saveUser(user);
      socketToUser[socket.id] = user.id;
      userToSocket[user.id] = socket.id;
      const token = issueSessionToken(user.id);
      const rewardNotify = await popPendingRewardNotify(user);
      const warningNotify = await popPendingWarningNotify(user);
      cb({ success: true, user: { ...user, isAdmin: isAdmin(user) }, token, rewardNotify, warningNotify });
      broadcastUsers();
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  // 세션 토큰으로 자동 로그인""",
"""      user.isOnline = true;
      user.lastSeen = Date.now();
      const dailyRewardAmount = grantDailyLoginRewardIfNeeded(user);
      await saveUser(user);
      socketToUser[socket.id] = user.id;
      userToSocket[user.id] = socket.id;
      const token = issueSessionToken(user.id);
      const rewardNotify = await popPendingRewardNotify(user);
      const warningNotify = await popPendingWarningNotify(user);
      cb({ success: true, user: { ...user, isAdmin: isAdmin(user) }, token, rewardNotify, warningNotify, dailyRewardNotify: dailyRewardAmount ? { amount: dailyRewardAmount } : null });
      broadcastUsers();
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  // 세션 토큰으로 자동 로그인"""
),
(
"""      user.isOnline = true;
      user.lastSeen = Date.now();
      await saveUser(user);
      socketToUser[socket.id] = user.id;
      userToSocket[user.id] = socket.id;
      const token = issueSessionToken(user.id); // 갱신(연장)
      const rewardNotify = await popPendingRewardNotify(user);
      const warningNotify = await popPendingWarningNotify(user);
      cb({ success: true, user: { ...user, isAdmin: isAdmin(user) }, token, rewardNotify, warningNotify });
      broadcastUsers();""",
"""      user.isOnline = true;
      user.lastSeen = Date.now();
      const dailyRewardAmount = grantDailyLoginRewardIfNeeded(user);
      await saveUser(user);
      socketToUser[socket.id] = user.id;
      userToSocket[user.id] = socket.id;
      const token = issueSessionToken(user.id); // 갱신(연장)
      const rewardNotify = await popPendingRewardNotify(user);
      const warningNotify = await popPendingWarningNotify(user);
      cb({ success: true, user: { ...user, isAdmin: isAdmin(user) }, token, rewardNotify, warningNotify, dailyRewardNotify: dailyRewardAmount ? { amount: dailyRewardAmount } : null });
      broadcastUsers();"""
),
(
"""        if (!existing.deviceId && data.deviceId) existing.deviceId = data.deviceId; // 이 기능 추가 전 가입한 계정에 최초 1회만 채움
        await saveUser(existing);
        socketToUser[socket.id] = existing.id;
        userToSocket[existing.id] = socket.id;
        const token = issueSessionToken(existing.id);
        const rewardNotify = await popPendingRewardNotify(existing);
        const warningNotify = await popPendingWarningNotify(existing);
        cb({ success: true, user: { ...existing, isAdmin: isAdmin(existing) }, token, rewardNotify, warningNotify });
        broadcastUsers();""",
"""        if (!existing.deviceId && data.deviceId) existing.deviceId = data.deviceId; // 이 기능 추가 전 가입한 계정에 최초 1회만 채움
        const dailyRewardAmount = grantDailyLoginRewardIfNeeded(existing);
        await saveUser(existing);
        socketToUser[socket.id] = existing.id;
        userToSocket[existing.id] = socket.id;
        const token = issueSessionToken(existing.id);
        const rewardNotify = await popPendingRewardNotify(existing);
        const warningNotify = await popPendingWarningNotify(existing);
        cb({ success: true, user: { ...existing, isAdmin: isAdmin(existing) }, token, rewardNotify, warningNotify, dailyRewardNotify: dailyRewardAmount ? { amount: dailyRewardAmount } : null });
        broadcastUsers();"""
),
(
"""  // 차단 해제
  socket.on('user:unblock', async (targetId, cb) => {""",
"""  // 프로필 방문 기록 (KST 날짜별로 저장 - 날짜가 바뀌면 자연히 새 목록이 되어 "일일 초기화" 효과)
  // 본인 프로필을 본인이 보는 경우는 기록하지 않음
  socket.on('profile:record_visit', async (data, cb) => {
    try {
      const visitorId = socketToUser[socket.id];
      const targetId = data && data.targetUserId;
      if (!visitorId || !targetId || visitorId === targetId) return cb && cb({ success: true });
      const today = kstDateStr(new Date());
      await db.ref(`profileVisits/${targetId}/${today}/${visitorId}`).set(Date.now());
      cb && cb({ success: true });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 오늘(KST) 내 프로필 방문자 수 + 목록 조회 (본인만 조회 가능 - 로그인한 본인 소켓 기준으로 본인 것만 조회)
  socket.on('profile:get_today_visitors', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      if (!userId) return cb && cb({ success: false, count: 0, visitors: [] });
      const today = kstDateStr(new Date());
      const snap = await db.ref(`profileVisits/${userId}/${today}`).once('value');
      const raw = snap.val() || {};
      const visitorIds = Object.keys(raw).sort((a, b) => raw[b] - raw[a]);
      const users = await getAllUsers();
      const visitors = visitorIds.map(id => users[id]).filter(Boolean);
      cb && cb({ success: true, count: visitorIds.length, visitors });
    } catch (e) { console.error(e); cb && cb({ success: false, count: 0, visitors: [] }); }
  });

  // 차단 해제
  socket.on('user:unblock', async (targetId, cb) => {"""
),
]

html_replacements = [
(
"""        closeModal('landingScreen'); closeModal('authModal');
        initApp();
        if (res.rewardNotify){
          showMiniAlert(`어제의 인기 투표로 선정되셔서 포인트 ${res.rewardNotify.amount}개를 지급했어요!`, [{label:'확인', primary:true}]);
        }
        if (res.warningNotify){ showWarningModal(res.warningNotify.message); }""",
"""        closeModal('landingScreen'); closeModal('authModal');
        initApp();
        if (res.rewardNotify){
          showMiniAlert(`어제의 인기 투표로 선정되셔서 포인트 ${res.rewardNotify.amount}개를 지급했어요!`, [{label:'확인', primary:true}]);
        }
        if (res.dailyRewardNotify){
          showMiniAlert(`오늘의 접속 보상으로 쌀 ${res.dailyRewardNotify.amount}개가 지급되었습니다!`, [{label:'확인', primary:true}]);
        }
        if (res.warningNotify){ showWarningModal(res.warningNotify.message); }"""
),
(
"""        closeModal('landingScreen'); initApp();
        if (res.rewardNotify){
          showMiniAlert(`어제의 인기 투표로 선정되셔서 포인트 ${res.rewardNotify.amount}개를 지급했어요!`, [{label:'확인', primary:true}]);
        }
        if (res.warningNotify){ showWarningModal(res.warningNotify.message); }""",
"""        closeModal('landingScreen'); initApp();
        if (res.rewardNotify){
          showMiniAlert(`어제의 인기 투표로 선정되셔서 포인트 ${res.rewardNotify.amount}개를 지급했어요!`, [{label:'확인', primary:true}]);
        }
        if (res.dailyRewardNotify){
          showMiniAlert(`오늘의 접속 보상으로 쌀 ${res.dailyRewardNotify.amount}개가 지급되었습니다!`, [{label:'확인', primary:true}]);
        }
        if (res.warningNotify){ showWarningModal(res.warningNotify.message); }"""
),
(
"""  list.innerHTML = Object.keys(SORT_TYPE_LABELS).map(key => `
    <div class="category-item" style="${key===current?'background:var(--primary);color:#fff;':''}" onclick="applySortType('${key}')">${SORT_TYPE_LABELS[key]}</div>
  `).join('');""",
"""  list.innerHTML = Object.keys(SORT_TYPE_LABELS).map(key => {
    const isSelected = key === current;
    const isPopular = key === 'popular';
    const style = isSelected ? 'background:var(--primary);color:#fff;' : (isPopular ? 'color:#ff6b35;font-weight:700;' : '');
    const icon = isPopular ? '<i class="fa-solid fa-fire" style="margin-right:5px;"></i>' : '';
    return `<div class="category-item" style="${style}" onclick="applySortType('${key}')">${icon}${SORT_TYPE_LABELS[key]}</div>`;
  }).join('');"""
),
(
"""function openProfileDetailScreen(userId){
  currentProfileUserId = userId; profilePhotoIndex = 0;
  socket.emit('users:get_one', {userId}, (res)=>{""",
"""function openProfileDetailScreen(userId){
  currentProfileUserId = userId; profilePhotoIndex = 0;
  socket.emit('profile:record_visit', {targetUserId: userId});
  socket.emit('users:get_one', {userId}, (res)=>{"""
),
(
"""      <div class="mypage-stack" style="display:flex;flex-direction:column;gap:14px;">
        <div class="settings-card" style="background:var(--bg-card);border:1px solid var(--border-color);border-radius:16px;padding:16px;">
          <div style="margin-bottom:6px;">
            <h2 style="font-size:16px;margin:0;"><i class="fa-solid fa-id-card"></i> 내 프로필 편집</h2>
          </div>""",
"""      <div class="mypage-stack" style="display:flex;flex-direction:column;gap:14px;">
        <div class="settings-list-item" style="background:var(--bg-card);border:1px solid var(--border-color);border-radius:16px;padding:14px 16px;" onclick="openProfileVisitorsScreen()">
          <div><div class="sli-label"><i class="fa-solid fa-eye"></i> 오늘 내 프로필 방문자</div><div class="sli-sub">매일 자정에 초기화됩니다</div></div>
          <div class="sli-right"><span id="myPageVisitorCount" style="font-weight:700;margin-right:4px;">0명</span><i class="fa-solid fa-chevron-right"></i></div>
        </div>
        <div class="settings-card" style="background:var(--bg-card);border:1px solid var(--border-color);border-radius:16px;padding:16px;">
          <div style="margin-bottom:6px;">
            <h2 style="font-size:16px;margin:0;"><i class="fa-solid fa-id-card"></i> 내 프로필 편집</h2>
          </div>"""
),
(
"""  if (tab==='tab-mypage') loadProfileToForm();""",
"""  if (tab==='tab-mypage') { loadProfileToForm(); refreshMyPageVisitorCount(); }"""
),
(
"""/* ===================== 차단한 회원 목록 ===================== */
function openBlockedListScreen(){""",
"""/* ===================== 오늘 프로필 방문자 (본인만 조회 가능, 매일 자정 KST 초기화) ===================== */
function refreshMyPageVisitorCount(){
  socket.emit('profile:get_today_visitors', {}, (res)=>{
    const el = document.getElementById('myPageVisitorCount');
    if (el && res && res.success) el.textContent = `${res.count}명`;
  });
}
function openProfileVisitorsScreen(){
  socket.emit('profile:get_today_visitors', {}, (res)=>{
    const body = document.getElementById('profileVisitorsBody');
    const visitors = (res && res.visitors) || [];
    document.getElementById('myPageVisitorCount').textContent = `${(res && res.count) || 0}명`;
    body.innerHTML = visitors.length ? visitors.map(u=>`
      <div class="user-card" style="cursor:pointer;" onclick="openProfileDetailScreen('${u.id}')">
        ${avatarHtmlFor(u,'avatar')}
        <div style="flex:1;min-width:0;">
          <span class="user-nickname">${escapeHtml(u.nickname)}</span>
          <div style="display:flex;gap:6px;margin-top:4px;"><span class="tag">${u.region}</span><span class="tag">${u.gender==='female'?'여성':'남성'}</span><span class="tag">${u.age}세</span></div>
        </div>
      </div>`).join('') : `<div style="text-align:center;padding:40px;color:var(--text-muted);">오늘 방문한 사람이 아직 없습니다.</div>`;
    openFullScreen('profileVisitorsScreen');
  });
}

/* ===================== 차단한 회원 목록 ===================== */
function openBlockedListScreen(){"""
),
(
"""  <div id="blockedListScreen" class="full-screen-overlay">
    <div class="fs-header">
      <button class="back-btn" onclick="closeFullScreen('blockedListScreen')"><i class="fa-solid fa-arrow-left"></i></button>
      <div class="fs-title">차단한 회원</div>
    </div>
    <div class="fs-body" id="blockedListBody" style="padding:8px 16px;"></div>
  </div>""",
"""  <div id="blockedListScreen" class="full-screen-overlay">
    <div class="fs-header">
      <button class="back-btn" onclick="closeFullScreen('blockedListScreen')"><i class="fa-solid fa-arrow-left"></i></button>
      <div class="fs-title">차단한 회원</div>
    </div>
    <div class="fs-body" id="blockedListBody" style="padding:8px 16px;"></div>
  </div>

  <div id="profileVisitorsScreen" class="full-screen-overlay">
    <div class="fs-header">
      <button class="back-btn" onclick="closeFullScreen('profileVisitorsScreen')"><i class="fa-solid fa-arrow-left"></i></button>
      <div class="fs-title">오늘 방문자</div>
    </div>
    <div class="fs-body" id="profileVisitorsBody" style="padding:8px 16px;"></div>
  </div>"""
),
]

patch('server.js', server_replacements)
patch('public/index.html', html_replacements)
print("\n패치 완료. 다음 순서로 진행하세요:")
print("1) node -c server.js")
print("2) git add -A && git commit -m \"0-6: 일일 접속 보상(쌀50개) + 인기순 강조 + 프로필 오늘 방문자수/목록\"")
print("3) (모아뒀다가 원하실 때) git push")