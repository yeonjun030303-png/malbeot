# ===== server.js 수정 =====
path = "server.js"
with open(path, encoding="utf-8") as f:
    content = f.read()

old1 = """      const likerIds = Object.keys((target.photoLikes && target.photoLikes[photoIndex]) || {});
      const me = await getUser(myId);
      if (!hasTierAtLeast(me, 'gold')) {
        return cb && cb({ success: true, locked: true, count: likerIds.length, likers: [] });
      }
      const users = await getAllUsers();
      const likers = likerIds.map(id => users[id]).filter(Boolean);
      cb && cb({ success: true, locked: false, count: likerIds.length, likers });"""
new1 = """      const likerIds = Object.keys((target.photoLikes && target.photoLikes[photoIndex]) || {});
      const me = await getUser(myId);
      const users = await getAllUsers();
      const likers = likerIds.map(id => users[id]).filter(Boolean);
      // 0-24: locked이어도 실제 likers를 같이 내려줌 - 클라이언트가 블러 처리된 실제 카드로 잠금화면을 보여주기 위함
      const locked = !hasTierAtLeast(me, 'gold');
      cb && cb({ success: true, locked, count: likerIds.length, likers });"""
assert content.count(old1) == 1, "old1 count=%d" % content.count(old1)
content = content.replace(old1, new1, 1)

old2 = """      const visitorIds = Object.keys(latestByVisitor).sort((a, b) => latestByVisitor[b] - latestByVisitor[a]);
      const me = await getUser(userId);
      if (!hasTierAtLeast(me, 'gold')) {
        return cb && cb({ success: true, locked: true, count: visitorIds.length, visitors: [] });
      }
      const users = await getAllUsers();
      const visitors = visitorIds.map(id => users[id]).filter(Boolean);
      cb && cb({ success: true, locked: false, count: visitorIds.length, visitors });"""
new2 = """      const visitorIds = Object.keys(latestByVisitor).sort((a, b) => latestByVisitor[b] - latestByVisitor[a]);
      const me = await getUser(userId);
      const users = await getAllUsers();
      const visitors = visitorIds.map(id => users[id]).filter(Boolean);
      // 0-24: locked이어도 실제 visitors를 같이 내려줌 - 클라이언트가 블러 처리된 실제 카드로 잠금화면을 보여주기 위함
      const locked = !hasTierAtLeast(me, 'gold');
      cb && cb({ success: true, locked, count: visitorIds.length, visitors });"""
assert content.count(old2) == 1, "old2 count=%d" % content.count(old2)
content = content.replace(old2, new2, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("✅ [1/2] server.js 패치 완료")

# ===== public/index.html 수정 =====
path = "public/index.html"
with open(path, encoding="utf-8") as f:
    content = f.read()

old_modal = """  <div id="miniAlertModal" class="modal-overlay">
    <div class="mini-alert-card">
      <h3 style="margin-bottom:10px;">알림</h3>
      <p id="miniAlertText" style="font-size:13px;color:#495057;line-height:1.5;"></p>
      <div id="miniAlertButtons" style="display:flex;gap:8px;margin-top:18px;"></div>
    </div>
  </div>"""

new_modal = old_modal + """

  <!-- 0-24: 골드 이상 전용 목록(방문자/좋아요) 잠금화면 - 탭하면 결제창 이동 여부를 물어보는 확인창 -->
  <div id="lockUpsellModal" class="modal-overlay">
    <div class="mini-alert-card" style="text-align:center;">
      <div style="width:48px;height:48px;border-radius:50%;background:rgba(0,0,0,.75);display:flex;align-items:center;justify-content:center;color:#fff;font-size:20px;margin:0 auto 14px;"><i class="fa-solid fa-lock"></i></div>
      <p style="font-size:14px;font-weight:800;margin-bottom:6px;">골드 이상 등급부터 확인 가능합니다</p>
      <p style="font-size:13px;color:#495057;margin-bottom:4px;">결제창으로 이동하시겠습니까?</p>
      <div style="display:flex;gap:8px;margin-top:18px;">
        <button class="btn btn-secondary" style="flex:1;" onclick="closeModal('lockUpsellModal')">취소</button>
        <button class="btn btn-primary" style="flex:1;" onclick="closeModal('lockUpsellModal');openSubscriptionScreen()">확인</button>
      </div>
    </div>
  </div>"""

assert content.count(old_modal) == 1, "modal count=%d" % content.count(old_modal)
content = content.replace(old_modal, new_modal, 1)

old_fn = """// 0-20: 방문자/좋아요 목록 등에서 무료 유저에게 보여줄 잠금 티저 UI (블러 처리된 아바타 + 가운데 자물쇠 + 인원수(9+))
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
}"""

new_fn = """// 0-24: 방문자/좋아요 목록 등에서 무료 유저에게 보여줄 잠금화면 - 실제 목록(프로필사진+별명) 그대로 두되 블러 처리,
// 탭하면 lockUpsellModal(골드 이상 등급부터 확인 가능 + 결제창 이동 확인)을 띄움
function showLockUpsellConfirm(){
  openModal('lockUpsellModal');
}
function renderLockTeaser(users){
  const list = (users || []).slice(0, 12);
  const rows = list.length ? list.map(function(u){
    return '<div class="user-card">'
      + avatarHtmlFor(u,'avatar')
      + '<div style="flex:1;min-width:0;"><span class="user-nickname">' + escapeHtml(u.nickname) + '</span>'
      + '<div style="display:flex;gap:6px;margin-top:4px;"><span class="tag">' + (u.region||'') + '</span><span class="tag">' + (u.gender==='female'?'여성':'남성') + '</span><span class="tag">' + (u.age||'') + '세</span></div></div></div>';
  }).join('') : '<div class="user-card"><div style="width:44px;height:44px;border-radius:50%;background:var(--bg-subtle);"></div><div style="flex:1;"><span class="user-nickname">●●●</span></div></div>';
  return '<div style="position:relative;cursor:pointer;" onclick="showLockUpsellConfirm()">'
    + '<div style="filter:blur(5px);pointer-events:none;user-select:none;">' + rows + '</div>'
    + '<div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,.3);border-radius:12px;">'
    + '<div style="width:40px;height:40px;border-radius:50%;background:rgba(0,0,0,.7);display:flex;align-items:center;justify-content:center;color:#fff;font-size:16px;"><i class="fa-solid fa-lock"></i></div></div></div>';
}"""

assert content.count(old_fn) == 1, "fn count=%d" % content.count(old_fn)
content = content.replace(old_fn, new_fn, 1)

old_call1 = """    if (res.locked){ body.innerHTML = renderLockTeaser(res.count, '이 사진에 좋아요 누른 사람을 확인할 수 있어요.'); openFullScreen('photoLikersScreen'); return; }"""
new_call1 = """    if (res.locked){ body.innerHTML = renderLockTeaser(res.likers); openFullScreen('photoLikersScreen'); return; }"""
assert content.count(old_call1) == 1, "call1 count=%d" % content.count(old_call1)
content = content.replace(old_call1, new_call1, 1)

old_call2 = """    if (res.locked){ wrap.innerHTML = renderLockTeaser(res.count, '구독 시작 이전 기록까지 포함한 전체 방문자를 확인할 수 있어요.'); return; }"""
new_call2 = """    if (res.locked){ wrap.innerHTML = renderLockTeaser(res.visitors); return; }"""
assert content.count(old_call2) == 1, "call2 count=%d" % content.count(old_call2)
content = content.replace(old_call2, new_call2, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("✅ [2/2] public/index.html 패치 완료 — 0-24 전체 완료")