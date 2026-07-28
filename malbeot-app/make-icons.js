const sharp = require('sharp');
const fs = require('fs');

const svg = fs.readFileSync('public/logo.svg', 'utf8');

// 흰 배경 위에 로고를 중앙 배치한 정사각형 SVG로 감싸기
const wrapped = (size) => `
<svg width="${size}" height="${size}" viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg">
  <rect width="512" height="512" fill="#ffffff"/>
  <g transform="translate(96, 176) scale(2)">
    ${svg.replace(/<\?xml[^>]*\?>/, '').replace(/<svg[^>]*>/, '').replace('</svg>', '')}
  </g>
</svg>`;

const sizes = [
  { name: 'apple-touch-icon.png', size: 180 },
  { name: 'icon-192.png', size: 192 },
  { name: 'icon-512.png', size: 512 }
];

(async () => {
  for (const { name, size } of sizes) {
    await sharp(Buffer.from(wrapped(size)))
      .resize(size, size)
      .png()
      .toFile(`public/${name}`);
    console.log(`생성 완료: public/${name}`);
  }
})();
