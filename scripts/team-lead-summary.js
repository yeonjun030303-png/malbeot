// 1단계: 팀장취합봇 - 지난 1주일 GitHub 이슈를 6개 팀별로 그룹핑하고 Gemini로 팀장 코멘트 생성
const fs = require('fs');

const GITHUB_TOKEN = process.env.GITHUB_TOKEN;
const REPO = process.env.GITHUB_REPOSITORY; // owner/repo, Actions가 자동 제공
const GEMINI_API_KEY = process.env.GEMINI_API_KEY;

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
    return data.candidates?.[0]?.content?.parts?.[0]?.text || '(응답 없음)';
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

function buildPrompt(team, issues) {
  const list = issues.map(i => `- [${i.labels.join(',')}] ${i.title}`).join('\n');
  return `당신은 "${team}" 팀장입니다. 아래는 지난 1주일간 팀 산하 자동화 봇들이 등록한 이슈 목록입니다.\n\n${list}\n\n이 내용을 검토해서 다음 형식으로 답하세요:\n1) 이번 주 팀 현황 3줄 요약\n2) 팀장으로서의 코멘트(이슈들 중 중요하거나 반복되는 문제가 있으면 지적)\n3) 실장에게 보고할 핵심 포인트 1~2개`;
}

async function main() {
  const issues = await fetchRecentIssues();
  const grouped = groupByTeam(issues);
  const summaries = {};

  for (const [team, teamIssues] of Object.entries(grouped)) {
    if (teamIssues.length === 0) {
      summaries[team] = { issueCount: 0, summary: '이번 주 등록된 이슈 없음', issues: [] };
      continue;
    }
    console.log(`${team} 처리 중 (${teamIssues.length}건)...`);
    const prompt = buildPrompt(team, teamIssues);
    const result = await callGeminiWithRetry(prompt);
    summaries[team] = {
      issueCount: teamIssues.length,
      summary: result || '(Gemini 응답 실패 - 이슈 목록만 첨부)',
      issues: teamIssues,
    };
  }

  fs.writeFileSync('team-summaries.json', JSON.stringify(summaries, null, 2));
  console.log('team-summaries.json 저장 완료');
}

main().then(() => process.exit(0)).catch(err => {
  console.error('팀장취합봇 실패:', err);
  process.exit(1);
});
