#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
0-53 패치: 0-51 이전에 탈퇴 처리된 유저들의 흔적(팔로우/팔로워/프로필좋아요)이
다른 유저들의 배열에 그대로 남아있어서 "프로필 카드에 보이는 숫자"와
"실제 목록 모달에 뜨는 인원수"가 어긋나는 버그가 있었음(예: 팔로잉 4명인데
목록엔 2명만 뜨는 문제). 0-51은 "앞으로의 탈퇴"만 정리하므로, 이미 남아있는
과거 잔여참조는 그대로였음.

이번 패치는 서버 시작 시 1회만 전체 유저를 스캔해서 존재하지 않는 유저ID를
followingIds/followerIds/profileLikedBy에서 제거하고, meta/staleFollowCleanupDone
플래그를 세워서 이후 재시작부터는 다시 스캔하지 않도록 함(계속 남겨둬도 안전).

실행 위치: 반드시 저장소 루트(C:\\malbeot)에서 실행할 것.
대상 파일: malbeot-app/server.js
"""
import pathlib, sys

TARGET = pathlib.Path("malbeot-app/server.js")

def main():
    if not TARGET.exists():
        print(f"❌ 파일을 찾을 수 없습니다: {TARGET.resolve()}")
        print("   → 반드시 저장소 루트(C:\\malbeot)에서 실행하세요. (지금 위치: %s)" % pathlib.Path.cwd())
        sys.exit(1)

    text = TARGET.read_text(encoding="utf-8")
    original_len = len(text)

    old = '''const PORT = process.env.PORT || 8080;
server.listen(PORT, () => console.log(`말벗 서버 실행 중 (Firebase 연동): http://localhost:${PORT}`));'''

    count = text.count(old)
    if count != 1:
        print(f"❌ old_str가 파일에서 {count}번 발견됨(1번이어야 함). 패치를 중단합니다.")
        sys.exit(1)

    new = '''// 0-53: 0-51 이전에 탈퇴 처리된 유저들의 팔로우/팔로워/프로필좋아요 잔여참조를
// 서버 시작 시 딱 1회만 정리함(meta/staleFollowCleanupDone 플래그로 재실행 방지, 계속 남겨둬도 안전)
async function cleanupStaleFollowRefsOnce() {
  try {
    const marker = await db.ref('meta/staleFollowCleanupDone').once('value');
    if (marker.val()) return;
    const usersSnap = await db.ref('users').once('value');
    const allUsers = usersSnap.val() || {};
    const validIds = new Set(Object.keys(allUsers));
    let cleanedUserCount = 0, removedRefCount = 0;
    for (const uid of Object.keys(allUsers)) {
      const u = allUsers[uid] || {};
      const updates = {};
      ['followingIds', 'followerIds', 'profileLikedBy'].forEach(field => {
        if (Array.isArray(u[field])) {
          const filtered = u[field].filter(id => validIds.has(id));
          if (filtered.length !== u[field].length) {
            updates[field] = filtered;
            removedRefCount += (u[field].length - filtered.length);
          }
        }
      });
      if (Object.keys(updates).length) {
        await db.ref(`users/${uid}`).update(updates);
        cleanedUserCount++;
      }
    }
    await db.ref('meta/staleFollowCleanupDone').set(true);
    console.log(`✅ 0-53: 팔로우/좋아요 잔여참조 정리 완료 (유저 ${cleanedUserCount}명, 참조 ${removedRefCount}건 제거)`);
  } catch (e) {
    console.error('0-53 잔여참조 정리 실패:', e);
  }
}
cleanupStaleFollowRefsOnce();

const PORT = process.env.PORT || 8080;
server.listen(PORT, () => console.log(`말벗 서버 실행 중 (Firebase 연동): http://localhost:${PORT}`));'''

    text = text.replace(old, new)
    TARGET.write_text(text, encoding="utf-8")
    print(f"✅ 0-53 패치 완료 (파일 크기 {original_len} → {len(text)} bytes)")
    print("   서버가 다음 재배포/재시작 때 콘솔에 '✅ 0-53: 팔로우/좋아요 잔여참조 정리 완료' 로그가 1회 출력됩니다.")

if __name__ == "__main__":
    main()