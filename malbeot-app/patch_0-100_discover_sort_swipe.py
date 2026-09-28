# -*- coding: utf-8 -*-
# 0-100: 관심사 탭 개선
#  (1) 리스트에서 왼쪽->오른쪽 스와이프로 카드 화면 복귀
#  (2) 내 관심사와 겹치는 카드를 각 섹션 맨 앞에 배치(별표+테두리), MBTI 포함
#  (3) 사람 리스트는 나와 겹치는 관심사가 많은 순으로 정렬
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

# CSS
h = rep(h, ".discover-listhead{display:flex;",
        ".discover-mine{border:2px solid var(--primary);}\n.discover-listhead{display:flex;", "CSS")

# 카드: 내 관심사 앞으로 + 표시
h = rep(h, "gr.items.forEach(item=>{", "discoverSortMine(gr.items).forEach(item=>{", "카드 정렬")
h = rep(h, "const cnt = users.filter(u=>discoverHas(u,item)).length;",
        "const mine = discoverIsMine(item);\n      const cnt = users.filter(u=>discoverHas(u,item)).length;", "mine 변수")
h = rep(h, "'<div class=\"discover-card\" onclick=\"openDiscoverCategory(",
        "'<div class=\"discover-card'+(mine?' discover-mine':'')+'\" onclick=\"openDiscoverCategory(", "카드 클래스")
h = rep(h, "<span class=\"discover-card-name\">'+escapeHtml(item.label)+'</span>",
        "<span class=\"discover-card-name\">'+(mine?'★ ':'')+escapeHtml(item.label)+'</span>", "카드 이름 별표")

# 사람 리스트 정렬
h = rep(h, "list.sort((a,b)=> (b.isOnline?1:0)-(a.isOnline?1:0) || (b.lastSeen||0)-(a.lastSeen||0));",
        "list.sort((a,b)=> discoverSharedCount(b)-discoverSharedCount(a) || (b.isOnline?1:0)-(a.isOnline?1:0) || (b.lastSeen||0)-(a.lastSeen||0));", "리스트 정렬")

# 도우미 함수 + 스와이프
HELPERS = """function discoverIsMine(item){ return !!(currentUser && discoverHas(currentUser, item)); }
function discoverSortMine(items){
  const mine = [], rest = [];
  items.forEach(it=>{ (discoverIsMine(it) ? mine : rest).push(it); });
  return mine.concat(rest);
}
function discoverSharedCount(u){
  let n = 0;
  discoverGroups().forEach(gr=>gr.items.forEach(it=>{ if (discoverIsMine(it) && discoverHas(u,it)) n++; }));
  return n;
}
// 왼쪽->오른쪽으로 밀면 리스트에서 카드 화면으로 복귀
let discoverSwipe = null;
document.addEventListener('touchstart', function(e){
  discoverSwipe = null;
  if (!discoverView || !e.touches || e.touches.length !== 1) return;
  const tc = document.getElementById('tab-discover');
  if (!tc || !tc.classList.contains('active') || !tc.contains(e.target)) return;
  discoverSwipe = {x:e.touches[0].clientX, y:e.touches[0].clientY};
}, {passive:true});
document.addEventListener('touchend', function(e){
  const s = discoverSwipe; discoverSwipe = null;
  if (!s || !discoverView || !e.changedTouches || !e.changedTouches.length) return;
  const dx = e.changedTouches[0].clientX - s.x, dy = e.changedTouches[0].clientY - s.y;
  if (dx > 70 && Math.abs(dy) < 60 && dx > Math.abs(dy) * 2) closeDiscoverCategory();
}, {passive:true});
document.addEventListener('touchcancel', function(){ discoverSwipe = null; }, {passive:true});
function openDiscoverTab(){ discoverView = null; loadDiscover(); }"""
h = rep(h, "function openDiscoverTab(){ discoverView = null; loadDiscover(); }", HELPERS, "도우미/스와이프")

bad_after = js_errors(h)
if len(bad_after) > len(bad_before):
    raise SystemExit("[실패] 수정 후 JS 문법 오류가 늘어남. 저장하지 않고 중단.")

write(hp, h)
print("[적용됨] public/index.html :: 내 관심사 우선 정렬 / 리스트 겹침순 / 스와이프 뒤로가기")
print("0-100 패치 완료.")