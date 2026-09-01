// 2단계: 결정위원회봇 - 팀장취합봇 결과(team-summaries.json)를 입력받아
// 본부장급 5인(서로 다른 성격)의 페르소나로 각각 Gemini를 호출해 안건(팀)별 찬반+근거를 생성하고 집계
const fs = require('fs');

const GEMINI_API_KEY = process.env.GEMINI_API_KEY;
const GEMINI_MODEL_PRIMARY = 'gemini-flash-latest';
const GEMINI_MODEL_FALLBACK = 'gemini-3.6-flash';

const PERSONAS = [
  { name: '원칙·리스크형', desc: '규정과 절차 준수를 최우선으로 여기며, 잠재적 리스크와 예외 상황을 엄격하게 짚어내는 성향' },
  { name: '성장·기대형', desc: '단기적 완벽함보다 성장 가능성과 기회를 중시하며, 다소 낙관적으로 판단하는 성향' },
  { name: '데이터·분석형', desc: '수치와 데이터, 재현 가능한 근거가 있을 때만 동의하며, 감이나 추측성 판단을 배격하는 성향' },
  { name: '고객·신뢰형', desc: '사용자/고객 신뢰와 서비스 평판에 미치는 영향을 최우선으로 보는 성향' },
  { name: '재무·효율형', desc: '비용 대비 효과와 운영 효율성을 최우선으로 따지는 성향' },
];

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function callGemini(prompt, model) {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${GEMINI_API_KEY}`;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 60000);
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] }),
      signal: controller.signal,
    });
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
      console.log(`주 모델 시도 ${i + 1} 실패: ${e.message}`);
      await sleep(backoffs[i]);
    }
  }
  for (let i = 0; i < 2; i++) {
    try {
      return await callGemini(prompt, GEMINI_MODEL_FALLBACK);
    } catch (e) {
      console.log(`대체 모델 시도 ${i + 1} 실패: ${e.message}`);
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

  return `당신은 회사의 결정위원회 소속 본부장이며, 성향은 다음과 같습니다: "${persona.desc}"

아래는 이번 주 각 팀(실행조직)의 팀장취합 보고 내용입니다. 각 팀의 이번 주 업무 처리 방식이 타당했는지, 당신의 성향에 따라 안건별로 찬성/반대를 판단하세요.

${agendaText}

반드시 아래 JSON 배열 형식으로만 답하세요. 다른 설명 문장은 절대 포함하지 마세요.
[
  {"team": "팀 이름", "verdict": "찬성 또는 반대", "reason": "한 문장 근거"}
]
안건(팀)은 위에 나온 팀 전체에 대해 빠짐없이 하나씩 판단하세요.`;
}

async function main() {
  const raw = fs.readFileSync('team-summaries.json', 'utf-8');
  const teamSummaries = JSON.parse(raw);

  const agendaTeams = Object.entries(teamSummaries)
    .filter(([, v]) => v.issueCount > 0)
    .map(([team, v]) => ({ team, issueCount: v.issueCount, summary: v.summary }));

  if (agendaTeams.length === 0) {
    const empty = { agendaCount: 0, teams: {}, note: '이번 주 이슈가 있었던 팀이 없어 위원회 안건 없음' };
    fs.writeFileSync('committee-result.json', JSON.stringify(empty, null, 2));
    console.log('안건 없음 - committee-result.json(빈 결과) 저장');
    return;
  }

  const perPersonaVotes = [];

  for (const persona of PERSONAS) {
    console.log(`${persona.name} 위원 검토 중...`);
    const prompt = buildPersonaPrompt(persona, agendaTeams);
    const responseText = await callGeminiWithRetry(prompt);
    const votes = parseJsonArray(responseText);
    if (!votes) {
      console.log(`${persona.name} 응답 파싱 실패 - 이번 위원 표는 집계에서 제외`);
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
        ? `위원회는 ${t.team}의 이번 주 처리 방식이 타당하다고 판단(찬성 ${approveCount} : 반대 ${opposeCount})`
        : `위원회는 ${t.team}의 이번 주 처리 방식에 재검토가 필요하다고 판단(찬성 ${approveCount} : 반대 ${opposeCount})`,
    };
  }

  fs.writeFileSync('committee-result.json', JSON.stringify(result, null, 2));
  console.log('committee-result.json 저장 완료');
}

main().then(() => process.exit(0)).catch(err => {
  console.error('결정위원회봇 실패:', err);
  process.exit(1);
});
