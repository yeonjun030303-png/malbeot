// 마크다운(review-result.md)을 가독성 좋은 HTML 파일(report.html)로 변환
const fs = require('fs');

function mdToHtml(md) {
  return md
    .replace(/^### (.*)$/gm, '<h3>$1</h3>')
    .replace(/^## (.*)$/gm, '<h2>$1</h2>')
    .replace(/^# (.*)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.*?)\*\*/g, '<b>$1</b>')
    .replace(/^- (.*)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>\n?)+/g, m => `<ul>${m}</ul>`)
    .split('\n\n').map(p => p.startsWith('<') ? p : `<p>${p}</p>`).join('\n');
}

const title = process.argv[2] || '리포트';
const md = fs.readFileSync('review-result.md', 'utf-8');
const html = `<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
body{font-family:'Malgun Gothic',sans-serif;max-width:700px;margin:30px auto;line-height:1.7;color:#222;padding:0 20px}
h1{color:#5b3ec8;border-bottom:2px solid #5b3ec8;padding-bottom:8px}
h2{color:#333;margin-top:28px}
li{margin:6px 0}
p{margin:10px 0}
.meta{color:#888;font-size:13px;margin-bottom:20px}
</style></head><body>
<h1>${title}</h1>
<div class="meta">생성일: ${new Date().toLocaleString('ko-KR', {timeZone:'Asia/Seoul'})}</div>
${mdToHtml(md)}
</body></html>`;

fs.writeFileSync('report.html', html);
console.log('report.html 생성 완료');
