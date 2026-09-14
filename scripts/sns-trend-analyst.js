const fs = require('fs');
const path = require('path');
const { callGemini } = require('./gemini-helper');

const HISTORY_PATH = path.join(__dirname, '..', 'sns-trend-history.json');

async function naverBlogSearch(query) {
  const id = process.env.NAVER_CLIENT_ID;
  const secret = process.env.NAVER_CLIENT_SECRET;
  if (!id || !secret) return null;
  const res = await fetch(
    `https://openapi.naver.com/v1/search/blog.json?query=${encodeURIComponent(query)}&display=10&sort=sim`,
    { headers: { 'X-Naver-Client-Id': id, 'X-Naver-Client-Secret': secret } }
  );
  if (!res.ok) { console.log('네이버 검색 API 오류', res.status); return null; }
  return res.json();
}

async function getOwnInstagramInsights() {
  const token = process.env.IG_ACCESS_TOKEN;
  const igUserId = process.env.IG_BUSINESS_ACCOUNT_ID;
  if (!token || !igUserId) return null;
  const res = await fetch(
    `https://graph.facebook.com/v19.0/${igUserId}/media?fields=id,caption,like_count,comments_count,timestamp&limit=10&access_token=${token}`
  );
  if (!res.ok) { console.log('인스타그램 인사이트 조회 실패', res.status); return null; }
  return res.json();
}

async function main() {
  const keywords = ['데이팅 앱', '채팅 앱 추천', '온라인 친구 만들기', '외로움 해소'];
  const naverResults = [];
  for (const kw of keywords) {
    const r = await naverBlogSearch(kw);
    if (r) naverResults.push({ keyword: kw, items: r.items });
  }

  const igInsights = await getOwnInstagramInsights();

  const prompt = `아래는 네이버 블로그 검색 결과와 자사 인스타그램 게시물 성과 데이터입니다. (둘 다 없을 수도 있음)

네이버 검색 결과: ${naverResults.length ? JSON.stringify(naverResults).slice(0, 3000) : '데이터 없음(API 키 미등록)'}
자사 인스타 성과: ${igInsights ? JSON.stringify(igInsights).slice(0, 2000) : '데이터 없음(인스타그램 연동 전)'}

이를 바탕으로:
1. 사람들이 좋아하는 문장 패턴, 제목 후킹 포인트, 톤을 분석하세요.
2. 내일 "말벗" 앱 포스팅(인스타그램/네이버블로그)에 바로 적용 가능한 캡션·제목 가이드라인을 작성하세요.
3. 데이터가 부족하면 일반적으로 알려진 SNS 카피라이팅 원칙을 바탕으로 제안하세요.`;

  const analysis = await callGemini(prompt);

  let history = [];
  if (fs.existsSync(HISTORY_PATH)) history = JSON.parse(fs.readFileSync(HISTORY_PATH, 'utf8'));
  history.push({ date: new Date().toISOString().slice(0, 10), analysis });
  if (history.length > 60) history = history.slice(-60);
  fs.writeFileSync(HISTORY_PATH, JSON.stringify(history, null, 2), 'utf8');

  fs.writeFileSync(
    path.join(__dirname, '..', 'sns-trend-report.md'),
    `# SNS트렌드분석관 일일 리포트\n생성일: ${new Date().toISOString().slice(0, 10)}\n\n${analysis}`,
    'utf8'
  );
  console.log('sns-trend-report.md 생성 완료');
}

main().catch(e => { console.error(e); process.exit(1); });
