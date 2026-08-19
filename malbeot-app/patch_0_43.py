import re

path = "server.js"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = """      // 대표사진뿐 아니라 추가 사진까지(최대 5장) 전부 검사
      if (data.photos && data.photos.length) {
        for (const photoData of data.photos) {
          if (!photoData) continue;
          const nsfwResult = await checkImageNsfw(photoData);
          if (nsfwResult.isNsfw) return cb({ success: false, message: '부적절한 사진이 포함되어 있어 변경할 수 없습니다.' });
        }
      }"""

new = """      // 0-43: 이미 검사를 통과한 기존 사진은 매번 재검사하지 않고, 새로 추가/변경된 사진만 검사함
      // (사진 5장 전부를 저장할 때마다 재검사하면 서버 메모리 부담이 커져 Render에서 502/재시작이 발생할 수 있었음)
      if (data.photos && data.photos.length) {
        const prevPhotos = user.photos || [];
        for (const photoData of data.photos) {
          if (!photoData) continue;
          if (prevPhotos.includes(photoData)) continue; // 기존에 이미 검사 통과한 사진은 스킵
          const nsfwResult = await checkImageNsfw(photoData);
          if (nsfwResult.isNsfw) return cb({ success: false, message: '부적절한 사진이 포함되어 있어 변경할 수 없습니다.' });
        }
      }"""

if old not in content:
    print("❌ 매치 실패 - old_str을 찾을 수 없습니다. server.js가 예상과 다른 상태일 수 있습니다.")
else:
    content = content.replace(old, new, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("✅ 0-43 패치 완료: 사진 재검사 최적화 적용됨")