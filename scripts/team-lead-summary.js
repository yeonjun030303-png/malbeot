// 1단계: 팀장취합봇 - 지난 1주일 GitHub 이슈를 6개팀으로 그룹핑 후 Gemini에 "한 번만" 호출해
// 팀 전체 요약(팀장 코멘트)을 받아옴(429 quota 절약을 위해 팀별 개별호출 → 배치 1회 호출로 변경)
const fs = require('fs');

const GITHUB_TOKEN = process.env.GITHUB_TOKEN;
const REPO = process.env.GITHUB_REPOSITORY;
const GEMINI_KEYS = [process.env.GEMINI_API_KEY, process.env.GEMINI_API_KEY_2, process.env.GEMINI_API_KEY_3].filter(Boolean);
let keyIndex = 0;

const TEAM_LABEL_MAP = {
  '개발팀': ['daily-review'],
  '성장팀': ['idea', 'marketing'],
  '운영팀': ['inquiry-monitor', 'review-monitor', 'report-review'],
  '기획예산팀': ['budget-report', 'metrics', 'monetization-idea', 'benchmark-research'],
  '행정법무팀': ['policy-check', 'license-audit'],
  '감찰팀': ['bot-quality-audit', 'abuse-detection', 'security-audit'],
};

const GEMINI_MODEL_PRIMARY = 'gemini-flash-latest';
const GEMINI_MODEL_FALLBACK = 'gemini-3.6-flash';

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function fetchRecentIssues() {
  const since = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();
  const url = `https://api.github.com/repos/${REPO}/issues?state=all&since=${since}&labels=bot&per_page=100`;
  const res = await fetch(url, {
    headers: {
      Authorization: `Bearer ${GITHUB_TOKEN}`,
      Accept: 'application/vnd.github+json',
    },
  });
  if (!res.ok) throw new Error(`GitHub API 오류: ${res.status}`);
  const issues = await res.json();
  return issues.filter(i => !i.pull_request && new Date(i.created_at) >= new Date(since));
}

function groupByTeam(issues) {
  const grouped = {};
  for (const team of Object.keys(TEAM_LABEL_MAP)) grouped[team] = [];
  for (const issue of issues) {
    const labels = issue.labels.map(l => (typeof l === 'string' ? l : l.name));
    for (const [team, teamLabels] of Object.entries(TEAM_LABEL_MAP)) {
      if (labels.some(l => teamLabels.includes(l))) {
        grouped[team].push({ title: issue.title, url: issue.html_url, labels, created_at: issue.created_at });
        break;
      }
    }
  }
  return grouped;
}

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
        console.log(`주 모델 429 - 키 로테이션(${(keyIndex % GEMINI_KEYS.length) + 1}/${GEMINI_KEYS.length}번째 키)`);
        await sleep(2000);
        continue;
      }
      console.log(`주 모델 시도 ${i + 1} 실패: ${e.message}`);
      await sleep(backoffs[i]);
    }
  }
  for (let i = 0; i < 2; i++) {
    try {
      return await callGemini(prompt, GEMINI_MODEL_FALLBACK);
    } catch (e) {
      if (e.status === 429 && GEMINI_KEYS.length > 1) {
        keyIndex++;
        console.log(`대체 모델 429 - 키 로테이션(${(keyIndex % GEMINI_KEYS.length) + 1}/${GEMINI_KEYS.length}번째 키)`);
        await sleep(2000);
        continue;
      }
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

function buildBatchPrompt(teamsWithIssues) {
  const teamText = teamsWithIssues.map(({ team, issues }) => {
    const list = issues.map(i => `- [${i.labels.join(',')}] ${i.title}`).join('\n');
    return `### ${team} (이슈 ${issues.length}건)\n${list}`;
  }).join('\n\n');

  return `당신은 각 팀의 팀장들입니다. 아래는 지난 1주일간 각 팀 소속 자동화 봇이 생성한 이슈 목록입니다.
팀별로 아래 형식을 지켜 팀장 코멘트를 작성해주세요. 각 팀마다 이번 주 상황 요약과 다음 액션 우선순위를 담아 팀장다운 어투로 작성해주세요.

${teamText}

반드시 아래 JSON 배열 형태로만 응답해주세요. 다른 설명이나 마크다운 없이 JSON만 출력해야 합니다.
[
  {"team": "팀 이름", "summary": "팀장 코멘트 전체 텍스트(여러 문단 가능, \\n으로 줄바꿈)"}
]
응답은 팀 이름이 위와 정확히 일치해야 하며, 목록에 없는 팀은 포함하지 마세요.`;
}

async function main() {
  const issues = await fetchRecentIssues();
  const grouped = groupByTeam(issues);
  const summaries = {};

  const teamsWithIssues = Object.entries(grouped)
    .filter(([, teamIssues]) => teamIssues.length > 0)
    .map(([team, teamIssues]) => ({ team, issues: teamIssues }));

  for (const team of Object.keys(grouped)) {
    if (grouped[team].length === 0) {
      summaries[team] = { issueCount: 0, summary: '이번 주 등록된 이슈 없음', issues: [] };
    }
  }

  if (teamsWithIssues.length > 0) {
    console.log(`${teamsWithIssues.length}개 팀 배치 요약 요청 중(1회 호출)...`);
    const prompt = buildBatchPrompt(teamsWithIssues);
    const responseText = await callGeminiWithRetry(prompt);
    const parsed = parseJsonArray(responseText);

    for (const { team, issues } of teamsWithIssues) {
      const found = parsed && parsed.find(p => p.team === team);
      summaries[team] = {
        issueCount: issues.length,
        summary: found ? found.summary : '(Gemini 응답 실패 - 이슈 목록만 첨부)',
        issues,
      };
    }
  }

  fs.writeFileSync('team-summaries.json', JSON.stringify(summaries, null, 2));
  console.log('team-summaries.json 저장 완료');
}

main().then(() => process.exit(0)).catch(err => {
  console.error('팀장취합봇 실패:', err);
  process.exit(1);
});
