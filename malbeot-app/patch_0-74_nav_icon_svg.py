import re

path = "public/index.html"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1) CSS: .nav-item 바로 뒤에 .nav-icon-svg 크기 규칙 추가
old_css = ".nav-item{background:none;border:none;flex:1;height:100%;display:flex;align-items:center;justify-content:center;color:var(--text-muted);cursor:pointer;font-size:21px;}"
new_css = old_css + "\n.nav-icon-svg{width:22px;height:22px;display:block;}"

count_css = content.count(old_css)
if count_css != 1:
    raise SystemExit(f"[실패] .nav-item CSS 매치 {count_css}개 (1개여야 함) - 파일이 이전과 달라졌는지 확인 필요")
content = content.replace(old_css, new_css, 1)

# 2) 하단 네비 마크업: Font Awesome <i> 아이콘 4개를 인라인 SVG로 교체
old_nav = '''  <nav class="bottom-nav">
    <button class="nav-item active" data-tab="tab-home"><i class="fa-solid fa-house"></i></button>
    <button class="nav-item" data-tab="tab-community"><i class="fa-solid fa-newspaper"></i></button>
    <button class="nav-item" data-tab="tab-chat"><i class="fa-solid fa-comment-dots"></i></button>
    <button class="nav-item" data-tab="tab-mypage"><i class="fa-solid fa-gear"></i></button>
  </nav>'''

new_nav = '''  <nav class="bottom-nav">
    <button class="nav-item active" data-tab="tab-home"><svg class="nav-icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 11l9-8 9 8"/><path d="M5 10v10h14V10"/><path d="M9 20v-6h6v6"/></svg></button>
    <button class="nav-item" data-tab="tab-community"><svg class="nav-icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="14" rx="2"/><line x1="7" y1="9" x2="17" y2="9"/><line x1="7" y1="13" x2="17" y2="13"/><line x1="7" y1="17" x2="13" y2="17"/></svg></button>
    <button class="nav-item" data-tab="tab-chat"><svg class="nav-icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/><circle cx="8" cy="12" r="1" fill="currentColor" stroke="none"/><circle cx="12" cy="12" r="1" fill="currentColor" stroke="none"/><circle cx="16" cy="12" r="1" fill="currentColor" stroke="none"/></svg></button>
    <button class="nav-item" data-tab="tab-mypage"><svg class="nav-icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1"/></svg></button>
  </nav>'''

count_nav = content.count(old_nav)
if count_nav != 1:
    raise SystemExit(f"[실패] bottom-nav 마크업 매치 {count_nav}개 (1개여야 함) - 파일이 이전과 달라졌는지 확인 필요")
content = content.replace(old_nav, new_nav, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("[완료] 하단 네비 아이콘 4개를 Font Awesome 폰트 -> 인라인 SVG로 교체함 (CSS 규칙 1개, 마크업 1블록 수정)")
print("       Font Awesome CDN 링크 자체는 다른 화면에서 계속 쓰일 수 있어 그대로 남겨둠")
