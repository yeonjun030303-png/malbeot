const fs = require('fs');
const path = require('path');
const { callGemini } = require('./gemini-helper');

const POOL_PATH = path.join(__dirname, '..', 'dev-idea-pool.json');

function extractIdeas(markdown, source) {
  const chunks = markdown.split(/^### /m).slice(1);
  return chunks.map(chunk => {
    const lines = chunk.split('\n');
    const title = lines[0].trim();
    const detail = lines.slice(1).join('\n').trim();
    return { title, detail, source, addedDate: new Date().toISOString().slice(0, 10), status: 'new' };
  });
}

function loadPool() {
  if (!fs.existsSync(POOL_PATH)) return [];
  return JSON.parse(fs.readFileSync(POOL_PATH, 'utf8'));
}

function savePool(pool) {
  const trimmed = pool.slice(-500); // 최근 500개까지만 보관
  fs.writeFileSync(POOL_PATH, JSON.stringify(trimmed, null, 2), 'utf8');
}

async function main() {
  const blueOceanPath = path.join(__dirname, '..', 'blue-ocean-report.md');
  const painPointPath = path.join(__dirname, '..', 'pain-point-report.md');

  let pool = loadPool();
  if (fs.existsSync(blueOceanPath)) {
    pool.push(...extractIdeas(fs.readFileSync(blueOceanPath, 'utf8'), '블루오션기획관'));
  }
  if (fs.existsSync(painPointPath)) {
    pool.push(...extractIdeas(fs.readFileSync(painPointPath, 'utf8'), '불편함조사관'));
  }

  const notStarted = pool.filter(i => i.status !== 'started');
  const target = notStarted.slice(-100); // 미착수 아이디어 중 최근 100개

  const poolSummary = target
    .map((i, idx) => `${idx + 1}. [${i.source}/${i.addedDate}] ${i.title} - ${i.detail.slice(0, 200)}`)
    .join('\n');

  const prompt = `아래는 신개발팀이 지금까지 제안했지만 아직 실제 개발에 착수하지 않은 아이디어 목록입니다(최대 100개).

${poolSummary}

당신은 신개발팀장입니다. 아래 절차로 검토하세요:

1. 이 아이디어들을 종합 순위로 정렬하세요(1위가 가장 유망).
2. 각 아이디어에 대해 성격이 다른 4명의 위원(비관적 리스크형, 현실적 실무형, 법률·규제형, 사용자가치형)이 찬반 의견을 내는 미니 위원회 토론을 시뮬레이션해서 핵심 찬반 논리를 요약하세요.
3. 실현가능성을 판단하세요: 이미 존재하는 AI 서비스로 대체 가능한지, 무료 플랜(비용 없이)으로 구현 가능한지, 법적/행정적 리스크가 있는지.
4. 상위 20개는 상세히, 나머지는 순위와 한 줄 요약만 정리하세요.

마크다운 보고서 형식으로 작성하세요.`;

  const review = await callGemini(prompt);
  const output = `# 신개발팀장 주간 리포트\n생성일: ${new Date().toISOString().slice(0, 10)}\n대상 아이디어 수: ${target.length}\n\n${review}`;
  fs.writeFileSync(path.join(__dirname, '..', 'new-dev-lead-report.md'), output, 'utf8');

  savePool(pool);
  console.log('new-dev-lead-report.md 생성 완료');
}

main().catch(e => { console.error(e); process.exit(1); });
