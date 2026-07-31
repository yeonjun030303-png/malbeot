// 1회성 소급 스캔: 기존 게시글/댓글/닉네임을 재검사해서 filtered 플래그를 갱신합니다.
// 실행: node scripts/rescan-existing.js
require('dotenv').config();
const admin = require('firebase-admin');
const { containsBannedWord, checkImageNsfw } = require('../moderation');

const serviceAccount = JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT);
admin.initializeApp({
  credential: admin.credential.cert(serviceAccount),
  databaseURL: process.env.FIREBASE_DB_URL
});
const db = admin.database();

async function main() {
  let userCount = 0, postCount = 0, commentCount = 0;

  // 1) 유저 닉네임 재검사 (원본 닉네임은 유지, nicknameFiltered 플래그만 심음)
  const usersSnap = await db.ref('users').once('value');
  const users = usersSnap.val() || {};
  for (const uid of Object.keys(users)) {
    const u = users[uid];
    const isBad = containsBannedWord(u.nickname || '');
    if (!!u.nicknameFiltered !== isBad) {
      await db.ref(`users/${uid}/nicknameFiltered`).set(isBad);
      userCount++;
      console.log(`[유저] ${uid} 닉네임 "${u.nickname}" → nicknameFiltered=${isBad}`);
    }
  }

  // 2) 게시글 + 댓글 재검사
  const postsSnap = await db.ref('posts').once('value');
  const posts = postsSnap.val() || {};
  for (const pid of Object.keys(posts)) {
    const p = posts[pid];
    let changed = false;

    if (!p.filtered) {
      const bannedWord = containsBannedWord(p.content || '');
      let imageBlocked = false;
      if (p.photo && !bannedWord) {
        const nsfwResult = await checkImageNsfw(p.photo);
        imageBlocked = nsfwResult.isNsfw;
      }
      const isFiltered = bannedWord || imageBlocked;
      if (isFiltered) {
        p.filtered = true;
        p.filteredAt = Date.now();
        if (imageBlocked) p.photo = '';
        changed = true;
        postCount++;
        console.log(`[게시글] ${pid} 필터링됨 (금지어:${bannedWord} 이미지:${imageBlocked})`);
      }
    }

    if (p.comments) {
      for (const cid of Object.keys(p.comments)) {
        const c = p.comments[cid];
        if (!c.filtered && containsBannedWord(c.content || '')) {
          c.filtered = true;
          changed = true;
          commentCount++;
          console.log(`[댓글] ${pid}/${cid} 필터링됨`);
        }
      }
    }

    if (changed) {
      await db.ref(`posts/${pid}`).set(p);
    }
  }

  console.log(`\n완료: 닉네임 ${userCount}건, 게시글 ${postCount}건, 댓글 ${commentCount}건 필터링 처리됨`);
  process.exit(0);
}

main().catch(err => {
  console.error('스캔 중 오류:', err);
  process.exit(1);
});