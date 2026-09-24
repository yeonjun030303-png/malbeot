# 0-93: 하단 우측 탭 아이콘 햇빛 -> 톱니바퀴(설정)로 복원
# 0-94: 홈/커뮤니티(스토리)/채팅/설정 탭에서 맨 위를 아래로 당겨 새로고침(로딩 아이콘 표시, 상단 헤더·필터바는 고정)
# 0-95: 채팅 입력창을 누르면 최신 메시지(맨 아래)로 먼저 내린 뒤 키보드가 올라오고, 키보드 높이 변경 후에도 맨 아래 유지
# 0-96: 화면 전환 애니메이션(탭 페이드, 전체화면 슬라이드, 드로어, 모달 팝, 닫힐 때 애니메이션)
# 0-97: 롱프레스 말풍선 커지기 재수정(iOS 기본 텍스트선택/콜아웃 차단, 터치 미세 떨림 허용, 놓을 때 메뉴 닫힘 방지)
import sys, io, re, subprocess, tempfile, os

p = 'public/index.html'
s = io.open(p, encoding='utf-8').read()

def rep(old, new, label):
    global s
    n = s.count(old)
    if n != 1:
        print('FAIL', label, 'count=', n)
        print('-> 파일이 인수인계 시점과 달라졌을 수 있음. git pull 후 다시 시도하거나 클로드에게 알려주세요.')
        sys.exit(1)
    s = s.replace(old, new)
    print('OK  ', label)

def rep_func(name, new, label):
    global s
    head = 'function ' + name + '('
    if s.count(head) != 1:
        print('FAIL', label, 'count=', s.count(head)); sys.exit(1)
    i = s.index(head)
    j = s.index('\n}\n', i) + 3
    s = s[:i] + new + s[j:]
    print('OK  ', label)

# ---------------------------------------------------------------- 0-93
GEAR = ('<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>')
rep('<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1"/>',
    GEAR, '0-93 nav gear icon')

# ---------------------------------------------------------------- CSS (0-94, 0-96, 0-97)
rep(""".msg-bubble.msg-pressed{position:relative;z-index:5;transform:scale(1.07);box-shadow:0 6px 18px rgba(0,0,0,.22);animation:msgPop .22s ease-out;}
.msg-row.mine .msg-bubble.msg-pressed{transform-origin:right center;}
.msg-row.other .msg-bubble.msg-pressed{transform-origin:left center;}
@keyframes msgPop{0%{transform:scale(1);}55%{transform:scale(1.11);}100%{transform:scale(1.07);}}""",
""".msg-bubble{-webkit-user-select:none;user-select:none;-webkit-touch-callout:none;-webkit-tap-highlight-color:transparent;transition:transform .2s cubic-bezier(.2,.9,.3,1.25),box-shadow .2s ease;}
.msg-bubble.msg-pressed{position:relative;z-index:5;transform:scale(1.08);box-shadow:0 8px 20px rgba(0,0,0,.25);}
.msg-row.mine .msg-bubble.msg-pressed{transform-origin:right center;}
.msg-row.other .msg-bubble.msg-pressed{transform-origin:left center;}""", '0-97 css')

CSS_ADD = r"""
/* 0-94: 당겨서 새로고침 */
#ptrWrap{position:sticky;top:0;height:0;z-index:9;pointer-events:none;}
#ptrIndicator{position:absolute;left:50%;top:-12px;width:38px;height:38px;margin-left:-19px;border-radius:50%;background:#fff;box-shadow:0 2px 10px rgba(0,0,0,.18);display:flex;align-items:center;justify-content:center;color:var(--primary);font-size:16px;opacity:0;transform:translateY(-46px);}
#ptrIndicator.ptr-loading i{animation:mbPtrSpin .8s linear infinite;}
@keyframes mbPtrSpin{to{transform:rotate(360deg);}}
body.dark-mode #ptrIndicator{background:var(--bg-card);}
/* 0-96: 화면 전환 애니메이션 (열릴 때는 .active, 닫힐 때는 JS가 잠깐 붙이는 .closing 으로 재생) */
.tab-content.active{animation:mbTabIn .24s ease-out;}
@keyframes mbTabIn{from{opacity:0;transform:translateY(8px);}to{opacity:1;transform:none;}}
.full-screen-overlay.active{animation:mbSlideIn .3s cubic-bezier(.22,.9,.32,1);}
@keyframes mbSlideIn{from{transform:translateX(32px);opacity:0;}to{transform:none;opacity:1;}}
.full-screen-overlay.closing:not(.active){display:flex;pointer-events:none;animation:mbSlideOut .2s ease-in forwards;}
@keyframes mbSlideOut{from{transform:none;opacity:1;}to{transform:translateX(32px);opacity:0;}}
#storyViewerScreen.active,#photoPreviewScreen.active{animation:mbFadeIn .22s ease-out;}
#storyViewerScreen.closing:not(.active),#photoPreviewScreen.closing:not(.active),#chatModal.closing:not(.active),#groupChatModal.closing:not(.active){animation:mbFadeOut .16s ease-in forwards;}
.full-screen-overlay.drawer-right.active{animation:mbDrawerIn .3s cubic-bezier(.22,.9,.32,1);}
.full-screen-overlay.drawer-right.closing:not(.active){animation:mbDrawerOut .22s ease-in forwards;}
@keyframes mbDrawerIn{from{transform:translateX(100%);}to{transform:none;}}
@keyframes mbDrawerOut{from{transform:none;}to{transform:translateX(100%);}}
#drawerBackdrop{display:block;opacity:0;pointer-events:none;transition:opacity .28s ease;}
#drawerBackdrop.active{opacity:1;pointer-events:auto;}
.modal-overlay.active{animation:mbFadeIn .2s ease-out;}
.modal-overlay.active:not(.bottom-sheet-overlay) > .modal-card,.modal-overlay.active > .mini-alert-card{animation:mbCardPop .26s cubic-bezier(.2,.9,.3,1.15);}
.modal-overlay.closing:not(.active){display:flex;pointer-events:none;animation:mbFadeOut .16s ease-in forwards;}
.bottom-sheet-overlay.closing:not(.active) .modal-card{animation:mbSheetDown .18s ease-in forwards;}
@keyframes mbFadeIn{from{opacity:0;}to{opacity:1;}}
@keyframes mbFadeOut{from{opacity:1;}to{opacity:0;}}
@keyframes mbCardPop{from{transform:scale(.94) translateY(8px);opacity:0;}to{transform:none;opacity:1;}}
@keyframes mbSheetDown{from{transform:none;opacity:1;}to{transform:translateY(40px);opacity:0;}}
@media (prefers-reduced-motion:reduce){
  .tab-content.active,.full-screen-overlay.active,.modal-overlay.active,.modal-overlay.active .modal-card,.modal-overlay.active .mini-alert-card{animation:none !important;}
  .full-screen-overlay.closing:not(.active),.modal-overlay.closing:not(.active){display:none !important;}
}"""
rep("@keyframes sheetUp{from{transform:translateY(24px);opacity:.5;}to{transform:translateY(0);opacity:1;}}",
    "@keyframes sheetUp{from{transform:translateY(24px);opacity:.5;}to{transform:translateY(0);opacity:1;}}" + CSS_ADD,
    '0-94/0-96 css')

# ---------------------------------------------------------------- 0-97 롱프레스
NEW_ATTACH = r"""// 0-97: 롱프레스 공통 처리. (1) iOS는 손가락이 1~2px만 흔들려도 touchmove가 발생하는데 기존엔 그때마다 타이머를 취소해서
// 롱프레스가 거의 안 먹었음 -> 10px 넘게 움직였을 때만 취소. (2) iOS 기본 텍스트선택/콜아웃(CSS로 차단)이 터치를 가로채던 것 차단.
// (3) 손가락을 뗄 때 발생하는 click이 방금 띄운 메뉴를 바로 닫아버리던 것 방지.
let msgMenuOpenedAt = 0;
let msgSuppressClickUntil = 0;
function msgHapticTick(){
  try {
    const H = window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.Haptics;
    if (H && H.impact) { H.impact({ style: 'MEDIUM' }); return; }
  } catch (e) {}
  try { if (navigator.vibrate) navigator.vibrate(15); } catch (e) {}
}
function bindMsgLongPress(bubbleEl, openFn){
  let sx = 0, sy = 0, fired = false;
  const cancelT = ()=>{ if (msgPressTimer){ clearTimeout(msgPressTimer); msgPressTimer = null; } };
  bubbleEl.addEventListener('touchstart', (e)=>{
    cancelT();
    if (!e.touches || e.touches.length !== 1) return;
    const t = e.touches[0]; sx = t.clientX; sy = t.clientY; fired = false;
    msgPressTimer = setTimeout(()=>{
      msgPressTimer = null; fired = true;
      msgHapticTick();
      openFn(sx, sy);
      setMsgHighlight(bubbleEl);
      msgMenuOpenedAt = Date.now();
      msgSuppressClickUntil = Date.now() + 8000;
    }, 380);
  }, { passive: true });
  bubbleEl.addEventListener('touchmove', (e)=>{
    const t = e.touches && e.touches[0]; if (!t) return;
    if (Math.abs(t.clientX - sx) > 10 || Math.abs(t.clientY - sy) > 10) cancelT();
  }, { passive: true });
  const endT = (e)=>{
    cancelT();
    if (fired){
      fired = false;
      msgSuppressClickUntil = Date.now() + 450;
      if (e.cancelable) e.preventDefault();
    }
  };
  bubbleEl.addEventListener('touchend', endT, { passive: false });
  bubbleEl.addEventListener('touchcancel', endT, { passive: false });
  bubbleEl.addEventListener('contextmenu', (e)=>{
    e.preventDefault();
    openFn(e.clientX, e.clientY);
    setMsgHighlight(bubbleEl);
    msgMenuOpenedAt = Date.now();
  });
}
function attachMsgLongPress(bubbleEl, m){
  bindMsgLongPress(bubbleEl, (x, y)=> openMsgContextMenuAt(x, y, m));
}
"""
rep_func('attachMsgLongPress', NEW_ATTACH, '0-97 attachMsgLongPress')
rep_func('attachGroupMsgLongPress',
"""function attachGroupMsgLongPress(bubbleEl, m){
  bindMsgLongPress(bubbleEl, (x, y)=> openGroupMsgContextMenuAt(x, y, m));
}
""", '0-97 attachGroupMsgLongPress')
rep("function closeMsgContextMenuOutside(e){\n  if (msgContextMenuEl && !msgContextMenuEl.contains(e.target)) closeMsgContextMenu();",
    "function closeMsgContextMenuOutside(e){\n  if (Date.now() < msgSuppressClickUntil) return;\n  if (msgContextMenuEl && !msgContextMenuEl.contains(e.target)) closeMsgContextMenu();",
    '0-97 outside click guard')

# ---------------------------------------------------------------- 키보드 후 맨 아래 유지 훅 (0-95)
rep("    document.body.classList.toggle('keyboard-open', kbHeight > 0);",
    "    document.body.classList.toggle('keyboard-open', kbHeight > 0);\n    if (kbHeight > 0 && window.malbeotStickChatBottom) window.malbeotStickChatBottom();",
    '0-95 native keyboard hook')
rep("      document.body.classList.toggle('keyboard-open', isOpen);",
    "      document.body.classList.toggle('keyboard-open', isOpen);\n      if (isOpen && window.malbeotStickChatBottom) window.malbeotStickChatBottom();",
    '0-95 web keyboard hook')

# ---------------------------------------------------------------- 새 스크립트 (0-94, 0-95, 0-96)
NEW_SCRIPT = r"""<script>
/* ===== 0-95: 채팅 입력창을 누르면 최신 메시지로 먼저 내린 뒤 키보드가 올라오게 ===== */
(function initChatKeyboardStick(){
  var PAIRS = [
    { modal:'chatModal', input:'chatInputText', area:'chatMessageArea', armedAt:0 },
    { modal:'groupChatModal', input:'groupChatInputText', area:'groupChatMessageArea', armedAt:0 }
  ];
  function toBottom(area, smooth){
    if (!area) return;
    if (smooth && area.scrollTo){ try { area.scrollTo({ top: area.scrollHeight, behavior: 'smooth' }); return; } catch (e) {} }
    area.scrollTop = area.scrollHeight;
  }
  // 키보드 높이가 반영돼 채팅 영역이 줄어든 직후에도 맨 아래를 유지 (입력창을 직접 눌러 연 경우에만)
  window.malbeotStickChatBottom = function(){
    PAIRS.forEach(function(p){
      var modal = document.getElementById(p.modal), input = document.getElementById(p.input);
      if (!modal || !input || !modal.classList.contains('active') || document.activeElement !== input) return;
      if (Date.now() - p.armedAt > 3000) return;
      var area = document.getElementById(p.area);
      toBottom(area, false);
      requestAnimationFrame(function(){ toBottom(area, false); });
    });
  };
  PAIRS.forEach(function(p){
    var input = document.getElementById(p.input), area = document.getElementById(p.area);
    if (!input || !area) return;
    // 손가락이 입력창에 닿는 순간(키보드가 뜨기 전) 먼저 최신 메시지로 부드럽게 내림
    function pre(){
      if (document.activeElement === input) return;
      p.armedAt = Date.now();
      toBottom(area, true);
    }
    input.addEventListener('touchstart', pre, { passive: true });
    input.addEventListener('mousedown', pre);
    input.addEventListener('focus', function(){
      if (Date.now() - p.armedAt > 1000) return; // 답장 버튼 등 코드로 focus 되는 경우는 스크롤 위치 유지
      toBottom(area, false);
      [80, 200, 380, 600].forEach(function(d){
        setTimeout(function(){ if (document.activeElement === input) toBottom(area, false); }, d);
      });
    });
  });
})();

/* ===== 0-94: 당겨서 새로고침 (홈 / 커뮤니티(스토리) / 채팅 / 설정 탭) ===== */
(function initPullToRefresh(){
  var main = document.querySelector('.content-area');
  if (!main) return;
  var wrap = document.createElement('div');
  wrap.id = 'ptrWrap';
  wrap.innerHTML = '<div id="ptrIndicator"><i class="fa-solid fa-rotate-right"></i></div>';
  main.insertBefore(wrap, main.firstChild);
  var ind = wrap.firstChild, icon = ind.firstChild;
  var THRESHOLD = 56, MAX = 96, HOLD = 52;
  var startY = 0, startX = 0, tracking = false, pulling = false, refreshing = false, pullY = 0;

  function activeTab(){ return main.querySelector('.tab-content.active'); }
  function clearTabStyles(){
    main.querySelectorAll('.tab-content').forEach(function(t){ t.style.transform = ''; t.style.transition = ''; });
  }
  function setPull(p, animate){
    pullY = p;
    var tab = activeTab();
    var ease = 'transform .25s cubic-bezier(.2,.8,.3,1)';
    if (tab){ tab.style.transition = animate ? ease : 'none'; tab.style.transform = p > 0 ? 'translateY(' + p + 'px)' : ''; }
    ind.style.transition = animate ? ease + ', opacity .2s' : 'none';
    ind.style.opacity = p > 4 ? '1' : '0';
    ind.style.transform = 'translateY(' + (p - 46) + 'px)';
    if (!refreshing) icon.style.transform = 'rotate(' + Math.round(Math.min(p / THRESHOLD, 1) * 270) + 'deg)';
  }
  function doRefresh(){
    var tab = activeTab(); var id = tab ? tab.id : '';
    try { if (typeof socket !== 'undefined' && socket && socket.connected === false) socket.connect(); } catch (e) {}
    if (id === 'tab-home') loadHomeUserList();
    else if (id === 'tab-community') loadCommunityPosts();
    else if (id === 'tab-chat') loadChatRoomList();
    else if (id === 'tab-mypage') { loadProfileToForm(); refreshMyPageVisitorCount(); refreshMypageSubLabel(); }
  }
  function finish(){
    refreshing = false;
    ind.classList.remove('ptr-loading');
    icon.style.transform = '';
    setPull(0, true);
    setTimeout(function(){ if (!refreshing && !pulling){ clearTabStyles(); ind.style.transition = 'none'; } }, 300);
  }
  function startRefresh(){
    refreshing = true;
    ind.classList.add('ptr-loading');
    setPull(HOLD, true);
    try { doRefresh(); } catch (e) { console.error('당겨서 새로고침 실패:', e); }
    setTimeout(finish, 900);
  }
  function stop(){ tracking = false; pulling = false; main.removeEventListener('touchmove', onMove); }
  function onStart(e){
    if (refreshing || !e.touches || e.touches.length !== 1) return;
    if (main.scrollTop > 0) return;
    startY = e.touches[0].clientY; startX = e.touches[0].clientX;
    tracking = true; pulling = false;
    main.addEventListener('touchmove', onMove, { passive: false });
  }
  function onMove(e){
    if (!tracking) return;
    var t = e.touches[0]; if (!t) return;
    var dy = t.clientY - startY, dx = t.clientX - startX;
    if (!pulling){
      if (main.scrollTop > 0 || dy < -6){ stop(); return; }       // 이미 스크롤됐거나 위로 미는 중이면 일반 스크롤
      if (dy < 8) return;
      if (Math.abs(dx) > Math.abs(dy)){ stop(); return; }            // 가로 스와이프(채팅방 밀기 등)는 제외
      pulling = true;
    }
    if (e.cancelable) e.preventDefault();                           // iOS 기본 바운스 대신 직접 처리
    setPull(Math.min(MAX, (dy - 8) * 0.65), false);
  }
  function onEnd(){
    if (!tracking) return;
    var was = pulling, p = pullY;
    stop();
    if (!was) return;
    if (p >= THRESHOLD) startRefresh();
    else { setPull(0, true); setTimeout(function(){ if (!refreshing) clearTabStyles(); }, 300); }
  }
  main.addEventListener('touchstart', onStart, { passive: true });
  main.addEventListener('touchend', onEnd, { passive: true });
  main.addEventListener('touchcancel', onEnd, { passive: true });
})();

/* ===== 0-96: 화면/모달이 닫힐 때도 애니메이션이 재생되도록 .closing 을 잠깐 붙임 ===== */
(function initOverlayCloseAnimation(){
  if (!window.MutationObserver) return;
  var obs = new MutationObserver(function(muts){
    muts.forEach(function(m){
      var el = m.target;
      if (!el.classList || !(el.classList.contains('full-screen-overlay') || el.classList.contains('modal-overlay'))) return;
      var was = (m.oldValue || '').split(/\s+/).indexOf('active') !== -1;
      var now = el.classList.contains('active');
      if (was && !now && !el.classList.contains('closing')){
        if (document.hidden) return;
        el.classList.add('closing');
        clearTimeout(el._closingT);
        el._closingT = setTimeout(function(){ el.classList.remove('closing'); }, 240);
      } else if (now && el.classList.contains('closing')){
        el.classList.remove('closing');
        clearTimeout(el._closingT);
      }
    });
  });
  document.querySelectorAll('.full-screen-overlay, .modal-overlay').forEach(function(el){
    obs.observe(el, { attributes: true, attributeFilter: ['class'], attributeOldValue: true });
  });
})();
</script>
"""
rep("</script>\n</body>\n<script>\n(function(){\n  var MALBEOT_BANNER_ID",
    "</script>\n" + NEW_SCRIPT + "</body>\n<script>\n(function(){\n  var MALBEOT_BANNER_ID",
    '0-94/0-95/0-96 script')

io.open(p, 'w', encoding='utf-8', newline='').write(s)

# JS 문법 검사(inline script 전부)
ok = True
for i, b in enumerate(re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', s, re.S)):
    f = os.path.join(tempfile.gettempdir(), 'chk_%d.js' % i)
    io.open(f, 'w', encoding='utf-8').write(b)
    r = subprocess.run(['node', '--check', f], capture_output=True, text=True, shell=(os.name == 'nt'))
    if r.returncode != 0:
        ok = False; print('SYNTAX ERROR in script', i); print(r.stderr)
print('SYNTAX OK' if ok else 'SYNTAX FAIL - git checkout public/index.html 로 되돌리세요')
print('DONE')