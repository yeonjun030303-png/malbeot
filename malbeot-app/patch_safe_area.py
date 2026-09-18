import re

path = r'public\index.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

replacements = [
    (
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">'
    ),
    (
        '.chat-header-row{height:56px;flex-shrink:0;display:flex;align-items:center;padding:0 10px;border-bottom:1px solid #d8e6f2;gap:8px;}',
        '.chat-header-row{min-height:56px;flex-shrink:0;display:flex;align-items:center;padding:env(safe-area-inset-top) 10px 0 10px;border-bottom:1px solid #d8e6f2;gap:8px;}'
    ),
    (
        '.chat-input-bar{padding:10px;background:#fff;display:flex;gap:8px;align-items:center;flex-shrink:0;}',
        '.chat-input-bar{padding:10px 10px calc(10px + env(safe-area-inset-bottom)) 10px;background:#fff;display:flex;gap:8px;align-items:center;flex-shrink:0;}'
    ),
]

applied = 0
missing = []
for old, new in replacements:
    count = content.count(old)
    if count == 1:
        content = content.replace(old, new)
        applied += 1
    elif count == 0:
        missing.append(old[:60] + '...')
    else:
        print(f'[경고] 패턴이 {count}번 발견됨(1번이어야 함), 건너뜀: {old[:60]}...')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f'[완료] {applied}/{len(replacements)}개 패치 적용됨')
if missing:
    print('[누락된 패턴]')
    for m in missing:
        print(' -', m)
