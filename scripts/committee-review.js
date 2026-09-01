// 2단계: 결정위원회봇(committee-review.js) - 1단계 결과(team-summaries.json)를 입력받음
// 페르소나 5인(성격 다른 임원급)이 각자 관점으로 매주 팀별 결과를 재검토하고 찬반+근거를 생성
const fs = require('fs');

const GEMINI_KEYS = [process.env.GEMINI_API_KEY, process.env.GEMINI_API_KEY_2, process.env.GEMINI_API_KEY_3].filter(Boolean);
let keyIndex = 0;
const GEMINI_MODEL_PRIMARY = 'gemini-flash-latest';
const GEMINI_MODEL_FALLBACK = 'gemini-3.6-flash';

const PERSONAS = [
  { name: '원칙·리스크형', desc: '규정 준수와 리스크 관리를 최우선으로, 애매한 경우 보수적으로 판단하고 절차상 문제를 엄격히 지적' },
  { name: '성장·기대형', desc: '단기 손실보다 성장 가능성과 기회를 중시, 다소 공격적인 실행을 옹호' },
  { name: '데이터·분석형', desc: '감정보다 데이터, 숫자로 검증 안 된 근거는 받아들이지 않고 정량 분석 위주로 판단' },
  { name: '고객·신뢰형', desc: '유저/고객 신뢰와 평판에 미칠 영향을 최우선으로 고려' },
  { name: '재무·효율형', desc: '비용 대비 효과와 리소스 효율성을 최우선으로 고려' },
];

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function callGemini(prompt, model) {
  const key = GEMINI_KEYS[keyIndex % GEMINI_KEYS.length];
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${key}`;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 60000);
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] }),
      signal: controller.signal,
    });
    if (res.status === 429) {
      const err = new Error('Gemini API 오류 429');
      err.status = 429;
      throw err;
    }
    if (!res.ok) throw new Error(`Gemini API 오류 ${res.status}`);
    const data = await res.json();
    return data.candidates?.[0]?.content?.parts?.[0]?.text || '';
  } finally {
    clearTimeout(timeout);
  }
}

async function callGeminiWithRetry(prompt) {
  const backoffs = [20000, 40000, 80000, 80000];
  for (let i = 0; i < backoffs.length; i++) {
    try {
      return await callGemini(prompt, GEMINI_MODEL_PRIMARY);
    } catch (e) {
      if (e.status === 429 && GEMINI_KEYS.length > 1) {
        keyIndex++;
        console.log(`주 모델 429 - 다음 키로 전환(${(keyIndex % GEMINI_KEYS.length) + 1}/${GEMINI_KEYS.length}번 키)`);
        await sleep(2000);
        continue;
      }
      console.log(`주 모델 실패 ${i + 1} 시도: ${e.message}`);
      await sleep(backoffs[i]);
    }
  }
  for (let i = 0; i < 2; i++) {
    try {
      return await callGemini(prompt, GEMINI_MODEL_FALLBACK);
    } catch (e) {
      if (e.status === 429 && GEMINI_KEYS.length > 1) {
        keyIndex++;
        console.log(`대체 모델 429 - 다음 키로 전환(${(keyIndex % GEMINI_KEYS.length) + 1}/${GEMINI_KEYS.length}번 키)`);
        await sleep(2000);
        continue;
      }
      console.log(`대체 모델 실패 ${i + 1} 시도: ${e.message}`);
      await sleep(15000);
    }
  }
  return null;
}

function parseJsonArray(text) {
  if (!text) return null;
  const cleaned = text.replace(/```json/gi, '').replace(/```/g, '').trim();
  try {
    const parsed = JSON.parse(cleaned);
    return Array.isArray(parsed) ? parsed : null;
  } catch (e) {
    console.log('JSON 파싱 실패:', e.message);
    return null;
  }
}

function buildPersonaPrompt(persona, agendaTeams) {
  const agendaText = agendaTeams.map(t =>
    `### ${t.team} (이슈 ${t.issueCount}건)\n${t.summary}`
  ).join('\n\n');

  return `너는 회사의 결정위원회 임원 중 한 명이고, 성격은 다음과 같다: "${persona.desc}"

아래는 이번 주 각 팀(부서)에서 취합된 업무 결과 요약이다. 각 팀 별로 이번 주 처리 방식이 타당했는지, 문제나 리스크 신호가 있었는지 판단하고 그에 따라 찬성/반대를 결정하라.

${agendaText}

반드시 아래 JSON 배열 형식으로만 답하라. 다른 부연 설명은 절대 하지 마라.
[
  { "team": "팀 이름", "verdict": "찬성 또는 반대", "reason": "한 문장 근거" }
]
`;
}

async function main() {
  const raw = fs.readFileSync('team-summaries.json', 'utf-8');
  const teamSummaries = JSON.parse(raw);

  const agendaTeams = Object.entries(teamSummaries)
    .filter(([, v]) => v.issueCount > 0)
    .map(([team, v]) => ({ team, issueCount: v.issueCount, summary: v.summary }));

  if (agendaTeams.length === 0) {
    const empty = { agendaCount: 0, teams: {}, note: '이번 주 이슈 안건이 없어서 위원회 심의 없이 종료' };
    fs.writeFileSync('committee-result.json', JSON.stringify(empty, null, 2));
    console.log('안건 없음 - committee-result.json(빈 상태) 저장');
    return;
  }

  const perPersonaVotes = [];

  for (const persona of PERSONAS) {
    console.log(`${persona.name} 의견 검토 중...`);
    const prompt = buildPersonaPrompt(persona, agendaTeams);
    const responseText = await callGeminiWithRetry(prompt);
    const votes = parseJsonArray(responseText);
    if (!votes) {
      console.log(`${persona.name} 응답 파싱 실패 - 이번 페르소나는 스킵`);
      continue;
    }
    perPersonaVotes.push({ persona: persona.name, votes });
  }

  const result = { agendaCount: agendaTeams.length, teams: {} };

  for (const t of agendaTeams) {
    const opinions = [];
    let approveCount = 0;
    let opposeCount = 0;

    for (const p of perPersonaVotes) {
      const v = p.votes.find(x => x.team === t.team);
      if (!v) continue;
      opinions.push({ persona: p.persona, verdict: v.verdict, reason: v.reason });
      if (v.verdict === '찬성') approveCount++;
      else if (v.verdict === '반대') opposeCount++;
    }

    result.teams[t.team] = {
      approveCount,
      opposeCount,
      opinions,
      recommendation: approveCount >= opposeCount
        ? `찬성 우세 - ${t.team}의 이번 주 처리 방식이 타당하다는 판단으로 위원회 결론 (찬성 ${approveCount} : 반대 ${opposeCount})`
        : `반대 우세 - ${t.team}의 이번 주 처리 방식에 재검토가 필요하다는 위원회 판단 (찬성 ${approveCount} : 반대 ${opposeCount})`,
    };
  }

  fs.writeFileSync('committee-result.json', JSON.stringify(result, null, 2));
  console.log('committee-result.json 저장 완료');
}

main().then(() => process.exit(0)).catch(err => {
  console.error('위원회검토봇 실패:', err);
  process.exit(1);
});
