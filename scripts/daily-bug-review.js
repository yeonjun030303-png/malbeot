// 데일리 버그 리뷰 스크립트
// - 최근 30시간 이내 커밋의 diff를 모아서 Gemini에게 리뷰를 맡김
// - 결과를 review-result.md 파일로 저장 (없으면 워크플로우가 이슈를 안 만듦 = 변경사항 없거나 특이사항 없을 때)
// - Gemini가 503(일시 과부하) 등으로 응답 실패하면 지수 백오프로 재시도하고,
//   그래도 계속 실패하면 대체 모델(gemini-3.6-flash)로 한 번 더 시도함

const { execSync } = require('child_process');
const fs = require('fs');

function run(cmd) {
  return execSync(cmd, { encoding: 'utf-8' }).trim();
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function callGeminiModel(model, prompt, apiKey, maxRetries, baseDelayMs) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    const res = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] })
      }
    );
    const data = await res.json();
    const text = data?.candidates?.[0]?.content?.parts?.[0]?.text;

    if (text) return text;

    const isRetryable = data?.error?.code === 503 || data?.error?.code === 429;
    console.error(`[${model}] Gemini 응답 실패 (시도 ${attempt}/${maxRetries}):`, JSON.stringify(data));

    if (isRetryable && attempt < maxRetries) {
      const delay = baseDelayMs * Math.pow(2, attempt - 1); // 지수 백오프
      console.log(`[${model}] ${delay / 1000}초 후 재시도...`);
      await sleep(delay);
      continue;
    }
    return null;
  }
  return null;
}

async function callGemini(prompt, apiKey) {
  // 1차: 주 모델(gemini-flash-latest)로 지수 백오프 재시도 (20s, 40s, 80s)
  let text = await callGeminiModel('gemini-flash-latest', prompt, apiKey, 4, 20000);
  if (text) return text;

  // 2차: 주 모델이 계속 과부하면 대체 모델로 한 번 더 시도
  console.log('주 모델(gemini-flash-latest) 실패 - 대체 모델(gemini-3.6-flash)로 재시도');
  text = await callGeminiModel('gemini-3.6-flash', prompt, apiKey, 2, 15000);
  return text;
}

async function main() {
  let commits;
  try {
    commits = run(`git log --since="30 hours ago" --format=%H`);
  } catch (e) {
    commits = '';
  }
  if (!commits) {
    console.log('최근 30시간 내 커밋 없음 - 리뷰 스킵');
    return;
  }

  const commitList = commits.split('\n').filter(Boolean);
  const oldest = commitList[commitList.length - 1];

  let diff;
  try {
    diff = run(`git diff ${oldest}~1 HEAD`);
  } catch (e) {
    diff = run(`git diff ${oldest} HEAD`);
  }

  if (!diff || diff.length < 10) {
    console.log('실질적인 변경사항 없음 - 리뷰 스킵');
    return;
  }

  const MAX = 15000;
  const truncated = diff.length > MAX ? diff.slice(0, MAX) + '\n...(길어서 생략됨)' : diff;

  const prompt = `당신은 시니어 백엔드/풀스택 개발자입니다. 아래는 채팅 앱(Node/Express+Socket.io+Firebase 백엔드, Render 무료 플랜 배포, 메모리 512MB 한도) 저장소의 최근 변경사항(git diff)입니다.

다음 관점에서 한국어로 검토해주세요:
- 명백한 버그나 처리되지 않은 엣지케이스
- 에러 핸들링 누락 (특히 소켓/DB 콜백 - cb가 항상 호출되는지)
- 보안 이슈 (하드코딩된 키, 인증 우회, 인젝션 등)
- 메모리/성능 이슈 (이 서버는 메모리 한도가 빡빡해서 특히 중요)

각 항목에 심각도(CRITICAL/WARNING/INFO)를 붙이고 파일명과 대략적인 위치를 언급해주세요. 특별한 문제가 없으면 "특이사항 없음"이라고만 답하세요. 과장하지 말고 실제 위험한 것만 짚어주세요.

--- DIFF ---
${truncated}`;

  const apiKey = process.env.GEMINI_API_KEY;
  const reviewText = await callGemini(prompt, apiKey);

  if (!reviewText) {
    console.error('Gemini 응답을 최종적으로 받지 못함 (주/대체 모델 모두 재시도 소진) - 이번 회차는 리뷰 스킵');
    return;
  }

  if (reviewText.includes('특이사항 없음') && reviewText.length < 50) {
    console.log('특이사항 없음 - 이슈 생성 스킵');
    return;
  }

  fs.writeFileSync('review-result.md', reviewText);
  console.log(reviewText);
}

main().catch(err => {
  console.error('스크립트 오류:', err);
});
