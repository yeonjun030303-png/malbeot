# -*- coding: utf-8 -*-
# 0-101: SNS포스팅집행관 개편
#  - 스크린샷 방식 삭제(초상권), 자체 디자인 카드(puppeteer)만 사용
#  - PNG -> JPEG(4:5, 1080x1350) 변환
#  - 인스타 로그인 방식 주소(graph.instagram.com)로 변경
#  - 후킹 형식 5종 순환 + 금지어 검사 + 대학생 타깃 문구
import io, os, shutil, subprocess

P = "scripts/sns-content-publisher.js"
if not os.path.exists(P):
    raise SystemExit("[실패] %s 없음. C:\\malbeot 에서 실행했는지 확인" % P)

JS = r'''const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const { callGemini } = require('./gemini-helper');

const REPO = process.env.GITHUB_REPOSITORY;
const TODAY = new Date().toISOString().slice(0, 10);
const IMAGE_REL_PATH = `sns-images/${TODAY}.jpg`;
const IMAGE_ABS_PATH = path.join(__dirname, '..', IMAGE_REL_PATH);
const IG_HOST = 'https://graph.instagram.com/v21.0';

const FORMATS = ['공감형', '질문형', '리스트형', '상황극형', '관심사형'];
const FORMAT_GUIDE = {
  '공감형': '대학생이 일상에서 느끼는 심심함/혼자인 순간을 짚는 공감 한 줄로 시작',
  '질문형': '"너는 어느 쪽?" 같은 가벼운 선택 질문으로 시작해서 댓글을 유도',
  '리스트형': '"이럴 때 말벗 켜는 사람 특징 3가지"처럼 짧은 리스트',
  '상황극형': '카톡/과제/시험기간/공강 같은 상황을 짧은 대사 톤으로 묘사',
  '관심사형': 'MBTI, 게임, 카페, 여행 등 관심사로 사람을 만난다는 점을 강조'
};
const BANNED = /랜덤\s*채팅|치유|상담|365일|24시간|100%|무조건|AI|인공지능|힐링/i;

const THEMES = [
  { bg: '#2F6BFF', fg: '#FFFFFF', ac: '#FFD166' },
  { bg: '#FFFFFF', fg: '#14223F', ac: '#2F6BFF' },
  { bg: '#FF7A59', fg: '#FFFFFF', ac: '#14223F' },
  { bg: '#EAF0FF', fg: '#14223F', ac: '#FF7A59' }
];

function dayIndex() {
  return Math.floor(Date.now() / 86400000);
}

function esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function cardHtml(hook, sub, theme) {
  const len = hook.replace(/\s/g, '').length;
  const size = len <= 12 ? 104 : len <= 20 ? 84 : 68;
  return `<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@500;900&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{width:1080px;height:1350px;background:${theme.bg};color:${theme.fg};font-family:'Noto Sans KR','Noto Sans CJK KR',sans-serif;position:relative;overflow:hidden;}
.dot1{position:absolute;right:-120px;top:-120px;width:420px;height:420px;border-radius:50%;background:${theme.ac};opacity:.9;}
.dot2{position:absolute;left:-90px;bottom:180px;width:240px;height:240px;border-radius:50%;background:${theme.ac};opacity:.35;}
.wrap{position:absolute;left:90px;right:90px;top:400px;}
.hook{font-size:${size}px;font-weight:900;line-height:1.3;word-break:keep-all;}
.sub{margin-top:44px;font-size:42px;font-weight:500;line-height:1.5;word-break:keep-all;opacity:.92;}
.foot{position:absolute;left:90px;right:90px;bottom:80px;display:flex;justify-content:space-between;align-items:center;font-size:36px;font-weight:900;}
.tag{font-size:28px;font-weight:500;opacity:.8;}
</style></head><body>
<div class="dot1"></div><div class="dot2"></div>
<div class="wrap"><div class="hook">${esc(hook)}</div><div class="sub">${esc(sub)}</div></div>
<div class="foot"><span>말벗</span><span class="tag">관심사로 만나는 사람들 · 19+</span></div>
</body></html>`;
}

async function makeCardImage(hook, sub) {
  const sharp = require('sharp');
  const puppeteer = require('puppeteer');
  const theme = THEMES[dayIndex() % THEMES.length];
  const browser = await puppeteer.launch({ args: ['--no-sandbox'] });
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1080, height: 1350 });
    await page.setContent(cardHtml(hook, sub, theme), { waitUntil: 'networkidle0', timeout: 30000 });
    await page.evaluate(() => document.fonts.ready);
    const png = await page.screenshot({ type: 'png' });
    await sharp(png).flatten({ background: '#ffffff' }).jpeg({ quality: 90 }).toFile(IMAGE_ABS_PATH);
  } finally {
    await browser.close();
  }
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

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function publishToInstagram(caption, imageUrl) {
  const token = process.env.IG_ACCESS_TOKEN;
  const igUserId = process.env.IG_BUSINESS_ACCOUNT_ID;
  if (!token || !igUserId) { console.log('인스타그램 미연동 상태 - 게시 건너뜀'); return null; }

  await sleep(15000); // raw.githubusercontent 반영 대기
  const createRes = await fetch(
    `${IG_HOST}/${igUserId}/media?image_url=${encodeURIComponent(imageUrl)}&caption=${encodeURIComponent(caption)}&access_token=${token}`,
    { method: 'POST' }
  );
  const createData = await createRes.json();
  if (!createData.id) throw new Error(`미디어 컨테이너 생성 실패: ${JSON.stringify(createData)}`);

  await sleep(5000);
  const publishRes = await fetch(
    `${IG_HOST}/${igUserId}/media_publish?creation_id=${createData.id}&access_token=${token}`,
    { method: 'POST' }
  );
  return publishRes.json();
}

async function checkRecentPerformance() {
  const token = process.env.IG_ACCESS_TOKEN;
  const igUserId = process.env.IG_BUSINESS_ACCOUNT_ID;
  if (!token || !igUserId) return '인스타그램 미연동 상태 - 성과 조회 불가';
  const res = await fetch(
    `${IG_HOST}/${igUserId}/media?fields=id,caption,like_count,comments_count,timestamp&limit=3&access_token=${token}`
  );
  if (!res.ok) return `성과 조회 실패(${res.status})`;
  const data = await res.json();
  return JSON.stringify(data.data, null, 2);
}

function parseJson(text) {
  const m = String(text).match(/\{[\s\S]*\}/);
  if (!m) return null;
  try { return JSON.parse(m[0]); } catch (e) { return null; }
}

function buildPrompt(trendGuide, format) {
  return `당신은 20대 초반 대학생을 대상으로 하는 SNS 마케터입니다.
"말벗"은 관심사(취미, MBTI, 만남 목적)로 실제 사람들과 채팅하는 19세 이상 전용 앱입니다.

[오늘의 트렌드 가이드]
${trendGuide || '(없음)'}

[오늘의 형식] ${format}: ${FORMAT_GUIDE[format]}

규칙:
- 대상은 대학생. 말투는 친구에게 말하듯 짧고 가볍게. 이모지는 캡션에 2개 이내.
- 트렌드 단어는 어휘로만 자연스럽게 쓰고, 다른 계정의 문장이나 유행 문장을 그대로 따라 쓰지 않는다.
- 실제 사람들과 채팅하는 앱이라는 점만 말한다. AI, 상담, 치유, 위로 약속, 랜덤채팅, 과장 표현(100%, 무조건, 24시간, 365일)은 쓰지 않는다.
- 연예인, 브랜드, 드라마/영화, 노래 제목, 특정 학교 이름은 쓰지 않는다.
- hook은 공백 포함 20자 이내, 스크롤을 멈추게 하는 한 줄.
- sub는 hook 보충 한 줄(30자 이내).
- caption은 첫 줄 후킹, 본문 3~4줄, 마지막 줄 행동 유도(예: 프로필 링크에서 확인).
- hashtags는 6~8개, 일반 단어만(예: 대학생, 공강, 시험기간, mbti, 친구만들기).
- blog_title, blog_body(500자 내외)는 네이버 블로그용.

반드시 아래 JSON만 출력하세요(코드블록 금지):
{"hook":"","sub":"","caption":"","hashtags":["",""],"blog_title":"","blog_body":""}`;
}

async function generate(trendGuide, format) {
  for (let i = 0; i < 2; i++) {
    const raw = await callGemini(buildPrompt(trendGuide, format));
    const obj = parseJson(raw);
    if (!obj || !obj.hook || !obj.caption) continue;
    const tags = (obj.hashtags || []).map(t => String(t).replace(/^#/, '').trim()).filter(t => t && !BANNED.test(t));
    const all = [obj.hook, obj.sub, obj.caption, obj.blog_title, obj.blog_body].join(' ');
    if (BANNED.test(all)) { console.log('금지어 검출, 재생성 시도', i + 1); continue; }
    return { ...obj, tags };
  }
  return null;
}

async function main() {
  fs.mkdirSync(path.dirname(IMAGE_ABS_PATH), { recursive: true });

  const trendReportPath = path.join(__dirname, '..', 'sns-trend-report.md');
  const trendGuide = fs.existsSync(trendReportPath) ? fs.readFileSync(trendReportPath, 'utf8') : '';
  const format = FORMATS[dayIndex() % FORMATS.length];

  const g = await generate(trendGuide, format);
  let report;

  if (!g) {
    report = `# SNS포스팅집행관 일일 리포트
생성일: ${TODAY}

## 결과
금지어 검사 또는 생성 실패로 오늘은 게시하지 않았습니다.
`;
  } else {
    const igCaption = `${g.caption.trim()}\n\n${g.tags.map(t => '#' + t).join(' ')}\n\n19세 이상 이용 가능`;

    await makeCardImage(g.hook, g.sub || '');
    await pushImageToRepo();
    const imageUrl = getRawImageUrl();

    let igResult = null;
    try {
      igResult = await publishToInstagram(igCaption, imageUrl);
    } catch (e) {
      console.log('인스타그램 게시 실패:', e.message);
    }
    const performance = await checkRecentPerformance();

    report = `# SNS포스팅집행관 일일 리포트
생성일: ${TODAY}
형식: ${format}

## 이미지 문구
${g.hook}
${g.sub || ''}

## 인스타그램 캡션
${igCaption}

## 사용 이미지
자체 제작 카드 이미지(JPEG 1080x1350) (${imageUrl})

## 인스타그램 게시 결과
${igResult ? JSON.stringify(igResult, null, 2) : '미연동 상태 또는 실패 - 게시 건너뜀(수동 등록 필요)'}

## 최근 게시물 반응(재검토)
${performance}

## 네이버 블로그 (반자동 - 아래 내용 복붙해서 직접 등록해주세요)
제목: ${g.blog_title}

${g.blog_body}
`;
  }

  fs.writeFileSync(path.join(__dirname, '..', 'sns-content-report.md'), report, 'utf8');
  console.log('sns-content-report.md 생성 완료');
}

main().catch(e => { console.error(e); process.exit(1); });
'''

bak = P + ".bak"
shutil.copyfile(P, bak)
with io.open(P, "w", encoding="utf-8", newline="\n") as f:
    f.write(JS)

r = subprocess.run(["node", "--check", P], capture_output=True, text=True)
if r.returncode != 0:
    shutil.copyfile(bak, P)
    os.remove(bak)
    print(r.stderr)
    raise SystemExit("[실패] 문법 오류. 원래 파일로 복구함.")

os.remove(bak)
print("[적용됨] scripts/sns-content-publisher.js 교체 완료 (문법 검사 통과)")