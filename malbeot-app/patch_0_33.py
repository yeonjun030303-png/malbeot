# 0-33: 결제 내역(쌀 충전/구독) 기록 + 유저용 조회 화면 추가

# ===== 1) server.js =====
path_s = "server.js"
with open(path_s, "r", encoding="utf-8") as f:
    s = f.read()

old = '''    await saveUser(user);
    if (eventId) await db.ref(`processedPurchaseEvents/${eventId}`).set({ userId, productId, grantPoints, at: Date.now() });'''
assert old in s, "웹훅 저장부를 찾을 수 없습니다"

new = '''    await saveUser(user);
    if (eventId) await db.ref(`processedPurchaseEvents/${eventId}`).set({ userId, productId, grantPoints, at: Date.now() });
    // 0-33: 유저가 나중에 "결제 내역" 화면에서 조회할 수 있도록 기록해둠(관리자가 테스트로 지급한 구독은 여기 안 남음 - 실제 결제 건만)
    await db.ref(`purchaseHistory/${userId}`).push({
      productId,
      points: grantPoints,
      subscriptionTier: subProduct ? subProduct.tier : null,
      subscriptionDays: subProduct ? subProduct.days : null,
      at: Date.now()
    });'''

s = s.replace(old, new)

# 유저 본인의 결제 내역 조회 소켓 핸들러 추가 (photo:get_likers 핸들러 앞에 삽입)
anchor2 = "  // 0-20: 특정 사진에 좋아요 누른 사람 \"목록\" 조회 - 골드 이상 구독 중인 사람만 실제 목록 열람 가능"
assert anchor2 in s, "삽입 위치(photo:get_likers 주석)를 찾을 수 없습니다"

new_handler = '''  // 0-33: 본인의 결제 내역(쌀 충전/구독) 조회
  socket.on('points:get_purchase_history', async (data, cb) => {
    try {
      const myId = socketToUser[socket.id];
      if (!myId) return cb && cb({ success: false, history: [] });
      const snap = await db.ref(`purchaseHistory/${myId}`).once('value');
      const all = snap.val() || {};
      const history = Object.values(all).sort((a, b) => (b.at || 0) - (a.at || 0)).slice(0, 100);
      cb && cb({ success: true, history });
    } catch (e) { console.error(e); cb && cb({ success: false, history: [] }); }
  });

''' + anchor2

s = s.replace(anchor2, new_handler)

with open(path_s, "w", encoding="utf-8") as f:
    f.write(s)

print("✅ [1/2] server.js — 결제 내역 기록 + 조회 핸들러 추가 완료")

# ===== 2) public/index.html =====
path_h = "public/index.html"
with open(path_h, "r", encoding="utf-8") as f:
    h = f.read()

# 2-1) 설정 화면에 메뉴 추가 ("차단한 회원" 항목 바로 아래)
old_menu = '''      <div class="settings-list-item" onclick="openBlockedListScreen()">
        <div class="sli-label">차단한 회원</div>
        <div class="sli-right"><span id="blockedCountLabel"></span><i class="fa-solid fa-chevron-right"></i></div>
      </div>
      </div>'''
assert old_menu in h, "설정화면 차단한 회원 메뉴를 찾을 수 없습니다"

new_menu = '''      <div class="settings-list-item" onclick="openBlockedListScreen()">
        <div class="sli-label">차단한 회원</div>
        <div class="sli-right"><span id="blockedCountLabel"></span><i class="fa-solid fa-chevron-right"></i></div>
      </div>
      <div class="settings-list-item" onclick="openPurchaseHistoryScreen()">
        <div class="sli-label">결제 내역</div>
        <div class="sli-right"><i class="fa-solid fa-chevron-right"></i></div>
      </div>
      </div>'''

h = h.replace(old_menu, new_menu)

# 2-2) 화면 마크업 추가 (blockedListScreen 바로 뒤)
old_screen_anchor = '''    <div class="fs-body" id="blockedListBody" style="padding:8px 16px;"></div>
  </div>

  <div id="profileVisitorsScreen" class="full-screen-overlay">'''
assert old_screen_anchor in h, "blockedListScreen 마크업 뒤 삽입 위치를 찾을 수 없습니다"

new_screen = '''    <div class="fs-body" id="blockedListBody" style="padding:8px 16px;"></div>
  </div>

  <div id="purchaseHistoryScreen" class="full-screen-overlay">
    <div class="fs-header">
      <button class="back-btn" onclick="closeFullScreen('purchaseHistoryScreen')"><i class="fa-solid fa-arrow-left"></i></button>
      <div class="fs-title">결제 내역</div>
    </div>
    <div class="fs-body" id="purchaseHistoryBody" style="padding:8px 16px;"></div>
  </div>

  <div id="profileVisitorsScreen" class="full-screen-overlay">'''

h = h.replace(old_screen_anchor, new_screen)

# 2-3) 렌더링 함수 추가
anchor3 = "function loadAdminReports(){"
assert anchor3 in h, "loadAdminReports 앵커를 찾을 수 없습니다"

new_fn = '''const PURCHASE_PRODUCT_LABEL = {
  points_1000: '쌀 1000개 충전', points_3000: '쌀 3000개 충전', points_5000: '쌀 5000개 충전',
  sub_gold_14d: '골드 구독 14일권', sub_platinum_14d: '플래티넘 구독 14일권',
  sub_gold_365d: '골드 구독 1년권', sub_platinum_365d: '플래티넘 구독 1년권'
};
function openPurchaseHistoryScreen(){
  const body = document.getElementById('purchaseHistoryBody');
  body.innerHTML = `<div style="text-align:center;padding:30px;color:var(--text-muted);">불러오는 중...</div>`;
  openFullScreen('purchaseHistoryScreen');
  socket.emit('points:get_purchase_history', {}, (res)=>{
    if (!res || !res.success || !res.history.length){ body.innerHTML = `<div style="text-align:center;padding:40px;color:var(--text-muted);">결제 내역이 없습니다.</div>`; return; }
    body.innerHTML = res.history.map(function(hst){
      const label = PURCHASE_PRODUCT_LABEL[hst.productId] || hst.productId;
      return '<div class="settings-list-item" style="flex-direction:column;align-items:stretch;cursor:default;">'
        + '<div style="display:flex;justify-content:space-between;"><b>' + escapeHtml(label) + '</b><span style="font-size:12px;color:var(--text-muted);">' + formatRelativeTime(hst.at) + '</span></div>'
        + '<div style="font-size:12px;color:var(--text-muted);margin-top:4px;">쌀 +' + hst.points + '개' + (hst.subscriptionTier ? (' · ' + (hst.subscriptionTier==='platinum'?'플래티넘':'골드') + ' ' + hst.subscriptionDays + '일') : '') + '</div>'
        + '</div>';
    }).join('');
  });
}
function loadAdminReports(){'''

h = h.replace(anchor3, new_fn)

with open(path_h, "w", encoding="utf-8") as f:
    f.write(h)

print("✅ [2/2] public/index.html — 결제 내역 메뉴/화면/렌더링 추가 완료")
print("0-33 패치 전체 완료")