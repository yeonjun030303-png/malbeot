const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const { callGemini } = require('./gemini-helper');

const REPO = process.env.GITHUB_REPOSITORY;
const TODAY = new Date().toISOString().slice(0, 10);
const IMAGE_REL_PATH = `sns-images/${TODAY}.png`;
const IMAGE_ABS_PATH = path.join(__dirname, '..', IMAGE_REL_PATH);

async function makeCardImage(caption) {
  const sharp = require('sharp');
  const escaped = caption.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const svg = `
  <svg width="1080" height="1080" xmlns="http://www.w3.org/2000/svg">
    <rect width="100%" height="100%" fill="#FFDE59"/>
    <foreignObject x="80" y="300" width="920" height="480">
      <div xmlns="http://www.w3.org/1999/xhtml" style="font-family:sans-serif;font-size:56px;font-weight:bold;color:#222;line-height:1.4;">
        ${escaped}
      </div>
    </foreignObject>
    <text x="80" y="1000" font-size="40" fill="#222" font-family="sans-serif">말벗 - 마음을 나누는 친구</text>
  </svg>`;
  await sharp(Buffer.from(svg)).png().toFile(IMAGE_ABS_PATH);
}

async function takeScreenshot() {
  const puppeteer = require('puppeteer');
  const browser = await puppeteer.launch({ args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1080, height: 1080 });
  await page.goto('https://malbeot-1.onrender.com', { waitUntil: 'networkidle2', timeout: 30000 });
  await page.screenshot({ path: IMAGE_ABS_PATH });
  await browser.close();
}

async function pushImageToRepo() {
  fs.mkdirSync(path.dirname(IMAGE_ABS_PATH), { recursive: true });
  execSync('git config user.email "bot@cnsstudiokorea.com"');
  execSync('git config user.name "말벗 SNS관리자 봇"');
  execSync(`git add ${IMAGE_REL_PATH}`);
  execSync(`git commit -m "SNS 포스팅 이미지 ${TODAY}"`);
  execSync('git push');
}

function getRawImageUrl() {
  return `https://raw.githubusercontent.com/${REPO}/main/${IMAGE_REL_PATH}`;
}

async function publishToInstagram(caption, imageUrl) {
  const token = process.env.IG_ACCESS_TOKEN;
  const igUserId = process.env.IG_BUSINESS_ACCOUNT_ID;
  if (!token || !igUserId) { console.log('인스타그램 미연동 상태 - 게시 건너뜀'); return null; }

  const createRes = await fetch(
    `https://graph.facebook.com/v19.0/${igUserId}/media?image_url=${encodeURIComponent(imageUrl)}&caption=${encodeURIComponent(caption)}&access_token=${token}`,
    { method: 'POST' }
  );
  const createData = await createRes.json();
  if (!createData.id) throw new Error(`미디어 컨테이너 생성 실패: ${JSON.stringify(createData)}`);

  const publishRes = await fetch(
    `https://graph.facebook.com/v19.0/${igUserId}/media_publish?creation_id=${createData.id}&access_token=${token}`,
    { method: 'POST' }
  );
  return publishRes.json();
}

async function checkYesterdayPerformance() {
  const token = process.env.IG_ACCESS_TOKEN;
  const igUserId = process.env.IG_BUSINESS_ACCOUNT_ID;
  if (!token || !igUserId) return '인스타그램 미연동 상태 - 성과 조회 불가';
  const res = await fetch(
    `https://graph.facebook.com/v19.0/${igUserId}/media?fields=id,caption,like_count,comments_count,timestamp&limit=3&access_token=${token}`
  );
  if (!res.ok) return `성과 조회 실패(${res.status})`;
  const data = await res.json();
  return JSON.stringify(data.data, null, 2);
}

async function main() {
  const trendReportPath = path.join(__dirname, '..', 'sns-trend-report.md');
  const trendGuide = fs.existsSync(trendReportPath) ? fs.readFileSync(trendReportPath, 'utf8') : '';

  const captionPrompt = `아래는 오늘의 SNS 트렌드 분석 가이드입니다.

${trendGuide}

이 가이드를 참고해서 "말벗"(마음을 나누는 친구, 실시간 채팅·커뮤니티 앱) 오늘자 인스타그램 캡션 1개와 네이버 블로그 포스팅용 제목+본문 1개를 작성하세요.

형식:
[인스타그램 캡션]
(캡션 + 해시태그 5~10개)

[네이버 블로그 제목]
(제목)

[네이버 블로그 본문]
(본문, 500자 내외)`;

  const content = await callGemini(captionPrompt);
  const igCaptionMatch = content.match(/\[인스타그램 캡션\]([\s\S]*?)\[네이버 블로그 제목\]/);
  const igCaption = igCaptionMatch ? igCaptionMatch[1].trim() : content.slice(0, 300);

  const useScreenshot = Math.random() < 0.5;
  try {
    if (useScreenshot) await takeScreenshot();
    else await makeCardImage(igCaption.slice(0, 80));
  } catch (e) {
    console.log('스크린샷 실패, 카드 이미지로 대체:', e.message);
    await makeCardImage(igCaption.slice(0, 80));
  }

  await pushImageToRepo();
  const imageUrl = getRawImageUrl();

  let igResult = null;
  try {
    igResult = await publishToInstagram(igCaption, imageUrl);
  } catch (e) {
    console.log('인스타그램 게시 실패:', e.message);
  }

  const performance = await checkYesterdayPerformance();

  const report = `# SNS포스팅집행관 일일 리포트
생성일: ${TODAY}

## 오늘 생성한 콘텐츠
${content}

## 사용 이미지
${useScreenshot ? '앱 실제화면 스크린샷' : '텍스트+아이콘 카드 이미지'} (${imageUrl})

## 인스타그램 게시 결과
${igResult ? JSON.stringify(igResult, null, 2) : '미연동 상태 - 게시 건너뜀(수동 등록 필요)'}

## 최근 게시물 반응(재검토)
${performance}

## 네이버 블로그 (반자동 - 아래 내용 복붙해서 직접 등록해주세요)
${content}
`;

  fs.writeFileSync(path.join(__dirname, '..', 'sns-content-report.md'), report, 'utf8');
  console.log('sns-content-report.md 생성 완료');
}

main().catch(e => { console.error(e); process.exit(1); });
