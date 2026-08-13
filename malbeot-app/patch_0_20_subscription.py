#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
0-20: 유료 구독제(골드/플래티넘) - 1차 구현
1) 서버: SUBSCRIPTION_PRODUCTS 상품맵 + RevenueCat 웹훅에서 구독 등급/만료일 부여(연장 지원)
2) 서버: 방문자 전체기간 조회(profile:get_all_visitors), 사진 좋아요 누른사람 목록(photo:get_likers) - 골드 이상만 열람
3) 서버: 등급 표시 옵션 저장(account:set_subscription_prefs) - 로고색상/뱃지 온오프
4) 클라이언트: 구독 구매 화면(subscriptionScreen), 마이페이지 진입카드, 설정화면 등급카드(로고색상/뱃지 스위치)
5) 클라이언트: 방문자 화면에 "전체기간 방문자" 섹션 추가(잠금 티저 UI 포함), 사진뷰어에 "좋아요 누른 사람" 진입점+화면 추가
6) 클라이언트: 로고 그라디언트 색상 실시간 적용(본인 화면에서만), 나만의 페이지 별명 옆 등급 뱃지 표시
"""

SERVER_PATH = "server.js"
INDEX_PATH = "public/index.html"


def patch_server():
    with open(SERVER_PATH, "r", encoding="utf-8") as f:
        s = f.read()

    # 1) getUser/saveUser 바로 뒤에 구독 헬퍼 함수 추가
    old_getuser = """async function getUser(id) {
  const snap = await db.ref(`users/${id}`).once('value');
  return snap.val();
}
async function saveUser(user) {
  await db.ref(`users/${user.id}`).set(user);
}"""
    assert s.count(old_getuser) == 1, "getUser/saveUser 블록을 찾지 못함"
    new_getuser = old_getuser + """
// 0-20: 유료 구독(골드/플래티넘) 헬퍼 - expiresAt이 지나지 않았을 때만 "활성 구독"으로 인정함
const SUBSCRIPTION_TIER_RANK = { gold: 1, platinum: 2 };
function getActiveSubscription(user) {
  const sub = user && user.subscription;
  if (!sub || !sub.tier || !sub.expiresAt || sub.expiresAt <= Date.now()) return null;
  return sub;
}
function hasTierAtLeast(user, minTier) {
  const sub = getActiveSubscription(user);
  if (!sub) return false;
  return (SUBSCRIPTION_TIER_RANK[sub.tier] || 0) >= (SUBSCRIPTION_TIER_RANK[minTier] || 0);
}"""
    s = s.replace(old_getuser, new_getuser, 1)

    # 2) POINTS_BY_PRODUCT 옆에 SUBSCRIPTION_PRODUCTS 상품맵 추가
    old_points_map = """const POINTS_BY_PRODUCT = {
  points_1000: 1100, // 1000 + 10% 보너스
  points_3000: 3600, // 3000 + 20% 보너스
  points_5000: 6750  // 5000 + 35% 보너스
};"""
    assert s.count(old_points_map) == 1, "POINTS_BY_PRODUCT 맵을 찾지 못함"
    new_points_map = old_points_map + """

// 0-20: 유료 구독제(골드/플래티넘) 상품 - 자동결제(정기구독)가 아닌 14일권/1년권 "1회성 구매" 상품임.
// 상품ID/일수/등급/보너스쌀 값은 실제 Play 콘솔·App Store Connect·RevenueCat 대시보드에 등록한 상품과
// 정확히 같아야 함(실제 상품 등록/가격 확정은 코드 범위 밖 - 기존 쌀 상품과 동일하게 사용자가 직접 진행).
// 가격은 참고용 placeholder(1년권 = 14일권 26회분의 70%로 계산)이며 실제 판매가는 스토어 콘솔에서 확정함.
const SUBSCRIPTION_PRODUCTS = {
  sub_gold_14d:      { tier: 'gold',     days: 14,  points: 1000 },
  sub_platinum_14d:  { tier: 'platinum', days: 14,  points: 3000 },
  sub_gold_365d:     { tier: 'gold',     days: 365, points: 1000 },
  sub_platinum_365d: { tier: 'platinum', days: 365, points: 3000 }
};"""
    s = s.replace(old_points_map, new_points_map, 1)

    # 3) 웹훅 본문 - 구독 상품이면 등급/만료일도 함께 갱신하도록 분기 추가
    old_webhook_body = """    const userId = event.app_user_id;
    const productId = event.product_id;
    const grantPoints = POINTS_BY_PRODUCT[productId];

    if (!userId || !grantPoints) {
      console.warn('[RevenueCat 웹훅] 알 수 없는 유저 또는 상품:', userId, productId);
      return res.status(200).send('unknown product or user');
    }

    const user = await getUser(userId);
    if (!user) {
      console.warn('[RevenueCat 웹훅] 유저를 찾을 수 없음:', userId);
      return res.status(200).send('user not found');
    }

    user.points = (user.points || 0) + grantPoints;
    await saveUser(user);
    if (eventId) await db.ref(`processedPurchaseEvents/${eventId}`).set({ userId, productId, grantPoints, at: Date.now() });

    console.log(`[RevenueCat 웹훅] ${userId} 유저에게 쌀 ${grantPoints}개 지급 완료 (상품: ${productId})`);

    // 지금 접속 중인 유저라면 실시간으로 잔액을 갱신해줌 (접속 중이 아니면 다음 로그인 시 서버 데이터로 자동 반영됨)
    const sId = userToSocket[userId];
    if (sId) io.to(sId).emit('points:updated', { points: user.points });

    res.status(200).send('ok');"""
    assert s.count(old_webhook_body) == 1, "웹훅 본문 블록을 찾지 못함"
    new_webhook_body = """    const userId = event.app_user_id;
    const productId = event.product_id;
    const subProduct = SUBSCRIPTION_PRODUCTS[productId];
    const grantPoints = subProduct ? subProduct.points : POINTS_BY_PRODUCT[productId];

    if (!userId || !grantPoints) {
      console.warn('[RevenueCat 웹훅] 알 수 없는 유저 또는 상품:', userId, productId);
      return res.status(200).send('unknown product or user');
    }

    const user = await getUser(userId);
    if (!user) {
      console.warn('[RevenueCat 웹훅] 유저를 찾을 수 없음:', userId);
      return res.status(200).send('user not found');
    }

    user.points = (user.points || 0) + grantPoints;

    // 0-20: 구독 상품이면 등급+만료일도 함께 갱신. 이미 활성 구독 중이면 남은 기간에 새로 산 기간을 이어붙임(연장).
    // 등급이 다르면(예: 골드 구독 중 플래티넘 구매) 더 높은 등급으로 올리고 남은 기간은 그대로 이어붙임.
    if (subProduct) {
      const now = Date.now();
      const prevSub = getActiveSubscription(user);
      const base = prevSub ? prevSub.expiresAt : now;
      const newTier = (prevSub && (SUBSCRIPTION_TIER_RANK[prevSub.tier] || 0) > (SUBSCRIPTION_TIER_RANK[subProduct.tier] || 0))
        ? prevSub.tier : subProduct.tier;
      user.subscription = {
        tier: newTier,
        expiresAt: base + subProduct.days * 24 * 60 * 60 * 1000,
        logoColorOn: (user.subscription && typeof user.subscription.logoColorOn === 'boolean') ? user.subscription.logoColorOn : true,
        badgeOn: (user.subscription && typeof user.subscription.badgeOn === 'boolean') ? user.subscription.badgeOn : true
      };
    }

    await saveUser(user);
    if (eventId) await db.ref(`processedPurchaseEvents/${eventId}`).set({ userId, productId, grantPoints, at: Date.now() });

    console.log(`[RevenueCat 웹훅] ${userId} 유저에게 쌀 ${grantPoints}개 지급 완료${subProduct ? ` + 구독(${subProduct.tier}, ${subProduct.days}일)` : ''} (상품: ${productId})`);

    // 지금 접속 중인 유저라면 실시간으로 잔액+구독 상태를 갱신해줌 (접속 중이 아니면 다음 로그인 시 서버 데이터로 자동 반영됨)
    const sId = userToSocket[userId];
    if (sId) io.to(sId).emit('points:updated', { points: user.points, subscription: user.subscription || null });
    broadcastUsers();

    res.status(200).send('ok');"""
    s = s.replace(old_webhook_body, new_webhook_body, 1)

    # 4) profile:get_today_visitors 핸들러 뒤에 전체기간 조회 핸들러 추가
    old_today_visitors = """  // 오늘(KST) 내 프로필 방문자 수 + 목록 조회 (본인만 조회 가능 - 로그인한 본인 소켓 기준으로 본인 것만 조회)
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
  });"""
    assert s.count(old_today_visitors) == 1, "profile:get_today_visitors 핸들러를 찾지 못함"
    new_today_visitors = old_today_visitors + """

  // 0-20: 방문자 "전체 기간" 조회 - 골드 이상 구독 중인 본인만 실제 목록 열람 가능(오늘 방문자는 위 핸들러로 계속 무료 열람)
  socket.on('profile:get_all_visitors', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      if (!userId) return cb && cb({ success: false, count: 0, visitors: [] });
      const snap = await db.ref(`profileVisits/${userId}`).once('value');
      const byDate = snap.val() || {};
      const latestByVisitor = {};
      Object.keys(byDate).forEach(date => {
        const dayMap = byDate[date] || {};
        Object.keys(dayMap).forEach(vId => {
          const ts = dayMap[vId];
          if (!latestByVisitor[vId] || ts > latestByVisitor[vId]) latestByVisitor[vId] = ts;
        });
      });
      const visitorIds = Object.keys(latestByVisitor).sort((a, b) => latestByVisitor[b] - latestByVisitor[a]);
      const me = await getUser(userId);
      if (!hasTierAtLeast(me, 'gold')) {
        return cb && cb({ success: true, locked: true, count: visitorIds.length, visitors: [] });
      }
      const users = await getAllUsers();
      const visitors = visitorIds.map(id => users[id]).filter(Boolean);
      cb && cb({ success: true, locked: false, count: visitorIds.length, visitors });
    } catch (e) { console.error(e); cb && cb({ success: false, count: 0, visitors: [] }); }
  });"""
    s = s.replace(old_today_visitors, new_today_visitors, 1)

    # 5) photo:like 핸들러 뒤에 좋아요 누른 사람 목록 조회 핸들러 추가
    old_photo_like_tail = """      await saveUser(target);
      cb && cb({ success: true, liked: !alreadyLiked, likeCount: Object.keys(target.photoLikes[photoIndex] || {}).length });
      broadcastUsers();
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });"""
    assert s.count(old_photo_like_tail) == 1, "photo:like 핸들러 끝부분을 찾지 못함"
    new_photo_like_tail = old_photo_like_tail + """

  // 0-20: 특정 사진에 좋아요 누른 사람 "목록" 조회 - 골드 이상 구독 중인 사람만 실제 목록 열람 가능
  // (하트 개수 자체는 기존처럼 누구나 항상 전체 공개 - 이 핸들러와 무관하게 photoLikes 데이터로 이미 계산됨)
  socket.on('photo:get_likers', async (data, cb) => {
    try {
      const myId = socketToUser[socket.id];
      const targetId = data && data.targetUserId;
      const photoIndex = data && typeof data.photoIndex === 'number' ? data.photoIndex : null;
      if (!myId || !targetId || photoIndex === null) return cb && cb({ success: false, count: 0, likers: [] });
      const target = await getUser(targetId);
      if (!target) return cb && cb({ success: false, count: 0, likers: [] });
      const likerIds = Object.keys((target.photoLikes && target.photoLikes[photoIndex]) || {});
      const me = await getUser(myId);
      if (!hasTierAtLeast(me, 'gold')) {
        return cb && cb({ success: true, locked: true, count: likerIds.length, likers: [] });
      }
      const users = await getAllUsers();
      const likers = likerIds.map(id => users[id]).filter(Boolean);
      cb && cb({ success: true, locked: false, count: likerIds.length, likers });
    } catch (e) { console.error(e); cb && cb({ success: false, count: 0, likers: [] }); }
  });"""
    s = s.replace(old_photo_like_tail, new_photo_like_tail, 1)

    # 6) account:set_phone 핸들러 앞에 구독 표시 옵션 저장 핸들러 추가
    old_phone_comment = """  // ===================== 개인 전화번호 등록/변경 =====================
  // 카카오 가입 후 최초 1회만 본인 전화번호를 직접 입력받아 저장(카카오 실제번호 대조는 카카오 비즈앱 심사 필요해 이번 범위 아님).
  // 이미 번호가 등록돼 있으면 phoneChangeApproved(관리자 승인)가 true일 때만 재등록 가능하고, 성공하면 승인 플래그는 소모됨.
  socket.on('account:set_phone', async (data, cb) => {"""
    assert s.count(old_phone_comment) == 1, "account:set_phone 핸들러 앞부분을 찾지 못함"
    new_phone_comment = """  // 0-20: 구독 등급 표시 옵션(로고 색상 적용 / 상대방에게 등급뱃지 노출) 온오프 - 활성 구독 중일 때만 저장 가능
  socket.on('account:set_subscription_prefs', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const target = userId ? await getUser(userId) : null;
      if (!target) return cb && cb({ success: false });
      if (!hasTierAtLeast(target, 'gold')) return cb && cb({ success: false, message: '구독 중일 때만 설정할 수 있습니다.' });
      target.subscription = target.subscription || {};
      if (typeof (data && data.logoColorOn) === 'boolean') target.subscription.logoColorOn = data.logoColorOn;
      if (typeof (data && data.badgeOn) === 'boolean') target.subscription.badgeOn = data.badgeOn;
      await saveUser(target);
      cb && cb({ success: true, subscription: target.subscription });
      broadcastUsers();
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // ===================== 개인 전화번호 등록/변경 =====================
  // 카카오 가입 후 최초 1회만 본인 전화번호를 직접 입력받아 저장(카카오 실제번호 대조는 카카오 비즈앱 심사 필요해 이번 범위 아님).
  // 이미 번호가 등록돼 있으면 phoneChangeApproved(관리자 승인)가 true일 때만 재등록 가능하고, 성공하면 승인 플래그는 소모됨.
  socket.on('account:set_phone', async (data, cb) => {"""
    s = s.replace(old_phone_comment, new_phone_comment, 1)

    with open(SERVER_PATH, "w", encoding="utf-8") as f:
        f.write(s)
    print("server.js 패치 완료")


def patch_index():
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        s = f.read()

    # 1) riceChargeScreen 뒤에 subscriptionScreen / photoLikersScreen 전체화면 추가
    old_rice_close = """      <p style="font-size:11px;color:var(--text-muted);text-align:center;margin-top:18px;line-height:1.6;">
        결제는 Google Play / App Store 인앱결제로 안전하게 처리됩니다.<br>
        쌀은 충전 즉시 사용 가능하며, 일부라도 사용 시 환불이 제한됩니다.<br>부적절한 언행으로 이용정지·회원탈퇴 처리될 경우 환불이 불가합니다.
      </p>
    </div>
  </div>"""
    assert s.count(old_rice_close) == 1, "riceChargeScreen 종료부를 찾지 못함"
    new_rice_close = old_rice_close + """

  <div id="subscriptionScreen" class="full-screen-overlay">
    <div class="fs-header"><button class="back-btn" onclick="closeFullScreen('subscriptionScreen')"><i class="fa-solid fa-arrow-left"></i></button><div class="fs-title">말벗 구독</div></div>
    <div class="fs-body" style="padding:20px 16px 40px;">
      <div id="subscriptionCurrentStatus" style="text-align:center;margin-bottom:18px;font-size:13px;color:var(--text-muted);line-height:1.6;"></div>
      <div id="subscriptionPackageGrid" style="display:flex;flex-direction:column;gap:10px;"></div>
      <p style="font-size:11px;color:var(--text-muted);text-align:center;margin-top:18px;line-height:1.6;">
        구독 상품은 자동 결제(정기결제)가 아닌 1회성 결제이며, 만료되면 자동으로 연장되지 않습니다.<br>
        기존에 남은 기간이 있는 상태에서 다시 구매하면 남은 기간에 이어서 연장됩니다.<br>
        결제는 Google Play / App Store 인앱결제로 안전하게 처리됩니다.
      </p>
    </div>
  </div>

  <div id="photoLikersScreen" class="full-screen-overlay">
    <div class="fs-header"><button class="back-btn" onclick="closeFullScreen('photoLikersScreen')"><i class="fa-solid fa-arrow-left"></i></button><div class="fs-title">좋아요 누른 사람</div></div>
    <div class="fs-body" id="photoLikersBody" style="padding:8px 16px;"></div>
  </div>"""
    s = s.replace(old_rice_close, new_rice_close, 1)

    # 2) tab-mypage에 "말벗 구독" 진입 카드 추가 (오늘 방문자 카드 바로 아래)
    old_mypage_visitor_card = """        <div class="settings-list-item" style="background:var(--bg-card);border:1px solid var(--border-color);border-radius:16px;padding:14px 16px;" onclick="openProfileVisitorsScreen()">
          <div><div class="sli-label"><i class="fa-solid fa-eye"></i> 오늘 내 프로필 방문자</div><div class="sli-sub">매일 자정에 초기화됩니다</div></div>
          <div class="sli-right"><span id="myPageVisitorCount" style="font-weight:700;margin-right:4px;">0명</span><i class="fa-solid fa-chevron-right"></i></div>
        </div>"""
    assert s.count(old_mypage_visitor_card) == 1, "마이페이지 오늘 방문자 카드를 찾지 못함"
    new_mypage_visitor_card = old_mypage_visitor_card + """
        <div class="settings-list-item" style="background:linear-gradient(135deg,#fff7e0,#fff1c9);border:1px solid #f0d98a;border-radius:16px;padding:14px 16px;" onclick="openSubscriptionScreen()">
          <div><div class="sli-label"><i class="fa-solid fa-crown" style="color:#c9891a;"></i> 말벗 구독</div><div class="sli-sub" id="mypageSubStatusSub">골드/플래티넘 구독하고 더 많은 기능을 이용해보세요</div></div>
          <div class="sli-right"><i class="fa-solid fa-chevron-right"></i></div>
        </div>"""
    s = s.replace(old_mypage_visitor_card, new_mypage_visitor_card, 1)

    # 3) 설정화면 상단(관리자모드 행 뒤)에 구독 등급 카드(구독 중일 때만 노출) 추가
    old_admin_row = """      <div class="settings-list-item" id="adminModeRow" style="display:none;">
        <div><div class="sli-label">관리자 모드</div><div class="sli-sub">본인 계정에만 표시됩니다</div></div>
        <div class="toggle-switch" id="toggleAdminMode" onclick="toggleAdminMode()"><div class="knob"></div></div>
      </div>"""
    assert s.count(old_admin_row) == 1, "설정화면 관리자모드 행을 찾지 못함"
    new_admin_row = old_admin_row + """
      <div class="settings-card" id="subStatusCard" style="display:none;background:var(--bg-card);border:1px solid var(--border-color);border-radius:16px;padding:14px 16px;margin-bottom:14px;">
        <div style="display:flex;justify-content:space-between;align-items:center;cursor:pointer;" onclick="toggleSubStatusAccordion()">
          <div><span id="subStatusTierLabel" style="font-weight:800;font-size:14px;"></span><div style="font-size:11px;color:var(--text-muted);margin-top:2px;" id="subStatusExpireLabel"></div></div>
          <i class="fa-solid fa-chevron-down accordion-arrow" id="subStatusArrow"></i>
        </div>
        <div id="subStatusBody" style="display:none;margin-top:12px;">
          <div class="settings-list-item">
            <div><div class="sli-label">로고 색상 적용</div><div class="sli-sub">앱 전체에서 내 화면에만 말벗 로고가 등급 색상으로 표시돼요</div></div>
            <div class="toggle-switch" id="toggleSubLogoColor" onclick="toggleSubLogoColor()"><div class="knob"></div></div>
          </div>
          <div class="settings-list-item">
            <div><div class="sli-label">상대방에게 등급 표기</div><div class="sli-sub">내 별명 옆에 등급 뱃지가 다른 사람에게 보여요</div></div>
            <div class="toggle-switch" id="toggleSubBadge" onclick="toggleSubBadge()"><div class="knob"></div></div>
          </div>
        </div>
      </div>"""
    s = s.replace(old_admin_row, new_admin_row, 1)

    # 4) openSettingsScreen 안에서 구독카드 렌더 호출 추가
    old_settings_open_tail = """  document.getElementById('adminModeRow').style.display = (currentUser && currentUser.isAdmin) ? 'flex' : 'none';
  document.getElementById('toggleAdminMode').classList.remove('on');
  openFullScreen('settingsScreen');
}"""
    assert s.count(old_settings_open_tail) == 1, "openSettingsScreen 끝부분을 찾지 못함"
    new_settings_open_tail = """  document.getElementById('adminModeRow').style.display = (currentUser && currentUser.isAdmin) ? 'flex' : 'none';
  document.getElementById('toggleAdminMode').classList.remove('on');
  renderSubStatusCard();
  openFullScreen('settingsScreen');
}
// 0-20: 설정화면 상단 구독 등급 카드 - 활성 구독 중일 때만 노출됨
function renderSubStatusCard(){
  const card = document.getElementById('subStatusCard');
  if (!card) return;
  const sub = currentUser && currentUser.subscription;
  const active = sub && sub.tier && sub.expiresAt && sub.expiresAt > Date.now();
  card.style.display = active ? 'block' : 'none';
  if (!active) return;
  document.getElementById('subStatusTierLabel').textContent = (sub.tier === 'platinum' ? '💎 플래티넘' : '🏅 골드') + ' 구독 중';
  document.getElementById('subStatusExpireLabel').textContent = `${new Date(sub.expiresAt).toLocaleDateString('ko-KR')}까지`;
  document.getElementById('toggleSubLogoColor').classList.toggle('on', sub.logoColorOn !== false);
  document.getElementById('toggleSubBadge').classList.toggle('on', sub.badgeOn !== false);
}
function toggleSubStatusAccordion(){
  const body = document.getElementById('subStatusBody');
  const willOpen = body.style.display === 'none';
  body.style.display = willOpen ? 'block' : 'none';
  document.getElementById('subStatusArrow').classList.toggle('open', willOpen);
}
function toggleSubLogoColor(){
  const sub = (currentUser && currentUser.subscription) || {};
  const next = !(sub.logoColorOn !== false);
  socket.emit('account:set_subscription_prefs', {logoColorOn: next}, (res)=>{
    if (res && res.success){ currentUser.subscription = res.subscription; saveSession(); renderSubStatusCard(); applySubscriptionLogoColor(); }
  });
}
function toggleSubBadge(){
  const sub = (currentUser && currentUser.subscription) || {};
  const next = !(sub.badgeOn !== false);
  socket.emit('account:set_subscription_prefs', {badgeOn: next}, (res)=>{
    if (res && res.success){ currentUser.subscription = res.subscription; saveSession(); renderSubStatusCard(); }
  });
}
// 0-20: 마이페이지 "말벗 구독" 진입 카드의 부제목을 현재 구독 상태에 맞게 갱신
function refreshMypageSubLabel(){
  const el = document.getElementById('mypageSubStatusSub');
  if (!el) return;
  const sub = currentUser && currentUser.subscription;
  const active = sub && sub.tier && sub.expiresAt && sub.expiresAt > Date.now();
  el.textContent = active
    ? `${sub.tier==='platinum'?'플래티넘':'골드'} 구독 중 · ${new Date(sub.expiresAt).toLocaleDateString('ko-KR')}까지`
    : '골드/플래티넘 구독하고 더 많은 기능을 이용해보세요';
}
// 0-20: 나만의 페이지/방문자·좋아요 목록에서 별명 옆에 붙는 등급 뱃지 (활성 구독 + 뱃지 표시 옵션 켜져있을 때만)
function subscriptionBadgeHtml(user){
  const sub = user && user.subscription;
  if (!sub || !sub.tier || !sub.expiresAt || sub.expiresAt <= Date.now() || sub.badgeOn === false) return '';
  const isPlat = sub.tier === 'platinum';
  const bg = isPlat ? 'linear-gradient(135deg,#34d399,#059669)' : 'linear-gradient(135deg,#f6c453,#c9891a)';
  const label = isPlat ? '플래티넘' : '골드';
  return `<span style="display:inline-flex;align-items:center;gap:3px;background:${bg};color:#fff;font-size:9px;font-weight:800;padding:2px 7px;border-radius:99px;vertical-align:middle;margin-left:5px;"><i class="fa-solid fa-crown" style="font-size:8px;"></i>${label}</span>`;
}
// 0-20: 방문자/좋아요 목록 등에서 무료 유저에게 보여줄 잠금 티저 UI (블러 처리된 아바타 + 가운데 자물쇠 + 인원수(9+))
function renderLockTeaser(count, ctaText){
  const shown = Math.max(Math.min(count, 5), 1);
  const displayCount = count > 9 ? '9+' : String(count);
  let avatars = '';
  for (let i=0;i<shown;i++){
    avatars += `<div style="width:44px;height:44px;border-radius:50%;background:var(--bg-subtle);border:2px solid #fff;margin-left:${i===0?0:-14}px;filter:blur(3px);"></div>`;
  }
  return `
    <div style="position:relative;text-align:center;padding:30px 16px 22px;background:var(--bg-subtle);border-radius:16px;">
      <div style="display:flex;justify-content:center;">${avatars}</div>
      <div style="position:absolute;top:14px;left:50%;transform:translateX(-50%);width:34px;height:34px;border-radius:50%;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center;color:#fff;font-size:14px;"><i class="fa-solid fa-lock"></i></div>
      <div style="font-size:15px;font-weight:800;margin-top:10px;">${displayCount}명</div>
      <div style="font-size:12px;color:var(--text-muted);margin:6px 0 12px;">골드 이상 등급을 구독하면 ${ctaText}</div>
      <button class="btn btn-primary btn-sm" onclick="openSubscriptionScreen()">구독하기</button>
    </div>`;
}
// 0-20: 구독 상품 목록/구매/화면 - 기존 쌀 충전(RICE_PACKAGES/handleBuyRicePackage)과 동일한 방식으로 window.buyItem 재사용
// 가격은 참고용 placeholder(실제 판매가는 RevenueCat/스토어 콘솔에서 확정, server.js의 SUBSCRIPTION_PRODUCTS와 상품ID가 반드시 같아야 함)
const SUBSCRIPTION_PACKAGES = [
  { id: 'sub_gold_14d',      tier: 'gold',     days: 14,  price: 11900,  label: '골드 14일권' },
  { id: 'sub_platinum_14d',  tier: 'platinum', days: 14,  price: 26900,  label: '플래티넘 14일권' },
  { id: 'sub_gold_365d',     tier: 'gold',     days: 365, price: 216000, label: '골드 1년권' },
  { id: 'sub_platinum_365d', tier: 'platinum', days: 365, price: 489000, label: '플래티넘 1년권' }
];
function openSubscriptionScreen(){
  renderSubscriptionPackages();
  openFullScreen('subscriptionScreen');
}
function renderSubscriptionPackages(){
  const statusEl = document.getElementById('subscriptionCurrentStatus');
  const sub = currentUser && currentUser.subscription;
  const active = sub && sub.tier && sub.expiresAt && sub.expiresAt > Date.now();
  statusEl.innerHTML = active
    ? `현재 <strong style="color:var(--primary);">${sub.tier==='platinum'?'플래티넘':'골드'}</strong> 구독 중 (${new Date(sub.expiresAt).toLocaleDateString('ko-KR')}까지)<br>지금 구매하면 남은 기간에 이어서 연장돼요.`
    : `구독하면 쌀 지급 + 로고 색상 + 등급 뱃지 + 방문자/좋아요 전체 열람 혜택을 받아요.`;
  const grid = document.getElementById('subscriptionPackageGrid');
  grid.innerHTML = SUBSCRIPTION_PACKAGES.map(p=>{
    const isPlat = p.tier === 'platinum';
    const periodLabel = p.days >= 365 ? '1년권' : '14일권';
    return `
      <div style="display:flex;justify-content:space-between;align-items:center;border:1px solid ${isPlat?'#059669':'#c9891a'};border-radius:14px;padding:14px;">
        <div>
          <div style="font-weight:800;font-size:14px;">${isPlat?'💎 플래티넘':'🏅 골드'} ${periodLabel}</div>
          <div style="font-size:11px;color:var(--text-muted);margin-top:2px;">쌀 ${(isPlat?3000:1000).toLocaleString()}개 지급 · 등급뱃지 · 로고색상 · 방문자/좋아요 전체열람</div>
        </div>
        <div style="text-align:right;">
          <div style="font-weight:800;font-size:15px;margin-bottom:6px;">${p.price.toLocaleString()}원</div>
          <button class="btn ${isPlat?'':'btn-secondary'} btn-sm" style="${isPlat?'background:#059669;border-color:#059669;color:#fff;':''}" onclick="handleBuySubscriptionPackage('${p.id}')">구독</button>
        </div>
      </div>`;
  }).join('');
}
function handleBuySubscriptionPackage(productId){
  if (!window.buyItem){
    showMiniAlert('결제 기능을 사용할 수 없는 환경입니다. 말벗 앱(스토어 설치 버전)에서 이용해주세요.', [{label:'확인', primary:true}]);
    return;
  }
  window.buyItem(productId);
  // 실제 등급 지급은 서버가 결제 완료를 확인한 뒤 'points:updated' 이벤트(subscription 포함)로 반영됨
}
// 0-20: 말벗 로고 색상 - 화면 어디서든 fill="url(#mbGrad1/2)"로 참조하는 공용 그라디언트의 stop-color를
// 직접 바꿔서, 이 로그인 계정 화면에서만(다른 사람에게는 영향 없음) 로고가 즉시 등급 색상으로 보이게 함
const LOGO_GRAD_DEFAULT = [['#5c7cfa','#4c6ef5'],['#91a7ff','#5c7cfa']];
const LOGO_GRAD_GOLD = [['#f6c453','#c9891a'],['#ffe08a','#f0a93a']];
const LOGO_GRAD_PLATINUM = [['#34d399','#059669'],['#6ee7b7','#10b981']];
function applySubscriptionLogoColor(){
  const sub = currentUser && currentUser.subscription;
  const active = sub && sub.tier && sub.expiresAt && sub.expiresAt > Date.now() && sub.logoColorOn !== false;
  const pair = !active ? LOGO_GRAD_DEFAULT : (sub.tier === 'platinum' ? LOGO_GRAD_PLATINUM : LOGO_GRAD_GOLD);
  const g1 = document.querySelectorAll('#mbGrad1 stop');
  const g2 = document.querySelectorAll('#mbGrad2 stop');
  if (g1[0]) g1[0].setAttribute('stop-color', pair[0][0]);
  if (g1[1]) g1[1].setAttribute('stop-color', pair[0][1]);
  if (g2[0]) g2[0].setAttribute('stop-color', pair[1][0]);
  if (g2[1]) g2[1].setAttribute('stop-color', pair[1][1]);
}"""
    s = s.replace(old_settings_open_tail, new_settings_open_tail, 1)

    # 5) updateUserUI 안에서 로고색상/마이페이지 라벨을 항상 최신 상태로 반영
    old_update_ui = """function updateUserUI(){
  if (!currentUser) return;
  document.getElementById('userPoints').textContent = currentUser.points;
  document.getElementById('mypagePointCount').textContent = currentUser.points;
  const adminBtn = document.getElementById('headerAdminModeBtn');
  if (adminBtn) adminBtn.classList.toggle('hidden', !currentUser.isAdmin);
}"""
    assert s.count(old_update_ui) == 1, "updateUserUI 함수를 찾지 못함"
    new_update_ui = """function updateUserUI(){
  if (!currentUser) return;
  document.getElementById('userPoints').textContent = currentUser.points;
  document.getElementById('mypagePointCount').textContent = currentUser.points;
  const adminBtn = document.getElementById('headerAdminModeBtn');
  if (adminBtn) adminBtn.classList.toggle('hidden', !currentUser.isAdmin);
  applySubscriptionLogoColor();
  refreshMypageSubLabel();
}"""
    s = s.replace(old_update_ui, new_update_ui, 1)

    # 6) points:updated 리스너 - subscription 필드도 함께 반영
    old_points_updated = """// 서버(RevenueCat 웹훅)가 인앱결제 완료를 확인하고 쌀을 지급하면, 접속 중인 클라이언트에 실시간으로 알려줌
socket.on('points:updated', ({points})=>{
  if (!currentUser) return;
  currentUser.points = points; updateUserUI(); saveSession();
  showMiniAlert(`쌀 충전이 완료되었습니다! (현재 쌀: ${points}개)`, [{label:'확인', primary:true}]);
});"""
    assert s.count(old_points_updated) == 1, "points:updated 리스너를 찾지 못함"
    new_points_updated = """// 서버(RevenueCat 웹훅)가 인앱결제 완료를 확인하고 쌀을 지급하면, 접속 중인 클라이언트에 실시간으로 알려줌
// 0-20: 구독 상품 결제였다면 subscription 필드도 함께 실려오므로 같이 반영함
socket.on('points:updated', ({points, subscription})=>{
  if (!currentUser) return;
  currentUser.points = points;
  if (typeof subscription !== 'undefined') currentUser.subscription = subscription;
  updateUserUI(); saveSession();
  if (subscription && subscription.tier && subscription.expiresAt > Date.now()){
    showMiniAlert(`${subscription.tier==='platinum'?'플래티넘':'골드'} 구독이 적용되었습니다! (쌀 ${points}개)`, [{label:'확인', primary:true}]);
  } else {
    showMiniAlert(`쌀 충전이 완료되었습니다! (현재 쌀: ${points}개)`, [{label:'확인', primary:true}]);
  }
});"""
    s = s.replace(old_points_updated, new_points_updated, 1)

    # 7) tab-mypage 전환시 구독 라벨도 갱신
    old_switch_tab_mypage = "if (tab==='tab-mypage') { loadProfileToForm(); refreshMyPageVisitorCount(); }"
    assert s.count(old_switch_tab_mypage) == 1, "tab-mypage 전환 코드를 찾지 못함"
    new_switch_tab_mypage = "if (tab==='tab-mypage') { loadProfileToForm(); refreshMyPageVisitorCount(); refreshMypageSubLabel(); }"
    s = s.replace(old_switch_tab_mypage, new_switch_tab_mypage, 1)

    # 8) 나만의 페이지 별명 옆 등급 뱃지 표시
    old_profile_name = '<div class="profile-name">${escapeHtml(user.nickname)}</div>'
    assert s.count(old_profile_name) == 1, "profile-name 렌더 코드를 찾지 못함"
    new_profile_name = '<div class="profile-name">${escapeHtml(user.nickname)}${subscriptionBadgeHtml(user)}</div>'
    s = s.replace(old_profile_name, new_profile_name, 1)

    # 9) 프로필 사진뷰어 좋아요 버튼 - 하트(토글)와 개수(누른사람 목록 보기)를 분리, 본인 사진도 개수/목록은 볼 수 있게 변경
    old_photo_like_btn = '${(!isMe && hasPhotos)?`<button class="photo-like-btn" onclick="toggleProfilePhotoLike(\'${user.id}\', ${profilePhotoIndex})"><i class="fa-${iLikedThisPhoto?\'solid\':\'regular\'} fa-heart" style="color:${iLikedThisPhoto?\'#ff4d6d\':\'#fff\'};"></i> <span>${photoLikeCount}</span></button>`:\'\'}'
    assert s.count(old_photo_like_btn) == 1, "photo-like-btn 렌더 코드를 찾지 못함"
    new_photo_like_btn = '${hasPhotos?`<div class="photo-like-btn" style="display:flex;align-items:center;gap:7px;">${isMe?\'\':`<span onclick="toggleProfilePhotoLike(\'${user.id}\', ${profilePhotoIndex})" style="cursor:pointer;"><i class="fa-${iLikedThisPhoto?\'solid\':\'regular\'} fa-heart" style="color:${iLikedThisPhoto?\'#ff4d6d\':\'#fff\'};"></i></span>`}<span onclick="event.stopPropagation();openPhotoLikersScreen(\'${user.id}\', ${profilePhotoIndex})" style="cursor:pointer;">${photoLikeCount}</span></div>`:\'\'}'
    s = s.replace(old_photo_like_btn, new_photo_like_btn, 1)

    # 10) 사진뷰어 "좋아요 누른 사람" 화면 오픈 함수 추가 (toggleProfilePhotoLike 함수 뒤)
    old_toggle_like_fn = """function toggleProfilePhotoLike(targetUserId, photoIndex){
  socket.emit('photo:like', {targetUserId, photoIndex}, (res)=>{
    if (!res || !res.success || !currentProfileUserCache) return;
    if (!currentProfileUserCache.photoLikes) currentProfileUserCache.photoLikes = {};
    if (!currentProfileUserCache.photoLikes[photoIndex]) currentProfileUserCache.photoLikes[photoIndex] = {};
    if (res.liked) currentProfileUserCache.photoLikes[photoIndex][currentUser.id] = true;
    else delete currentProfileUserCache.photoLikes[photoIndex][currentUser.id];
    renderProfileDetail(currentProfileUserCache);
  });
}"""
    assert s.count(old_toggle_like_fn) == 1, "toggleProfilePhotoLike 함수를 찾지 못함"
    new_toggle_like_fn = old_toggle_like_fn + """
// 0-20: 사진에 좋아요 누른 사람 "목록" 열람 - 골드 이상 구독 중이어야 실제 목록이 보임(아니면 잠금 티저 표시)
function openPhotoLikersScreen(targetUserId, photoIndex){
  socket.emit('photo:get_likers', {targetUserId, photoIndex}, (res)=>{
    const body = document.getElementById('photoLikersBody');
    if (!res || !res.success) return;
    if (res.locked){ body.innerHTML = renderLockTeaser(res.count, '이 사진에 좋아요 누른 사람을 확인할 수 있어요.'); openFullScreen('photoLikersScreen'); return; }
    const likers = res.likers || [];
    body.innerHTML = likers.length ? likers.map(u=>`
      <div class="user-card" style="cursor:pointer;" onclick="closeFullScreen('photoLikersScreen');openProfileDetailScreen('${u.id}')">
        ${avatarHtmlFor(u,'avatar')}
        <div style="flex:1;min-width:0;">
          <span class="user-nickname">${escapeHtml(u.nickname)}${subscriptionBadgeHtml(u)}</span>
          <div style="display:flex;gap:6px;margin-top:4px;"><span class="tag">${u.region}</span><span class="tag">${u.gender==='female'?'여성':'남성'}</span><span class="tag">${u.age}세</span></div>
        </div>
      </div>`).join('') : `<div style="text-align:center;padding:40px;color:var(--text-muted);">아직 좋아요를 누른 사람이 없습니다.</div>`;
    openFullScreen('photoLikersScreen');
  });
}"""
    s = s.replace(old_toggle_like_fn, new_toggle_like_fn, 1)

    # 11) 방문자 화면 - 오늘 방문자 아래에 "전체 기간 방문자" 섹션(구독 게이트) 추가
    old_visitors_screen_fn = """function openProfileVisitorsScreen(){
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
}"""
    assert s.count(old_visitors_screen_fn) == 1, "openProfileVisitorsScreen 함수를 찾지 못함"
    new_visitors_screen_fn = """function openProfileVisitorsScreen(){
  socket.emit('profile:get_today_visitors', {}, (res)=>{
    const body = document.getElementById('profileVisitorsBody');
    const visitors = (res && res.visitors) || [];
    document.getElementById('myPageVisitorCount').textContent = `${(res && res.count) || 0}명`;
    body.innerHTML = `<div style="font-size:13px;font-weight:700;margin:2px 0 6px;">오늘 방문자</div>` + (visitors.length ? visitors.map(u=>`
      <div class="user-card" style="cursor:pointer;" onclick="openProfileDetailScreen('${u.id}')">
        ${avatarHtmlFor(u,'avatar')}
        <div style="flex:1;min-width:0;">
          <span class="user-nickname">${escapeHtml(u.nickname)}${subscriptionBadgeHtml(u)}</span>
          <div style="display:flex;gap:6px;margin-top:4px;"><span class="tag">${u.region}</span><span class="tag">${u.gender==='female'?'여성':'남성'}</span><span class="tag">${u.age}세</span></div>
        </div>
      </div>`).join('') : `<div style="text-align:center;padding:24px;color:var(--text-muted);">오늘 방문한 사람이 아직 없습니다.</div>`)
      + `<div style="margin-top:20px;"><div style="font-size:13px;font-weight:700;margin:2px 0 6px;">전체 기간 방문자</div><div id="profileAllVisitorsBody"></div></div>`;
    openFullScreen('profileVisitorsScreen');
    loadAllVisitorsSection();
  });
}
// 0-20: 방문자 "전체 기간" 섹션 - 골드 이상 구독 중이면 실제 목록, 아니면 잠금 티저(9+ 인원수+자물쇠) 표시
function loadAllVisitorsSection(){
  socket.emit('profile:get_all_visitors', {}, (res)=>{
    const wrap = document.getElementById('profileAllVisitorsBody');
    if (!wrap || !res || !res.success) return;
    if (res.locked){ wrap.innerHTML = renderLockTeaser(res.count, '구독 시작 이전 기록까지 포함한 전체 방문자를 확인할 수 있어요.'); return; }
    const visitors = res.visitors || [];
    wrap.innerHTML = visitors.length ? visitors.map(u=>`
      <div class="user-card" style="cursor:pointer;" onclick="openProfileDetailScreen('${u.id}')">
        ${avatarHtmlFor(u,'avatar')}
        <div style="flex:1;min-width:0;">
          <span class="user-nickname">${escapeHtml(u.nickname)}${subscriptionBadgeHtml(u)}</span>
          <div style="display:flex;gap:6px;margin-top:4px;"><span class="tag">${u.region}</span><span class="tag">${u.gender==='female'?'여성':'남성'}</span><span class="tag">${u.age}세</span></div>
        </div>
      </div>`).join('') : `<div style="text-align:center;padding:24px;color:var(--text-muted);">아직 방문한 사람이 없습니다.</div>`;
  });
}"""
    s = s.replace(old_visitors_screen_fn, new_visitors_screen_fn, 1)

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(s)
    print("public/index.html 패치 완료")


if __name__ == "__main__":
    patch_server()
    patch_index()
    print("0-20 패치(1차) 전체 완료")