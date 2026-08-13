import re

# ===== 1) server.js 수정 =====
path_server = "server.js"
with open(path_server, "r", encoding="utf-8") as f:
    s = f.read()

# 1-1) 마스킹 헬퍼 함수 추가 (SUBSCRIPTION_TIER_RANK 헬퍼 블록 바로 뒤)
anchor_server = '''function hasTierAtLeast(user, minTier) {
  const sub = getActiveSubscription(user);
  if (!sub) return false;
  return (SUBSCRIPTION_TIER_RANK[sub.tier] || 0) >= (SUBSCRIPTION_TIER_RANK[minTier] || 0);
}'''
assert anchor_server in s, "SUBSCRIPTION_TIER_RANK 헬퍼 블록을 찾을 수 없습니다"

new_server = anchor_server + '''
// 0-28: 방문자/좋아요 잠금화면(0-24)이 CSS 블러만으로 실제 데이터를 가려서, 개발자도구로 블러를 끄거나
// 네트워크 응답만 봐도 닉네임/사진 원본이 그대로 노출되는 문제가 있었음 - locked 상태일 때는 서버에서부터
// 닉네임은 마스킹하고 사진 원본 URL은 아예 내려보내지 않도록 함(클라이언트는 기본 실루엣 아이콘으로 대체)
function maskUserForLockedTeaser(u) {
  const nick = (u && u.nickname) || '';
  const masked = nick.length <= 1 ? '○' : nick[0] + '○'.repeat(Math.min(nick.length - 1, 2));
  return { id: u.id, nickname: masked, region: u.region, gender: u.gender, age: u.age };
}'''

s = s.replace(anchor_server, new_server)

# 1-2) profile:get_all_visitors - locked이면 마스킹된 데이터로 교체
old_visitors = '''      const visitors = visitorIds.map(id => users[id]).filter(Boolean);
      // 0-24: locked이어도 실제 visitors를 같이 내려줌 - 클라이언트가 블러 처리된 실제 카드로 잠금화면을 보여주기 위함
      const locked = !hasTierAtLeast(me, 'gold');
      cb && cb({ success: true, locked, count: visitorIds.length, visitors });'''
assert old_visitors in s, "visitors 핸들러를 찾을 수 없습니다"

new_visitors = '''      const rawVisitors = visitorIds.map(id => users[id]).filter(Boolean);
      const locked = !hasTierAtLeast(me, 'gold');
      // 0-28: locked이면 실제 닉네임/사진 대신 마스킹된 정보만 내려보냄(브라우저에서 실제 데이터 노출 방지)
      const visitors = locked ? rawVisitors.map(maskUserForLockedTeaser) : rawVisitors;
      cb && cb({ success: true, locked, count: visitorIds.length, visitors });'''

s = s.replace(old_visitors, new_visitors)

# 1-3) photo:get_likers - locked이면 마스킹된 데이터로 교체
old_likers = '''      const likers = likerIds.map(id => users[id]).filter(Boolean);
      // 0-24: locked이어도 실제 likers를 같이 내려줌 - 클라이언트가 블러 처리된 실제 카드로 잠금화면을 보여주기 위함
      const locked = !hasTierAtLeast(me, 'gold');
      cb && cb({ success: true, locked, count: likerIds.length, likers });'''
assert old_likers in s, "likers 핸들러를 찾을 수 없습니다"

new_likers = '''      const rawLikers = likerIds.map(id => users[id]).filter(Boolean);
      const locked = !hasTierAtLeast(me, 'gold');
      // 0-28: locked이면 실제 닉네임/사진 대신 마스킹된 정보만 내려보냄(브라우저에서 실제 데이터 노출 방지)
      const likers = locked ? rawLikers.map(maskUserForLockedTeaser) : rawLikers;
      cb && cb({ success: true, locked, count: likerIds.length, likers });'''

s = s.replace(old_likers, new_likers)

with open(path_server, "w", encoding="utf-8") as f:
    f.write(s)

print("✅ [1/2] server.js — 잠금화면 마스킹 처리 완료")

# ===== 2) public/index.html 수정 =====
path_html = "public/index.html"
with open(path_html, "r", encoding="utf-8") as f:
    h = f.read()

old_teaser = '''function renderLockTeaser(users){
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
}'''
assert old_teaser in h, "renderLockTeaser 함수를 찾을 수 없습니다"

new_teaser = '''function renderLockTeaser(users){
  const list = (users || []).slice(0, 12);
  const rows = list.length ? list.map(function(u){
    // 0-28: locked 상태에서는 서버가 마스킹된 닉네임만 내려주고 실제 사진 URL은 주지 않으므로,
    // 항상 기본 실루엣 아이콘을 사용함(개발자도구로 봐도 실제 사진/닉네임이 노출되지 않도록)
    return '<div class="user-card">'
      + defaultAvatarHtml(u.gender,'avatar')
      + '<div style="flex:1;min-width:0;"><span class="user-nickname">' + escapeHtml(u.nickname) + '</span>'
      + '<div style="display:flex;gap:6px;margin-top:4px;"><span class="tag">' + (u.region||'') + '</span><span class="tag">' + (u.gender==='female'?'여성':'남성') + '</span><span class="tag">' + (u.age||'') + '세</span></div></div></div>';
  }).join('') : '<div class="user-card"><div style="width:44px;height:44px;border-radius:50%;background:var(--bg-subtle);"></div><div style="flex:1;"><span class="user-nickname">●●●</span></div></div>';
  return '<div style="position:relative;cursor:pointer;" onclick="showLockUpsellConfirm()">'
    + '<div style="filter:blur(5px);pointer-events:none;user-select:none;">' + rows + '</div>'
    + '<div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,.3);border-radius:12px;">'
    + '<div style="width:40px;height:40px;border-radius:50%;background:rgba(0,0,0,.7);display:flex;align-items:center;justify-content:center;color:#fff;font-size:16px;"><i class="fa-solid fa-lock"></i></div></div></div>';
}'''

h = h.replace(old_teaser, new_teaser)

with open(path_html, "w", encoding="utf-8") as f:
    f.write(h)

print("✅ [2/2] public/index.html — 잠금화면에서 기본 실루엣 아이콘만 쓰도록 변경 완료")
print("0-28 패치 전체 완료")