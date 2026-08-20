const nsfwjs = require('nsfwjs');
const tf = require('@tensorflow/tfjs-node');
const sharp = require('sharp');

// 텍스트 금지어 목록
const BANNED_WORDS = [
  // 1. 심한 욕설 및 비하
  '씨발', '시발', '씨팔', '씨발놈', '씨발년', '씨발새끼',
  '개새끼', '개새', '개지랄', '좆', '좆같', '좆까',
  '병신', '븅신', '지랄',
  // 2. 패륜 및 가족 비하
  '느금', '느금마', '엠창', '엄창', '니엄마',
  '니애미', '니애비', '애미뒤진', '애비뒤진', '호로새끼',
  // 3. 성적 단어 및 음란 표현
  '섹스', '성관계', '자지', '보지', '자위',
  '딸딸이', '정액', '음모', '강간', '성폭행',
  '성매매', '조건만남', '원나잇', '야동', '포르노',
  // 4. 정치·사회적 극단 혐오 및 차별
  '일베', '메갈', '한남충', '틀딱', '짱깨',
  '쪽바리', '좌빨', '빨갱이', '자살해라', '살인'
];

function containsBannedWord(text) {
  if (!text) return false;
  const normalized = text.toLowerCase().replace(/\s/g, '');
  return BANNED_WORDS.some(word => normalized.includes(word));
}

// NSFW 이미지 감지 모델 (최초 1회 로드 후 재사용)
let nsfwModel = null;
async function loadNsfwModel() {
  if (!nsfwModel) {
    nsfwModel = await nsfwjs.load();
  }
  return nsfwModel;
}

// ===== 0-62: 무료 플랜(RAM 512MB) 502/503 완화 =====
// 1) 동시에 한 건만 실제 검사가 돌게 큐로 직렬화 -> 여러 명이 동시에 사진을 올려도 메모리 스파이크 방지
// 2) 검사 전 sharp로 300x300 이하로 축소한 뒤 디코딩 -> 원본 큰 이미지를 그대로 텐서로 올리지 않음
// 3) 이미 메모리가 위험 수준이면 검사를 건너뛰고 통과 처리 -> 서버가 죽어서 502/503 나는 것보다 나은 선택
//    (검사를 건너뛴 경우는 error 필드에 남겨서 나중에 로그로 확인 가능)
let nsfwQueue = Promise.resolve();
const MEMORY_GUARD_RSS_MB = 430; // Render 무료 플랜 512MB 중 이 이상이면 위험 수준으로 판단

function currentRssMb() {
  return process.memoryUsage().rss / (1024 * 1024);
}

async function shrinkForNsfw(buffer) {
  try {
    return await sharp(buffer)
      .resize(300, 300, { fit: 'inside', withoutEnlargement: true })
      .toFormat('jpeg', { quality: 70 })
      .toBuffer();
  } catch (err) {
    // 축소 실패 시 원본 그대로 사용(안전하게 폴백)
    return buffer;
  }
}

async function runNsfwCheck(imageInput) {
  const model = await loadNsfwModel();
  let imageBuffer = imageInput;
  if (typeof imageInput === 'string') {
    const base64 = imageInput.includes(',') ? imageInput.split(',')[1] : imageInput;
    imageBuffer = Buffer.from(base64, 'base64');
  }
  const shrunk = await shrinkForNsfw(imageBuffer);

  tf.engine().startScope();
  let predictions;
  try {
    const image = await tf.node.decodeImage(shrunk, 3);
    predictions = await model.classify(image);
    image.dispose();
  } finally {
    tf.engine().endScope();
  }

  const scoreMap = {};
  predictions.forEach(p => { scoreMap[p.className] = p.probability; });

  const dangerScore =
    (scoreMap['Porn'] || 0) +
    (scoreMap['Hentai'] || 0) +
    (scoreMap['Sexy'] || 0);

  return {
    isNsfw: dangerScore >= 0.95,
    score: dangerScore,
    details: predictions
  };
}

// imageInput: 이미지 파일의 Buffer 또는 data URI 문자열(data:image/...;base64,...)
const NSFW_CHECK_TIMEOUT_MS = 12000; // 0-64: 검사 1건이 이 시간을 넘기면 포기하고 통과 처리(큐가 영구히 막히는 것 방지)

function withTimeout(promise, ms, label) {
  let timer;
  const timeout = new Promise((resolve) => {
    timer = setTimeout(() => {
      console.warn(`NSFW 검사 타임아웃(${ms}ms 초과, 통과 처리): ${label}`);
      resolve({ isNsfw: false, score: 0, error: `타임아웃(${ms}ms) - 통과 처리` });
    }, ms);
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer));
}

async function checkImageNsfw(imageInput) {
  // 0-64: 이번 검사 결과를 기다리는 것과 별개로, 큐는 타임아웃 시점에 무조건 다음으로 넘어가게 함
  // (기존에는 runNsfwCheck가 응답 없이 멈추면 큐 전체가 영구히 막혀서 이후의 모든 사진 전송/프로필저장이
  //  같이 멈추는 문제가 있었음 - 채팅 사진전송/프로필 사진저장이 동시에 "먹통"이 되던 버그의 원인)
  const task = nsfwQueue.then(async () => {
    const rss = currentRssMb();
    if (rss >= MEMORY_GUARD_RSS_MB) {
      console.warn(`NSFW 검사 스킵(메모리 보호): 현재 RSS ${rss.toFixed(0)}MB`);
      return { isNsfw: false, score: 0, error: `메모리 보호로 검사 스킵(RSS ${rss.toFixed(0)}MB, 통과 처리)` };
    }
    try {
      return await withTimeout(runNsfwCheck(imageInput), NSFW_CHECK_TIMEOUT_MS, 'checkImageNsfw');
    } catch (err) {
      console.error('NSFW 검사 중 오류:', err);
      // 검사 실패 시 안전하게 통과시킬지 차단할지는 정책 결정 필요 (기본: 통과)
      return { isNsfw: false, score: 0, error: err.message };
    }
  });
  // 이번 검사가 실패/타임아웃되더라도 큐 자체는 끊기지 않고 다음 검사로 이어지게 함
  nsfwQueue = task.catch(() => {});
  return task;
}

module.exports = {
  BANNED_WORDS,
  containsBannedWord,
  checkImageNsfw,
  loadNsfwModel
};
