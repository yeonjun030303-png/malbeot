path = "public/index.html"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old1 = """  window.addEventListener('resize', setAppViewportHeight);
  window.addEventListener('orientationchange', setAppViewportHeight);
  if (window.visualViewport){
    window.visualViewport.addEventListener('resize', setAppViewportHeight);
    window.visualViewport.addEventListener('scroll', setAppViewportHeight);
  }"""

new1 = """  var vphRaf = null;
  function scheduleSetAppViewportHeight(){
    if (vphRaf) cancelAnimationFrame(vphRaf);
    vphRaf = requestAnimationFrame(function(){ vphRaf = null; setAppViewportHeight(); });
  }
  window.addEventListener('resize', scheduleSetAppViewportHeight);
  window.addEventListener('orientationchange', scheduleSetAppViewportHeight);
  if (window.visualViewport){
    window.visualViewport.addEventListener('resize', scheduleSetAppViewportHeight);
  }"""

c1 = content.count(old1)
if c1 == 0:
    print("[오류] 패턴1을 찾을 수 없습니다.")
else:
    content = content.replace(old1, new1)
    print(f"[완료] 패턴1 교체됨 ({c1}곳)")

old2 = """  function setAppViewportHeight(){
    var container = document.getElementById('appContainer');
    if(!container) return;
    var vp = window.visualViewport;
    var h = vp ? vp.height : window.innerHeight;
    var ratio = window.innerWidth >= 500 ? 0.92 : 1;
    container.style.height = Math.round(h * ratio) + 'px';
  }"""

new2 = """  function setAppViewportHeight(){
    var container = document.getElementById('appContainer');
    if(!container) return;
    var vp = window.visualViewport;
    var h = vp ? vp.height : window.innerHeight;
    var ratio = window.innerWidth >= 500 ? 0.92 : 1;
    var newHeight = Math.round(h * ratio);
    var prev = parseInt(container.style.height, 10) || 0;
    if (Math.abs(newHeight - prev) < 20) return;
    container.style.height = newHeight + 'px';
  }"""

c2 = content.count(old2)
if c2 == 0:
    print("[오류] 패턴2를 찾을 수 없습니다.")
else:
    content = content.replace(old2, new2)
    print(f"[완료] 패턴2 교체됨 ({c2}곳)")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
