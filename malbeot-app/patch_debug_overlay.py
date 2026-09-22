path = "public/index.html"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = """  document.addEventListener('visibilitychange', function(){
    if (!document.hidden) setAppViewportHeight();
  });"""

new = """  document.addEventListener('visibilitychange', function(){
    if (!document.hidden) setAppViewportHeight();
  });

  // ===== 임시 디버그 오버레이 (문제 진단용, 나중에 제거 예정) =====
  // 화면 좌상단에 실시간 값을 표시해서, 문제 재현 시 캡쳐만 하면
  // 실제 원인을 정확히 파악할 수 있게 함
  var dbg = document.createElement('div');
  dbg.id = 'malbeotDebugOverlay';
  dbg.style.cssText = 'position:fixed;left:4px;top:4px;z-index:999999;background:rgba(0,0,0,.8);color:#0f0;font-size:9px;font-family:monospace;padding:5px 7px;border-radius:5px;line-height:1.5;pointer-events:none;white-space:pre;max-width:94vw;';
  document.addEventListener('DOMContentLoaded', function(){ document.body.appendChild(dbg); });
  function updateDebugOverlay(){
    if (!dbg.parentNode) return;
    var vp = window.visualViewport;
    var nav = document.querySelector('.bottom-nav');
    var container = document.getElementById('appContainer');
    var chatModal = document.getElementById('chatModal');
    var inputBar = document.querySelector('.chat-input-bar');
    var lines = [];
    lines.push('innerH:' + window.innerHeight + ' vpH:' + (vp ? Math.round(vp.height) : '-') + ' gap:' + (vp ? Math.round(window.innerHeight - vp.height) : '-'));
    lines.push('body.keyboard-open: ' + document.body.classList.contains('keyboard-open'));
    lines.push('appContainer style.h:' + (container ? container.style.height : '-') + ' rect.h:' + (container ? Math.round(container.getBoundingClientRect().height) : '-'));
    lines.push('chatModal style.h:' + (chatModal ? chatModal.style.height : '-') + ' active:' + (chatModal ? chatModal.classList.contains('active') : '-'));
    if (inputBar){
      var ibRect = inputBar.getBoundingClientRect();
      lines.push('inputBar bottom:' + Math.round(ibRect.bottom) + ' (innerH=' + window.innerHeight + ')');
    }
    if (nav){
      var r = nav.getBoundingClientRect();
      var cs = getComputedStyle(nav);
      lines.push('nav rect top:' + Math.round(r.top) + ' h:' + Math.round(r.height) + ' bottom:' + Math.round(r.bottom));
      lines.push('nav display:' + cs.display + ' vis:' + cs.visibility + ' opac:' + cs.opacity + ' pe:' + cs.pointerEvents + ' z:' + cs.zIndex);
      lines.push('nav classList:' + nav.className);
    } else {
      lines.push('nav: 요소를 못찾음(null)');
    }
    dbg.textContent = lines.join('\\n');
  }
  setInterval(updateDebugOverlay, 300);
  window.addEventListener('resize', updateDebugOverlay);
  window.addEventListener('orientationchange', updateDebugOverlay);
  if (window.visualViewport) window.visualViewport.addEventListener('resize', updateDebugOverlay);
  document.addEventListener('DOMContentLoaded', updateDebugOverlay);
  window.addEventListener('load', updateDebugOverlay);
  // ===== 디버그 오버레이 끝 ====="""

count = content.count(old)
if count != 1:
    print(f"[오류] 패턴이 {count}개 발견됨(1개여야 함)")
else:
    content = content.replace(old, new, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[완료] 디버그 오버레이 추가됨")
