require('dotenv').config();
const express = require('express');
const http = require('http');
const path = require('path');
const { Server } = require('socket.io');
const admin = require('firebase-admin');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const { checkImageNsfw, containsBannedWord } = require('./moderation');

const serviceAccount = JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT);
admin.initializeApp({
  credential: admin.credential.cert(serviceAccount),
  databaseURL: process.env.FIREBASE_DB_URL
});
const db = admin.database();

const app = express();
const server = http.createServer(app);
// CORS: .env에 ALLOWED_ORIGIN(예: https://본인도메인)을 설정하면 그 주소에서만 접속을 허용함.
// 설정 안 하면 개발 편의를 위해 전체 허용('*')으로 동작하되 경고를 남김 - 배포 전에 반드시 설정 권장.
const ALLOWED_ORIGIN = process.env.ALLOWED_ORIGIN || '*';
if (!process.env.ALLOWED_ORIGIN) {
  console.warn('[경고] ALLOWED_ORIGIN이 .env에 설정되어 있지 않아 모든 출처(*)를 허용합니다. 배포 시 실제 도메인으로 제한하는 것을 권장합니다.');
}
const io = new Server(server, { cors: { origin: ALLOWED_ORIGIN }, maxHttpBufferSize: 1.5e7 });
app.use(express.json()); // /api/reports 같은 REST 라우트가 req.body를 읽으려면 필요함 (신고 시스템 추가하며 필요해짐)
app.use(express.static(path.join(__dirname, 'public')));

// 신고 시스템 (메시지 신고 접수 + 관리자 조회/처리)
const reportsRouter = require('./reports');
app.use('/api/reports', reportsRouter);

// 상시 구동 확인용 헬스체크 엔드포인트 (UptimeRobot 등 외부 핑 서비스로 주기적으로 호출하면
// 호스팅 서비스가 무접속 상태에서 슬립 모드로 전환되는 것을 막는 데 사용할 수 있음)
app.get('/health', (req, res) => res.status(200).send('ok'));

let socketToUser = {};
let userToSocket = {};

/* =====================================================================
   RevenueCat 웹훅 (구글 플레이/애플 앱스토어 인앱결제 완료 알림 수신)
   - RevenueCat 대시보드 > Project Settings > Integrations > Webhooks 에서
     이 서버의 주소(예: https://본인도메인/api/revenuecat-webhook)를 등록하고,
     "Authorization header value"에 아래 REVENUECAT_WEBHOOK_SECRET과 같은 값을 넣어야 함.
   - app_user_id는 클라이언트(iap-client.js)에서 Purchases.logIn(유저id)로 반드시
     연결되어 있어야, 여기서 어느 유저에게 쌀을 지급할지 알 수 있음.
   - 상품 ID(product_id)는 Play Console/App Store Connect에 등록한 ID와
     정확히 같아야 하며, points.html 등에서 쓰던 것과 동일하게 맞춰둠.
===================================================================== */
const POINTS_BY_PRODUCT = {
  points_1000: 1100, // 1000 + 10% 보너스
  points_3000: 3600, // 3000 + 20% 보너스
  points_5000: 6750  // 5000 + 35% 보너스
};

app.post('/api/revenuecat-webhook', async (req, res) => {
  try {
    const authHeader = req.headers['authorization'] || '';
    if (!process.env.REVENUECAT_WEBHOOK_SECRET || authHeader !== `Bearer ${process.env.REVENUECAT_WEBHOOK_SECRET}`) {
      console.warn('[RevenueCat 웹훅] 인증 실패 - REVENUECAT_WEBHOOK_SECRET 설정을 확인하세요.');
      return res.status(403).send('forbidden');
    }
    const event = req.body && req.body.event;
    if (!event) return res.status(400).send('no event');

    // 구매/갱신 이벤트만 포인트 지급 대상. 환불(CANCELLATION 등)은 별도 처리하지 않고 로그만 남김
    // (환불정책상 이미 지급된 쌀 회수는 관리자가 수동 확인하도록 남겨둠)
    if (event.type !== 'INITIAL_PURCHASE' && event.type !== 'NON_RENEWING_PURCHASE' && event.type !== 'RENEWAL') {
      console.log('[RevenueCat 웹훅] 처리 대상 아닌 이벤트:', event.type);
      return res.status(200).send('ignored');
    }

    // 이벤트 중복 처리 방지 (RevenueCat이 같은 이벤트를 재전송할 수 있음)
    const eventId = event.id;
    if (eventId) {
      const already = await db.ref(`processedPurchaseEvents/${eventId}`).once('value');
      if (already.exists()) {
        console.log('[RevenueCat 웹훅] 이미 처리된 이벤트:', eventId);
        return res.status(200).send('duplicate');
      }
    }

    const userId = event.app_user_id;
    const productId = event.product_id;
    const grantPoints = POINTS_BY_PRODUCT[productId];

    if (!userId || !grantPoints) {
      console.warn('[RevenueCat 웹훅] 알 수 없는 유저 또는 상품:', userId, productId);
      return res.status(200).send('unknown product or user');
    }

    const user = await getUser(userId);
    if (!user) {
      console.warn('[RevenueCat 웹훅] 유저를 찾을 수 없음:', userId);
      return res.status(200).send('user not found');
    }

    user.points = (user.points || 0) + grantPoints;
    await saveUser(user);
    if (eventId) await db.ref(`processedPurchaseEvents/${eventId}`).set({ userId, productId, grantPoints, at: Date.now() });

    console.log(`[RevenueCat 웹훅] ${userId} 유저에게 쌀 ${grantPoints}개 지급 완료 (상품: ${productId})`);

    // 지금 접속 중인 유저라면 실시간으로 잔액을 갱신해줌 (접속 중이 아니면 다음 로그인 시 서버 데이터로 자동 반영됨)
    const sId = userToSocket[userId];
    if (sId) io.to(sId).emit('points:updated', { points: user.points });

    res.status(200).send('ok');
  } catch (e) {
    console.error('[RevenueCat 웹훅 오류]', e);
    res.status(500).send('error');
  }
});

// 회원가입 / 카카오 추가정보 입력 공통 검증: 닉네임 미입력, 나이가 숫자가 아니거나 비정상 범위(14~120)면 거부.
// (기존에는 나이를 검증 없이 parseInt만 해서, 이상한 값을 넣으면 NaN이 그대로 DB에 저장되는 문제가 있었음)
function validateProfileInput(data) {
  if (!data.nickname || !String(data.nickname).trim().length) return '닉네임을 입력해주세요.';
  const age = parseInt(data.age, 10);
  if (isNaN(age) || age < 14 || age > 120) return '나이를 올바르게 입력해주세요.';
  return null;
}

const THIRTY_DAYS = 30 * 24 * 60 * 60 * 1000;
const ONE_DAY = 24 * 60 * 60 * 1000;
const genId = (p) => `${p}_${Date.now()}_${Math.floor(Math.random() * 100000)}`;
const roomIdFor = (a, b) => [a, b].sort().join('_room_');

/* =====================================================================
   로그인 세션 (전화번호+비밀번호 / 카카오)
   - SESSION_SECRET: .env에 반드시 설정해야 함 (예: 아무 랜덤 문자열 32자 이상)
     설정 안 하면 서버가 매번 다른 임시 비밀키를 써서, 서버 재시작할 때마다
     기존에 로그인해있던 사람들이 전부 세션이 끊겨 재로그인하게 되니 주의.
   - SESSION_MAX_AGE: 세션(로그인 유지) 유효기간. "7일 이상 미접속 시 재로그인"
     요구사항에 맞춰 7일로 설정. 접속할 때마다 새 토큰을 발급(연장)하므로,
     7일 안에 한 번이라도 들어오면 계속 로그인 상태가 유지됨.
===================================================================== */
const SESSION_SECRET = process.env.SESSION_SECRET || 'dev_only_insecure_secret_please_set_env';
if (!process.env.SESSION_SECRET) {
  console.warn('[경고] SESSION_SECRET이 .env에 설정되어 있지 않습니다. 반드시 설정해주세요 (안 하면 서버 재시작마다 전체 로그아웃됨).');
}
const SESSION_MAX_AGE = '7d';

function issueSessionToken(userId) {
  return jwt.sign({ uid: userId }, SESSION_SECRET, { expiresIn: SESSION_MAX_AGE });
}
function verifySessionToken(token) {
  try { return jwt.verify(token, SESSION_SECRET); } catch (e) { return null; }
}
async function hashPassword(plain) {
  return bcrypt.hash(plain, 10);
}
async function comparePassword(plain, hash) {
  if (!hash) return false;
  return bcrypt.compare(plain, hash);
}

async function getAllUsers() {
  const snap = await db.ref('users').once('value');
  return snap.val() || {};
}
async function findUserByPhone(phone) {
  const users = await getAllUsers();
  return Object.values(users).find(u => u.phone === phone);
}
async function findUserByKakaoId(kakaoId) {
  const users = await getAllUsers();
  return Object.values(users).find(u => u.kakaoId === kakaoId);
}
async function getUser(id) {
  const snap = await db.ref(`users/${id}`).once('value');
  return snap.val();
}
async function saveUser(user) {
  await db.ref(`users/${user.id}`).set(user);
}
async function getRawPosts() {
  const snap = await db.ref('posts').once('value');
  const val = snap.val() || {};
  return Object.values(val);
}
async function getPost(id) {
  const snap = await db.ref(`posts/${id}`).once('value');
  return snap.val();
}
async function savePost(post) {
  await db.ref(`posts/${post.id}`).set(post);
}
async function deletePostDb(id) {
  await db.ref(`posts/${id}`).remove();
}
async function getRoom(roomId) {
  const snap = await db.ref(`chats/${roomId}`).once('value');
  return snap.val();
}
async function saveRoomMeta(roomId, meta) {
  await db.ref(`chats/${roomId}`).update(meta);
}
async function addMessage(roomId, msg) {
  const ref = db.ref(`chats/${roomId}/messages`).push();
  msg.id = ref.key;
  await ref.set(msg);
  return msg;
}
async function deleteRoom(roomId) {
  await db.ref(`chats/${roomId}`).remove();
}

// data URL의 mime 타입을 보고 이미지/동영상을 구분 (video/* 이면 동영상)
function detectMediaType(dataUrl) {
  if (!dataUrl) return null;
  return /^data:video\//.test(dataUrl) ? 'video' : 'image';
}

// 게시물/댓글에 작성자의 "현재" 닉네임/지역/성별/나이/사진을 실시간으로 붙여주는 함수
// -> 유저가 닉네임을 바꾸면 예전 글에도 자동으로 새 닉네임이 반영됨
async function enrichPosts(rawPosts) {
  const users = await getAllUsers();
  return rawPosts.map(p => {
    const author = users[p.authorId] || {};
    const rawComments = p.comments ? Object.values(p.comments) : [];
    const comments = rawComments.map(c => {
      const cu = users[c.authorId] || {};
      return {
        ...c,
        authorNickname: cu.nicknameFiltered ? '삭제된 닉네임입니다' : (cu.nickname || '(탈퇴한 사용자)'),
        authorPhoto: (cu.photos && cu.photos[0]) || '',
        authorGender: cu.gender || 'female',
        authorPhotoPosition: cu.photoPosition || null
      };
    });
    // viewedBy(조회자별 마지막 조회 시각)는 조회수 집계용 내부 데이터라 클라이언트로는 내려주지 않음
    const { viewedBy, ...postRest } = p;
    return {
      ...postRest,
      authorNickname: author.nicknameFiltered ? '삭제된 닉네임입니다' : (author.nickname || '(탈퇴한 사용자)'),
      authorRegion: author.region || '',
      authorGender: author.gender || 'female',
      authorAge: author.age || 0,
      authorPhoto: (author.photos && author.photos[0]) || '',
      authorPhotoPosition: author.photoPosition || null,
      mediaType: p.photo ? detectMediaType(p.photo) : null,
      viewCount: p.viewCount || 0,
      comments
    };
  });
}

function broadcastUsers() { io.emit('users:updated'); }
function broadcastPosts() { io.emit('posts:updated'); }

// 특정 유저에게만 알림을 보냄 (그 유저가 접속 중일 때만 전송됨)
function notifyUser(userId, payload) {
  if (!userId) return;
  const sId = userToSocket[userId];
  if (sId) io.to(sId).emit('notify:new', payload);
}

// 내가 팔로우하는 사람이 새 글/스토리를 올리면 팔로워 전원에게 알림
// action: '작성' (새 글) 또는 '수정' (기존 글 수정)
async function notifyFollowersNewPost(author, post, action) {
  try {
    const followerIds = author.followerIds || [];
    if (!followerIds.length) return;
    const name = author.nickname || '누군가';
    const body = action === '수정' ? '게시글을 수정하였습니다' : '새로운 글을 작성하였습니다';
    followerIds.forEach(fid => {
      notifyUser(fid, { type: 'follow_post', postId: post.id, title: name, body });
    });
  } catch (e) { console.error('[팔로우 알림 오류]', e); }
}

// 각 유저가 등록해둔 키워드(notifyKeywords)가 게시글 내용에 포함되면 해당 유저에게 알림
// action: '등록' 또는 '수정'
async function notifyKeywordMatches(post, authorId, action) {
  try {
    const author = await getUser(authorId);
    const authorName = (author && author.nickname) || '누군가';
    const users = await getAllUsers();
    const content = post.content || '';
    Object.values(users).forEach(u => {
      if (!u || u.id === authorId) return;
      const keywords = u.notifyKeywords || [];
      const matched = keywords.find(k => k && content.includes(k));
      if (matched) {
        notifyUser(u.id, { type: 'keyword', postId: post.id, title: authorName, body: `'${matched}' 키워드가 포함된 글이 ${action}되었습니다` });
      }
    });
  } catch (e) { console.error('[키워드 알림 오류]', e); }
}

// ===== 정렬 카테고리 (기본순 / 인기순 / 거리순 / 조회수순) =====
// 게시글(커뮤니티) 정렬. list는 이미 최신순(기본순)으로 정렬된 상태로 들어온다고 가정.
function sortPostsByType(list, sortType, myRegion) {
  switch (sortType) {
    case 'popular': // 인기순: 좋아요 많은 순
      return [...list].sort((a, b) => (b.likes || 0) - (a.likes || 0));
    case 'distance': // 거리순: 같은 지역 우선, 그 안에서는 최신순
      if (!myRegion) return list;
      return [...list].sort((a, b) => {
        const aSame = a.authorRegion === myRegion ? 1 : 0;
        const bSame = b.authorRegion === myRegion ? 1 : 0;
        if (aSame !== bSame) return bSame - aSame;
        return (b.updatedAt || b.createdAt) - (a.updatedAt || a.createdAt);
      });
    case 'views': // 조회수순
      return [...list].sort((a, b) => (b.viewCount || 0) - (a.viewCount || 0));
    default: // 기본순
      return list;
  }
}

// 유저(홈) 정렬
function sortUsersByType(list, sortType, myRegion) {
  switch (sortType) {
    case 'popular': // 인기순: 팔로워 수 + 프로필 공감 수 합산
      return [...list].sort((a, b) => {
        const aScore = (a.followerIds ? a.followerIds.length : 0) + (a.profileLikedBy ? a.profileLikedBy.length : 0);
        const bScore = (b.followerIds ? b.followerIds.length : 0) + (b.profileLikedBy ? b.profileLikedBy.length : 0);
        return bScore - aScore;
      });
    case 'distance': // 거리순: 같은 지역 우선
      if (!myRegion) return list;
      return [...list].sort((a, b) => {
        const aSame = a.region === myRegion ? 1 : 0;
        const bSame = b.region === myRegion ? 1 : 0;
        if (aSame !== bSame) return bSame - aSame;
        return (b.profileUpdatedAt || b.lastSeen || 0) - (a.profileUpdatedAt || a.lastSeen || 0);
      });
    case 'views': // 유저 프로필 자체 조회수 데이터는 없어 인기순과 동일 기준으로 처리
      return sortUsersByType(list, 'popular', myRegion);
    default:
      return list;
  }
}

// ===== 말벗스토리 랜덤 알고리즘 =====
// 조회수가 높을수록 노출 가중치가 높아지되, 내가 이미 본 스토리는 가중치를 크게 낮추고
// 매 호출마다 랜덤값을 곱해 순서를 섞음 -> 아래/좌로 넘겨서 다시 호출할 때마다 다른 순서로 나옴
function weightedShuffleStories(stories, userId) {
  const withWeight = stories.map(s => {
    const viewed = userId && s.viewedBy && s.viewedBy[userId];
    const viewCount = s.viewCount || 0;
    let weight = viewCount + 1;
    if (viewed) weight = weight * 0.15; // 이미 본 스토리는 다시 뜰 확률을 크게 낮춤
    return { post: s, weight: weight * (0.5 + Math.random()) };
  });
  withWeight.sort((a, b) => b.weight - a.weight);
  return withWeight.map(w => w.post);
}

// ===== AI 말벗도우미 (매일 1회 자동 게시글 업로드) =====
const AI_BOT_ID = 'ai_malbeot_bot';

// 실제 유행곡/챌린지명을 그대로 언급하면 저작권 문제가 될 수 있어,
// 20~30대가 공감할 만한 순화된 일상 문구로 구성함 (필요하면 이 배열만 계속 늘려서 다양화 가능)
const AI_BOT_POST_TEMPLATES = [
  '오늘 날씨 완전 산책하기 좋은 날이네요! 다들 오늘 뭐하고 계신가요? 🍃',
  '요즘 다들 어떤 챌린지 하고 계세요? 저도 하나 배워보고 싶어요 😊',
  '점심시간! 오늘은 뭐 드셨나요? 저는 든든하게 챙겨 먹었어요 🍚',
  '주말에 다들 뭐 하실 계획이세요? 저는 재밌는 영상 찾아볼 예정이에요 🎬',
  '요즘 노래 뭐 듣고 계세요? 플레이리스트 추천 받아요 🎧',
  '오늘 하루도 다들 힘내세요! 소소한 행복 찾으면서 지내요 ✨',
  '커피 한 잔의 여유, 다들 즐기고 계신가요? ☕',
  '요즘 다들 취미 뭐 있으세요? 저도 새로운 취미 만들어보려고요!'
];

async function ensureAiBotUser() {
  let bot = await getUser(AI_BOT_ID);
  if (!bot) {
    bot = {
      id: AI_BOT_ID, phone: '', nickname: 'AI 말벗도우미',
      region: '전체', gender: 'female', age: 99,
      bio: '매일 소소한 이야기를 전해드리는 AI 말벗도우미예요 :)',
      photos: [], points: 999999, isOnline: true, lastSeen: Date.now(),
      blockedUserIds: [], lastPostDate: null, adWatchCountToday: 0,
      lastAdChargeDate: null, profileUpdatedAt: Date.now(),
      followingIds: [], followerIds: [], profileLikedBy: [], notifyKeywords: []
    };
    await saveUser(bot);
  }
  return bot;
}

const AI_BOT_HOTTOPIC_TEMPLATES = [
  { content: '요즘 제일 핫한 챌린지, 뭐가 제일 재밌어요? 🔥', options: ['댄스 챌린지', '먹방 챌린지', '운동 챌린지', '기타'] },
  { content: '스트레스 풀리는 방법 뭐가 제일 좋아요? 😌', options: ['운동하기', '맛있는거 먹기', '잠자기', '친구랑 수다떨기'] },
  { content: '주말에 제일 하고싶은 거 골라주세요! ✨', options: ['집에서 넷플릭스', '밖에서 나들이', '친구 만나기', '푹 자기'] },
];
const AI_BOT_BALANCE_TEMPLATES = [
  { content: '치킨 vs 피자, 오늘 저녁 뭐 먹을까요? 🍗🍕', options: ['치킨', '피자'] },
  { content: '여름 vs 겨울, 더 좋아하는 계절은? ☀️❄️', options: ['여름', '겨울'] },
  { content: '아침형 인간 vs 밤형 인간, 나는 어느 쪽? 🌅🌙', options: ['아침형', '밤형'] },
  { content: '국내여행 vs 해외여행, 다음 휴가는? ✈️', options: ['국내여행', '해외여행'] },
];

async function postAsAiBotIfNeeded() {
  try {
    const bot = await ensureAiBotUser();
    const todayStr = new Date().toISOString().slice(0, 10);
    if (bot.lastPostDate === todayStr) return; // 오늘 이미 게시함

    const roll = Math.random();
    let content, category = 'normal', pollOptions = null, pollVotes = null;
    if (roll < 0.3) {
      const t = AI_BOT_HOTTOPIC_TEMPLATES[Math.floor(Math.random() * AI_BOT_HOTTOPIC_TEMPLATES.length)];
      content = t.content; category = 'hottopic';
      pollOptions = t.options.map((text, i) => ({ id: 'o' + i, text })); pollVotes = {};
    } else if (roll < 0.5) {
      const t = AI_BOT_BALANCE_TEMPLATES[Math.floor(Math.random() * AI_BOT_BALANCE_TEMPLATES.length)];
      content = t.content; category = 'balance';
      pollOptions = t.options.map((text, i) => ({ id: 'o' + i, text })); pollVotes = {};
    } else {
      content = AI_BOT_POST_TEMPLATES[Math.floor(Math.random() * AI_BOT_POST_TEMPLATES.length)];
    }

    const post = {
      id: genId('p'), authorId: bot.id, content, photo: '', logType: 'story',
      category, pollOptions, pollVotes,
      createdAt: Date.now(), updatedAt: Date.now(), likes: 0, likedBy: [], comments: {},
      viewCount: 0, viewedBy: {}
    };
    await savePost(post);
    bot.lastPostDate = todayStr;
    await saveUser(bot);
    broadcastPosts();
    notifyFollowersNewPost(bot, post, '작성');
    notifyKeywordMatches(post, bot.id, '등록');
    console.log('[AI 말벗도우미] 오늘의 이야기 게시 완료:', content);
  } catch (e) { console.error('[AI 말벗도우미 게시 오류]', e); }
}

// 서버 시작 시 1회 체크 + 이후 1시간마다 날짜가 바뀌었는지 체크
// (무료 호스팅 환경의 sleep을 고려해 별도 cron 라이브러리 없이 setInterval로 처리)
ensureAiBotUser().then(() => postAsAiBotIfNeeded());
setInterval(postAsAiBotIfNeeded, 60 * 60 * 1000);

// 필터링/삭제된 게시글·댓글 자동 정리: 각각의 시점으로부터 3일이 지나면 완전 삭제
async function purgeExpiredFilteredPosts() {
  try {
    const posts = await getRawPosts();
    const now = Date.now();
    const THREE_DAYS = 3 * 24 * 60 * 60 * 1000;
    let purgedAny = false;
    for (const p of posts) {
      if (p.filtered && p.filteredAt && (now - p.filteredAt) > THREE_DAYS) {
        await deletePostDb(p.id);
        purgedAny = true;
        continue;
      }
      if (p.deleted && p.deletedAt && (now - p.deletedAt) > THREE_DAYS) {
        await deletePostDb(p.id);
        purgedAny = true;
        continue;
      }
      if (p.comments) {
        let commentsChanged = false;
        Object.keys(p.comments).forEach(cid => {
          const c = p.comments[cid];
          if (c.deleted && c.deletedAt && (now - c.deletedAt) > THREE_DAYS) {
            delete p.comments[cid];
            commentsChanged = true;
          }
        });
        if (commentsChanged) { savePost(p); purgedAny = true; }
      }
    }
    if (purgedAny) broadcastPosts();

    const chatsSnap = await db.ref('chats').once('value');
    const allChats = chatsSnap.val() || {};
    for (const roomId of Object.keys(allChats)) {
      const room = allChats[roomId];
      if (room.withdrawnAt && (now - room.withdrawnAt) > THREE_DAYS) {
        await deleteRoom(roomId);
      }
    }
  } catch (e) { console.error('[필터링/삭제 게시글 자동정리 오류]', e); }
}
setInterval(purgeExpiredFilteredPosts, 60 * 60 * 1000);

// 관리자 전화번호 목록. Render/​.env의 ADMIN_PHONES에 "01012345678,01099998888"처럼
// 콤마로 구분해서 등록해두면, 그 번호로 로그인한 사람은 커뮤니티 글/댓글을 누구 것이든
// 삭제할 수 있게 됨 (신고 시스템과 별개로 즉시 삭제 가능한 권한).
const ADMIN_PHONES = (process.env.ADMIN_PHONES || '').split(',').map(s => s.trim()).filter(Boolean);
function isAdminPhone(phone) { return !!phone && ADMIN_PHONES.includes(phone); }
const ADMIN_KAKAO_IDS = (process.env.ADMIN_KAKAO_IDS || "").split(",").map(s => s.trim()).filter(Boolean); function isAdminKakao(kakaoId) { return !!kakaoId && ADMIN_KAKAO_IDS.includes(String(kakaoId)); } function isAdmin(user) { return !!user && (isAdminPhone(user.phone) || isAdminKakao(user.kakaoId)); }

/* =====================================================================
   카카오 로그인
   - Kakao Developers(https://developers.kakao.com)에서 앱을 만들고,
     .env에 KAKAO_REST_API_KEY 를 등록해야 동작함.
   - "플랫폼 > Web" 에 실제 배포 도메인을 등록하고,
     "카카오 로그인 > Redirect URI" 에 "https://본인도메인/" (index.html이 뜨는 주소)를
     정확히 등록해야 함. 로컬 테스트 시엔 http://localhost:8080/ 도 추가로 등록.
   - KAKAO_CLIENT_SECRET: 카카오 디벨로퍼스 REST API 키의 "클라이언트 시크릿"이
     활성화(ON) 상태인 경우 반드시 .env에 설정해야 함. 활성화된 상태에서 이 값을
     안 보내면 토큰 발급이 실패함.
===================================================================== */
const KAKAO_REST_API_KEY = process.env.KAKAO_REST_API_KEY || '';
const KAKAO_CLIENT_SECRET = process.env.KAKAO_CLIENT_SECRET || '';

async function exchangeKakaoCode(code, redirectUri) {
  const params = new URLSearchParams({
    grant_type: 'authorization_code',
    client_id: KAKAO_REST_API_KEY,
    client_secret: KAKAO_CLIENT_SECRET,
    redirect_uri: redirectUri,
    code
  });
  const tokenRes = await fetch('https://kauth.kakao.com/oauth/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8' },
    body: params.toString()
  });
  const tokenData = await tokenRes.json();
  if (!tokenData.access_token) throw new Error('카카오 토큰 발급 실패: ' + JSON.stringify(tokenData));

  const profileRes = await fetch('https://kapi.kakao.com/v2/user/me', {
    headers: { Authorization: `Bearer ${tokenData.access_token}` }
  });
  const profileData = await profileRes.json();
  return { kakaoId: String(profileData.id) };
}

io.on('connection', (socket) => {

  // 전화번호+비밀번호 로그인
  // - 기존(비밀번호 없이 가입한) 회원은 그대로 전화번호만으로 로그인 가능(마이그레이션 배려)
  // - 비밀번호를 설정한 회원(신규 가입자)은 반드시 비밀번호까지 일치해야 로그인됨
  socket.on('auth:login', async (data, cb) => {
    try {
      const user = await findUserByPhone(data.phone);
      if (!user) return cb({ success: false, notFound: true, wrongField: 'phone' });
      if (user.passwordHash) {
        const ok = await comparePassword(data.password || '', user.passwordHash);
        if (!ok) return cb({ success: false, wrongField: 'password' });
      }
      user.isOnline = true;
      user.lastSeen = Date.now();
      await saveUser(user);
      socketToUser[socket.id] = user.id;
      userToSocket[user.id] = socket.id;
      const token = issueSessionToken(user.id);
      cb({ success: true, user: { ...user, isAdmin: isAdmin(user) }, token });
      broadcastUsers();
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  // 세션 토큰으로 자동 로그인 (브라우저 재접속/소켓 재연결 시 사용).
  // 토큰이 유효하면(7일 이내 발급/갱신) 비밀번호 재입력 없이 자동 로그인되고,
  // 이때 토큰을 다시 새로 발급(연장)해서 계속 접속하는 한 로그인이 유지되게 함.
  // 토큰이 없거나 7일이 지나 만료됐으면 실패 응답을 보내 재로그인(비밀번호 재입력)을 요구함.
  socket.on('auth:session_resume', async (data, cb) => {
    try {
      const payload = verifySessionToken(data && data.token);
      if (!payload) return cb({ success: false, expired: true });
      const user = await getUser(payload.uid);
      if (!user) return cb({ success: false });
      user.isOnline = true;
      user.lastSeen = Date.now();
      await saveUser(user);
      socketToUser[socket.id] = user.id;
      userToSocket[user.id] = socket.id;
      const token = issueSessionToken(user.id); // 갱신(연장)
      cb({ success: true, user: { ...user, isAdmin: isAdmin(user) }, token });
      broadcastUsers();
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  // 회원가입 (이미 등록된 번호면 거부). 비밀번호는 형식 제한 없이 받되, 반드시 입력해야 함(대소문자 구분은
  // bcrypt 해시 비교 특성상 자동으로 지켜짐 - 원문 그대로 비교하므로 대/소문자가 다르면 다른 비밀번호로 처리됨).
  socket.on('auth:signup', async (data, cb) => {
    try {
      if (!/^01[0-9]{9}$/.test(data.phone || '')) return cb({ success: false, message: '휴대폰 번호를 정확히 입력해주세요. (예: 010-0000-0000)' });
      if (!data.password || !String(data.password).length) return cb({ success: false, message: '비밀번호를 입력해주세요.' });
      const profileError = validateProfileInput(data);
      if (profileError) return cb({ success: false, message: profileError });
      if (containsBannedWord(data.nickname) && data.confirmed !== true) {
        return cb({ success: false, needsConfirm: true });
      }
      const existing = await findUserByPhone(data.phone);
      if (existing) return cb({ success: false, alreadyExists: true });
      const passwordHash = await hashPassword(String(data.password));
      const user = {
        id: genId('u'), phone: data.phone, passwordHash, nickname: data.nickname,
        nicknameFiltered: containsBannedWord(data.nickname),
        region: data.region, gender: data.gender, age: parseInt(data.age, 10),
        bio: data.bio || '반갑습니다!', photos: data.photos || [], points: 100,
        isOnline: true, lastSeen: Date.now(), blockedUserIds: [],
        lastPostDate: null, adWatchCountToday: 0, lastAdChargeDate: null,
        profileUpdatedAt: Date.now(),
        followingIds: [], followerIds: [], profileLikedBy: [], notifyKeywords: []
      };
      await saveUser(user);
      socketToUser[socket.id] = user.id;
      userToSocket[user.id] = socket.id;
      const token = issueSessionToken(user.id);
      cb({ success: true, user: { ...user, isAdmin: isAdmin(user) }, token });
      broadcastUsers();
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  // 회원가입 전 번호 중복 체크
  socket.on('auth:check_phone', async (data, cb) => {
    try {
      const user = await findUserByPhone(data.phone);
      cb({ exists: !!user });
    } catch (e) { console.error(e); cb({ exists: false }); }
  });

  // 카카오 로그인: 인가 코드를 받아 카카오 사용자 고유 ID를 확인.
  // - 이미 이 kakaoId로 가입된 계정이 있으면 바로 로그인 처리
  // - 처음 로그인하는 카카오 계정이면, 추가 프로필(닉네임/지역/성별/나이) 입력이 필요하다는 뜻으로
  //   pendingToken(10분간 유효한 임시 토큰)을 발급해서 돌려줌 -> 클라이언트는 추가 정보 입력 화면을 띄우고
  //   auth:kakao_complete_profile 이벤트로 pendingToken과 함께 나머지 정보를 제출함
  socket.on('auth:kakao_login', async (data, cb) => {
    try {
      if (!KAKAO_REST_API_KEY) return cb({ success: false, message: '카카오 로그인이 아직 설정되지 않았습니다. (KAKAO_REST_API_KEY 미설정)' });
      const { kakaoId } = await exchangeKakaoCode(data.code, data.redirectUri); console.log('[KAKAO_ID]', kakaoId);
      const existing = await findUserByKakaoId(kakaoId);
      if (existing) {
        existing.isOnline = true;
        existing.lastSeen = Date.now();
        await saveUser(existing);
        socketToUser[socket.id] = existing.id;
        userToSocket[existing.id] = socket.id;
        const token = issueSessionToken(existing.id);
        cb({ success: true, user: { ...existing, isAdmin: isAdmin(existing) }, token });
        broadcastUsers();
        return;
      }
      const pendingToken = jwt.sign({ kakaoId, purpose: 'kakao_signup' }, SESSION_SECRET, { expiresIn: '10m' });
      cb({ success: false, needProfile: true, pendingToken });
    } catch (e) { console.error('[카카오 로그인 오류]', e); cb({ success: false, message: '카카오 로그인 중 오류가 발생했습니다.' }); }
  });

  // 카카오 신규 가입자의 추가 정보(닉네임/지역/성별/나이) 제출 -> 계정 생성
  // 카카오로 가입한 계정은 phone이 없고 passwordHash도 없어서(전화번호 로그인 대상이 아니므로) 관리자 권한 대상은 아님.
  socket.on('auth:kakao_complete_profile', async (data, cb) => {
    try {
      let payload;
      try { payload = jwt.verify(data.pendingToken, SESSION_SECRET); } catch (e) { payload = null; }
      if (!payload || payload.purpose !== 'kakao_signup') return cb({ success: false, message: '인증이 만료되었습니다. 카카오 로그인을 다시 시도해주세요.' });
      const already = await findUserByKakaoId(payload.kakaoId);
      if (already) return cb({ success: false, alreadyExists: true });
      const profileError = validateProfileInput(data);
      if (profileError) return cb({ success: false, message: profileError });
      if (containsBannedWord(data.nickname) && data.confirmed !== true) {
        return cb({ success: false, needsConfirm: true });
      }
      if (data.photos && data.photos[0]) {
        const nsfwResult = await checkImageNsfw(data.photos[0]);
        if (nsfwResult.isNsfw) return cb({ success: false, message: '부적절한 프로필 사진으로 감지되어 가입할 수 없습니다. 다른 사진을 등록해주세요.' });
      }
      const user = {
        id: genId('u'), phone: '', kakaoId: payload.kakaoId, nickname: data.nickname,
        nicknameFiltered: containsBannedWord(data.nickname),
        region: data.region, gender: data.gender, age: parseInt(data.age, 10),
        bio: data.bio || '반갑습니다!', photos: data.photos || [], points: 100,
        isOnline: true, lastSeen: Date.now(), blockedUserIds: [],
        lastPostDate: null, adWatchCountToday: 0, lastAdChargeDate: null,
        profileUpdatedAt: Date.now(),
        followingIds: [], followerIds: [], profileLikedBy: [], notifyKeywords: []
      };
      await saveUser(user);
      socketToUser[socket.id] = user.id;
      userToSocket[user.id] = socket.id;
      const token = issueSessionToken(user.id);
      cb({ success: true, user: { ...user, isAdmin: false }, token });
      broadcastUsers();
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  socket.on('profile:update', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const user = await getUser(userId);
      if (!user) return cb({ success: false });

      if (data.nickname && containsBannedWord(data.nickname) && data.confirmed !== true) {
        return cb({ success: false, needsConfirm: true });
      }
      if (data.nickname) {
        data.nicknameFiltered = containsBannedWord(data.nickname);
      }

      if (data.photos && data.photos[0]) {
        const nsfwResult = await checkImageNsfw(data.photos[0]);
        if (nsfwResult.isNsfw) return cb({ success: false, message: '부적절한 프로필 사진으로 감지되어 변경할 수 없습니다.' });
      }

      Object.assign(user, data, { profileUpdatedAt: Date.now() });
      await saveUser(user);
      cb({ success: true, user: { ...user, isAdmin: isAdmin(user) } });
      broadcastUsers();
    } catch (e) { console.error(e); cb({ success: false }); }
  });
// 회원탈퇴: 게시글/스토리/릴스 전부 삭제, 채팅방은 남기되 시스템 메시지로 탈퇴 안내, 계정 삭제
  socket.on('account:withdraw', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const user = await getUser(userId);
      if (!user) return cb({ success: false });

      const postsSnap = await db.ref('posts').once('value');
      const allPosts = postsSnap.val() || {};
      for (const pid of Object.keys(allPosts)) {
        if (allPosts[pid].authorId === userId) await deletePostDb(pid);
      }

      const chatsSnap = await db.ref('chats').once('value');
      const allChats = chatsSnap.val() || {};
      for (const roomId of Object.keys(allChats)) {
        const room = allChats[roomId];
        if (room.userIds && room.userIds.includes(userId)) {
          await addMessage(roomId, { senderId: 'system', text: '탈퇴한 사용자입니다.', timestamp: Date.now() });
          await saveRoomMeta(roomId, { withdrawnAt: Date.now() });
          const otherId = room.userIds.find(id => id !== userId);
          const sId = userToSocket[otherId];
          if (sId) io.to(sId).emit('chat:new_message', { roomId, message: { senderId: 'system', text: '탈퇴한 사용자입니다.', timestamp: Date.now() } });
        }
      }

      await db.ref(`users/${userId}`).remove();
      delete socketToUser[socket.id];
      delete userToSocket[userId];
      cb({ success: true });
      broadcastUsers();
      broadcastPosts();
    } catch (e) { console.error(e); cb({ success: false }); }
  });
  // 홈 리스트: 나 자신 포함, filters.sort로 기본순/popular/distance/views 정렬 선택 가능
  socket.on('users:get_list', async (filters, cb) => {
    try {
      const users = await getAllUsers();
      let list = Object.values(users);
      if (filters.region && filters.region !== '전체') list = list.filter(u => u.region === filters.region);
      if (filters.gender && filters.gender !== '전체') list = list.filter(u => u.gender === filters.gender);
      list = list.filter(u => u.age >= filters.ageMin && u.age <= filters.ageMax);
      list.sort((a, b) => (b.profileUpdatedAt || b.lastSeen || 0) - (a.profileUpdatedAt || a.lastSeen || 0));
      const myUserId = socketToUser[socket.id];
      const myUser = myUserId ? await getUser(myUserId) : null;
      list = sortUsersByType(list, filters.sort, myUser && myUser.region);
      list = list.map(u => u.nicknameFiltered ? { ...u, nickname: "삭제된 닉네임입니다" } : u);
      cb({ success: true, users: list });
    } catch (e) { console.error(e); cb({ success: false, users: [] }); }
  });

  // 커뮤니티 리스트: filters.sort로 기본순/popular/distance/views 정렬 선택 가능
  socket.on('posts:get_list', async (filters, cb) => {
    try {
      const now = Date.now();
      let list = await enrichPosts(await getRawPosts());
      list = list.filter(p => (now - (p.updatedAt || p.createdAt)) < THIRTY_DAYS);
      if (filters.region && filters.region !== '전체') list = list.filter(p => p.authorRegion === filters.region);
      if (filters.gender && filters.gender !== '전체') list = list.filter(p => p.authorGender === filters.gender);
      list = list.filter(p => p.authorAge >= filters.ageMin && p.authorAge <= filters.ageMax);
      list.sort((a, b) => (b.updatedAt || b.createdAt) - (a.updatedAt || a.createdAt));
      const myUserId = socketToUser[socket.id];
      const myUser = myUserId ? await getUser(myUserId) : null;
      list = sortPostsByType(list, filters.sort, myUser && myUser.region);
      cb({ success: true, posts: list });
    } catch (e) { console.error(e); cb({ success: false, posts: [] }); }
  });

  // 말벗스토리 피드: 조회수 기반 가중치 + 이미 본 스토리 감점 + 랜덤 셔플
  // 클라이언트에서 아래/좌로 넘길 때마다 이 이벤트를 다시 호출하면 매번 새로운 랜덤 순서를 받게 됨
  socket.on('stories:get_feed', async (filters, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const now = Date.now();
      let raw = await getRawPosts();
      raw = raw.filter(p => p.logType === 'log' && !p.deleted && !p.filtered && (now - (p.updatedAt || p.createdAt)) < THIRTY_DAYS);
      const shuffled = weightedShuffleStories(raw, userId);
      const enriched = await enrichPosts(shuffled);
      cb({ success: true, stories: enriched });
    } catch (e) { console.error(e); cb({ success: false, stories: [] }); }
  });

  // 별명 검색 (홈 화면, 포인트 좌측의 작은 검색창에서 사용) - 부분 문자열 일치, 대소문자/자모 구분 없이 매칭
  socket.on('users:search', async (data, cb) => {
    try {
      const q = ((data && data.query) || '').trim().toLowerCase();
      if (!q) return cb({ success: true, users: [] });
      const users = await getAllUsers();
      const list = Object.values(users).filter(u => (u.nickname || '').toLowerCase().includes(q));
      cb({ success: true, users: list });
    } catch (e) { console.error(e); cb({ success: false, users: [] }); }
  });

  // 커뮤니티 검색: 게시글 본문 + 댓글 내용에서 검색어를 찾음.
  // matchedCommentIds에 담긴 댓글 id들을 클라이언트에서 최대 3줄까지 파란 강조 박스로 렌더링하면 됨
  socket.on('posts:search', async (data, cb) => {
    try {
      const q = ((data && data.query) || '').trim().toLowerCase();
      if (!q) return cb({ success: true, results: [] });
      const list = await enrichPosts(await getRawPosts());
      const results = [];
      list.forEach(p => {
        const contentMatch = (p.content || '').toLowerCase().includes(q);
        const matchedComments = (p.comments || []).filter(c => (c.content || '').toLowerCase().includes(q));
        if (contentMatch || matchedComments.length) {
          results.push({
            ...p,
            matchedCommentIds: matchedComments.map(c => c.id).slice(0, 3)
          });
        }
      });
      results.sort((a, b) => (b.updatedAt || b.createdAt) - (a.updatedAt || a.createdAt));
      cb({ success: true, results, query: data.query });
    } catch (e) { console.error(e); cb({ success: false, results: [] }); }
  });

  socket.on('posts:create', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const user = await getUser(userId);
      if (!user) return cb({ success: false });

      const bannedWord = containsBannedWord(data.content);
      if (bannedWord && data.confirmed !== true) return cb({ success: false, needsConfirm: true });
      let imageBlocked = false;
      if (data.photo) {
        const nsfwResult = await checkImageNsfw(data.photo);
        imageBlocked = nsfwResult.isNsfw;
      }
      const isFiltered = bannedWord || imageBlocked;

      const todayStr = new Date().toISOString().slice(0, 10);
      let earned = false;
      if (user.lastPostDate !== todayStr) { user.points += 50; user.lastPostDate = todayStr; earned = true; }
      await saveUser(user);
      const category = ['hottopic', 'balance'].includes(data.category) ? data.category : 'normal';
      let pollOptions = null, pollVotes = null;
      if (category !== 'normal') {
        const rawOptions = Array.isArray(data.pollOptions) ? data.pollOptions.map(t => (t || '').trim()).filter(Boolean) : [];
        const min = 2, max = category === 'balance' ? 2 : 4;
        if (rawOptions.length < min || rawOptions.length > max) return cb({ success: false, message: '투표 항목 개수를 확인해주세요.' });
        pollOptions = rawOptions.slice(0, max).map((text, i) => ({ id: 'o' + i, text: text.slice(0, 30) }));
        pollVotes = {};
      }
      const post = {
        id: genId('p'), authorId: user.id,
        content: (data.content || '').slice(0, 100), photo: imageBlocked ? '' : (data.photo || ''), logType: data.logType || 'story',
        category, pollOptions, pollVotes,
        createdAt: Date.now(), updatedAt: Date.now(), likes: 0, likedBy: [], comments: {},
        viewCount: 0, viewedBy: {},
        filtered: isFiltered, filteredAt: isFiltered ? Date.now() : null
      };
      await savePost(post);
      cb({ success: true, earned, points: user.points, filtered: isFiltered });
      broadcastPosts();
      if (!isFiltered) {
        // 팔로워에게 새 글/스토리 알림 + 키워드 알림 등록 유저에게 알림 (필터링된 글은 알림 생략)
        notifyFollowersNewPost(user, post, '작성');
        notifyKeywordMatches(post, user.id, '등록');
      }
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  socket.on('posts:update', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const post = await getPost(data.id);
      if (!post || post.authorId !== userId) return cb({ success: false });

      const bannedWord = containsBannedWord(data.content);
      if (bannedWord && data.confirmed !== true) return cb({ success: false, needsConfirm: true });
      let imageBlocked = false;
      if (data.photo) {
        const nsfwResult = await checkImageNsfw(data.photo);
        imageBlocked = nsfwResult.isNsfw;
      }
      const isFiltered = bannedWord || imageBlocked;
      const wasFiltered = !!post.filtered;

      post.content = (data.content || '').slice(0, 100);
      post.photo = imageBlocked ? '' : (data.photo || '');
      post.logType = data.logType || post.logType || 'story';
      post.updatedAt = Date.now();
      post.filtered = isFiltered;
      // 원래 정상이었다가 이번에 새로 걸린 경우에만 3일 타이머 시작.
      // 이미 필터링돼있던 글이면 기존 filteredAt(마감시한)을 그대로 유지함.
      if (isFiltered && !wasFiltered) post.filteredAt = Date.now();
      if (!isFiltered) post.filteredAt = null;

      await savePost(post);
      cb({ success: true, filtered: isFiltered });
      broadcastPosts();
      if (!isFiltered) {
        // 수정된 글도 키워드 알림 대상 + 팔로워 알림 대상에 포함 (필터링된 글은 알림 생략)
        const author = await getUser(userId);
        if (author) notifyFollowersNewPost(author, post, '수정');
        notifyKeywordMatches(post, userId, '수정');
      }
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  socket.on('posts:delete', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const post = await getPost(data.id);
      if (!post) return cb({ success: false });
      const requester = await getUser(userId);
      const admin = requester && isAdmin(requester);
      if (post.authorId !== userId && !admin) return cb({ success: false });
      post.deleted = true;
      post.deletedAt = Date.now();
      post.deletedByAdmin = !!(admin && post.authorId !== userId);
      await savePost(post);
      cb({ success: true });
      broadcastPosts();
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  socket.on('posts:like', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const post = await getPost(data.id);
      if (!post) return cb({ success: false });
      if (!post.likedBy) post.likedBy = [];
      const i = post.likedBy.indexOf(userId);
      let liked = false;
      if (i !== -1) { post.likedBy.splice(i, 1); post.likes = Math.max(0, (post.likes || 1) - 1); }
      else { post.likedBy.push(userId); post.likes = (post.likes || 0) + 1; liked = true; }
      await savePost(post);
      cb({ success: true, likes: post.likes, liked });
      broadcastPosts();
      if (liked && post.authorId && post.authorId !== userId) {
        const liker = await getUser(userId);
        const name = (liker && liker.nickname) || '누군가';
        notifyUser(post.authorId, { type: 'like', postId: post.id, title: name, body: '게시글에 공감하였습니다' });
      }
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  // 말벗스토리(및 게시글) 조회수 등록: 화면 진입/재진입 시점마다 호출되지만,
  // 같은 사람이 이미 24시간 이내에 조회한 적이 있으면 무시(카운트 증가 안 함) — 24시간당 1인 1회 제한
  socket.on('posts:view', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      if (!userId) return cb && cb({ success: false });
      const post = await getPost(data.postId);
      if (!post) return cb && cb({ success: false });
      if (!post.viewedBy) post.viewedBy = {};
      const last = post.viewedBy[userId] || 0;
      const now = Date.now();
      if (now - last >= ONE_DAY) {
        post.viewedBy[userId] = now;
        post.viewCount = (post.viewCount || 0) + 1;
        await savePost(post);
      }
      cb && cb({ success: true, viewCount: post.viewCount || 0 });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  socket.on('posts:vote', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      if (!userId) return cb({ success: false });
      const post = await getPost(data.postId);
      if (!post || post.deleted || post.filtered) return cb({ success: false });
      if (!post.pollOptions || !post.pollOptions.length) return cb({ success: false });
      const optionId = data.optionId;
      if (!post.pollOptions.find(o => o.id === optionId)) return cb({ success: false });
      if (!post.pollVotes) post.pollVotes = {};
      post.pollVotes[userId] = optionId;
      await savePost(post);
      cb({ success: true, pollVotes: post.pollVotes });
      broadcastPosts();
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  socket.on('comments:add', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const post = await getPost(data.postId);
      if (!post) return cb({ success: false });
      if (post.deleted || post.filtered) return cb({ success: false, message: '삭제된 게시글에는 댓글을 작성할 수 없습니다.' });

      const isFiltered = containsBannedWord(data.content);

      const commentId = genId('c');
      const comment = {
        id: commentId, authorId: userId,
        content: data.content, parentId: data.parentId || null,
        createdAt: Date.now(), updatedAt: Date.now(),
        filtered: isFiltered
      };
      if (!post.comments) post.comments = {};
      const parentComment = data.parentId ? post.comments[data.parentId] : null;
      post.comments[commentId] = comment;
      await savePost(post);
      cb({ success: true, filtered: isFiltered });
      broadcastPosts();

      if (!isFiltered) {
        const commenter = await getUser(userId);
        const name = (commenter && commenter.nickname) || '누군가';
        if (parentComment) {
          if (parentComment.authorId && parentComment.authorId !== userId) {
            notifyUser(parentComment.authorId, { type: 'reply', postId: post.id, title: name, body: '내 댓글에 답글을 달았습니다' });
          }
        } else if (post.authorId && post.authorId !== userId) {
          notifyUser(post.authorId, { type: 'comment', postId: post.id, title: name, body: '게시글에 댓글을 달았습니다' });
        }
      }
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  socket.on('comments:like', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const post = await getPost(data.postId);
      const c = post && post.comments && post.comments[data.commentId];
      if (!c) return cb && cb({ success: false });
      if (!c.likedBy) c.likedBy = [];
      const i = c.likedBy.indexOf(userId);
      let liked = false;
      if (i !== -1) { c.likedBy.splice(i, 1); c.likes = Math.max(0, (c.likes || 1) - 1); }
      else { c.likedBy.push(userId); c.likes = (c.likes || 0) + 1; liked = true; }
      await savePost(post);
      cb && cb({ success: true });
      broadcastPosts();
      if (liked && c.authorId && c.authorId !== userId) {
        const liker = await getUser(userId);
        const name = (liker && liker.nickname) || '누군가';
        notifyUser(c.authorId, { type: 'like', postId: post.id, title: name, body: '댓글에 공감하였습니다' });
      }
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  socket.on('comments:edit', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const post = await getPost(data.postId);
      const c = post && post.comments && post.comments[data.commentId];
      if (!c || c.authorId !== userId) return cb({ success: false });
      c.content = data.content;
      c.filtered = containsBannedWord(data.content);
      c.updatedAt = Date.now();
      await savePost(post);
      cb({ success: true, filtered: c.filtered });
      broadcastPosts();
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  socket.on('comments:delete', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const post = await getPost(data.postId);
      if (!post || !post.comments) return cb({ success: false });
      const c = post.comments[data.commentId];
      if (!c) return cb({ success: false });
      const requester = await getUser(userId);
      const admin = requester && isAdmin(requester);
      if (c.authorId !== userId && !admin) return cb({ success: false });
      c.deleted = true;
      c.deletedAt = Date.now();
      c.deletedByAdmin = !!(admin && c.authorId !== userId);
      await savePost(post);
      cb({ success: true });
      broadcastPosts();
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  socket.on('chat:get_list', async (cb) => {
    try {
      const userId = socketToUser[socket.id];
      const snap = await db.ref('chats').once('value');
      const allChats = snap.val() || {};
      const rooms = [];
      for (const roomId of Object.keys(allChats)) {
        const room = allChats[roomId];
        if (!room.userIds || !room.userIds.includes(userId)) continue;
        const otherId = room.userIds.find(id => id !== userId);
        const targetUser = await getUser(otherId);
        const messages = room.messages ? Object.values(room.messages) : [];
        const unreadCount = messages.filter(m => m.senderId !== userId && m.senderId !== 'system' && !m.read).length;
        rooms.push({ roomId, targetUser, messages, unreadCount });
      }
      cb({ success: true, rooms });
    } catch (e) { console.error(e); cb({ success: false, rooms: [] }); }
  });

  socket.on('chat:start_or_send', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const user = await getUser(userId);
      const target = await getUser(data.targetId);
      if (!user || !target) return cb({ success: false, message: '대상 사용자를 찾을 수 없습니다.' });
      if ((user.blockedUserIds || []).includes(target.id) || (target.blockedUserIds || []).includes(user.id)) {
        return cb({ success: false, message: '차단된 상대와는 대화할 수 없습니다.' });
      }
      const roomId = roomIdFor(user.id, target.id);
      let room = await getRoom(roomId);
      const isNew = !room;
      if (isNew) {
        if (user.points < 50) return cb({ success: false, needPoints: true });
        user.points -= 50;
        await saveUser(user);
        await saveRoomMeta(roomId, { roomId, userIds: [user.id, target.id] });
        await addMessage(roomId, { senderId: 'system', text: '대화가 시작되었습니다. (쌀 50개 차감)', timestamp: Date.now() });
      }
      const msg = await addMessage(roomId, { senderId: user.id, text: data.text, timestamp: Date.now(), read: false });
      cb({ success: true, roomId, points: user.points });
      [user.id, target.id].forEach(uid => {
        const sId = userToSocket[uid];
        if (sId) io.to(sId).emit('chat:new_message', { roomId, message: msg, senderNickname: user.nickname });
      });
      broadcastUsers();
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  socket.on('chat:send_message', async (data) => {
    try {
      const userId = socketToUser[socket.id];
      const room = await getRoom(data.roomId);
      if (!room || !room.userIds.includes(userId)) return;
      const msg = await addMessage(data.roomId, { senderId: userId, text: data.text, timestamp: Date.now(), read: false });
      const sender = await getUser(userId);
      room.userIds.forEach(uid => {
        const sId = userToSocket[uid];
        if (sId) io.to(sId).emit('chat:new_message', { roomId: data.roomId, message: msg, senderNickname: sender && sender.nickname });
      });
    } catch (e) { console.error(e); }
  });

  socket.on('chat:send_image', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const room = await getRoom(data.roomId);
      if (!room || !room.userIds.includes(userId)) return cb && cb({ success: false });
      const nsfwResult = await checkImageNsfw(data.image);
      if (nsfwResult.isNsfw) return cb && cb({ success: false, blocked: true, message: '부적절한 사진으로 감지되어 전송할 수 없습니다.' });
      const msg = await addMessage(data.roomId, { senderId: userId, type: 'image', data: data.image, timestamp: Date.now(), read: false });
      const sender = await getUser(userId);
      room.userIds.forEach(uid => {
        const sId = userToSocket[uid];
        if (sId) io.to(sId).emit('chat:new_message', { roomId: data.roomId, message: msg, senderNickname: sender && sender.nickname });
      });
      cb && cb({ success: true });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 채팅방을 열람하면(=내 채팅창에 들어오면) 상대가 보낸 안읽은 메시지를 모두 읽음 처리
  socket.on('chat:mark_read', async (data) => {
    try {
      const userId = socketToUser[socket.id];
      const room = await getRoom(data.roomId);
      if (!room || !room.userIds || !room.userIds.includes(userId)) return;
      const messages = room.messages || {};
      const updates = {};
      Object.keys(messages).forEach(mid => {
        const m = messages[mid];
        if (m && m.senderId !== userId && m.senderId !== 'system' && !m.read) {
          updates[`chats/${data.roomId}/messages/${mid}/read`] = true;
        }
      });
      if (Object.keys(updates).length) {
        await db.ref().update(updates);
        const otherId = room.userIds.find(id => id !== userId);
        const sId = userToSocket[otherId];
        if (sId) io.to(sId).emit('chat:read_receipt', { roomId: data.roomId });
      }
    } catch (e) { console.error(e); }
  });

  // 팔로우 / 언팔로우 토글 (알림은 발생시키지 않음)
  socket.on('user:follow', async (targetId, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const user = await getUser(userId);
      const target = await getUser(targetId);
      if (!user || !target || userId === targetId) return cb && cb({ success: false });
      user.followingIds = user.followingIds || [];
      target.followerIds = target.followerIds || [];
      const isFollowing = user.followingIds.includes(targetId);
      if (isFollowing) {
        user.followingIds = user.followingIds.filter(id => id !== targetId);
        target.followerIds = target.followerIds.filter(id => id !== userId);
      } else {
        user.followingIds.push(targetId);
        target.followerIds.push(userId);
      }
      await saveUser(user);
      await saveUser(target);
      if (!isFollowing) {
        const followerName = user.nickname || '누군가';
        notifyUser(targetId, { type: 'follow', userId: user.id, title: followerName, body: '나를 팔로우하였습니다' });
      }
      cb && cb({ success: true, following: !isFollowing });
      broadcastUsers();
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 특정 유저를 팔로우하는 사람 목록 (제3자도 조회 가능)
  socket.on('user:get_followers', async (targetId, cb) => {
    try {
      const target = await getUser(targetId);
      const ids = (target && target.followerIds) || [];
      const users = await getAllUsers();
      let list = ids.map(id => users[id]).filter(Boolean);
      list = list.map(u => u.nicknameFiltered ? { ...u, nickname: "삭제된 닉네임입니다" } : u);
      cb && cb({ success: true, users: list });
    } catch (e) { console.error(e); cb && cb({ success: false, users: [] }); }
  });

  // 특정 유저가 팔로우하는 사람 목록 (제3자도 조회 가능) - 팔로잉 목록 모달용
  socket.on('user:get_following', async (targetId, cb) => {
    try {
      const target = await getUser(targetId);
      const ids = (target && target.followingIds) || [];
      const users = await getAllUsers();
      let list = ids.map(id => users[id]).filter(Boolean);
      list = list.map(u => u.nicknameFiltered ? { ...u, nickname: "삭제된 닉네임입니다" } : u);
      cb && cb({ success: true, users: list });
    } catch (e) { console.error(e); cb && cb({ success: false, users: [] }); }
  });

  // 프로필 공감 토글 (알림은 발생시키지 않음, 제3자도 공감자 목록 조회 가능)
  socket.on('profile:like', async (targetId, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const target = await getUser(targetId);
      if (!target || userId === targetId) return cb && cb({ success: false });
      target.profileLikedBy = target.profileLikedBy || [];
      const i = target.profileLikedBy.indexOf(userId);
      let liked = false;
      if (i !== -1) target.profileLikedBy.splice(i, 1);
      else { target.profileLikedBy.push(userId); liked = true; }
      await saveUser(target);
      cb && cb({ success: true, liked, count: target.profileLikedBy.length });
      broadcastUsers();
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  socket.on('user:get_profile_likers', async (targetId, cb) => {
    try {
      const target = await getUser(targetId);
      const ids = (target && target.profileLikedBy) || [];
      const users = await getAllUsers();
      const list = ids.map(id => users[id]).filter(Boolean);
      cb && cb({ success: true, users: list });
    } catch (e) { console.error(e); cb && cb({ success: false, users: [] }); }
  });

  // 차단한 회원 목록 조회 (프로필 목록처럼 그대로 재사용할 수 있게 유저 객체 배열로 반환)
  socket.on('user:get_blocked_list', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const user = await getUser(userId);
      if (!user) return cb({ success: false, users: [] });
      const ids = user.blockedUserIds || [];
      const users = await getAllUsers();
      const list = ids.map(id => users[id]).filter(Boolean);
      cb({ success: true, users: list });
    } catch (e) { console.error(e); cb({ success: false, users: [] }); }
  });

  // 차단 해제
  socket.on('user:unblock', async (targetId, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const user = await getUser(userId);
      if (!user) return cb && cb({ success: false });
      user.blockedUserIds = (user.blockedUserIds || []).filter(id => id !== targetId);
      await saveUser(user);
      cb && cb({ success: true });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 명시적 로그아웃 (연결은 유지한 채 온라인 상태만 즉시 내려줌)
  socket.on('auth:logout', async (cb) => {
    try {
      const userId = socketToUser[socket.id];
      if (userId) {
        const user = await getUser(userId);
        if (user) { user.isOnline = false; user.lastSeen = Date.now(); await saveUser(user); }
        delete userToSocket[userId];
        delete socketToUser[socket.id];
        broadcastUsers();
      }
      cb && cb({ success: true });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  socket.on('chat:end', async (roomId, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const room = await getRoom(roomId);
      if (room) {
        const otherId = room.userIds.find(id => id !== userId);
        const sId = userToSocket[otherId];
        if (sId) io.to(sId).emit('chat:ended_notify', { roomId });
        await deleteRoom(roomId);
      }
      if (cb) cb({ success: true });
    } catch (e) { console.error(e); if (cb) cb({ success: false }); }
  });

  socket.on('user:block', async (targetId, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const user = await getUser(userId);
      if (!user) return cb && cb({ success: false });
      if (!user.blockedUserIds) user.blockedUserIds = [];
      if (!user.blockedUserIds.includes(targetId)) user.blockedUserIds.push(targetId);
      await saveUser(user);
      const roomId = roomIdFor(userId, targetId);
      const room = await getRoom(roomId);
      if (room) {
        const sId = userToSocket[targetId];
        if (sId) io.to(sId).emit('chat:blocked_notify', { roomId });
        await deleteRoom(roomId);
      }
      cb && cb({ success: true });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  socket.on('user:report', (data, cb) => {
    console.log('[신고 접수]', new Date().toISOString(), data);
    cb && cb({ success: true });
  });

  socket.on('disconnect', async () => {
    try {
      const userId = socketToUser[socket.id];
      if (userId) {
        const user = await getUser(userId);
        if (user) {
          user.isOnline = false;
          user.lastSeen = Date.now();
          await saveUser(user);
          broadcastUsers();
        }
      }
      delete socketToUser[socket.id];
    } catch (e) { console.error(e); }
  });
});

const PORT = process.env.PORT || 8080;
server.listen(PORT, () => console.log(`말벗 서버 실행 중 (Firebase 연동): http://localhost:${PORT}`));