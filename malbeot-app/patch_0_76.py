# -*- coding: utf-8 -*-
# 0-76: showMiniAlert 공용 함수 - 버튼 3개 이상(메뉴류)일 때만 카카오톡처럼 화면 하단 고정 시트로 표시
#       (버튼 2개 이하의 단순 확인/취소 창은 기존처럼 화면 중앙 유지)
import os, sys

path = os.path.join(os.getcwd(), "public", "index.html")
if not os.path.exists(path):
    print("!! public/index.html 을 못 찾았습니다. C:\\malbeot\\malbeot-app 에서 실행해주세요.")
    sys.exit(1)

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

orig_len = len(content)
edits_applied = []

def apply_edit(name, old, new, content, expect=1):
    cnt = content.count(old)
    if cnt != expect:
        print(f"!! [{name}] 매칭 개수가 예상({expect})과 다릅니다(찾은 개수: {cnt}). 패치를 중단합니다.")
        return content, False
    content = content.replace(old, new)
    edits_applied.append(name)
    return content, True

old_a = '''function showMiniAlert(text, buttons){
  document.getElementById('miniAlertText').textContent = text;
  const wrap = document.getElementById('miniAlertButtons'); wrap.innerHTML = '';
  buttons.forEach(b=>{
    const btn = document.createElement('button');
    btn.className = 'btn ' + (b.primary ? 'btn-primary' : 'btn-secondary');
    btn.style.flex = '1'; btn.textContent = b.label;
    if (b.danger){
      // 톤온톤 경고색: 배경은 danger색의 옅은 버전, 글자는 danger색 그대로
      btn.style.background = 'color-mix(in srgb, var(--danger) 15%, #fff)';
      btn.style.color = 'var(--danger)';
      btn.style.border = 'none';
      btn.style.fontWeight = '700';
    }
    btn.onclick = () => { closeModal('miniAlertModal'); if (b.onClick) b.onClick(); };
    wrap.appendChild(btn);
  });
  openModal('miniAlertModal');
}'''
new_a = '''function showMiniAlert(text, buttons){
  document.getElementById('miniAlertText').textContent = text;
  const wrap = document.getElementById('miniAlertButtons'); wrap.innerHTML = '';
  const overlay = document.getElementById('miniAlertModal');
  const card = overlay.querySelector('.mini-alert-card');
  const isMenu = buttons.length >= 3;
  overlay.style.alignItems = isMenu ? 'flex-end' : '';
  overlay.style.padding = isMenu ? '0' : '';
  if (card){
    card.style.width = isMenu ? '100%' : '';
    card.style.maxWidth = isMenu ? '480px' : '';
    card.style.margin = isMenu ? '0 auto' : '';
    card.style.borderRadius = isMenu ? '16px 16px 0 0' : '';
    card.style.paddingBottom = isMenu ? 'calc(20px + env(safe-area-inset-bottom))' : '';
  }
  wrap.style.flexDirection = isMenu ? 'column' : 'row';
  buttons.forEach(b=>{
    const btn = document.createElement('button');
    btn.className = 'btn ' + (b.primary ? 'btn-primary' : 'btn-secondary');
    btn.style.flex = isMenu ? 'none' : '1';
    if (isMenu) btn.style.width = '100%';
    btn.textContent = b.label;
    if (b.danger){
      // 톤온톤 경고색: 배경은 danger색의 옅은 버전, 글자는 danger색 그대로
      btn.style.background = 'color-mix(in srgb, var(--danger) 15%, #fff)';
      btn.style.color = 'var(--danger)';
      btn.style.border = 'none';
      btn.style.fontWeight = '700';
    }
    btn.onclick = () => { closeModal('miniAlertModal'); if (b.onClick) b.onClick(); };
    wrap.appendChild(btn);
  });
  openModal('miniAlertModal');
}'''
content, ok = apply_edit("A-미니알림하단시트분기", old_a, new_a, content)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"완료: {len(edits_applied)}/1 항목 적용됨 -> {edits_applied}")
print(f"파일 크기 변화: {orig_len} -> {len(content)} bytes")
if len(edits_applied) < 1:
    print("!! 적용 실패. 커밋/푸시하지 마세요.")
    sys.exit(1)