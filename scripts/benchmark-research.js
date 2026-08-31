// 벤치마킹 담당 봇 (기획예산팀) - 매주 금 17:00
// 경쟁 데이팅/말벗형 채팅 앱 트렌드를 Gemini로 리서치
// 503/429 재시도: 지수백오프(20/40/80/80s) 후 대체모델로 2회(15초 간격) 재시도

const fs = require('fs');

const PRIMARY_MODEL = 'gemini-flash-latest';
const FALLBACK_MODEL = 'gemini-3.6-flash';
const API_KEY = process.env.GEMINI_API_KEY;

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function callGemini(model, prompt) {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${API_KEY}`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] })
  });
  if (!res.ok) {
    const err = new Error(`Gemini ${model} 응답 오류: ${res.status}`);
    err.status = res.status;
    throw err;
  }
  const data = await res.json();
  return (data.candidates && data.candidates[0] && data.candidates[0].content
    && data.candidates[0].content.parts && data.candidates[0].content.parts[0]
    && data.candidates[0].content.parts[0].text) || '';
}

async function callWithRetry(prompt) {
  const backoffs = [20000, 40000, 80000, 80000];
  for (let i = 0; i < backoffs.length; i++) {
    try { return await callGemini(PRIMARY_MODEL, prompt); }
    catch (e) {
      if (![429, 503].includes(e.status)) throw e;
      await sleep(backoffs[i]);
    }
  }
  for (let i = 0; i < 2; i++) {
    try { return await callGemini(FALLBACK_MODEL, prompt); }
    catch (e) {
      if (![429, 503].includes(e.status) || i === 1) throw e;
      await sleep(15000);
    }
  }
}

async function main() {
  const prompt = '너는 데이팅/소셜 채팅 앱 시장 분석가야. 국내외 유사 데이팅/말벗형 채팅 앱들의 최근 트렌드, 신기능, UX 변화를 조사해서 한국어로 정리해줘.\n' +
    '형식: 마크다운, "## 📊 벤치마킹 리포트" 제목으로 시작, 앱별로 소제목을 나눠서 3~5개 앱의 최근 동향을 요약하고 마지막에 "### 우리 앱에 적용 가능한 시사점" 섹션을 추가해줘.';

  try {
    const text = await callWithRetry(prompt);
    fs.writeFileSync('benchmark-result.md', text);
    console.log(text);
  } catch (e) {
    console.error('벤치마킹 리서치 실패(재시도 소진):', e.message);
    fs.writeFileSync('benchmark-result.md', '⚠️ 이번 주 벤치마킹 리포트 생성 실패 (Gemini API 응답 없음)');
  }
}

main();
