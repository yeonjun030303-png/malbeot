# -*- coding: utf-8 -*-
"""
0-22 패치
1) server.js: 관리자모드에 "구독관리" 탭 추가용 소켓 2개 신설
   - admin:subscription:grant (userId, tier, days) : 골드/플래티넘 수동 지급(테스트/CS용, 즉시 덮어쓰기 방식)
   - admin:subscription:revoke (userId) : 구독 해제
2) public/index.html:
   - 관리자모드에 "구독관리" 탭 추가(닉네임 검색 → 골드14일/1년, 플래티넘14일/1년 지급 버튼 + 회수 버튼)
   - 관리자 탭 버튼 줄을 가로 스크롤 방식으로 변경(탭 5개로 늘어나 안 잘리게)
   - 골드 아이콘을 메달(🏅) 대신 플래티넘과 같은 보석 아이콘(fa-gem)의 금색 버전으로 통일
실행: 저장소 루트(/workspaces/malbeot/malbeot-app)에서 python3 patch_0_22.py
"""
import sys

SERVER_PATH = 'server.js'
HTML_PATH = 'public/index.html'

def replace_once(text, old, new, label):
    cnt = text.count(old)
    if cnt != 1:
        print(f'[실패] {label} — 매칭 {cnt}건(1건이어야 함). 패치 중단.')
        sys.exit(1)
    return text.replace(old, new)

# ============================================================
# 1) server.js
# ============================================================
with open(SERVER_PATH, encoding='utf-8') as f:
    server = f.read()

old_anchor = """  // 어뷰징 의심(동일 기기로 계정 2개 이상) 그룹 목록 - 관리자만
  socket.on('admin:abuse:list', async (data, cb) => {"""

new_block = """  // 0-22: 관리자 - 구독 등급(골드/플래티넘) 수동 지급/회수 (테스트·CS 대응용, 결제 없이 즉시 반영)
  socket.on('admin:subscription:grant', async (data, cb) => {
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
  });
  // 0-22: 관리자 - 구독 강제 해제
  socket.on('admin:subscription:revoke', async (data, cb) => {
    try {
      const requester = await getUser(socketToUser[socket.id]);
      if (!requester || !isAdmin(requester)) return cb && cb({ success: false });
      const targetId = data && data.userId;
      if (!targetId) return cb && cb({ success: false });
      const target = await getUser(targetId);
      if (!target) return cb && cb({ success: false, message: '유저를 찾을 수 없습니다.' });
      target.subscription = null;
      await saveUser(target);
      console.log(`[관리자 구독 해제] ${requester.nickname}(이)가 ${target.nickname}의 구독을 해제`);
      const sId = userToSocket[target.id];
      if (sId) io.to(sId).emit('points:updated', { points: target.points, subscription: null });
      broadcastUsers();
      cb && cb({ success: true });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 어뷰징 의심(동일 기기로 계정 2개 이상) 그룹 목록 - 관리자만
  socket.on('admin:abuse:list', async (data, cb) => {"""

server = replace_once(server, old_anchor, new_block, '1-1 admin 구독 지급/회수 소켓 추가')

with open(SERVER_PATH, 'w', encoding='utf-8') as f:
    f.write(server)
print('✅ [1/2] server.js — 관리자 구독 지급/회수 소켓(admin:subscription:grant/revoke) 추가 완료')

# ============================================================
# 2) public/index.html
# ============================================================
with open(HTML_PATH, encoding='utf-8') as f:
    html = f.read()

# 2-1 관리자 탭 버튼 줄: 가로 스크롤 방식으로 변경 + "구독관리" 탭 버튼 추가
old_tabs = """      <div style="display:flex;gap:8px;margin-bottom:16px;">
        <button id="adminTabReportsBtn" class="btn btn-secondary" style="flex:1;" onclick="switchAdminTab('reports')">신고 관리</button>
        <button id="adminTabChatsBtn" class="btn btn-secondary" style="flex:1;" onclick="switchAdminTab('chats')">전체 채팅방</button>
        <button id="adminTabAbuseBtn" class="btn btn-secondary" style="flex:1;" onclick="switchAdminTab('abuse')">어뷰징 의심</button>
        <button id="adminTabPhoneBtn" class="btn btn-secondary" style="flex:1;" onclick="switchAdminTab('phone')">번호변경</button>
      </div>"""
new_tabs = """      <div style="display:flex;gap:8px;margin-bottom:16px;overflow-x:auto;padding-bottom:2px;">
        <button id="adminTabReportsBtn" class="btn btn-secondary" style="flex:0 0 auto;white-space:nowrap;" onclick="switchAdminTab('reports')">신고 관리</button>
        <button id="adminTabChatsBtn" class="btn btn-secondary" style="flex:0 0 auto;white-space:nowrap;" onclick="switchAdminTab('chats')">전체 채팅방</button>
        <button id="adminTabAbuseBtn" class="btn btn-secondary" style="flex:0 0 auto;white-space:nowrap;" onclick="switchAdminTab('abuse')">어뷰징 의심</button>
        <button id="adminTabPhoneBtn" class="btn btn-secondary" style="flex:0 0 auto;white-space:nowrap;" onclick="switchAdminTab('phone')">번호변경</button>
        <button id="adminTabSubBtn" class="btn btn-secondary" style="flex:0 0 auto;white-space:nowrap;" onclick="switchAdminTab('sub')">구독관리</button>
      </div>"""
html = replace_once(html, old_tabs, new_tabs, '2-1 관리자 탭 버튼 줄 교체')

# 2-2 구독관리 탭 패널 추가(번호변경 탭 뒤에)
old_phone_tab = """      <div id="adminPhoneTab" class="hidden">
        <div id="adminPhoneRequestList"></div>
      </div>"""
new_phone_tab = """      <div id="adminPhoneTab" class="hidden">
        <div id="adminPhoneRequestList"></div>
      </div>
      <div id="adminSubTab" class="hidden">
        <div style="font-size:12px;color:var(--text-muted);margin-bottom:10px;">닉네임으로 유저를 검색해 골드/플래티넘을 결제 없이 즉시 지급하거나 회수할 수 있어요(테스트·CS 대응용).</div>
        <div style="display:flex;gap:8px;margin-bottom:14px;">
          <input id="adminSubSearchInput" type="text" placeholder="닉네임 검색" style="flex:1;padding:10px 12px;border:1px solid var(--border-color);border-radius:10px;background:var(--bg-input);color:var(--text-main);" onkeydown="if(event.key==='Enter') searchAdminSubscriptionUsers()">
          <button class="btn btn-secondary" onclick="searchAdminSubscriptionUsers()">검색</button>
        </div>
        <div id="adminSubSearchResults"></div>
      </div>"""
html = replace_once(html, old_phone_tab, new_phone_tab, '2-2 구독관리 탭 패널 추가')

# 2-3 switchAdminTab에 'sub' 케이스 추가
old_switch = """  const pBtn = document.getElementById('adminTabPhoneBtn');
  rBtn.style.background = tab==='reports' ? 'var(--primary)' : '';
  rBtn.style.color = tab==='reports' ? '#fff' : '';
  cBtn.style.background = tab==='chats' ? 'var(--primary)' : '';
  cBtn.style.color = tab==='chats' ? '#fff' : '';
  aBtn.style.background = tab==='abuse' ? 'var(--primary)' : '';
  aBtn.style.color = tab==='abuse' ? '#fff' : '';
  pBtn.style.background = tab==='phone' ? 'var(--primary)' : '';
  pBtn.style.color = tab==='phone' ? '#fff' : '';
  document.getElementById('adminReportsTab').classList.toggle('hidden', tab!=='reports');
  document.getElementById('adminChatsTab').classList.toggle('hidden', tab!=='chats');
  document.getElementById('adminAbuseTab').classList.toggle('hidden', tab!=='abuse');
  document.getElementById('adminPhoneTab').classList.toggle('hidden', tab!=='phone');
  if (tab==='reports') loadAdminReports();
  else if (tab==='chats') loadAdminChatRooms();
  else if (tab==='phone') loadAdminPhoneRequests();
  else loadAdminAbuse();
}"""
new_switch = """  const pBtn = document.getElementById('adminTabPhoneBtn');
  const sBtn = document.getElementById('adminTabSubBtn');
  rBtn.style.background = tab==='reports' ? 'var(--primary)' : '';
  rBtn.style.color = tab==='reports' ? '#fff' : '';
  cBtn.style.background = tab==='chats' ? 'var(--primary)' : '';
  cBtn.style.color = tab==='chats' ? '#fff' : '';
  aBtn.style.background = tab==='abuse' ? 'var(--primary)' : '';
  aBtn.style.color = tab==='abuse' ? '#fff' : '';
  pBtn.style.background = tab==='phone' ? 'var(--primary)' : '';
  pBtn.style.color = tab==='phone' ? '#fff' : '';
  sBtn.style.background = tab==='sub' ? 'var(--primary)' : '';
  sBtn.style.color = tab==='sub' ? '#fff' : '';
  document.getElementById('adminReportsTab').classList.toggle('hidden', tab!=='reports');
  document.getElementById('adminChatsTab').classList.toggle('hidden', tab!=='chats');
  document.getElementById('adminAbuseTab').classList.toggle('hidden', tab!=='abuse');
  document.getElementById('adminPhoneTab').classList.toggle('hidden', tab!=='phone');
  document.getElementById('adminSubTab').classList.toggle('hidden', tab!=='sub');
  if (tab==='reports') loadAdminReports();
  else if (tab==='chats') loadAdminChatRooms();
  else if (tab==='phone') loadAdminPhoneRequests();
  else if (tab==='sub') { /* 검색 후 로드되므로 초기엔 아무것도 안 함 */ }
  else loadAdminAbuse();
}
// 0-22: 관리자 구독관리 탭 - 닉네임 검색 + 지급/회수
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
      const statusText = active
        ? `${sub.tier==='platinum'?'플래티넘':'골드'} 구독 중 · ${new Date(sub.expiresAt).toLocaleDateString('ko-KR')}까지`
        : '구독 없음';
      return `
      <div class="settings-list-item" style="flex-direction:column;align-items:stretch;cursor:default;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <b>${escapeHtml(u.nickname)}</b>
          <span style="font-size:11px;color:${active?'var(--primary)':'var(--text-muted)'};">${statusText}</span>
        </div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;">
          <button class="btn btn-secondary btn-sm" onclick="grantAdminSubscription('${u.id}','gold',14)">골드 14일</button>
          <button class="btn btn-secondary btn-sm" onclick="grantAdminSubscription('${u.id}','gold',365)">골드 1년</button>
          <button class="btn btn-secondary btn-sm" onclick="grantAdminSubscription('${u.id}','platinum',14)">플래 14일</button>
          <button class="btn btn-secondary btn-sm" onclick="grantAdminSubscription('${u.id}','platinum',365)">플래 1년</button>
          ${active?`<button class="btn btn-sm" style="background:var(--danger,#ef4444);color:#fff;" onclick="revokeAdminSubscription('${u.id}')">회수</button>`:''}
        </div>
      </div>`;
    }).join('');
  });
}
function grantAdminSubscription(userId, tier, days){
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
html = replace_once(html, old_switch, new_switch, '2-3 switchAdminTab에 sub 탭 로직 추가')

# 2-4 골드 아이콘 통일: 메달(🏅) 대신 플래티넘과 같은 보석 아이콘(fa-gem)을 금색으로
old_icon1 = "document.getElementById('subStatusTierLabel').textContent = (sub.tier === 'platinum' ? '💎 플래티넘' : '🏅 골드') + ' 구독 중';"
new_icon1 = "document.getElementById('subStatusTierLabel').innerHTML = `<i class=\"fa-solid fa-gem\" style=\"color:${sub.tier==='platinum'?'#059669':'#c9891a'};margin-right:4px;\"></i>${sub.tier === 'platinum' ? '플래티넘' : '골드'} 구독 중`;"
html = replace_once(html, old_icon1, new_icon1, '2-4 마이페이지 등급 라벨 아이콘 통일')

old_icon2 = '<div style="font-weight:800;font-size:14px;">${isPlat?\'💎 플래티넘\':\'🏅 골드\'} ${periodLabel}</div>'
new_icon2 = '<div style="font-weight:800;font-size:14px;"><i class="fa-solid fa-gem" style="color:${isPlat?\'#059669\':\'#c9891a\'};margin-right:4px;"></i>${isPlat?\'플래티넘\':\'골드\'} ${periodLabel}</div>'
html = replace_once(html, old_icon2, new_icon2, '2-5 구독 상품 목록 아이콘 통일')

with open(HTML_PATH, 'w', encoding='utf-8') as f:
    f.write(html)
print('✅ [2/2] public/index.html — 관리자 구독관리 탭 UI 추가 + 골드/플래티넘 아이콘 통일(같은 보석 모양, 색만 다름) 완료')
print('   0-22 패치 전체 완료')