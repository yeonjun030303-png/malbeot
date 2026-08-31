// 아이디어제안 담당 봇 (기획예산팀, 수익화·예산 한정) - 매주 화 17:00
// 무리한 개발 없이 적용 가능한 수익화 아이디어를 Gemini로 제안
// 503/429 재시도: 지수백오프(20/40/80/80s) 후 대체모델로 2회(15초 간격) 재시도

const fs = require('fs');

const PRIMARY_MODEL = 'gemini-flash-latest';
const FALLBACK_MODEL = 'gemini-3.6-flash';
const API_KEY = process.env.GEMINI_API_KEY;

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function callGemini(model, prompt) {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${API_KEY}`;
  let res;
  try {
    console.log('[진단] fetch 호출 직전: ' + model + ' / ' + new Date().toISOString());
    res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] }),
      signal: AbortSignal.timeout(60000)
    });
    console.log('[진단] fetch 완료, status: ' + res.status + ' / ' + new Date().toISOString());
  } catch (e) {
    console.log('[진단] catch 진입: ' + e.name + ' / ' + e.message + ' / ' + new Date().toISOString());
    const err = new Error('Gemini ' + model + ' 타임아웃/네트워크 오류: ' + e.message);
    err.status = 503;
    throw err;
  }
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
  const prompt = '너는 소규모 1인 개발 데이팅/말벗형 채팅 앱의 수익화 컨설턴트야. 개발 리소스와 예산이 매우 한정된 상황을 전제로,\n' +
    '이번 주에 바로 검토 가능한 수익화 아이디어 3개를 제안해줘 (예: 구독 등급 조정, 소액 인앱결제 아이템, 광고 삽입 지점 등).\n' +
    '형식: 마크다운, "## 💰 수익화 아이디어" 제목으로 시작, 아이디어마다 (1)내용 (2)예상 구현 난이도 (3)예상 효과를 정리해줘.';

  try {
    const text = await callWithRetry(prompt);
    fs.writeFileSync('monetization-result.md', text);
    console.log(text);
  } catch (e) {
    console.error('수익화 아이디어 제안 실패(재시도 소진):', e.message);
    fs.writeFileSync('monetization-result.md', '⚠️ 이번 주 수익화 아이디어 생성 실패 (Gemini API 응답 없음)');
  }
}

main().then(() => process.exit(0)).catch(err => { console.error(err); process.exit(1); });
