# -*- coding: utf-8 -*-
# 0-54 패치: 이 파일은 반드시 저장소 루트(C:\malbeot)에서 열고, malbeot-app 폴더 안에서 실행하세요.
#   python ..\patch_0_54.py  (malbeot-app 안에서 실행하는 경우)
# 실행 전 pwd/ls로 malbeot-app/server.js, malbeot-app/public/index.html이 보이는지 꼭 확인!
import re, sys, os

BASE = os.path.dirname(os.path.abspath(__file__))
# 이 스크립트가 malbeot-app 안에 있든, 저장소 루트에 있든 둘 다 동작하도록 경로 자동 탐색
if os.path.exists(os.path.join(BASE, 'server.js')):
    APP_DIR = BASE
elif os.path.exists(os.path.join(BASE, 'malbeot-app', 'server.js')):
    APP_DIR = os.path.join(BASE, 'malbeot-app')
else:
    print("❌ server.js를 찾을 수 없습니다. malbeot-app 폴더 안에서 실행했는지 확인하세요.")
    sys.exit(1)

SERVER_PATH = os.path.join(APP_DIR, 'server.js')
INDEX_PATH = os.path.join(APP_DIR, 'public', 'index.html')

def apply(path, replacements, label):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    for old, new in replacements:
        if old not in content:
            print(f"❌ [{label}] 찾는 코드가 없습니다(이미 적용됐거나 코드가 달라졌을 수 있음). 아래 코드 일부를 확인하세요:")
            print(old[:200])
            sys.exit(1)
        count = content.count(old)
        if count != 1:
            print(f"❌ [{label}] 코드가 {count}번 발견되어 중복됩니다. 수동 확인이 필요합니다.")
            sys.exit(1)
        content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ [{label}] 적용 완료")

# =====================================================================
# 1) server.js - 구독 1년권 매월 지급 (RevenueCat 웹훅)
# =====================================================================
server_replacements = []

old_webhook = """    user.points = (user.points || 0) + grantPoints;

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
    // 0-33: 유저가 나중에 "결제 내역" 화면에서 조회할 수 있도록 기록해둠(관리자가 테스트로 지급한 구독은 여기 안 남음 - 실제 결제 건만)
    await db.ref(`purchaseHistory/${userId}`).push({
      productId,
      points: grantPoints,
      subscriptionTier: subProduct ? subProduct.tier : null,
      subscriptionDays: subProduct ? subProduct.days : null,
      at: Date.now()
    });

    console.log(`[RevenueCat 웹훅] ${userId} 유저에게 쌀 ${grantPoints}개 지급 완료${subProduct ? ` + 구독(${subProduct.tier}, ${subProduct.days}일)` : ''} (상품: ${productId})`);"""

new_webhook = """    // 0-54: 1년권(365일 이상)은 쌀을 한번에 다 주지 않고 매달 1일 자동으로 나눠 지급함(재구매 유도).
    // 14일권 등 그 외 상품은 기존처럼 즉시 전액 지급.
    const isMonthlyPayout = subProduct && subProduct.days >= 365;
    if (!isMonthlyPayout) {
      user.points = (user.points || 0) + grantPoints;
    }

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
      // 0-54: 1년권 매월 지급 - lastGrantedMonth를 null로 둬서 grantMonthlySubscriptionBonusIfNeeded()가
      // 다음 체크(최대 1시간 이내)에 이번 달 몫을 바로 지급하게 함. 이후 매월 1일 자동 지급.
      if (isMonthlyPayout) {
        user.subscription.monthlyBonus = { amount: subProduct.points, lastGrantedMonth: null };
      } else if (user.subscription) {
        delete user.subscription.monthlyBonus;
      }
    }

    await saveUser(user);
    if (eventId) await db.ref(`processedPurchaseEvents/${eventId}`).set({ userId, productId, grantPoints, at: Date.now() });
    // 0-33: 유저가 나중에 "결제 내역" 화면에서 조회할 수 있도록 기록해둠(관리자가 테스트로 지급한 구독은 여기 안 남음 - 실제 결제 건만)
    // 0-54: 1년권은 이 시점엔 아직 포인트를 지급 안 했으므로(매달 나눠 지급) points를 0으로 기록함.
    // 실제 매월 지급분은 grantMonthlySubscriptionBonusIfNeeded()에서 별도로 purchaseHistory에 기록함.
    await db.ref(`purchaseHistory/${userId}`).push({
      productId,
      points: isMonthlyPayout ? 0 : grantPoints,
      subscriptionTier: subProduct ? subProduct.tier : null,
      subscriptionDays: subProduct ? subProduct.days : null,
      at: Date.now()
    });

    console.log(`[RevenueCat 웹훅] ${userId} 유저에게 ${isMonthlyPayout ? `구독(${subProduct.tier}, ${subProduct.days}일, 매달 ${grantPoints}개 지급 시작)` : `쌀 ${grantPoints}개 지급 완료${subProduct ? ` + 구독(${subProduct.tier}, ${subProduct.days}일)` : ''}`} (상품: ${productId})`);"""

server_replacements.append((old_webhook, new_webhook))

old_admin_grant = """      target.subscription = {
        tier,
        expiresAt: Date.now() + days * 24 * 60 * 60 * 1000,
        logoColorOn: (target.subscription && typeof target.subscription.logoColorOn === 'boolean') ? target.subscription.logoColorOn : true,
        badgeOn: (target.subscription && typeof target.subscription.badgeOn === 'boolean') ? target.subscription.badgeOn : true
      };
      // 실구매(RevenueCat 웹훅)와 동일하게 등급별 보너스 쌀도 즉시 지급 (골드 1000 / 플래티넘 3000)
      const bonusPoints = tier === 'platinum' ? 3000 : 1000;
      target.points = (target.points || 0) + bonusPoints;
      await saveUser(target);"""

new_admin_grant = """      target.subscription = {
        tier,
        expiresAt: Date.now() + days * 24 * 60 * 60 * 1000,
        logoColorOn: (target.subscription && typeof target.subscription.logoColorOn === 'boolean') ? target.subscription.logoColorOn : true,
        badgeOn: (target.subscription && typeof target.subscription.badgeOn === 'boolean') ? target.subscription.badgeOn : true
      };
      // 0-54: 실구매와 동일한 흐름 - 365일(1년권) 관리자 지급은 매달 1일 자동 지급(monthlyBonus)으로 처리,
      // 그 외(14일권 등) 관리자 지급은 기존처럼 즉시 전액 지급
      const bonusPoints = tier === 'platinum' ? 3000 : 1000;
      if (days >= 365) {
        target.subscription.monthlyBonus = { amount: bonusPoints, lastGrantedMonth: null };
      } else {
        target.points = (target.points || 0) + bonusPoints;
      }
      await saveUser(target);"""

server_replacements.append((old_admin_grant, new_admin_grant))

old_kst = """function kstDateStr(d) {
  return new Date(d.getTime() + 9 * 60 * 60 * 1000).toISOString().slice(0, 10);
}"""

new_kst = """function kstDateStr(d) {
  return new Date(d.getTime() + 9 * 60 * 60 * 1000).toISOString().slice(0, 10);
}
function kstMonthStr(d) { return kstDateStr(d).slice(0, 7); }

/* =====================================================================
   0-54: 구독 1년권 매월 자동 지급
   - 1년권(365일 이상) 구매/지급 시 쌀을 한번에 몰아주지 않고, 매달(KST 기준 달이 바뀔 때마다)
     구독이 유효한 동안 자동으로 나눠 지급함. 구매 직후에는 lastGrantedMonth가 null이라
     이 함수가 처음 도는 시점(최대 1시간 이내)에 이번 달 몫이 바로 지급됨.
   - 무료 호스팅 환경 특성상 정확한 cron 대신 다른 일일 작업들과 동일하게 1시간마다 체크.
===================================================================== */
async function grantMonthlySubscriptionBonusIfNeeded() {
  try {
    const now = Date.now();
    const thisMonth = kstMonthStr(new Date());
    const allUsers = await getAllUsers();
    for (const user of Object.values(allUsers)) {
      const sub = user.subscription;
      const mb = sub && sub.monthlyBonus;
      if (!mb || !mb.amount) continue;
      if (!sub.expiresAt || sub.expiresAt <= now) continue; // 구독 만료되면 더 이상 지급 안 함
      if (mb.lastGrantedMonth === thisMonth) continue; // 이번 달 몫은 이미 지급함
      user.points = (user.points || 0) + mb.amount;
      user.subscription.monthlyBonus.lastGrantedMonth = thisMonth;
      await saveUser(user);
      await db.ref(`purchaseHistory/${user.id}`).push({
        productId: `monthly_bonus_${sub.tier}`,
        points: mb.amount,
        subscriptionTier: sub.tier,
        subscriptionDays: null,
        at: now
      });
      const tierLabel = sub.tier === 'platinum' ? '플래티넘' : '골드';
      const msg = `${tierLabel} 구독 매월 지급 쌀 ${mb.amount.toLocaleString()}개가 지급되었습니다.`;
      const sId = userToSocket[user.id];
      if (sId) io.to(sId).emit('points:updated', { points: user.points, subscription: user.subscription });
      else sendWebPush(user.id, { title: '구독 매월 쌀 지급', body: msg, type: 'subscription_monthly_bonus' });
      console.log(`[구독 매월지급] ${user.id} 유저에게 ${tierLabel} 쌀 ${mb.amount}개 지급 (${thisMonth})`);
    }
  } catch (e) { console.error('[구독 매월지급 오류]', e); }
}
setInterval(grantMonthlySubscriptionBonusIfNeeded, 60 * 60 * 1000);"""

server_replacements.append((old_kst, new_kst))

apply(SERVER_PATH, server_replacements, 'server.js (0-54 구독 매월지급)')

# =====================================================================
# 2) index.html - 쌀충전소+구독 통합 페이지 + 할인 후킹 문구
# =====================================================================
index_replacements = []

# 2-1) 화면 HTML 통합: riceChargeScreen 하나에 구독 섹션까지 포함, subscriptionScreen 별도 div는 제거
old_screens = """  <div id="riceChargeScreen" class="full-screen-overlay">
    <div class="fs-header"><button class="back-btn" onclick="closeRiceChargeScreen()"><i class="fa-solid fa-arrow-left"></i></button><div class="fs-title">쌀 충전소</div></div>
    <div class="fs-body" style="padding:20px 16px 40px;">
      <div style="text-align:center;margin-bottom:18px;">
        <div style="font-size:13px;color:var(--text-muted);">보유 쌀</div>
        <div style="font-size:26px;font-weight:800;color:var(--primary);"><i class="fa-solid fa-bowl-rice" style="color:var(--warning);"></i> <span id="rechargeScreenBalance">0</span>개</div>
      </div>
      <div id="ricePackageGrid" style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;"></div>
      <p style="font-size:11px;color:var(--text-muted);text-align:center;margin-top:18px;line-height:1.6;">
        결제는 Google Play / App Store 인앱결제로 안전하게 처리됩니다.<br>
        쌀은 충전 즉시 사용 가능하며, 일부라도 사용 시 환불이 제한됩니다.<br>부적절한 언행으로 이용정지·회원탈퇴 처리될 경우 환불이 불가합니다.
      </p>
    </div>
  </div>

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
  </div>"""

new_screens = """  <div id="riceChargeScreen" class="full-screen-overlay">
    <div class="fs-header"><button class="back-btn" onclick="closeRiceChargeScreen()"><i class="fa-solid fa-arrow-left"></i></button><div class="fs-title">쌀 충전 · 구독</div></div>
    <div class="fs-body" style="padding:20px 16px 40px;">
      <div style="text-align:center;margin-bottom:18px;">
        <div style="font-size:13px;color:var(--text-muted);">보유 쌀</div>
        <div style="font-size:26px;font-weight:800;color:var(--primary);"><i class="fa-solid fa-bowl-rice" style="color:var(--warning);"></i> <span id="rechargeScreenBalance">0</span>개</div>
      </div>

      <div style="font-weight:800;font-size:15px;margin-bottom:2px;">🎁 회원님을 위한 추천 혜택</div>
      <div id="subscriptionCurrentStatus" style="font-size:12px;color:var(--text-muted);line-height:1.6;margin-bottom:10px;"></div>
      <div id="subscriptionPackageGrid" style="display:flex;flex-direction:column;gap:10px;margin-bottom:24px;"></div>

      <div style="font-weight:800;font-size:15px;margin-bottom:8px;"><i class="fa-solid fa-bowl-rice" style="color:var(--warning);"></i> 쌀 충전소</div>
      <div id="ricePackageGrid" style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;"></div>

      <p style="font-size:11px;color:var(--text-muted);text-align:center;margin-top:18px;line-height:1.6;">
        결제는 Google Play / App Store 인앱결제로 안전하게 처리됩니다.<br>
        쌀은 충전 즉시 사용 가능하며, 일부라도 사용 시 환불이 제한됩니다.<br>부적절한 언행으로 이용정지·회원탈퇴 처리될 경우 환불이 불가합니다.<br>
        구독 상품은 자동 결제(정기결제)가 아닌 1회성 결제이며, 만료되면 자동으로 연장되지 않습니다. 남은 기간이 있는 상태에서 다시 구매하면 이어서 연장됩니다.
      </p>
    </div>
  </div>"""

index_replacements.append((old_screens, new_screens))

# 2-2) "확인" 버튼에서 subscriptionScreen을 닫던 부분을 riceChargeScreen 기준으로 수정
old_lockupsell_btn = """<button class="btn btn-primary" style="flex:1;" onclick="closeModal('lockUpsellModal');closeFullScreen('photoLikersScreen');closeFullScreen('profileVisitorsScreen');openSubscriptionScreen()">확인</button>"""
new_lockupsell_btn = """<button class="btn btn-primary" style="flex:1;" onclick="closeModal('lockUpsellModal');closeFullScreen('photoLikersScreen');closeFullScreen('profileVisitorsScreen');openRiceChargeScreen()">확인</button>"""
index_replacements.append((old_lockupsell_btn, new_lockupsell_btn))

# 2-3) 구독 관련 진입점 함수를 통합 화면(riceChargeScreen) 기준으로 alias 처리 + 할인 후킹 문구 추가
old_sub_js = """function openSubscriptionScreen(){
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
          <div style="font-weight:800;font-size:14px;"><i class="fa-solid fa-gem" style="color:${isPlat?'#059669':'#c9891a'};margin-right:4px;"></i>${isPlat?'플래티넘':'골드'} ${periodLabel}</div>
          <div style="font-size:11px;color:var(--text-muted);margin-top:2px;">쌀 ${(isPlat?3000:1000).toLocaleString()}개 지급 · 등급뱃지 · 로고색상 · 방문자/좋아요 전체열람</div>
        </div>
        <div style="text-align:right;">
          <div style="font-weight:800;font-size:15px;margin-bottom:6px;">${p.price.toLocaleString()}원</div>
          <button class="btn ${isPlat?'':'btn-secondary'} btn-sm" style="${isPlat?'background:#059669;border-color:#059669;color:#fff;':''}" onclick="handleBuySubscriptionPackage('${p.id}')">구독</button>
        </div>
      </div>`;
  }).join('');
}"""

new_sub_js = """// 0-54: 쌀충전소+구독을 한 화면(riceChargeScreen)으로 통합함에 따라 openSubscriptionScreen()은
// 통합 화면을 여는 openRiceChargeScreen()의 별칭으로 유지(다른 화면에서 이 이름으로 호출하는 곳이 많아 삭제하지 않음)
function openSubscriptionScreen(){
  openRiceChargeScreen();
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
    const bonusAmt = isPlat ? 3000 : 1000;
    // 0-54: 1년권은 한번에 지급이 아니라 매달 1일 지급되는 방식이라 안내 문구를 구분함
    const bonusText = p.days >= 365 ? `매달 쌀 ${bonusAmt.toLocaleString()}개(매월 1일) 지급` : `쌀 ${bonusAmt.toLocaleString()}개 즉시 지급`;
    // 0-54: 1년권은 같은 등급 14일권의 26회분(365/14) 가격을 "정가"로 놓고 실제 할인율을 계산해서 크게 강조함
    let discountHtml = '';
    if (p.days >= 365) {
      const dailyEquivalent = SUBSCRIPTION_PACKAGES.find(x => x.tier === p.tier && x.days < 365);
      if (dailyEquivalent) {
        const fullPrice = Math.round(dailyEquivalent.price * 365 / dailyEquivalent.days);
        const discountPct = Math.round((1 - p.price / fullPrice) * 100);
        discountHtml = `<div style="font-size:10px;color:#e03131;font-weight:800;margin-bottom:2px;">정가 ${fullPrice.toLocaleString()}원 → <span style="font-size:12px;">${discountPct}% 할인!</span></div>`;
      }
    }
    return `
      <div style="display:flex;justify-content:space-between;align-items:center;border:1px solid ${isPlat?'#059669':'#c9891a'};border-radius:14px;padding:14px;">
        <div>
          <div style="font-weight:800;font-size:14px;"><i class="fa-solid fa-gem" style="color:${isPlat?'#059669':'#c9891a'};margin-right:4px;"></i>${isPlat?'플래티넘':'골드'} ${periodLabel}</div>
          <div style="font-size:11px;color:var(--text-muted);margin-top:2px;">${bonusText} · 등급뱃지 · 로고색상 · 방문자/좋아요 전체열람</div>
        </div>
        <div style="text-align:right;">
          ${discountHtml}
          <div style="font-weight:800;font-size:15px;margin-bottom:6px;">${p.price.toLocaleString()}원</div>
          <button class="btn ${isPlat?'':'btn-secondary'} btn-sm" style="${isPlat?'background:#059669;border-color:#059669;color:#fff;':''}" onclick="handleBuySubscriptionPackage('${p.id}')">구독</button>
        </div>
      </div>`;
  }).join('');
}"""

index_replacements.append((old_sub_js, new_sub_js))

# 2-4) openRiceChargeScreen()이 통합 화면이므로 구독 섹션도 같이 렌더링하도록 수정
old_open_rice = """function openRiceChargeScreen(){
  document.getElementById('rechargeScreenBalance').textContent = (currentUser ? currentUser.points : 0).toLocaleString();
  renderRicePackages();
  openFullScreen('riceChargeScreen');
}"""
new_open_rice = """function openRiceChargeScreen(){
  document.getElementById('rechargeScreenBalance').textContent = (currentUser ? currentUser.points : 0).toLocaleString();
  renderRicePackages();
  renderSubscriptionPackages(); // 0-54: 쌀충전소+구독 통합 화면이라 함께 렌더링
  openFullScreen('riceChargeScreen');
}"""
index_replacements.append((old_open_rice, new_open_rice))

apply(INDEX_PATH, index_replacements, 'index.html (0-54 쌀충전소+구독 통합)')

# =====================================================================
# 3) index.html - 채팅 목록 좌측 아이콘 재구성
#    - 검색창 자리를 광고란(홈처럼)으로 바꾸고, 돋보기 아이콘을 누르면 검색창이 나타나게 함
#    - 기존 + 버튼(오픈채팅 생성) 대신, 채팅아이콘+우측에 + 겹친 "오픈채팅 만들기" 전용 칸 신설
#    - 채팅방 검색은 대화내용(메시지 텍스트)까지 확장하고 일치 구간을 파란색으로 강조
# =====================================================================
chat_replacements = []

old_chat_header = """    <section id="tab-chat" class="tab-content">
      <div style="display:flex;gap:8px;padding:10px 14px;align-items:center;">
        <div style="flex:1;position:relative;">
          <i class="fa-solid fa-magnifying-glass" style="position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--text-muted);font-size:13px;"></i>
          <input type="text" id="groupSearchInput" placeholder="채팅방 검색" oninput="onGroupSearchInput(this.value)" style="width:100%;box-sizing:border-box;padding:9px 12px 9px 32px;border:1px solid var(--border-color);border-radius:20px;font-size:13px;background:var(--bg-card);color:inherit;">
        </div>
        <button type="button" onclick="openGroupCreateModal()" style="flex-shrink:0;width:36px;height:36px;border-radius:50%;border:none;background:var(--primary);color:#fff;font-size:15px;"><i class="fa-solid fa-plus"></i></button>
      </div>
      <div id="groupSearchResultList"></div>
      <div style="padding:0 14px 6px;"><a href="javascript:void(0)" onclick="promptJoinByCode()" style="font-size:12px;color:var(--text-muted);">초대코드로 입장하기</a></div>
      <div id="chatRoomList"></div>
    </section>"""

new_chat_header = """    <section id="tab-chat" class="tab-content">
      <div id="chatListIconRow" style="display:flex;gap:8px;padding:10px 14px;align-items:center;">
        <button type="button" onclick="toggleChatListSearch()" style="flex-shrink:0;width:36px;height:36px;border-radius:50%;border:1px solid var(--border-color);background:var(--bg-card);color:inherit;font-size:14px;"><i class="fa-solid fa-magnifying-glass"></i></button>
        <div id="openChatCreateEntry" onclick="openGroupCreateModal()" style="flex:1;position:relative;display:flex;align-items:center;gap:8px;border:1px solid var(--border-color);border-radius:20px;padding:8px 14px;background:var(--bg-card);cursor:pointer;">
          <span style="position:relative;display:inline-flex;">
            <i class="fa-solid fa-comment" style="font-size:15px;color:var(--primary);"></i>
            <span style="position:absolute;right:-6px;bottom:-5px;width:13px;height:13px;border-radius:50%;background:var(--primary);color:#fff;font-size:9px;display:flex;align-items:center;justify-content:center;"><i class="fa-solid fa-plus" style="font-size:8px;"></i></span>
          </span>
          <span style="font-size:13px;font-weight:600;">오픈채팅 만들기</span>
        </div>
        <button type="button" onclick="openSettingsScreen()" style="flex-shrink:0;width:36px;height:36px;border-radius:50%;border:1px solid var(--border-color);background:var(--bg-card);color:inherit;font-size:14px;"><i class="fa-solid fa-gear"></i></button>
      </div>
      <div id="chatListSearchRow" class="hidden" style="padding:0 14px 8px;">
        <div style="position:relative;">
          <i class="fa-solid fa-magnifying-glass" style="position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--text-muted);font-size:13px;"></i>
          <input type="text" id="groupSearchInput" placeholder="닉네임, 채팅방 이름, 대화 내용 검색" oninput="onGroupSearchInput(this.value)" style="width:100%;box-sizing:border-box;padding:9px 12px 9px 32px;border:1px solid var(--border-color);border-radius:20px;font-size:13px;background:var(--bg-card);color:inherit;">
        </div>
      </div>
      <div id="chatAdBannerRow" style="padding:0 14px 8px;">
        <div style="height:44px;border:1px dashed var(--border-color);border-radius:10px;display:flex;align-items:center;justify-content:center;color:var(--text-muted);font-size:12px;">광고 영역</div>
      </div>
      <div id="groupSearchResultList"></div>
      <div style="padding:0 14px 6px;"><a href="javascript:void(0)" onclick="promptJoinByCode()" style="font-size:12px;color:var(--text-muted);">초대코드로 입장하기</a></div>
      <div id="chatRoomList"></div>
    </section>"""

chat_replacements.append((old_chat_header, new_chat_header))

apply(INDEX_PATH, chat_replacements, 'index.html (0-54 채팅탭 아이콘 재구성 - 화면구조)')

# 3-2) 검색창 토글 함수 + 검색시 광고란/오픈채팅칸 숨김, 검색 종료시 복귀, 대화내용 검색+강조
old_search_fn_start = """function onGroupSearchInput(value){
  clearTimeout(groupSearchDebounce);
  const q = value.trim();
  const resultBox = document.getElementById('groupSearchResultList');
  const listBox = document.getElementById('chatRoomList');
  if (!q){ resultBox.innerHTML=''; listBox.style.display=''; return; }
  groupSearchDebounce = setTimeout(()=>{
    listBox.style.display='none';
    const qLower = q.toLowerCase();
    const joinedGroupIds = new Set((currentGroupChatRooms||[]).map(r=>r.roomId));
    const localDmMatches = (currentChatRooms||[]).filter(r=> ((r.targetUser&&r.targetUser.nickname)||'').toLowerCase().includes(qLower));
    const localGroupMatches = (currentGroupChatRooms||[]).filter(r=> (((r.meta)&&r.meta.title)||'').toLowerCase().includes(qLower));"""

new_search_fn_start = """// 0-54: 돋보기 아이콘을 눌러야 검색창이 나타나게 함(평소엔 광고란+오픈채팅 만들기 칸이 그 자리를 대신함)
function toggleChatListSearch(){
  const row = document.getElementById('chatListSearchRow');
  const willShow = row.classList.contains('hidden');
  row.classList.toggle('hidden');
  if (willShow) {
    document.getElementById('groupSearchInput').focus();
  } else {
    document.getElementById('groupSearchInput').value = '';
    onGroupSearchInput('');
  }
}
// 0-54: 검색어가 하나라도 있으면 광고란/오픈채팅 만들기 칸을 잠깐 숨기고 결과에 집중시킴(검색 지우면 복귀)
function setChatListBrowseUiVisible(visible){
  const ad = document.getElementById('chatAdBannerRow');
  const create = document.getElementById('openChatCreateEntry');
  if (ad) ad.classList.toggle('hidden', !visible);
  if (create) create.style.display = visible ? '' : 'none';
}
// 0-54: 검색어와 대상 텍스트를 비교해 일치하는 구간을 파란색으로 강조 표시함(닉네임/방이름/대화내용 공통 사용)
function highlightMatch(text, query){
  const safe = escapeHtml(text || '');
  if (!query) return safe;
  const idx = safe.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return safe;
  return safe.slice(0, idx) + `<span style="color:var(--primary);font-weight:700;">${safe.slice(idx, idx+query.length)}</span>` + safe.slice(idx+query.length);
}
function onGroupSearchInput(value){
  clearTimeout(groupSearchDebounce);
  const q = value.trim();
  const resultBox = document.getElementById('groupSearchResultList');
  const listBox = document.getElementById('chatRoomList');
  if (!q){ resultBox.innerHTML=''; listBox.style.display=''; setChatListBrowseUiVisible(true); return; }
  setChatListBrowseUiVisible(false);
  groupSearchDebounce = setTimeout(()=>{
    listBox.style.display='none';
    const qLower = q.toLowerCase();
    const joinedGroupIds = new Set((currentGroupChatRooms||[]).map(r=>r.roomId));
    // 0-54: 닉네임/방이름뿐 아니라 그동안 주고받은 대화 내용(전체 메시지 텍스트)에 검색어가 포함된 방도 매칭
    const roomContainsQuery = (r)=> (r.messages||[]).some(m => m.type!=='image' && (m.text||'').toLowerCase().includes(qLower));
    const localDmMatches = (currentChatRooms||[]).filter(r=>
      ((r.targetUser&&r.targetUser.nickname)||'').toLowerCase().includes(qLower) ||
      roomContainsQuery(r)
    );
    const localGroupMatches = (currentGroupChatRooms||[]).filter(r=>
      (((r.meta)&&r.meta.title)||'').toLowerCase().includes(qLower) ||
      roomContainsQuery(r)
    );"""

chat_replacements2 = [(old_search_fn_start, new_search_fn_start)]
apply(INDEX_PATH, chat_replacements2, 'index.html (0-54 채팅탭 검색 - 대화내용 확장/강조)')

print("\n🎉 0-54 패치 전체 적용 완료! 이제 아래 순서로 진행하세요:")
print("1) node -c server.js  (문법 확인)")
print("2) 브라우저에서 로컬 또는 Render 테스트")
print("3) git add -A ; git commit -m \"0-54: 구독1년권 매월지급 + 쌀충전소구독 통합페이지 + 채팅탭 아이콘 재구성\" ; git push")