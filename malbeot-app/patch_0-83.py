# -*- coding: utf-8 -*-
path = 'public/index.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

results = []

def do_replace(label, old, new, expected=1):
    global content
    count = content.count(old)
    if count != expected:
        results.append(f'[실패] {label}: 예상 {expected}건, 실제 {count}건 매칭 - 패치 건너뜀')
        return
    content = content.replace(old, new)
    results.append(f'[완료] {label}: {count}건 반영')

# ------------------------------------------------------------------
# 0-83-1: 채팅 입력창 엔터키(한글 조합 중 입력) 문제 수정
#   -> keydown 대신 keyup에서 처리 + isComposing 가드 추가
#   (한글 등 IME 조합 중에는 keydown 시점에 조합이 아직 안 끝나 있어
#    Enter를 눌러도 무시되거나 두 번 눌러야 전송되던 문제의 원인)
# ------------------------------------------------------------------
do_replace(
    '0-83-1 (msgComposeInput 엔터키)',
    "document.getElementById('msgComposeInput').addEventListener('keydown', (e)=>{\n"
    "  if (e.key === 'Enter' && !e.shiftKey){ e.preventDefault(); sendFirstMessage(); }\n"
    "});",
    "document.getElementById('msgComposeInput').addEventListener('keyup', (e)=>{\n"
    "  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing){ e.preventDefault(); sendFirstMessage(); }\n"
    "});"
)

do_replace(
    '0-83-2 (groupChatInputText 엔터키)',
    "document.getElementById('groupChatInputText').addEventListener('keydown', (e)=>{\n"
    "  if (e.key === 'Enter' && !e.shiftKey){ e.preventDefault(); document.getElementById('btnSendGroupMsg').click(); }\n"
    "});",
    "document.getElementById('groupChatInputText').addEventListener('keyup', (e)=>{\n"
    "  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing){ e.preventDefault(); document.getElementById('btnSendGroupMsg').click(); }\n"
    "});"
)

do_replace(
    '0-83-3 (chatInputText 엔터키)',
    "document.getElementById('chatInputText').addEventListener('keydown', (e)=>{\n"
    "  if (e.key === 'Enter' && !e.shiftKey){ e.preventDefault(); document.getElementById('btnSendMsg').click(); }\n"
    "});",
    "document.getElementById('chatInputText').addEventListener('keyup', (e)=>{\n"
    "  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing){ e.preventDefault(); document.getElementById('btnSendMsg').click(); }\n"
    "});"
)

# ------------------------------------------------------------------
# 0-84: 앱 최초 진입시 하단 네비/화면 하단이 잘리는 버그 수정
#   -> 콜드스타트 직후 2.5초간은 20px 미만 차이여도 무조건 높이 재적용,
#      load 이후 100/400/900/1800ms 뒤에도 재확인(iOS WKWebView가
#      visualViewport 값을 늦게 안정시키는 경우 대비)
# ------------------------------------------------------------------
do_replace(
    '0-84 (콜드스타트 뷰포트 높이 보정)',
    "(function(){\n"
    "  function setAppViewportHeight(){\n"
    "    var container = document.getElementById('appContainer');\n"
    "    if(!container) return;\n"
    "    var vp = window.visualViewport;\n"
    "    var h = vp ? vp.height : window.innerHeight;\n"
    "    var ratio = window.innerWidth >= 500 ? 0.92 : 1;\n"
    "    var newHeight = Math.round(h * ratio);\n"
    "    var prev = parseInt(container.style.height, 10) || 0;\n"
    "    if (Math.abs(newHeight - prev) < 20) return;\n"
    "    container.style.height = newHeight + 'px';\n"
    "  }\n"
    "\n"
    "  var vphRaf = null;\n"
    "  function scheduleSetAppViewportHeight(){\n"
    "    if (vphRaf) cancelAnimationFrame(vphRaf);\n"
    "    vphRaf = requestAnimationFrame(function(){ vphRaf = null; setAppViewportHeight(); });\n"
    "  }\n"
    "  window.addEventListener('resize', scheduleSetAppViewportHeight);\n"
    "  window.addEventListener('orientationchange', scheduleSetAppViewportHeight);\n"
    "  if (window.visualViewport){\n"
    "    window.visualViewport.addEventListener('resize', scheduleSetAppViewportHeight);\n"
    "  }\n"
    "  document.addEventListener('DOMContentLoaded', setAppViewportHeight);\n"
    "  window.addEventListener('load', setAppViewportHeight);\n",

    "(function(){\n"
    "  var coldStartGraceUntil = Date.now() + 2500; // 콜드스타트 직후 2.5초간은 값이 안 안정된 상태이므로 무조건 재적용\n"
    "  function setAppViewportHeight(){\n"
    "    var container = document.getElementById('appContainer');\n"
    "    if(!container) return;\n"
    "    var vp = window.visualViewport;\n"
    "    var h = vp ? vp.height : window.innerHeight;\n"
    "    var ratio = window.innerWidth >= 500 ? 0.92 : 1;\n"
    "    var newHeight = Math.round(h * ratio);\n"
    "    var prev = parseInt(container.style.height, 10) || 0;\n"
    "    var inGracePeriod = !prev || Date.now() < coldStartGraceUntil;\n"
    "    if (!inGracePeriod && Math.abs(newHeight - prev) < 20) return;\n"
    "    container.style.height = newHeight + 'px';\n"
    "  }\n"
    "\n"
    "  var vphRaf = null;\n"
    "  function scheduleSetAppViewportHeight(){\n"
    "    if (vphRaf) cancelAnimationFrame(vphRaf);\n"
    "    vphRaf = requestAnimationFrame(function(){ vphRaf = null; setAppViewportHeight(); });\n"
    "  }\n"
    "  window.addEventListener('resize', scheduleSetAppViewportHeight);\n"
    "  window.addEventListener('orientationchange', scheduleSetAppViewportHeight);\n"
    "  if (window.visualViewport){\n"
    "    window.visualViewport.addEventListener('resize', scheduleSetAppViewportHeight);\n"
    "  }\n"
    "  document.addEventListener('DOMContentLoaded', setAppViewportHeight);\n"
    "  window.addEventListener('load', function(){\n"
    "    setAppViewportHeight();\n"
    "    // iOS WKWebView는 콜드스타트 직후 visualViewport 값이 곧바로 안정화되지 않아\n"
    "    // 첫 측정이 부정확할 수 있음(하단 네비가 화면 밖으로 밀려 안 보이던 원인) -> 잠깐 몇 번 더 재확인\n"
    "    [100, 400, 900, 1800].forEach(function(delay){ setTimeout(setAppViewportHeight, delay); });\n"
    "  });\n"
)

# ------------------------------------------------------------------
# 0-85: 카카오 로그인 세션을 sessionStorage -> localStorage로 전환
#   -> 지금까지는 앱을 완전히 종료했다 재실행하면(iOS가 프로세스를 정리하며
#      WKWebView의 sessionStorage가 날아감) 세션이 사라져 매번 카카오
#      로그인을 다시 눌러야 했음. localStorage는 앱 삭제/로그아웃/탈퇴
#      전까지 유지되므로 이 문제가 근본적으로 해결됨.
# ------------------------------------------------------------------
do_replace(
    '0-85-1 (currentUser 저장소)',
    "let currentUser = JSON.parse(sessionStorage.getItem('malbeot_session')) || null;",
    "let currentUser = JSON.parse(localStorage.getItem('malbeot_session')) || null;"
)

do_replace(
    '0-85-2 (sessionToken 저장소)',
    "let sessionToken = sessionStorage.getItem('malbeot_token') || null;",
    "let sessionToken = localStorage.getItem('malbeot_token') || null;"
)

do_replace(
    '0-85-3 (saveSession)',
    "function saveSession(token){\n"
    "  if (token) { sessionToken = token; sessionStorage.setItem('malbeot_token', token); }\n"
    "  sessionStorage.setItem('malbeot_session', JSON.stringify(currentUser));\n"
    "}",
    "function saveSession(token){\n"
    "  if (token) { sessionToken = token; localStorage.setItem('malbeot_token', token); }\n"
    "  localStorage.setItem('malbeot_session', JSON.stringify(currentUser));\n"
    "}"
)

do_replace(
    '0-85-4 (clearSession)',
    "function clearSession(){\n"
    "  currentUser = null; sessionToken = null;\n"
    "  sessionStorage.removeItem('malbeot_session');\n"
    "  sessionStorage.removeItem('malbeot_token');\n"
    "}",
    "function clearSession(){\n"
    "  currentUser = null; sessionToken = null;\n"
    "  localStorage.removeItem('malbeot_session');\n"
    "  localStorage.removeItem('malbeot_token');\n"
    "}"
)

# ------------------------------------------------------------------
# 0-86: 스플래시(로딩) 화면 개선
#   - 안내 멘트 + 우측으로 이동하는 점 애니메이션 추가
#   - 저장된 세션이 있으면 자동로그인 결과가 나올 때까지 스플래시를
#     유지했다가 곧바로 앱으로 진입(로그인화면이 잠깐 스쳐 보이는 현상 방지)
# ------------------------------------------------------------------
do_replace(
    '0-86-1 (스플래시 CSS)',
    "#splashScreen .splash-sub{font-size:12px;color:var(--text-muted);margin-top:8px;text-align:center;}\n",
    "#splashScreen .splash-sub{font-size:12px;color:var(--text-muted);margin-top:8px;text-align:center;}\n"
    "#splashScreen .splash-status{font-size:12px;color:var(--text-muted);margin-top:14px;text-align:center;min-height:16px;}\n"
    "#splashScreen .splash-dots{position:relative;width:64px;height:10px;margin:10px auto 0 auto;overflow:hidden;}\n"
    "#splashScreen .splash-dots span{position:absolute;top:1px;left:0;width:8px;height:8px;border-radius:50%;background:var(--primary);opacity:0;animation:splashDotMove 1.3s ease-in-out infinite;}\n"
    "#splashScreen .splash-dots span:nth-child(2){animation-delay:.22s;}\n"
    "#splashScreen .splash-dots span:nth-child(3){animation-delay:.44s;}\n"
    "@keyframes splashDotMove{0%{left:0;opacity:0;}18%{opacity:1;}82%{opacity:1;}100%{left:56px;opacity:0;}}\n"
)

do_replace(
    '0-86-2 (스플래시 HTML)',
    '    <div class="splash-logo">말벗</div>\n'
    '    <div class="splash-sub">지금 이 순간, 실시간으로 이어지는 편안한 대화</div>\n'
    '  </div>\n'
    '</div>',
    '    <div class="splash-logo">말벗</div>\n'
    '    <div class="splash-sub">지금 이 순간, 실시간으로 이어지는 편안한 대화</div>\n'
    '    <div class="splash-dots"><span></span><span></span><span></span></div>\n'
    '    <div class="splash-status" id="splashStatusText">대화상대를 준비하고 있어요...</div>\n'
    '  </div>\n'
    '</div>'
)

do_replace(
    '0-86-3 (스플래시 유지/전환 로직)',
    "window.addEventListener('load', ()=>{\n"
    "  setTimeout(()=>{\n"
    "    const splash = document.getElementById('splashScreen');\n"
    "    splash.classList.add('fade-out');\n"
    "    setTimeout(()=>splash.remove(), 450);\n"
    "  }, 900);\n"
    "});",

    "/* 스플래시(로딩) 화면: 저장된 세션이 있으면 자동로그인 결과가 나올 때까지 유지했다가\n"
    "   바로 앱으로 진입시킴(로그인 화면이 잠깐 스쳐 보이고 다시 앱으로 넘어가는 깜빡임 방지) */\n"
    "let splashHidden = false;\n"
    "function hideSplash(){\n"
    "  if (splashHidden) return;\n"
    "  splashHidden = true;\n"
    "  const splash = document.getElementById('splashScreen');\n"
    "  if (!splash) return;\n"
    "  splash.classList.add('fade-out');\n"
    "  setTimeout(()=>splash.remove(), 450);\n"
    "}\n"
    "(function(){\n"
    "  const msgs = ['대화상대를 준비하고 있어요...', '말벗에 접속하는 중이에요...', '조금만 기다려주세요...'];\n"
    "  let i = 0;\n"
    "  const timer = setInterval(()=>{\n"
    "    if (splashHidden) { clearInterval(timer); return; }\n"
    "    const el = document.getElementById('splashStatusText');\n"
    "    if (!el) { clearInterval(timer); return; }\n"
    "    i = (i + 1) % msgs.length;\n"
    "    el.textContent = msgs[i];\n"
    "  }, 1400);\n"
    "})();\n"
    "window.addEventListener('load', ()=>{\n"
    "  const hasSavedSession = !!(currentUser && sessionToken);\n"
    "  if (!hasSavedSession){\n"
    "    // 저장된 세션이 없는 최초 방문 -> 브랜드만 잠깐 보여주고 바로 로그인 화면 노출\n"
    "    setTimeout(hideSplash, 700);\n"
    "  } else {\n"
    "    // 자동로그인 시도 결과는 attemptSessionResume()의 각 분기에서 hideSplash()를 호출함.\n"
    "    // 네트워크 문제 등으로 결과가 끝내 안 오는 경우를 대비한 최대 대기시간(안전장치)\n"
    "    setTimeout(hideSplash, 6000);\n"
    "  }\n"
    "});"
)

# ------------------------------------------------------------------
# 0-86-4: attemptSessionResume() 각 분기에서 hideSplash() 호출 추가
# ------------------------------------------------------------------
do_replace(
    '0-86-4 (세션복구 성공시 스플래시 해제)',
    "      currentUser = res.user; saveSession(res.token);\n"
    "      closeModal('landingScreen'); closeModal('authModal');\n"
    "      initApp();\n",
    "      currentUser = res.user; saveSession(res.token);\n"
    "      closeModal('landingScreen'); closeModal('authModal');\n"
    "      initApp();\n"
    "      hideSplash();\n"
)

do_replace(
    '0-86-5 (세션 만료/정지시 스플래시 해제)',
    "      sessionResumeRetryCount = 0;\n"
    "      clearSession();\n"
    "      resetToLandingScreen();\n"
    "      if (res.banned) showWarningModal(res.message || '이용이 제한된 계정입니다.');",
    "      sessionResumeRetryCount = 0;\n"
    "      clearSession();\n"
    "      resetToLandingScreen();\n"
    "      hideSplash();\n"
    "      if (res.banned) showWarningModal(res.message || '이용이 제한된 계정입니다.');"
)

do_replace(
    '0-86-6 (재시도 소진시 스플래시 해제)',
    "      } else {\n"
    "        sessionResumeRetryCount = 0;\n"
    "        clearSession();\n"
    "        resetToLandingScreen();\n"
    "      }\n"
    "    }\n"
    "  });\n"
    "}\n"
    "socket.on('connect', ()=>{",
    "      } else {\n"
    "        sessionResumeRetryCount = 0;\n"
    "        clearSession();\n"
    "        resetToLandingScreen();\n"
    "        hideSplash();\n"
    "      }\n"
    "    }\n"
    "  });\n"
    "}\n"
    "socket.on('connect', ()=>{"
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print('\n'.join(results))