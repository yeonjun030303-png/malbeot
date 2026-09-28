# -*- coding: utf-8 -*-
# 0-98: 커뮤니티 헤더 "일상 이야기" -> "스토리"
# 0-99: 하단 탭 신규 "관심사"(홈과 스토리 사이) - 관심사 카드 그리드 + 인원수 + 카드 누르면 사람 리스트
#  * 서버 수정 없음(기존 users:get_list 사용, 인원수는 화면에서 계산)
import io, re, os, subprocess, tempfile

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

def js_errors(html):
    bad = []
    blocks = re.findall(r'<script(?![^>]*\bsrc=)(?![^>]*\btype=)[^>]*>(.*?)</script>', html, re.S)
    for i, code in enumerate(blocks):
        fd, path = tempfile.mkstemp(suffix=".js")
        os.close(fd)
        try:
            with io.open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(code)
            r = subprocess.run(["node", "--check", path], capture_output=True)
            if r.returncode != 0:
                bad.append(i)
        finally:
            os.remove(path)
    return bad

hp = "public/index.html"
h = read(hp)
bad_before = js_errors(h)

# ---------- 0-98: 이름 변경 ----------
h = rep(h, "title.textContent='일상 이야기'", "title.textContent='스토리'", "0-98 헤더 제목")
h = rep(h, "커뮤니티에서 일상을 공유해요", "스토리에서 일상을 공유해요", "0-98 온보딩 문구")

# ---------- 0-99: CSS ----------
CSS = """.nav-item.active{color:var(--primary);}
/* 0-99: 관심사 탭 */
#discoverRoot{padding-bottom:24px;}
.discover-sec-title{font-size:15px;font-weight:800;margin:18px 16px 10px;}
.discover-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:0 14px;}
.discover-card{background:var(--bg-card);border:1px solid var(--border-color);border-radius:22px;aspect-ratio:3/4;display:flex;flex-direction:column;justify-content:space-between;padding:12px 14px;cursor:pointer;overflow:hidden;}
.discover-card:active{transform:scale(.98);}
.discover-card-icon{flex:1;display:flex;align-items:center;justify-content:center;min-height:0;}
.discover-emoji{font-size:72px;line-height:1;}
.discover-mbti{font-size:34px;font-weight:900;color:var(--primary);letter-spacing:1px;}
.discover-img{max-width:78%;max-height:100%;object-fit:contain;}
.discover-card-foot{display:flex;justify-content:space-between;align-items:baseline;gap:6px;}
.discover-card-name{font-size:14px;font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.discover-card-count{font-size:14px;color:var(--text-muted);}
.discover-empty{text-align:center;padding:40px 16px;color:var(--text-muted);font-size:13px;}
.discover-listhead{display:flex;align-items:center;gap:10px;padding:12px 14px;}
.discover-back{background:none;border:none;font-size:18px;color:inherit;cursor:pointer;padding:4px 8px;}
.discover-listtitle{font-size:17px;font-weight:800;flex:1;}"""
h = rep(h, ".nav-item.active{color:var(--primary);}", CSS, "0-99 CSS")

# ---------- 0-99: 하단 탭 버튼 ----------
NAV_ICON = '<button class="nav-item" data-tab="tab-discover"><svg class="nav-icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="8" height="8" rx="2"/><rect x="13" y="3" width="8" height="8" rx="2"/><rect x="3" y="13" width="8" height="8" rx="2"/><rect x="13" y="13" width="8" height="8" rx="2"/></svg></button>\n    '
h = rep(h, '<button class="nav-item" data-tab="tab-community">', NAV_ICON + '<button class="nav-item" data-tab="tab-community">', "0-99 하단 탭 버튼")

# ---------- 0-99: 탭 화면 영역 ----------
SECTION = '<section id="tab-discover" class="tab-content">\n      <div id="discoverRoot"></div>\n    </section>\n\n    '
h = rep(h, '<section id="tab-community" class="tab-content">', SECTION + '<section id="tab-community" class="tab-content">', "0-99 탭 화면")

# ---------- 0-99: 헤더 제목 ----------
h = rep(h, "else if (tab==='tab-chat'){ title.textContent='채팅';",
        "else if (tab==='tab-discover'){ title.textContent='관심사'; filterBar.classList.add('hidden'); }\n  else if (tab==='tab-chat'){ title.textContent='채팅';", "0-99 헤더 분기")

# ---------- 0-99: switchTab 연결 ----------
h = rep(h, "if (tab==='tab-chat') loadChatRoomList();",
        "if (tab==='tab-discover') openDiscoverTab();\n  if (tab==='tab-chat') loadChatRoomList();", "0-99 switchTab 연결")

# ---------- 0-99: JS ----------
JS = """/* ===================== 0-99: 관심사 탭 (카드 그리드 + 인원수 + 사람 리스트) ===================== */
const DISCOVER_INCLUDE_ME = false; // 테스트용: true로 바꾸면 내 계정도 인원수에 포함
const DISCOVER_ICONS = {light:'🎈',contact:'💬',serious:'💍',sports:'⚽',activity:'🏄',homebody:'🛋️',netflix:'📺',game:'🎮',travel:'✈️',food:'🍜',cafe:'☕',reading:'📚',pet:'🐾',fitness:'🏋️',music:'🎧',cooking:'🍳',photo:'📷'};
let discoverUsers = null;
let discoverView = null;
function discoverGroups(){
  const g = (currentUser && currentUser.gender) || 'female';
  return [
    {title:'어떤 만남을 찾고 있나요?', items: PURPOSE_OPTIONS.map(o=>({kind:'purpose', key:o.key, label:o.label}))},
    {title:'같은 취미로 만나요', items: HOBBY_OPTIONS.map(o=>({kind:'hobby', key:o.key, label:hobbyLabel(o,g)}))},
    {title:'MBTI로 만나요', items: MBTI_TYPES.map(t=>({kind:'mbti', key:t, label:t}))}
  ];
}
function discoverFindItem(kind, key){
  const gs = discoverGroups();
  for (let i=0;i<gs.length;i++){ const f = gs[i].items.find(it=>it.kind===kind && it.key===key); if (f) return f; }
  return null;
}
function discoverHas(u, item){
  const it = (u && u.interests) || {};
  if (item.kind==='purpose') return it.purpose===item.key;
  if (item.kind==='mbti') return it.mbti===item.key;
  return (it.hobbies||[]).includes(item.key);
}
function discoverVisibleUsers(list){
  const me = currentUser || {};
  const blocked = me.blockedUserIds || [];
  return (list||[]).filter(u=>{
    if (!u || u.deleted) return false;
    if (!DISCOVER_INCLUDE_ME && me.id && u.id===me.id) return false;
    return !blocked.includes(u.id);
  });
}
function discoverIconHtml(item){
  const fb = item.kind==='mbti'
    ? '<span class="discover-mbti">'+item.key+'</span>'
    : '<span class="discover-emoji">'+(DISCOVER_ICONS[item.key]||'✨')+'</span>';
  return fb + '<img class="discover-img" src="interests/'+item.key.toLowerCase()+'.png" alt="" style="display:none" onload="this.style.display=\\'block\\';this.previousElementSibling.style.display=\\'none\\'" onerror="this.remove()">';
}
function openDiscoverTab(){ discoverView = null; loadDiscover(); }
function loadDiscover(){
  const root = document.getElementById('discoverRoot'); if (!root) return;
  if (!discoverUsers) root.innerHTML = '<div class="discover-empty">불러오는 중...</div>';
  socket.emit('users:get_list', {region:'전체', gender:'전체', ageMin:19, ageMax:99}, (res)=>{
    if (!res || !res.success){ if (!discoverUsers) root.innerHTML = '<div class="discover-empty">불러오지 못했어요. 잠시 후 다시 시도해주세요.</div>'; return; }
    discoverUsers = discoverVisibleUsers(res.users);
    if (discoverView) renderDiscoverList(discoverView); else renderDiscoverGrid();
  });
}
function renderDiscoverGrid(){
  const root = document.getElementById('discoverRoot'); if (!root) return;
  const users = discoverUsers || [];
  let html = '';
  discoverGroups().forEach(gr=>{
    html += '<div class="discover-sec-title">'+gr.title+'</div><div class="discover-grid">';
    gr.items.forEach(item=>{
      const cnt = users.filter(u=>discoverHas(u,item)).length;
      html += '<div class="discover-card" onclick="openDiscoverCategory(\\''+item.kind+'\\',\\''+item.key+'\\')">'
        + '<div class="discover-card-icon">'+discoverIconHtml(item)+'</div>'
        + '<div class="discover-card-foot"><span class="discover-card-name">'+escapeHtml(item.label)+'</span><span class="discover-card-count">'+cnt+'</span></div></div>';
    });
    html += '</div>';
  });
  root.innerHTML = html;
}
function openDiscoverCategory(kind, key){
  discoverView = {kind:kind, key:key};
  renderDiscoverList(discoverView);
  const tc = document.getElementById('tab-discover'); if (tc) tc.scrollTop = 0;
}
function closeDiscoverCategory(){
  discoverView = null;
  renderDiscoverGrid();
}
function renderDiscoverList(view){
  const root = document.getElementById('discoverRoot'); if (!root) return;
  const item = discoverFindItem(view.kind, view.key);
  if (!item){ discoverView = null; renderDiscoverGrid(); return; }
  const list = (discoverUsers||[]).filter(u=>discoverHas(u,item));
  list.sort((a,b)=> (b.isOnline?1:0)-(a.isOnline?1:0) || (b.lastSeen||0)-(a.lastSeen||0));
  root.innerHTML = '<div class="discover-listhead"><button class="discover-back" onclick="closeDiscoverCategory()"><i class="fa-solid fa-chevron-left"></i></button>'
    + '<span class="discover-listtitle">'+escapeHtml(item.label)+'</span><span class="discover-card-count">'+list.length+'명</span></div>'
    + '<div id="discoverUserList" class="user-cards-grid"></div>';
  const c = document.getElementById('discoverUserList');
  if (!list.length){ c.innerHTML = '<div class="discover-empty">아직 이 관심사를 가진 사람이 없어요.</div>'; return; }
  list.forEach(u=>{
    const div = document.createElement('div'); div.className = 'user-card'; div.onclick = ()=>openProfileDetailScreen(u.id);
    div.innerHTML = avatarHtmlFor(u,'avatar')+'<div style="flex:1;min-width:0;">'
      + '<div class="user-card-top"><span class="user-nickname">'+escapeHtml(u.nickname||'')+'</span><span class="user-card-lastseen">'+escapeHtml(formatLastSeen(u.lastSeen, u.isOnline))+'</span></div>'
      + '<div style="display:flex;gap:6px;margin-top:4px;"><span class="tag">'+escapeHtml(u.region||'')+'</span><span class="tag">'+(u.gender==='female'?'여성':'남성')+'</span><span class="tag">'+(u.age||'')+'세</span></div>'
      + '<p style="font-size:12px;color:var(--text-muted);margin-top:6px;">'+escapeHtml(u.bio||'')+'</p></div>';
    c.appendChild(div);
  });
}

/* ===================== 커뮤니티 ===================== */"""
h = rep(h, "/* ===================== 커뮤니티 ===================== */", JS, "0-99 JS 삽입")

# ---------- 문법 검사 ----------
bad_after = js_errors(h)
if len(bad_after) > len(bad_before):
    raise SystemExit("[실패] 수정 후 JS 문법 오류가 늘어남. 저장하지 않고 중단.")

write(hp, h)
print("[적용됨] public/index.html :: 헤더 제목 '스토리' / 온보딩 문구 / 관심사 탭(버튼, 화면, CSS, JS)")

# 남아있는 옛 표기 안내
left = []
for i, line in enumerate(h.split("\n"), 1):
    if ("일상 이야기" in line or "일상이야기" in line) and "/*" not in line:
        left.append("%d: %s" % (i, line.strip()[:120]))
if left:
    print("[참고] 아직 남은 '일상 이야기' 표기:")
    for l in left:
        print("  " + l)
else:
    print("[확인] 남은 '일상 이야기' 표기 없음")
print("0-98 / 0-99 패치 완료.")