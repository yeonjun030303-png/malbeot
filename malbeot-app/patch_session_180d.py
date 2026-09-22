path = 'server.js'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
old = "const SESSION_MAX_AGE = '7d';"
new = "const SESSION_MAX_AGE = '180d';"
count = content.count(old)
if count == 0:
    print('[오류] 패턴을 찾을 수 없습니다.')
else:
    content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'[완료] SESSION_MAX_AGE 7d -> 180d 로 변경됨 ({count}곳)')
