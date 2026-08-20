# -*- coding: utf-8 -*-

def patch_file(path, replacements):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    for old, new, label in replacements:
        count = content.count(old)
        if count == 1:
            content = content.replace(old, new)
            print(f"완료: {label}")
        elif count == 0:
            print(f"매치 0건(이미 적용되었거나 코드가 변경됨): {label}")
        else:
            print(f"매치 {count}건(고유하지 않음, 건너뜀): {label}")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

old = """let uiBackStack = [];
let uiPopping = false;
const uiOverlayObserver = new MutationObserver(muts=>{
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
      uiBackStack.splice(idx, 1);
      // 0-47: 프로그램이 스스로 닫을 때(closeModal 등)도 히스토리 동기화를 위해 history.back()을 호출하는데,
      // 이 back()이 나중에 popstate로 돌아왔을 때 "사용자가 진짜로 뒤로가기를 누른 것"으로 오인해서
      // 그 아래 화면까지 한 번 더 닫아버리던 게 진짜 원인이었음. uiPopping을 여기서 미리 true로 세팅해서
      // 그 되돌아온 popstate가 무시되도록 함(진짜 뒤로가기와 구분).
      if (!uiPopping){ uiPopping = true; try{ history.back(); }catch(e){} }
    }
  });
});
document.querySelectorAll('.full-screen-overlay, .modal-overlay').forEach(el=> uiOverlayObserver.observe(el, {attributes:true}));
window.addEventListener('popstate', ()=>{
  // 0-47: 위에서 프로그램이 스스로 유발한 back()으로 인한 popstate면(uiPopping===true) 여기선 아무것도 안 하고 소비만 함
  if (uiPopping){ uiPopping = false; return; }
  if (uiBackStack.length > 0){
    uiPopping = true;
    const el = uiBackStack[uiBackStack.length - 1];
    el.classList.remove('active');
    setTimeout(()=>{ uiPopping = false; }, 0);
  }
});"""

new = """let uiBackStack = [];
// 0-65: 기존엔 uiPopping이 참/거짓 플래그 하나였는데, 한 번의 클릭 처리 안에서 모달 2개가 동시에
// 닫히는 경우(예: 확인창을 닫으면서 그 아래 설정창도 같이 닫는 버튼) 첫 번째 닫힘만 플래그로 상쇄되고
// 두 번째 닫힘은 history.back()이 호출되지 않아 앱 내부 스택과 브라우저 히스토리 깊이가 어긋났음.
// 그 어긋남이 누적되면 이후 아무 모달에서나 "취소/뒤로가기"를 눌러도 여러 단계가 한꺼번에 닫히면서
// 결국 홈까지 밀려나가는 버그로 이어졌음(설정→차단/신고 취소 시 홈으로 나가지는 버그의 원인).
// 카운터 방식으로 바꿔서 동시에 몇 개가 닫히든 정확히 그 개수만큼만 상쇄되도록 함.
let expectedPopstates = 0;
const uiOverlayObserver = new MutationObserver(muts=>{
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
});
document.querySelectorAll('.full-screen-overlay, .modal-overlay').forEach(el=> uiOverlayObserver.observe(el, {attributes:true}));
window.addEventListener('popstate', ()=>{
  // 프로그램이 스스로 유발한 back()으로 인한 popstate는 개수만큼 소비만 하고 아무것도 하지 않음
  if (expectedPopstates > 0){ expectedPopstates--; return; }
  // 여기부터는 사용자가 진짜로 기기/브라우저 뒤로가기를 누른 경우
  if (uiBackStack.length > 0){
    const el = uiBackStack.pop(); // observer가 이 클래스 변경을 또 다른 닫힘으로 오인해 이중 처리하지 않도록 먼저 스택에서 제거
    el.classList.remove('active');
  }
});"""

patch_file('public/index.html', [(old, new, '뒤로가기 히스토리 스택 동시닫힘 경합 버그 수정(카운터 방식)')])
print("완료")
