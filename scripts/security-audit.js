// 보안 점검관 봇
// - npm audit(high/critical 취약점), 코드 내 하드코딩된 API키/시크릿 패턴, Firebase 보안규칙 오픈 여부를 점검
// - 주간 실행, 이슈+이메일로 리포트

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

function runNpmAudit() {
  // 실제 앱 코드(malbeot-app/)에 package.json이 있으면 그쪽을 점검, 없으면 저장소 루트
  const appDir = path.join(process.cwd(), 'malbeot-app');
  const cwd = fs.existsSync(path.join(appDir, 'package.json')) ? appDir : process.cwd();
  if (!fs.existsSync(path.join(cwd, 'package-lock.json')) && !fs.existsSync(path.join(cwd, 'package.json'))) {
    return null; // 점검할 package.json 자체가 없음
  }
  try {
    const raw = execSync('npm audit --json', { encoding: 'utf8', maxBuffer: 20 * 1024 * 1024, cwd });
    return JSON.parse(raw);
  } catch (e) {
    // npm audit은 취약점이 있으면 non-zero exit코드를 내므로 stdout을 그대로 파싱
    if (e.stdout) {
      try { return JSON.parse(e.stdout); } catch (_) { return null; }
    }
    return null;
  }
}

function summarizeAudit(auditJson) {
  if (!auditJson || !auditJson.metadata || !auditJson.metadata.vulnerabilities) return null;
  const v = auditJson.metadata.vulnerabilities;
  const high = v.high || 0;
  const critical = v.critical || 0;
  if (high === 0 && critical === 0) return null;
  return { high, critical, total: v.total || 0 };
}

// 소스 파일에서 하드코딩된 키/시크릿으로 의심되는 패턴 스캔 (node_modules, .git 제외)
const SECRET_PATTERNS = [
  { name: 'Firebase/Google API Key', regex: /AIza[0-9A-Za-z\-_]{35}/g },
  { name: 'AWS Access Key', regex: /AKIA[0-9A-Z]{16}/g },
  { name: '일반 SK/PK 형태 시크릿', regex: /(sk|pk)_(live|test)_[0-9a-zA-Z]{16,}/g },
  { name: '하드코딩된 비밀번호 의심', regex: /(password|passwd|pwd)\s*[:=]\s*["'][^"']{6,}["']/gi },
];

const SCAN_EXCLUDE_DIRS = new Set(['node_modules', '.git', '.github']);
const SCAN_EXTENSIONS = new Set(['.js', '.json', '.html', '.env', '.yml', '.yaml']);

function walk(dir, files) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (SCAN_EXCLUDE_DIRS.has(entry.name)) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walk(full, files);
    } else if (SCAN_EXTENSIONS.has(path.extname(entry.name))) {
      files.push(full);
    }
  }
}

function scanForSecrets(rootDir) {
  const files = [];
  walk(rootDir, files);
  const findings = [];
  for (const file of files) {
    let content;
    try { content = fs.readFileSync(file, 'utf8'); } catch (_) { continue; }
    for (const pattern of SECRET_PATTERNS) {
      const matches = content.match(pattern.regex);
      if (matches) {
        findings.push({ file: path.relative(rootDir, file), pattern: pattern.name, count: matches.length });
      }
    }
  }
  return findings;
}

// Firebase 보안규칙 파일(있는 경우)에서 조건 없는 개방 규칙 탐지
function scanFirebaseRules(rootDir) {
  const candidates = ['database.rules.json', 'firestore.rules', 'malbeot-app/database.rules.json'];
  const findings = [];
  for (const rel of candidates) {
    const full = path.join(rootDir, rel);
    if (!fs.existsSync(full)) continue;
    const content = fs.readFileSync(full, 'utf8');
    if (/"\.read"\s*:\s*true/.test(content) || /"\.write"\s*:\s*true/.test(content)) {
      findings.push(rel);
    }
  }
  return findings;
}

function main() {
  const rootDir = process.cwd();
  const lines = [];

  const auditJson = runNpmAudit();
  const auditSummary = summarizeAudit(auditJson);
  const secretFindings = scanForSecrets(rootDir);
  const ruleFindings = scanFirebaseRules(rootDir);

  if (!auditSummary && secretFindings.length === 0 && ruleFindings.length === 0) {
    console.log('정상 - 특이사항 없음');
    process.exit(0);
  }

  lines.push('## 🔒 보안 점검 결과');
  lines.push('');

  if (auditSummary) {
    lines.push(`### 의존성 취약점 (npm audit)`);
    lines.push(`- high: ${auditSummary.high}건 / critical: ${auditSummary.critical}건 (전체 ${auditSummary.total}건)`);
    lines.push('- 조치: `npm audit fix` 실행 후 breaking change 여부 확인, 안 되면 `npm audit fix --force`');
    lines.push('');
  }

  if (secretFindings.length > 0) {
    lines.push(`### ⚠️ 하드코딩 의심 시크릿 (오탐 가능 - 반드시 직접 확인)`);
    secretFindings.forEach(f => {
      lines.push(`- \`${f.file}\` - ${f.pattern} 패턴 ${f.count}건`);
    });
    lines.push('');
  }

  if (ruleFindings.length > 0) {
    lines.push(`### 🚪 Firebase 보안규칙 전체 4cz개 의심`);
    ruleFindings.forEach(f => lines.push(`- \`${f}\` 에 조건 없는 .read/.write true 발견`));
    lines.push('');
  }

  fs.writeFileSync('review-result.md', lines.join('\n'));
  console.log(lines.join('\n'));
}

main();
