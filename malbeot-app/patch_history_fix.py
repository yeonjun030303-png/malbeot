path = "public\index.html"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = """const uiOverlayObserver = new MutationObserver(muts=>{
  muts.forEach(m=>{
    if (m.attributeName !== 'class') return;
    const el = m.target;
    if (!(el.classList.contains('full-screen-overlay') || el.classList.contains('modal-overlay'))) return;
    const isActive = el.classList.contains('active');
    const idx = uiBackStack.indexOf(el);
    if (isActive && idx === -1){
      uiBackStack.push(el);
      history.pushState({ uiOverlay: uiBackStack.length }, '');
    } else if (!isActive && idx !== -1){
      // 프로그램(closeModal 등)이 스스로 닫은 경우에만 여기로 들어옴. 실제 뒤로가기(popstate)로 닫힌
      // 경우엔 아래 popstate 핸들러가 스택에서 먼저 빼놓기 때문에 idx가 이미 -1이라 이 분기를 타지 않음.
      uiBackStack.splice(idx, 1);
      expectedPopstates++;
      try{ history.back(); }catch(e){ expectedPopstates--; }
    }
  });
});"""

new = """const uiOverlayObserver = new MutationObserver(muts=>{
  // 0-68: 같은 동기 실행 흐름 안에서 모달이 "닫히면서 동시에 다른 모달이 열리는" 경우
  // (예: 신고 사유 모달을 닫고 곧바로 완료 알림을 여는 confirmSubmitReport())
  // 기존 코드는 mutation을 하나씩 즉시 처리해서 history.back()(비동기)과 history.pushState()(동기)가
  // 뒤섞여 히스토리 깊이가 어긋났고, 그 어긋남이 누적되어 이후 아무 화면에서나 뒤로가기 1번에 여러 단계가
  // 한꺼번에 닫히며 landingScreen까지 노출되는 버그로 이어졌음.
  // → 배치 안의 모든 변화를 먼저 집계해서 "순변화(net)"만 반영. 닫힘+열림이 같은 배치에 섞여 순변화가 0이면
  //   history를 아예 건드리지 않음(상쇄) - back()과 pushState()가 뒤섞이는 상황 자체를 없앰.
  let opened = [];
  let closedCount = 0;
  muts.forEach(m=>{
    if (m.attributeName !== 'class') return;
    const el = m.target;
    if (!(el.classList.contains('full-screen-overlay') || el.classList.contains('modal-overlay'))) return;
    const isActive = el.classList.contains('active');
    const idx = uiBackStack.indexOf(el);
    if (isActive && idx === -1){
      opened.push(el);
    } else if (!isActive && idx !== -1){
      uiBackStack.splice(idx, 1);
      closedCount++;
    }
  });
  const net = opened.length - closedCount;
  if (net > 0){
    opened.forEach(el=>{
      uiBackStack.push(el);
      history.pushState({ uiOverlay: uiBackStack.length }, '');
    });
  } else if (net < 0){
    for (let i=0; i<-net; i++){
      expectedPopstates++;
      try{ history.back(); }catch(e){ expectedPopstates--; }
    }
    opened.forEach(el=> uiBackStack.push(el));
  } else {
    // 순변화 0: 히스토리 그대로 두고 스택 배열만 정리
    opened.forEach(el=> uiBackStack.push(el));
  }
});"""

count = content.count(old)
if count == 0:
    print("[오류] 패턴을 찾을 수 없습니다.")
elif count > 1:
    print(f"[경고] {count}번 발견됨(1번이어야 함), 건너뜀")
else:
    content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[완료] 모달 배치 처리 시 히스토리 순변화만 반영하도록 수정됨")
