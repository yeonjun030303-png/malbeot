// 약관·정책 점검 담당 봇 (행정법무팀) - 매월 1일 17:00
// 데이팅/채팅 앱에 적용되는 국내 최신 법/정책 변화를 Gemini로 점검(일반 지식 기반 조언, 법률 자문 아님)
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
    res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] }),
      signal: AbortSignal.timeout(60000)
    });
  } catch (e) {
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
  const prompt = '너는 국내 1인 개발 데이팅/채팅 앱 운영자를 돕는 법무 리서치 보조야(정식 법률 자문이 아님을 전제로).\n' +
    '개인정보보호법, 정보통신망법, 청소년보호법 등 데이팅/채팅 앱 운영에 영향을 줄 수 있는 국내 법/정책의 최근 동향이나 자주 놓치는 준수사항을 정리해줘.\n' +
    '형식: 마크다운, "## ⚖️ 약관·정책 점검" 제목으로 시작, 항목별로 (1)내용 (2)우리 앱 약관/정책에서 확인해볼 점을 정리하고, ' +
    '마지막 줄에 "본 리포트는 참고용이며 정식 법률 자문이 아닙니다."를 반드시 포함해줘.';

  try {
    const text = await callWithRetry(prompt);
    fs.writeFileSync('policy-result.md', text);
    console.log(text);
  } catch (e) {
    console.error('약관정책점검 실패(재시도 소진):', e.message);
    fs.writeFileSync('policy-result.md', '⚠️ 이번 달 약관·정책 점검 리포트 생성 실패 (Gemini API 응답 없음)');
  }
}

main();
