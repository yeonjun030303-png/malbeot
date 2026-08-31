// 봇 품질감사 담당 봇 (감찰팀) - 매주 토 17:00
// 지난 7일간 이 저장소의 GitHub Actions 실행 이력을 모아 봇별 성공/실패 횟수를 집계
// 별도 Secret 불필요: GitHub Actions가 자동 제공하는 GITHUB_TOKEN, GITHUB_REPOSITORY 사용

const fs = require('fs');

const TOKEN = process.env.GITHUB_TOKEN;
const REPO = process.env.GITHUB_REPOSITORY; // 예: yeonjun030303-png/malbeot
const WEEK_MS = 7 * 24 * 60 * 60 * 1000;

async function main() {
  const url = `https://api.github.com/repos/${REPO}/actions/runs?per_page=100`;
  const res = await fetch(url, {
    headers: {
      Authorization: `Bearer ${TOKEN}`,
      Accept: 'application/vnd.github+json'
    }
  });
  if (!res.ok) {
    console.error('GitHub Actions 실행 이력 조회 실패:', res.status);
    process.exit(1);
  }
  const data = await res.json();
  const now = Date.now();
  const recent = (data.workflow_runs || []).filter(r => (now - new Date(r.created_at).getTime()) <= WEEK_MS);

  const byWorkflow = {};
  recent.forEach(r => {
    const name = r.name || '(이름없음)';
    byWorkflow[name] = byWorkflow[name] || { success: 0, failure: 0, other: 0 };
    if (r.conclusion === 'success') byWorkflow[name].success++;
    else if (r.conclusion === 'failure') byWorkflow[name].failure++;
    else byWorkflow[name].other++;
  });

  const lines = [];
  lines.push('## 🔍 봇 품질감사 (최근 7일)');
  lines.push('');

  const problemWorkflows = Object.keys(byWorkflow).filter(name => byWorkflow[name].failure > 0);

  Object.keys(byWorkflow).forEach(name => {
    const s = byWorkflow[name];
    const total = s.success + s.failure + s.other;
    lines.push(`- ${name}: 총 ${total}회 (성공 ${s.success} / 실패 ${s.failure} / 기타 ${s.other})`);
  });

  if (problemWorkflows.length === 0) {
    lines.push('');
    lines.push('실패가 발생한 워크플로우가 없습니다.');
    fs.writeFileSync('bot-quality-result.md', '');
    console.log(lines.join('\n'));
    return;
  }

  lines.push('');
  lines.push('### 🚨 실패가 발생한 워크플로우');
  problemWorkflows.forEach(name => lines.push(`- ${name} (${byWorkflow[name].failure}회 실패) - Actions 탭에서 로그 확인 필요`));

  fs.writeFileSync('bot-quality-result.md', lines.join('\n'));
  console.log(lines.join('\n'));
}

main().catch(err => {
  console.error('봇품질감사 실패:', err);
  process.exit(1);
});
