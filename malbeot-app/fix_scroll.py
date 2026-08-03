import re

with open('public/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

replacements = []

old1 = ".user-cards-grid{display:flex;flex-direction:column;max-height:calc(7 * 68px);overflow-y:auto;}"
new1 = ".user-cards-grid{display:flex;flex-direction:column;}"
replacements.append((old1, new1, 'user-cards-grid'))

old2 = ".profile-posts-scroll{max-height:calc(3 * 74px);overflow-y:auto;}"
new2 = ".profile-posts-scroll{}"
replacements.append((old2, new2, 'profile-posts-scroll'))

old3 = "  c.style.maxHeight = 'calc(7 * 66px)'; c.style.overflowY='auto';"
new3 = "  // 자체 스크롤 제거: 바깥 .content-area 스크롤만 사용"
replacements.append((old3, new3, 'chatRoomList JS'))

for old, new, label in replacements:
    count = content.count(old)
    if count != 1:
        print(f'[경고] {label}: 매치 {count}개 (1개여야 정상) - 수동 확인 필요')
        continue
    content = content.replace(old, new)
    print(f'[완료] {label}')

with open('public/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('저장 완료')