path = "public/index.html"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

patches = []

# 1) 키보드 열려있을 때 safe-area 하단 여백을 무시하도록 CSS 클래스 추가
patches.append((
""".chat-input-bar{padding:10px 10px calc(10px + env(safe-area-inset-bottom)) 10px;background:#fff;display:flex;gap:8px;align-items:center;flex-shrink:0;}""",
""".chat-input-bar{padding:10px 10px calc(10px + env(safe-area-inset-bottom)) 10px;background:#fff;display:flex;gap:8px;align-items:center;flex-shrink:0;}
body.keyboard-open .chat-input-bar{padding-bottom:10px;}"""
))

# 2) visualViewport로 키보드 열림/닫힘을 감지해서 body에 keyboard-open 클래스 토글
patches.append((
"""  var vphRaf = null;
  function scheduleSetAppViewportHeight(){""",
"""  var lastKeyboardOpen = false;
  function updateKeyboardOpenState(){
    var vp = window.visualViewport;
    if (!vp) return;
    var gap = window.innerHeight - vp.height;
    var isOpen = gap > 100; // 키보드 뜨면 최소 100px 이상 줄어듦(홈인디케이터 34px보다 확실히 큰 값)
    if (isOpen !== lastKeyboardOpen){
      lastKeyboardOpen = isOpen;
      document.body.classList.toggle('keyboard-open', isOpen);
    }
  }
  var vphRaf = null;
  function scheduleSetAppViewportHeight(){"""
))

patches.append((
"""    if (!inGracePeriod && Math.abs(newHeight - prev) < 20) return;
    container.style.height = newHeight + 'px';
    ['chatModal','groupChatModal'].forEach(function(id){
      var el = document.getElementById(id);
      if (el) el.style.height = newHeight + 'px';
    });
  }""",
"""    if (!inGracePeriod && Math.abs(newHeight - prev) < 20){ updateKeyboardOpenState(); return; }
    container.style.height = newHeight + 'px';
    ['chatModal','groupChatModal'].forEach(function(id){
      var el = document.getElementById(id);
      if (el) el.style.height = newHeight + 'px';
    });
    updateKeyboardOpenState();
  }"""
))

results = []
for i, (old, new) in enumerate(patches, 1):
    count = content.count(old)
    if count != 1:
        results.append(f"[오류] 패치 {i}: 패턴이 {count}개 발견됨(1개여야 함) - 건너뜀")
        continue
    content = content.replace(old, new, 1)
    results.append(f"[완료] 패치 {i} 적용됨")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

for r in results:
    print(r)
