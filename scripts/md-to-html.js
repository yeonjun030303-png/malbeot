// 마크다운(.md)을 가독성 좋은 HTML 파일로 변환
// 0-84: 마크다운 표(|...|) 렌더링 + 🚨/✅ 배지 색상 + h4 지원 + 카드형 여백 정리
const fs = require('fs');

function mdToHtml(md) {
  const lines = md.split('\n');
  const outLines = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const next = lines[i + 1];
    if (/^\s*\|.*\|\s*$/.test(line) && next && /^\s*\|[\s:|-]+\|\s*$/.test(next)) {
      const headerCells = line.split('|').map(c => c.trim()).filter(c => c.length > 0);
      let table = '<table class="report-table"><thead><tr>' +
        headerCells.map(c => `<th>${c}</th>`).join('') + '</tr></thead><tbody>';
      i += 2;
      while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) {
        const cells = lines[i].split('|').map(c => c.trim());
        const rowCells = cells.slice(1, cells.length - 1);
        table += '<tr>' + rowCells.map(c => `<td>${c}</td>`).join('') + '</tr>';
        i++;
      }
      table += '</tbody></table>';
      outLines.push(table);
      continue;
    }
    outLines.push(line);
    i++;
  }

  let html = outLines.join('\n')
    .replace(/^#### (.*)$/gm, '<h4>$1</h4>')
    .replace(/^### (.*)$/gm, '<h3>$1</h3>')
    .replace(/^## (.*)$/gm, '<h2>$1</h2>')
    .replace(/^# (.*)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.*?)\*\*/g, '<b>$1</b>')
    .replace(/^- (.*)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>\n?)+/g, m => `<ul>${m}</ul>`);

  html = html.split('\n\n').map(p => (p.startsWith('<') ? p : `<p>${p}</p>`)).join('\n');

  return html
    .replace(/🚨위험/g, '<span class="badge badge-danger">🚨위험</span>')
    .replace(/✅정상/g, '<span class="badge badge-ok">✅정상</span>');
}

const mdFile = process.argv[2] || 'review-result.md';
const htmlFile = process.argv[3] || 'report.html';
const title = process.argv[4] || '리포트';
const md = fs.readFileSync(mdFile, 'utf-8');
const html = `<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
body{font-family:'Malgun Gothic',sans-serif;max-width:700px;margin:30px auto;line-height:1.7;color:#222;padding:0 20px}
h1{color:#5b3ec8;border-bottom:2px solid #5b3ec8;padding-bottom:8px}
h2{color:#333;margin-top:28px}
h3{color:#3d2a85;margin-top:24px;background:#f5f3fb;padding:8px 12px;border-radius:8px}
h4{color:#5b3ec8;margin-top:18px;background:#faf9fd;padding:6px 10px;border-left:3px solid #5b3ec8;border-radius:4px}
li{margin:6px 0}
p{margin:10px 0}
.meta{color:#888;font-size:13px;margin-bottom:20px}
table.report-table{border-collapse:collapse;width:100%;margin:14px 0;font-size:14px}
table.report-table th,table.report-table td{border:1px solid #e0ddf0;padding:8px 10px;text-align:left}
table.report-table th{background:#5b3ec8;color:#fff}
table.report-table tr:nth-child(even){background:#faf9fd}
.badge{display:inline-block;padding:2px 8px;border-radius:12px;font-weight:bold;font-size:13px}
.badge-danger{background:#fdecea;color:#c62828}
.badge-ok{background:#e8f5e9;color:#2e7d32}
</style></head><body>
<h1>${title}</h1>
<div class="meta">생성일시: ${new Date().toLocaleString('ko-KR', {timeZone:'Asia/Seoul'})}</div>
${mdToHtml(md)}
</body></html>`;

fs.writeFileSync(htmlFile, html);
console.log(htmlFile + ' 생성 완료');
