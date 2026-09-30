// AI 캐릭터 6명을 Firebase users에 등록(이미 있으면 프로필만 갱신, 팔로워 등은 유지)
// 실행: node scripts/register-ai-characters.js        (malbeot-app 폴더에서, .env 필요)
require('dotenv').config();
const admin = require('firebase-admin');
const { CHARACTERS, nickname, avatarDataUri } = require('../ai-characters');

admin.initializeApp({
  credential: admin.credential.cert(JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT)),
  databaseURL: process.env.FIREBASE_DB_URL
});
const db = admin.database();

async function main() {
  for (const c of CHARACTERS) {
    const ref = db.ref('users/' + c.id);
    const old = (await ref.once('value')).val();
    const base = old || {
      id: c.id, phone: '', points: 0, blockedUserIds: [], lastPostDate: null,
      adWatchCountToday: 0, lastAdChargeDate: null, joinedAt: Date.now(), onboardingSeen: true,
      followingIds: [], followerIds: [], profileLikedBy: [], notifyKeywords: []
    };
    const user = Object.assign({}, base, {
      nickname: nickname(c), region: c.region, gender: c.gender, age: c.age, bio: c.bio,
      photos: [avatarDataUri(c)], isAiCharacter: true, isOnline: true, lastSeen: Date.now(),
      profileUpdatedAt: base.profileUpdatedAt || Date.now()
    });
    await ref.set(user);
    console.log((old ? '갱신 ' : '등록 ') + user.nickname + ' (' + c.id + ')');
  }
  console.log('완료');
  process.exit(0);
}
main().catch(e => { console.error('오류:', e); process.exit(1); });