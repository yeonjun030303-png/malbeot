// 옛 'AI 말벗도우미'(ai_malbeot_bot)가 올린 글/계정 삭제
// 기본은 미리보기(dry-run)만 함. 실제로 지우려면: node scripts/cleanup-old-bot.js --go
require('dotenv').config();
const admin = require('firebase-admin');
const BOT = 'ai_malbeot_bot';
const GO = process.argv.includes('--go');

admin.initializeApp({
  credential: admin.credential.cert(JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT)),
  databaseURL: process.env.FIREBASE_DB_URL
});
const db = admin.database();

async function main() {
  const posts = (await db.ref('posts').once('value')).val() || {};
  const mine = Object.keys(posts).filter(id => posts[id] && posts[id].authorId === BOT);
  console.log('말벗도우미 게시글: ' + mine.length + '개');
  mine.slice(0, 5).forEach(id => console.log('  - ' + id + ': ' + String(posts[id].content || '').slice(0, 40)));

  const users = (await db.ref('users').once('value')).val() || {};
  const botUser = users[BOT];
  console.log('말벗도우미 계정: ' + (botUser ? '있음' : '없음'));
  const followers = Object.keys(users).filter(id => (users[id].followingIds || []).includes(BOT));
  console.log('말벗도우미를 팔로우 중인 유저: ' + followers.length + '명');

  if (!GO) { console.log('\n(미리보기만 했어. 실제로 지우려면 --go 를 붙여서 다시 실행)'); process.exit(0); }

  for (const id of mine) await db.ref('posts/' + id).remove();
  for (const id of followers) {
    const list = (users[id].followingIds || []).filter(x => x !== BOT);
    await db.ref('users/' + id + '/followingIds').set(list);
  }
  if (botUser) await db.ref('users/' + BOT).remove();
  console.log('\n삭제 완료: 게시글 ' + mine.length + '개, 팔로우 정리 ' + followers.length + '명, 계정 ' + (botUser ? '삭제' : '없었음'));
  process.exit(0);
}
main().catch(e => { console.error('오류:', e); process.exit(1); });