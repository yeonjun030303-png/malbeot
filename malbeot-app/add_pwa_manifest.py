import re

# 1. public/manifest.json 생성
manifest_content = '''{
  "name": "말벗 - 실시간으로 마음을 나누는 소통 커뮤니티",
  "short_name": "말벗",
  "description": "실시간으로 마음을 나누는 소통 커뮤니티",
  "id": "/",
  "start_url": "/",
  "scope": "/",
  "display": "standalone",
  "orientation": "portrait",
  "background_color": "#ffffff",
  "theme_color": "#5c7cfa",
  "lang": "ko",
  "icons": [
    {
      "src": "/icon-192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/icon-512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/icon-512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "maskable"
    }
  ]
}
'''

with open('public/manifest.json', 'w', encoding='utf-8') as f:
    f.write(manifest_content)
print("✅ public/manifest.json 생성 완료")

# 2. index.html <head>에 manifest 연결 + theme-color 메타 추가
with open('public/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

if 'rel="manifest"' in html:
    print("⚠️ index.html에 manifest 링크가 이미 있어서 건너뜀")
else:
    marker = '<title>말벗 - 실시간으로 마음을 나누는 소통 커뮤니티</title>'
    if marker not in html:
        raise SystemExit("❌ index.html에서 <title> 태그를 못 찾음 - 수동 확인 필요")
    insert = marker + '\n<link rel="manifest" href="/manifest.json">\n<meta name="theme-color" content="#5c7cfa">\n<link rel="apple-touch-icon" href="/apple-touch-icon.png">'
    html = html.replace(marker, insert, 1)
    with open('public/index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("✅ index.html에 manifest 링크 + theme-color 추가 완료")

# 3. server.js: express.static이 .well-known 같은 dotfiles 폴더도 서빙하도록 옵션 추가
with open('server.js', 'r', encoding='utf-8') as f:
    server = f.read()

old = "app.use(express.static(path.join(__dirname, 'public')));"
new = "app.use(express.static(path.join(__dirname, 'public'), { dotfiles: 'allow' }));"

if old not in server:
    if new in server:
        print("⚠️ server.js에 dotfiles 옵션이 이미 있어서 건너뜀")
    else:
        raise SystemExit("❌ server.js에서 express.static 줄을 못 찾음 - 수동 확인 필요")
else:
    server = server.replace(old, new, 1)
    with open('server.js', 'w', encoding='utf-8') as f:
        f.write(server)
    print("✅ server.js에 dotfiles: 'allow' 옵션 추가 완료 (나중에 /.well-known/assetlinks.json 서빙용)")

print("\n모든 작업 완료. node -c server.js 로 문법 확인 후 git add/commit 하세요.")
