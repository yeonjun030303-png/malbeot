// AI 캐릭터 삭제 스크립트. 기본 DRY(개수만 출력). 실제 삭제: DRY=false 그리고 CONFIRM=DELETE
'use strict';
const A = require('../ai-characters');
const admin = require('firebase-admin');
const log = s => console.log('[PURGE] ' + s);
const dry = String(process.env.DRY || 'true').toLowerCase() !== 'false';
const real = !dry && process.env.CONFIRM === 'DELETE';

async function main() {
  if (!process.env.FIREBASE_SERVICE_ACCOUNT || !process.env.FIREBASE_DB_URL) { console.error('환경변수가 없어'); process.exit(1); }
  admin.initializeApp({ credential: admin.credential.cert(JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT)), databaseURL: process.env.FIREBASE_DB_URL });
  const db = admin.database();
  log('모드: ' + (real ? '실제 삭제' : (dry ? 'DRY (DB 안 건드림)' : 'confirm 미입력 - DRY로 처리')));
  const ids = A.CHARACTERS.map(c => c.id);
  log('AI 캐릭터 ' + ids.length + '명: ' + A.CHARACTERS.map(c => c.name).join(', '));

  const root = (await db.ref().once('value')).val() || {};
  const users = root.users || {}, posts = root.posts || {};
  const updates = {};
  let nUsers = 0, nPosts = 0, nCm = 0, nHumanCmInAiPosts = 0, nOrphan = 0;

  ids.forEach(id => { if (users[id]) { updates['users/' + id] = null; nUsers++; } });
  Object.keys(posts).forEach(pid => {
    const p = posts[pid]; if (!p) return;
    const cs = p.comments || {};
    if (A.isAiCharId(p.authorId)) {
      updates['posts/' + pid] = null; nPosts++;
      Object.keys(cs).forEach(cid => { const c = cs[cid]; if (c && !A.isAiCharId(c.authorId)) nHumanCmInAiPosts++; });
      return;
    }
    const aiCm = {};
    Object.keys(cs).forEach(cid => {
      const c = cs[cid];
      if (c && A.isAiCharId(c.authorId)) { aiCm[cid] = true; updates['posts/' + pid + '/comments/' + cid] = null; nCm++; }
    });
    Object.keys(cs).forEach(cid => {
      const c = cs[cid];
      if (c && !A.isAiCharId(c.authorId) && c.parentId && aiCm[c.parentId]) nOrphan++;
    });
  });
  const hasStats = !!root.aiStats;
  if (hasStats) updates['aiStats'] = null;

  log('삭제 대상 AI 계정(users): ' + nUsers + '개');
  log('삭제 대상 AI 글: ' + nPosts + '개 (그 글에 달린 실제 이용자 댓글 ' + nHumanCmInAiPosts + '개도 같이 사라짐)');
  log('삭제 대상 AI 댓글/답글(다른 글에 달린 것): ' + nCm + '개');
  log('AI 댓글에 달린 이용자 답글(이번에 안 지움): ' + nOrphan + '개');
  log('AI 통계(aiStats) 삭제: ' + (hasStats ? '예' : '없음'));

  const sU = JSON.stringify(Object.keys(users).filter(k => ids.indexOf(k) < 0).map(k => users[k])) || '';
  const hitU = ids.filter(id => sU.indexOf(id) >= 0).map(id => id + ':' + (sU.split(id).length - 1));
  if (hitU.length) log('다른 이용자 데이터(users)에 AI id 흔적: ' + hitU.join(', ') + ' (팔로우/채팅방 등, 이번에 안 지움)');
  Object.keys(root).filter(k => k !== 'users' && k !== 'posts' && k !== 'aiStats').forEach(k => {
    const s = JSON.stringify(root[k]) || '';
    const hits = ids.filter(id => s.indexOf(id) >= 0).map(id => id + ':' + (s.split(id).length - 1));
    if (hits.length) log('다른 노드 [' + k + '] 에 AI id 흔적: ' + hits.join(', ') + ' (이번에 안 지움)');
  });

  if (real) {
    await db.ref().update(updates);
    log('삭제 완료: 경로 ' + Object.keys(updates).length + '개');
  } else {
    log('아무것도 삭제하지 않음');
  }
  process.exit(0);
}
main().catch(e => { console.error('오류:', e); process.exit(1); });