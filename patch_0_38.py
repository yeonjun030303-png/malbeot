# -*- coding: utf-8 -*-
import re

SERVER = 'server.js'
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

# ================= server.js =================
s = read(SERVER)

# 1) 관리자 구독 지급 시 보너스 쌀도 함께 지급 (실구매와 동일하게 골드1000/플래3000)
old_grant = """  socket.on('admin:subscription:grant', async (data, cb) => {
    try {
      const requester = await getUser(socketToUser[socket.id]);
      if (!requester || !isAdmin(requester)) return cb && cb({ success: false });
      const targetId = data && data.userId;
      const tier = data && data.tier;
      const days = Number(data && data.days);
      if (!targetId || !SUBSCRIPTION_TIER_RANK[tier] || !days || days <= 0) {
        return cb && cb({ success: false, message: '잘못된 요청입니다.' });
      }
      const target = await getUser(targetId);
      if (!target) return cb && cb({ success: false, message: '유저를 찾을 수 없습니다.' });
      target.subscription = {
        tier,
        expiresAt: Date.now() + days * 24 * 60 * 60 * 1000,
        logoColorOn: (target.subscription && typeof target.subscription.logoColorOn === 'boolean') ? target.subscription.logoColorOn : true,
        badgeOn: (target.subscription && typeof target.subscription.badgeOn === 'boolean') ? target.subscription.badgeOn : true
      };
      await saveUser(target);
      console.log(`[관리자 구독 지급] ${requester.nickname}(이)가 ${target.nickname}에게 ${tier}(${days}일) 수동 지급`);
      const sId = userToSocket[target.id];
      if (sId) io.to(sId).emit('points:updated', { points: target.points, subscription: target.subscription });
      broadcastUsers();
      cb && cb({ success: true, subscription: target.subscription });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });"""

new_grant = """  socket.on('admin:subscription:grant', async (data, cb) => {
    try {
      const requester = await getUser(socketToUser[socket.id]);
      if (!requester || !isAdmin(requester)) return cb && cb({ success: false });
      const targetId = data && data.userId;
      const tier = data && data.tier;
      const days = Number(data && data.days);
      if (!targetId || !SUBSCRIPTION_TIER_RANK[tier] || !days || days <= 0) {
        return cb && cb({ success: false, message: '잘못된 요청입니다.' });
      }
      const target = await getUser(targetId);
      if (!target) return cb && cb({ success: false, message: '유저를 찾을 수 없습니다.' });
      target.subscription = {
        tier,
        expiresAt: Date.now() + days * 24 * 60 * 60 * 1000,
        logoColorOn: (target.subscription && typeof target.subscription.logoColorOn === 'boolean') ? target.subscription.logoColorOn : true,
        badgeOn: (target.subscription && typeof target.subscription.badgeOn === 'boolean') ? target.subscription.badgeOn : true
      };
      // 실구매(RevenueCat 웹훅)와 동일하게 등급별 보너스 쌀도 즉시 지급 (골드 1000 / 플래티넘 3000)
      const bonusPoints = tier === 'platinum' ? 3000 : 1000;
      target.points = (target.points || 0) + bonusPoints;
      await saveUser(target);
      console.log(`[관리자 구독 지급] ${requester.nickname}(이)가 ${target.nickname}에게 ${tier}(${days}일) + 쌀 ${bonusPoints} 수동 지급`);
      const sId = userToSocket[target.id];
      if (sId) io.to(sId).emit('points:updated', { points: target.points, subscription: target.subscription });
      broadcastUsers();
      cb && cb({ success: true, subscription: target.subscription, points: target.points });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });"""

s = must_replace(s, old_grant, new_grant, "admin:subscription:grant 포인트 지급 추가")

# 2) 관리자 구독관리 - 검색 없이도 뜨는 우선순위 기본 목록 API 신규 추가 (revoke 핸들러 바로 뒤에 삽입)
anchor = """  // 어뷰징 의심(동일 기기로 계정 2개 이상) 그룹 목록 - 관리자만
  socket.on('admin:abuse:list', async (data, cb) => {"""

new_list_handler = """  // 0-38: 관리자 구독관리 - 검색 없이도 우선순위 목록을 바로 보여줌
  // 우선순위: 1) 구독 중인데 곧 만료되는 유저(임박순) 2) 최근 접속한 유저 순
  socket.on('admin:subscription:list', async (data, cb) => {
    try {
      const requester = await getUser(socketToUser[socket.id]);
      if (!requester || !isAdmin(requester)) return cb && cb({ success: false });
      const allUsers = Object.values(await getAllUsers());
      const now = Date.now();
      const activeSubUsers = allUsers
        .filter(u => u.subscription && u.subscription.tier && u.subscription.expiresAt && u.subscription.expiresAt > now)
        .sort((a, b) => a.subscription.expiresAt - b.subscription.expiresAt);
      const activeIds = new Set(activeSubUsers.map(u => u.id));
      const recentUsers = allUsers
        .filter(u => !activeIds.has(u.id))
        .sort((a, b) => (b.lastSeen || 0) - (a.lastSeen || 0))
        .slice(0, 30);
      cb && cb({ success: true, users: [...activeSubUsers, ...recentUsers] });
    } catch (e) { console.error(e); cb && cb({ success: false, users: [] }); }
  });

  // 어뷰징 의심(동일 기기로 계정 2개 이상) 그룹 목록 - 관리자만
  socket.on('admin:abuse:list', async (data, cb) => {"""

s = must_replace(s, anchor, new_list_handler, "admin:subscription:list 신규 핸들러 추가")

write(SERVER, s)
print("✅ server.js 패치 완료")

# ================= public/index.html =================
c = read(CLIENT)

# 3) 안내 문구 변경 + sub 탭 진입시 자동으로 기본 목록 로드
old_intro = '<div style="font-size:12px;color:var(--text-muted);margin-bottom:10px;">닉네임으로 유저를 검색해 기본/골드/플래티넘 등급을 결제 없이 바로 설정할 수 있어요(테스트·CS 대응용).</div>'
new_intro = '<div style="font-size:12px;color:var(--text-muted);margin-bottom:10px;">구독 만료 임박 유저와 최근 접속 유저가 검색 없이 아래에 바로 표시돼요. 다른 유저는 닉네임으로 검색하세요(테스트·CS 대응용).</div>'
c = must_replace(c, old_intro, new_intro, "구독관리 안내문구 교체")

old_switch = "else if (tab==='sub') { /* 검색 후 로드되므로 초기엔 아무것도 안 함 */ }"
new_switch = "else if (tab==='sub') { loadAdminSubscriptionDefaultList(); }"
c = must_replace(c, old_switch, new_switch, "sub 탭 진입시 기본목록 자동로드")

# 4) 렌더 함수를 공용화하고, 기본목록 로드 함수 신규 추가
old_js = """// 0-22: 관리자 구독관리 탭 - 닉네임 검색 + 지급/회수
function searchAdminSubscriptionUsers(){
  const q = (document.getElementById('adminSubSearchInput').value || '').trim();
  const box = document.getElementById('adminSubSearchResults');
  if (!q){ box.innerHTML = ''; return; }
  socket.emit('users:search', {query:q}, (res)=>{
    if (!res || !res.success || !res.users.length){
      box.innerHTML = `<div style="text-align:center;padding:30px;color:var(--text-muted);">검색 결과가 없습니다.</div>`;
      return;
    }
    box.innerHTML = res.users.map(u=>{
      const sub = u.subscription;
      const active = sub && sub.tier && sub.expiresAt && sub.expiresAt > Date.now();
      const curTier = active ? sub.tier : 'basic';
      const statusText = active
        ? `${sub.tier==='platinum'?'플래티넘':'골드'} 구독 중 · ${new Date(sub.expiresAt).toLocaleDateString('ko-KR')}까지`
        : '기본(구독 없음)';
      const btnStyle = (on)=> on
        ? 'background:var(--primary);color:#fff;border-color:var(--primary);'
        : 'background:var(--bg-input);color:var(--text-main);';
      return `
      <div class="settings-list-item" style="flex-direction:column;align-items:stretch;cursor:default;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <b>${escapeHtml(u.nickname)}</b>
          <span style="font-size:11px;color:${active?'var(--primary)':'var(--text-muted)'};">${statusText}</span>
        </div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;">
          <button class="btn btn-sm" style="${btnStyle(curTier==='basic')}" onclick="revokeAdminSubscription('${u.id}')">기본</button>
          <button class="btn btn-sm" style="${btnStyle(curTier==='gold')}" onclick="grantAdminSubscription('${u.id}','gold',14)">골드 14일</button>
          <button class="btn btn-secondary btn-sm" onclick="grantAdminSubscription('${u.id}','gold',365)">골드 1년</button>
          <button class="btn btn-sm" style="${btnStyle(curTier==='platinum')}" onclick="grantAdminSubscription('${u.id}','platinum',14)">플래 14일</button>
          <button class="btn btn-secondary btn-sm" onclick="grantAdminSubscription('${u.id}','platinum',365)">플래 1년</button>
        </div>
      </div>`;
    }).join('');
  });
}"""

new_js = """// 0-22/0-38: 관리자 구독관리 탭 - 닉네임 검색 + 지급/회수 (0-38: 검색 없이도 우선순위 기본목록 표시)
function renderAdminSubUserList(users, emptyText){
  const box = document.getElementById('adminSubSearchResults');
  if (!users || !users.length){
    box.innerHTML = `<div style="text-align:center;padding:30px;color:var(--text-muted);">${emptyText}</div>`;
    return;
  }
  box.innerHTML = users.map(u=>{
    const sub = u.subscription;
    const active = sub && sub.tier && sub.expiresAt && sub.expiresAt > Date.now();
    const curTier = active ? sub.tier : 'basic';
    const statusText = active
      ? `${sub.tier==='platinum'?'플래티넘':'골드'} 구독 중 · ${new Date(sub.expiresAt).toLocaleDateString('ko-KR')}까지`
      : '기본(구독 없음)';
    const btnStyle = (on)=> on
      ? 'background:var(--primary);color:#fff;border-color:var(--primary);'
      : 'background:var(--bg-input);color:var(--text-main);';
    return `
    <div class="settings-list-item" style="flex-direction:column;align-items:stretch;cursor:default;">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <b>${escapeHtml(u.nickname)}</b>
        <span style="font-size:11px;color:${active?'var(--primary)':'var(--text-muted)'};">${statusText}</span>
      </div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;">
        <button class="btn btn-sm" style="${btnStyle(curTier==='basic')}" onclick="revokeAdminSubscription('${u.id}')">기본</button>
        <button class="btn btn-sm" style="${btnStyle(curTier==='gold')}" onclick="grantAdminSubscription('${u.id}','gold',14)">골드 14일</button>
        <button class="btn btn-secondary btn-sm" onclick="grantAdminSubscription('${u.id}','gold',365)">골드 1년</button>
        <button class="btn btn-sm" style="${btnStyle(curTier==='platinum')}" onclick="grantAdminSubscription('${u.id}','platinum',14)">플래 14일</button>
        <button class="btn btn-secondary btn-sm" onclick="grantAdminSubscription('${u.id}','platinum',365)">플래 1년</button>
      </div>
    </div>`;
  }).join('');
}
function loadAdminSubscriptionDefaultList(){
  const box = document.getElementById('adminSubSearchResults');
  box.innerHTML = `<div style="text-align:center;padding:30px;color:var(--text-muted);">불러오는 중...</div>`;
  socket.emit('admin:subscription:list', {}, (res)=>{
    if (!res || !res.success){ box.innerHTML = `<div style="text-align:center;padding:30px;color:var(--text-muted);">목록을 불러오지 못했습니다.</div>`; return; }
    renderAdminSubUserList(res.users, '표시할 유저가 없습니다.');
  });
}
function searchAdminSubscriptionUsers(){
  const q = (document.getElementById('adminSubSearchInput').value || '').trim();
  if (!q){ loadAdminSubscriptionDefaultList(); return; }
  socket.emit('users:search', {query:q}, (res)=>{
    if (!res || !res.success){ renderAdminSubUserList([], '검색 결과가 없습니다.'); return; }
    renderAdminSubUserList(res.users, '검색 결과가 없습니다.');
  });
}"""

c = must_replace(c, old_js, new_js, "구독관리 렌더 함수 공용화 + 기본목록 함수 추가")

# 5) 지급/회수 후 목록 새로고침을 현재 검색어 유무에 따라 분기(검색 중이면 검색 유지, 아니면 기본목록 유지)
old_grant_cb = """function grantAdminSubscription(userId, tier, days){
  socket.emit('admin:subscription:grant', {userId, tier, days}, (res)=>{
    if (res && res.success) searchAdminSubscriptionUsers();
    else showMiniAlert((res && res.message) || '지급 중 오류가 발생했습니다.', [{label:'확인', primary:true}]);
  });
}
function revokeAdminSubscription(userId){
  socket.emit('admin:subscription:revoke', {userId}, (res)=>{
    if (res && res.success) searchAdminSubscriptionUsers();
    else showMiniAlert((res && res.message) || '회수 중 오류가 발생했습니다.', [{label:'확인', primary:true}]);
  });
}"""

new_grant_cb = """function refreshAdminSubList(){
  const q = (document.getElementById('adminSubSearchInput').value || '').trim();
  if (q) searchAdminSubscriptionUsers(); else loadAdminSubscriptionDefaultList();
}
function grantAdminSubscription(userId, tier, days){
  socket.emit('admin:subscription:grant', {userId, tier, days}, (res)=>{
    if (res && res.success) refreshAdminSubList();
    else showMiniAlert((res && res.message) || '지급 중 오류가 발생했습니다.', [{label:'확인', primary:true}]);
  });
}
function revokeAdminSubscription(userId){
  socket.emit('admin:subscription:revoke', {userId}, (res)=>{
    if (res && res.success) refreshAdminSubList();
    else showMiniAlert((res && res.message) || '회수 중 오류가 발생했습니다.', [{label:'확인', primary:true}]);
  });
}"""

c = must_replace(c, old_grant_cb, new_grant_cb, "지급/회수 후 새로고침 분기 처리")

# 6) 채팅 이미지 전송: compressImageFile 실패(예: 특정 사진 포맷 디코딩 실패) 시 원인 모른 채 조용히 안 보내지는 문제 방지
#    - try/catch로 감싸서 실패 사유를 사용자에게 안내(원인 파악 가능하도록)
old_chat_img = """async function handleChatImageUpload(e){
  const file = e.target.files[0]; if(!file || !activeRoomId) return;
  const image = await compressImageFile(file);
  socket.emit('chat:send_image', {roomId:activeRoomId, image}, (res)=>{
    if (res && res.blocked) showMiniAlert(res.message || '부적절한 사진으로 감지되어 전송할 수 없습니다.', [{label:'확인', primary:true}]);
  });
}"""

new_chat_img = """async function handleChatImageUpload(e){
  const file = e.target.files[0]; if(!file || !activeRoomId) return;
  let image;
  try {
    image = await compressImageFile(file);
  } catch (err) {
    console.error('사진 처리 실패:', err);
    showMiniAlert('이 사진은 불러올 수 없어요. 다른 사진으로 다시 시도해주세요.', [{label:'확인', primary:true}]);
    e.target.value = '';
    return;
  }
  socket.emit('chat:send_image', {roomId:activeRoomId, image}, (res)=>{
    if (!res) { showMiniAlert('사진 전송에 실패했어요. 잠시 후 다시 시도해주세요.', [{label:'확인', primary:true}]); return; }
    if (res.blocked) showMiniAlert(res.message || '부적절한 사진으로 감지되어 전송할 수 없습니다.', [{label:'확인', primary:true}]);
    else if (!res.success) showMiniAlert(res.message || '사진 전송에 실패했어요. 잠시 후 다시 시도해주세요.', [{label:'확인', primary:true}]);
  });
  e.target.value = '';
}"""

c = must_replace(c, old_chat_img, new_chat_img, "1:1 채팅 이미지 업로드 에러 처리 보강")

old_group_img = """async function handleGroupChatImageUpload(e){
  const file = e.target.files[0]; if(!file || !activeGroupRoomId) return;
  const image = await compressImageFile(file);
  socket.emit('group:send_image', {roomId:activeGroupRoomId, image}, (res)=>{
    if (res && res.blocked) showMiniAlert(res.message || '부적절한 사진으로 감지되어 전송할 수 없습니다.', [{label:'확인', primary:true}]);
  });
}"""

new_group_img = """async function handleGroupChatImageUpload(e){
  const file = e.target.files[0]; if(!file || !activeGroupRoomId) return;
  let image;
  try {
    image = await compressImageFile(file);
  } catch (err) {
    console.error('사진 처리 실패:', err);
    showMiniAlert('이 사진은 불러올 수 없어요. 다른 사진으로 다시 시도해주세요.', [{label:'확인', primary:true}]);
    e.target.value = '';
    return;
  }
  socket.emit('group:send_image', {roomId:activeGroupRoomId, image}, (res)=>{
    if (!res) { showMiniAlert('사진 전송에 실패했어요. 잠시 후 다시 시도해주세요.', [{label:'확인', primary:true}]); return; }
    if (res.blocked) showMiniAlert(res.message || '부적절한 사진으로 감지되어 전송할 수 없습니다.', [{label:'확인', primary:true}]);
    else if (!res.success) showMiniAlert(res.message || '사진 전송에 실패했어요. 잠시 후 다시 시도해주세요.', [{label:'확인', primary:true}]);
  });
  e.target.value = '';
}"""

c = must_replace(c, old_group_img, new_group_img, "단체채팅 이미지 업로드 에러 처리 보강")

write(CLIENT, c)
print("✅ public/index.html 패치 완료")
print("✅ 0-38 패치 전체 완료")