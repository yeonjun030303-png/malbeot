const nsfwjs = require('nsfwjs');
const tf = require('@tensorflow/tfjs-node');

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

// imageBuffer: 이미지 파일의 Buffer
async function checkImageNsfw(imageBuffer) {
  try {
    const model = await loadNsfwModel();
    const image = await tf.node.decodeImage(imageBuffer, 3);
    const predictions = await model.classify(image);
    image.dispose();

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
  } catch (err) {
    console.error('NSFW 검사 중 오류:', err);
    // 검사 실패 시 안전하게 통과시킬지 차단할지는 정책 결정 필요 (기본: 통과)
    return { isNsfw: false, score: 0, error: err.message };
  }
}

module.exports = {
  BANNED_WORDS,
  containsBannedWord,
  checkImageNsfw
};