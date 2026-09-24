# -*- coding: utf-8 -*-
# 0-88: 1) 사진편집 블러 -> 진짜 모자이크(픽셀화) 방식으로 교체 (구형 iOS WebView에서 ctx.filter blur가
#          아예 무시되어 "블러 안됨"으로 보이던 문제 근본 해결, 브라우저/iOS버전 상관없이 무조건 작동)
#       2) @capacitor/keyboard 네이티브 플러그인으로 키보드 높이를 정확히 받아 채팅 입력창을
#          정확히 그 높이만큼 띄우도록 변경 (기존 visualViewport 추정 방식이 iOS WKWebView에서
#          타이밍이 안 맞아 반복적으로 재발하던 키보드-전송버튼 간격 벌어짐 버그 근본 해결 시도)

import io, json, re

# ---------- 1) capacitor.config.json: Keyboard 플러그인 resize:none 추가 ----------
cap_path = "capacitor.config.json"
with io.open(cap_path, "r", encoding="utf-8-sig") as f:
    cap = json.load(f)
cap.setdefault("plugins", {})
cap["plugins"]["Keyboard"] = {"resize": "none"}
with io.open(cap_path, "w", encoding="utf-8", newline="\n") as f:
    json.dump(cap, f, ensure_ascii=False, indent=2)
    f.write("\n")
print("[적용됨] capacitor.config.json :: plugins.Keyboard.resize = none 추가")

# ---------- 2) public/index.html 수정 ----------
html_path = "public/index.html"
with io.open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

# 2-1) 블러 -> 모자이크(픽셀화) 방식으로 교체
old_blur = """  if (peStrokes.some(s=>s.tool==='blur') && !peBlurCanvas){
    peBlurCanvas = document.createElement('canvas');
    peBlurCanvas.width = peCanvas.width; peBlurCanvas.height = peCanvas.height;
    const bctx = peBlurCanvas.getContext('2d');
    bctx.filter = 'blur(28px)';
    bctx.drawImage(peOrigImg, 0, 0, peCanvas.width, peCanvas.height);
  }"""
new_blur = """  if (peStrokes.some(s=>s.tool==='blur') && !peBlurCanvas){
    // 0-88: ctx.filter='blur()' 방식은 구형 iOS WKWebView에서 지원이 안 돼 조용히 무시되고
    // 아무 효과도 안 나던 문제가 있었음 -> 필터 API에 의존하지 않는 순수 픽셀화(모자이크) 방식으로 교체.
    // 원본을 작게 축소했다가 다시 확대(스무딩 끔)하면 어느 환경에서도 확실하게 모자이크 효과가 남.
    peBlurCanvas = document.createElement('canvas');
    peBlurCanvas.width = peCanvas.width; peBlurCanvas.height = peCanvas.height;
    const bctx = peBlurCanvas.getContext('2d');
    const pixelSize = Math.max(10, Math.round(Math.min(peCanvas.width, peCanvas.height) / 24));
    const smallW = Math.max(1, Math.round(peCanvas.width / pixelSize));
    const smallH = Math.max(1, Math.round(peCanvas.height / pixelSize));
    const tmp = document.createElement('canvas');
    tmp.width = smallW; tmp.height = smallH;
    const tctx = tmp.getContext('2d');
    tctx.drawImage(peOrigImg, 0, 0, smallW, smallH);
    bctx.imageSmoothingEnabled = false;
    bctx.drawImage(tmp, 0, 0, smallW, smallH, 0, 0, peCanvas.width, peCanvas.height);
  }"""
if old_blur not in html:
    raise SystemExit("[실패] 블러 코드 매칭 실패 - 파일이 예상과 다름. 수정 없이 중단.")
html = html.replace(old_blur, new_blur, 1)
print("[적용됨] public/index.html :: 블러 -> 모자이크 방식 교체")

# 2-2) @capacitor/keyboard 리스너 추가 (기존 뷰포트 안정화 IIFE 끝부분에 이어붙임)
old_anchor = """  document.addEventListener('visibilitychange', function(){
    if (!document.hidden) resetPinchZoom();
  });
  window.addEventListener('pageshow', resetPinchZoom);
})();
</script>"""
new_anchor = """  document.addEventListener('visibilitychange', function(){
    if (!document.hidden) resetPinchZoom();
  });
  window.addEventListener('pageshow', resetPinchZoom);

  // 0-88: @capacitor/keyboard 네이티브 플러그인 - 기존 visualViewport 추정 방식은
  // iOS WKWebView에서 키보드 애니메이션과 타이밍이 안 맞아 "키보드 누르는 순간 잠깐/계속
  // 간격이 벌어지는" 문제가 반복됐음. 네이티브가 직접 주는 정확한 키보드 높이(px)로
  // 컨테이너 높이를 맞춰서 추정 오차를 없앰.
  function applyKeyboardHeight(kbHeight){
    var container = document.getElementById('appContainer');
    if (!container) return;
    var ratio = window.innerWidth >= 500 ? 0.92 : 1;
    var full = window.innerHeight * ratio;
    var newHeight = Math.round(kbHeight > 0 ? (full - kbHeight) : full);
    container.style.height = newHeight + 'px';
    ['chatModal','groupChatModal'].forEach(function(id){
      var el = document.getElementById(id);
      if (el) el.style.height = newHeight + 'px';
    });
    document.body.classList.toggle('keyboard-open', kbHeight > 0);
    var navEl = container.querySelector('.bottom-nav');
    if (navEl){ navEl.style.display = 'none'; void navEl.offsetHeight; navEl.style.display = ''; }
  }
  if (window.Capacitor && window.Capacitor.isNativePlatform && window.Capacitor.isNativePlatform() &&
      window.Capacitor.Plugins && window.Capacitor.Plugins.Keyboard){
    var MalbeotKeyboard = window.Capacitor.Plugins.Keyboard;
    MalbeotKeyboard.addListener('keyboardWillShow', function(info){ applyKeyboardHeight((info && info.keyboardHeight) || 0); });
    MalbeotKeyboard.addListener('keyboardDidShow', function(info){ applyKeyboardHeight((info && info.keyboardHeight) || 0); });
    MalbeotKeyboard.addListener('keyboardWillHide', function(){ applyKeyboardHeight(0); });
    MalbeotKeyboard.addListener('keyboardDidHide', function(){ applyKeyboardHeight(0); });
  }
})();
</script>"""
if old_anchor not in html:
    raise SystemExit("[실패] 키보드 리스너 삽입 위치 매칭 실패 - 파일이 예상과 다름. 수정 없이 중단.")
html = html.replace(old_anchor, new_anchor, 1)
print("[적용됨] public/index.html :: @capacitor/keyboard 리스너 추가")

with io.open(html_path, "w", encoding="utf-8", newline="\n") as f:
    f.write(html)

print("0-88 패치 완료.")

# ---------- 3) 0-89: 빌드번호 11 -> 12 (새 네이티브 플러그인 반영을 위한 새 빌드 준비) ----------
pbx_path = "ios/App/App.xcodeproj/project.pbxproj"
with io.open(pbx_path, "r", encoding="utf-8") as f:
    pbx = f.read()
before = pbx.count("CURRENT_PROJECT_VERSION = 11;")
pbx = pbx.replace("CURRENT_PROJECT_VERSION = 11;", "CURRENT_PROJECT_VERSION = 12;")
with io.open(pbx_path, "w", encoding="utf-8", newline="\n") as f:
    f.write(pbx)
print(f"[적용됨] 0-89 :: 빌드번호 11 -> 12 ({before}곳 교체, 2곳이어야 정상)")