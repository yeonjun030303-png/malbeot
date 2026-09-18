path = 'ios\App\App.xcodeproj\project.pbxproj'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old = 'CURRENT_PROJECT_VERSION = 5;'
new = 'CURRENT_PROJECT_VERSION = 6;'
count = content.count(old)

if count == 0:
    print('[오류] 패턴을 찾을 수 없습니다.')
else:
    content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'[완료] CURRENT_PROJECT_VERSION 5 -> 6 로 변경됨 ({count}곳)')
