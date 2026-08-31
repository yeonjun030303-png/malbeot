// 신고/제재 검토 봇
// - Firebase의 reports(pending) + 관련 컨텍스트(메시지/게시글/댓글 내용)를 모아 Gemini에게 판정을 맡김
// - 판정 결과:
//   AUTO_WARN     : 경고 수준의 명백한 위반 -> 봇이 즉시 경고 집행 (target.warnings + pendingWarningNotify)
//                   -> 기존 서버 로직(popPendingWarningNotify)이 다음 로그인 때 알림을 그대로 띄워줌
//   NEEDS_ADMIN   : 정지/영구정지가 필요하거나 판단이 애매한 경우 -> 자동집행 없이 관리자에게 넘김
//   LIKELY_DISMISS: 근거 불충분/오신고로 보이는 경우 -> 역시 자동집행 없이 "기각 권장"으로만 관리자에게 넘김
// - 텍스트 증거가 없는 신고(type: 'user' 프로필 신고 등)는 Gemini 판단 없이 무조건 NEEDS_ADMIN 처리
// - AUTO_WARN/NEEDS_ADMIN/LIKELY_DISMISS 모두 report.status는 'pending' 유지 (관리자 대시보드에서 그대로 확인 가능)
//   단, AUTO_WARN으로 실제 경고를 집행한 건은 status를 'resolved'로 갱신함(중복 경고 방지)

const fs = require('fs');
const { initializeApp, cert } = require('firebase-admin/app');
const { getDatabase } = require('firebase-admin/database');

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function callGeminiModel(model, prompt, apiKey, maxRetries, baseDelayMs) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    let data;
    try {
      const res = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] }),
          signal: AbortSignal.timeout(60000)
        }
      );
      data = await res.json();
    } catch (e) {
      console.error('[' + model + '] 타임아웃/네트워크 오류 (시도 ' + attempt + '/' + maxRetries + '): ' + e.message);
      if (attempt < maxRetries) {
        const delay = baseDelayMs * Math.pow(2, attempt - 1);
        console.log('[' + model + '] ' + (delay / 1000) + '초 후 재시도...');
        await sleep(delay);
        continue;
      }
      return null;
    }
    const text = data?.candidates?.[0]?.content?.parts?.[0]?.text;

    if (text) return text;

    const isRetryable = data?.error?.code === 503 || data?.error?.code === 429;
    console.error(`[${model}] Gemini 응답 실패 (시도 ${attempt}/${maxRetries}):`, JSON.stringify(data));

    if (isRetryable && attempt < maxRetries) {
      const delay = baseDelayMs * Math.pow(2, attempt - 1);
      console.log(`[${model}] ${delay / 1000}초 후 재시도...`);
      await sleep(delay);
      continue;
    }
    return null;
  }
  return null;
}

async function callGemini(prompt, apiKey) {
  let text = await callGeminiModel('gemini-flash-latest', prompt, apiKey, 4, 20000);
  if (text) return text;

  console.log('주 모델(gemini-flash-latest) 실패 - 대체 모델(gemini-3.6-flash)로 재시도');
  text = await callGeminiModel('gemini-3.6-flash', prompt, apiKey, 2, 15000);
  return text;
}

// report의 실제 텍스트 증거를 유형별로 가져옴 (server.js의 관리자 대시보드 표시 로직과 동일한 소스 사용)
async function getEvidenceText(db, report) {
  try {
    if (report.type === 'chat' && report.messageId) {
      const snap = await db.ref(`chats/${report.targetId}/messages/${report.messageId}`).once('value');
      const msg = snap.val();
      if (msg && !msg.deletedForEveryone) {
        if (msg.type === 'image') return '(이미지 메시지 - 텍스트 증거 없음)';
        return msg.text || null;
      }
      return report.messagePreview || null;
    }
    if (report.type === 'post') {
      const snap = await db.ref(`posts/${report.targetId}`).once('value');
      const post = snap.val();
      return post ? (post.content || null) : null;
    }
    if (report.type === 'comment') {
      const [postId, commentId] = (report.targetId || '').split('::');
      if (!postId || !commentId) return null;
      const snap = await db.ref(`posts/${postId}/comments/${commentId}`).once('value');
      const c = snap.val();
      return c ? (c.content || null) : null;
    }
    return null; // type === 'user' 등 텍스트 증거가 없는 유형
  } catch (e) {
    console.error(`[증거 조회 실패] report ${report.id}:`, e.message);
    return null;
  }
}

async function getAccusedUserId(db, report) {
  try {
    if (report.type === 'user') return report.targetId;
    if (report.type === 'post') {
      const snap = await db.ref(`posts/${report.targetId}`).once('value');
      const p = snap.val();
      return p ? p.authorId : null;
    }
    if (report.type === 'chat') {
      const snap = await db.ref(`chats/${report.targetId}`).once('value');
      const room = snap.val();
      return room && room.userIds ? room.userIds.find(uid => uid !== report.reporterUid) : null;
    }
    if (report.type === 'comment') {
      const [postId, commentId] = (report.targetId || '').split('::');
      if (!postId || !commentId) return null;
      const snap = await db.ref(`posts/${postId}/comments/${commentId}`).once('value');
      const c = snap.val();
      return c ? c.authorId : null;
    }
  } catch (e) {
    console.error(`[피신고자 조회 실패] report ${report.id}:`, e.message);
  }
  return null;
}

function extractJson(text) {
  const match = text.match(/\[[\s\S]*\]/);
  if (!match) return null;
  try {
    return JSON.parse(match[0]);
  } catch (e) {
    return null;
  }
}

async function main() {
  const serviceAccount = JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT);
  initializeApp({
    credential: cert(serviceAccount),
    databaseURL: process.env.FIREBASE_DB_URL
  });
  const db = getDatabase();

  const snap = await db.ref('reports').orderByChild('status').equalTo('pending').once('value');
  const all = snap.val() || {};
  const pending = Object.keys(all).map(id => ({ id, ...all[id] }));

  if (pending.length === 0) {
    console.log('처리할 미확인 신고 없음 - 스킵');
    process.exit(0);
  }

  // 같은 대상(type::targetId)에 쌓인 미처리 신고자 수 집계 (관리자 대시보드와 동일한 기준)
  const reportersByTarget = {};
  pending.forEach(r => {
    const key = `${r.type}::${r.targetId}`;
    if (!reportersByTarget[key]) reportersByTarget[key] = new Set();
    reportersByTarget[key].add(r.reporterUid || r.id);
  });
  const countByTarget = {};
  Object.keys(reportersByTarget).forEach(key => { countByTarget[key] = reportersByTarget[key].size; });

  // 텍스트 증거 수집 + Gemini에게 넘길 대상과, 증거가 없어 바로 NEEDS_ADMIN으로 갈 대상을 분리
  const withEvidence = [];
  const noEvidence = [];
  for (const r of pending) {
    const evidence = await getEvidenceText(db, r);
    const sameTargetCount = countByTarget[`${r.type}::${r.targetId}`] || 1;
    if (evidence) {
      withEvidence.push({ ...r, evidence, sameTargetCount });
    } else {
      noEvidence.push({ ...r, sameTargetCount });
    }
  }

  let decisions = {};
  if (withEvidence.length > 0) {
    const items = withEvidence.map(r =>
      `- id: ${r.id}\n  신고유형: ${r.type}\n  신고사유(카테고리): ${r.category || '(미기재)'}\n  같은 대상 누적 신고자 수: ${r.sameTargetCount}\n  신고된 내용: "${(r.evidence || '').slice(0, 300)}"`
    ).join('\n\n');

    const prompt = `당신은 채팅/커뮤니티 앱 "말벗"의 콘텐츠 모더레이션 검토자입니다. 아래는 사용자들이 신고한 내용 목록입니다. 각 항목마다 세 가지 중 하나로 판정해주세요.

- AUTO_WARN: 욕설, 비하, 스팸, 가벼운 성희롱 등 경고 조치가 명백히 타당한 경미~중간 수준의 위반
- NEEDS_ADMIN: 정지/영구정지급 조치가 필요해 보이거나(반복적 심각한 위반, 성적 착취/미성년자 관련, 폭력적 위협, 사기 등), 판단이 애매하거나 확신이 서지 않는 경우 (조금이라도 애매하면 반드시 이쪽으로 판정하세요)
- LIKELY_DISMISS: 신고 내용상 명백히 규정 위반이 아니거나 오신고로 보이는 경우 (그래도 최종 기각은 관리자가 결정하므로 "권장"일 뿐입니다)

각 항목에 대해 판정과 한국어로 된 1문장짜리 근거를 반드시 남기세요. 애매하면 절대 AUTO_WARN을 고르지 말고 NEEDS_ADMIN으로 판정하세요.

--- 신고 목록 ---
${items}

--- 출력 형식 ---
다른 설명 없이 아래 JSON 배열 형식으로만 답하세요:
[{"id": "신고id", "decision": "AUTO_WARN|NEEDS_ADMIN|LIKELY_DISMISS", "reason": "판정 근거 1문장"}]`;

    const apiKey = process.env.GEMINI_API_KEY;
    const raw = await callGemini(prompt, apiKey);

    if (!raw) {
      console.error('Gemini 응답을 최종적으로 받지 못함 - 증거 있는 신고 전부 NEEDS_ADMIN으로 안전하게 처리');
      withEvidence.forEach(r => { decisions[r.id] = { decision: 'NEEDS_ADMIN', reason: 'Gemini 응답 실패로 자동 판정 불가 - 직접 확인 필요' }; });
    } else {
      const parsed = extractJson(raw);
      if (!parsed) {
        console.error('Gemini 응답 JSON 파싱 실패 - 증거 있는 신고 전부 NEEDS_ADMIN으로 안전하게 처리');
        console.error('원본 응답:', raw);
        withEvidence.forEach(r => { decisions[r.id] = { decision: 'NEEDS_ADMIN', reason: 'Gemini 응답 파싱 실패로 자동 판정 불가 - 직접 확인 필요' }; });
      } else {
        parsed.forEach(d => { if (d && d.id) decisions[d.id] = d; });
        // 혹시 누락된 항목이 있으면 안전하게 NEEDS_ADMIN
        withEvidence.forEach(r => {
          if (!decisions[r.id]) decisions[r.id] = { decision: 'NEEDS_ADMIN', reason: 'Gemini 판정 누락 - 직접 확인 필요' };
        });
      }
    }
  }

  const autoWarned = [];
  const needsAdmin = [];
  const likelyDismiss = [];

  for (const r of withEvidence) {
    const d = decisions[r.id] || { decision: 'NEEDS_ADMIN', reason: '판정 누락' };
    if (d.decision === 'AUTO_WARN') {
      const accusedId = await getAccusedUserId(db, r);
      if (!accusedId) {
        needsAdmin.push({ ...r, geminiReason: d.reason + ' (피신고자 특정 실패로 자동경고 불가 - 직접 확인 필요)' });
        continue;
      }
      const userSnap = await db.ref(`users/${accusedId}`).once('value');
      const target = userSnap.val();
      if (!target) {
        needsAdmin.push({ ...r, geminiReason: d.reason + ' (대상 유저를 찾을 수 없음)' });
        continue;
      }
      const warnings = target.warnings || [];
      warnings.push({ reason: r.category || '', at: Date.now(), source: 'auto-mod-bot' });
      await db.ref(`users/${accusedId}`).update({
        warnings,
        pendingWarningNotify: { at: Date.now(), notified: false }
      });
      await db.ref(`reports/${r.id}`).update({
        status: 'resolved',
        resolveAction: 'warn_user',
        resolvedBy: 'auto-mod-bot',
        resolvedAt: Date.now()
      });
      autoWarned.push({ ...r, target, geminiReason: d.reason });
    } else if (d.decision === 'LIKELY_DISMISS') {
      likelyDismiss.push({ ...r, geminiReason: d.reason });
    } else {
      needsAdmin.push({ ...r, geminiReason: d.reason });
    }
  }

  noEvidence.forEach(r => {
    needsAdmin.push({ ...r, geminiReason: '텍스트 증거 없는 신고 유형(프로필/유저 신고 등) - 자동판정 대상 아님, 직접 확인 필요' });
  });

  if (autoWarned.length === 0 && needsAdmin.length === 0 && likelyDismiss.length === 0) {
    console.log('처리할 신고 없음 - 스킵');
    process.exit(0);
  }

  const lines = [];
  lines.push(`오늘 처리 대상 신고: 총 ${pending.length}건 (자동경고 ${autoWarned.length} / 관리자 확인 필요 ${needsAdmin.length} / 기각 권장 ${likelyDismiss.length})`);
  lines.push('');

  if (autoWarned.length > 0) {
    lines.push('## ✅ 자동 경고 처리 완료 (봇이 이미 실행함, 대상자는 다음 로그인 시 경고 알림을 받습니다)');
    autoWarned.forEach(r => {
      lines.push(`- **${r.target.nickname || r.targetId}** (신고유형: ${r.type}, 사유: ${r.category || '(미기재)'})`);
      lines.push(`  - Gemini 판정 근거: ${r.geminiReason}`);
    });
    lines.push('');
  }

  if (needsAdmin.length > 0) {
    lines.push('## 🔴 관리자 직접 확인 필요 (정지/영구정지 검토 대상 - 자동집행하지 않음)');
    needsAdmin.forEach(r => {
      lines.push(`- 신고ID: \`${r.id}\` / 유형: ${r.type} / 사유: ${r.category || '(미기재)'} / 같은 대상 누적 신고자 수: ${r.sameTargetCount}`);
      lines.push(`  - Gemini 판정 근거: ${r.geminiReason}`);
    });
    lines.push('');
    lines.push('👉 관리자 대시보드(admin-reports.html)에서 위 신고 건들을 확인하고 정지/영구정지 등 조치를 직접 결정해주세요.');
    lines.push('');
  }

  if (likelyDismiss.length > 0) {
    lines.push('## ⚪ 기각 권장 (자동 기각하지 않음, 참고용)');
    likelyDismiss.forEach(r => {
      lines.push(`- 신고ID: \`${r.id}\` / 유형: ${r.type} / 사유: ${r.category || '(미기재)'}`);
      lines.push(`  - Gemini 판정 근거: ${r.geminiReason}`);
    });
  }

  fs.writeFileSync('review-result.md', lines.join('\n'));
  console.log(lines.join('\n'));
}

main().catch(err => {
  console.error('스크립트 오류:', err);
  process.exit(1);
});
