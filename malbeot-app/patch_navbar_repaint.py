path = "public/index.html"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = """    if (!inGracePeriod && Math.abs(newHeight - prev) < 20){ updateKeyboardOpenState(); return; }
    container.style.height = newHeight + 'px';
    ['chatModal','groupChatModal'].forEach(function(id){
      var el = document.getElementById(id);
      if (el) el.style.height = newHeight + 'px';
    });
    updateKeyboardOpenState();
  }"""

new = """    if (!inGracePeriod && Math.abs(newHeight - prev) < 20){ updateKeyboardOpenState(); return; }
    container.style.height = newHeight + 'px';
    ['chatModal','groupChatModal'].forEach(function(id){
      var el = document.getElementById(id);
      if (el) el.style.height = newHeight + 'px';
    });
    updateKeyboardOpenState();
    // iOS WKWebView가 콜드스타트 직후 컨테이너 높이 변경 후에도 position:absolute로
    // 하단 고정된 네비게이션 바를 다시 그리지 않아(리페인트 안됨) 보이지도 않고
    // 클릭도 안 먹는 버그가 있었음(프로필 화면 열었다 닫으면 그 과정에서 우연히 정상화되던 원인).
    // 매번 강제로 display를 토글해서 리페인트를 유도함.
    var navEl = container.querySelector('.bottom-nav');
    if (navEl){
      navEl.style.display = 'none';
      void navEl.offsetHeight;
      navEl.style.display = '';
    }
  }"""

count = content.count(old)
if count != 1:
    print(f"[오류] 패턴이 {count}개 발견됨(1개여야 함)")
else:
    content = content.replace(old, new, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[완료] 하단 네비 강제 리페인트 로직 추가됨")
