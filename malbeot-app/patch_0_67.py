import re

# ===== 1) moderation.js: NSFW 자동검사(tfjs-node/nsfwjs) 완전 제거 =====
new_moderation = '''// ===== 0-67: NSFW 자동검사(tfjs-node) 완전 비활성화 =====
// Render 무료 플랜(RAM 512MB)에서 @tensorflow/tfjs-node 자체의 기본 메모리 사용량이
// 너무 커서(네이티브 바이너리만으로 150~300MB대) 서버가 반복적으로 OOM(FatalProcessOutOfMemory)
// 으로 죽는 문제가 있었음. 이건 코드로 우회할 수 없는 순수 메모리 한도 문제라서,
// tfjs-node/nsfwjs를 아예 불러오지 않도록 제거함. 사진은 자동차단 없이 통과시키고,
// 신고가 들어오면 관리자가 직접 확인하는 방식으로 운영(텍스트 금지어 필터는 그대로 유지).

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
  const normalized = text.toLowerCase().replace(/\\s/g, '');
  return BANNED_WORDS.some(word => normalized.includes(word));
}

// 0-67: NSFW 모델은 더 이상 로드하지 않음(호출부 호환을 위한 no-op, 항상 즉시 resolve)
async function loadNsfwModel() {
  return null;
}

// 0-67: 이미지 자동검사는 항상 통과 처리. 사진 모더레이션은 신고 기반으로 운영.
async function checkImageNsfw(imageInput) {
  return {
    isNsfw: false,
    score: 0,
    error: 'NSFW 자동검사 비활성화(무료플랜 메모리절약, 신고기반 모더레이션으로 운영)'
  };
}

module.exports = {
  BANNED_WORDS,
  containsBannedWord,
  checkImageNsfw,
  loadNsfwModel
};
'''

with open('moderation.js', 'w', encoding='utf-8') as f:
    f.write(new_moderation)

# ===== 2) package.json: 이제 안 쓰는 무거운 패키지 제거 =====
with open('package.json', 'r', encoding='utf-8') as f:
    pkg = f.read()

for line in [
    '    "@tensorflow/tfjs-node": "^4.22.0",\n',
    '    "nsfwjs": "^4.3.0",\n',
    '    "sharp": "^0.35.3",\n',
]:
    assert line in pkg, f"package.json에서 해당 줄을 못 찾음: {line!r}"
    pkg = pkg.replace(line, '', 1)

with open('package.json', 'w', encoding='utf-8') as f:
    f.write(pkg)

print("패치 완료: moderation.js 교체, package.json에서 tfjs-node/nsfwjs/sharp 제거")
