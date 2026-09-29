# -*- coding: utf-8 -*-
# 0-103: UI 자연스러움 개선 + 커뮤니티 카드 재정렬(니터즈 스타일 벤치마크, 색은 브랜드 색 유지)
import io, os, shutil, subprocess

P = "public/index.html"
if not os.path.exists(P):
    raise SystemExit("[실패] %s 없음. C:\\malbeot\\malbeot-app 에서 실행했는지 확인" % P)

s = io.open(P, "r", encoding="utf-8").read()
bak = P + ".bak"
shutil.copyfile(P, bak)

def rep(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit("[실패] %s : 매칭 %d곳(1곳이어야 함). 수정 없이 중단." % (label, n))
    return text.replace(old, new, 1)

# ---------- A. 전역 터치/스크롤 자연스러움 ----------
GLOBAL_CSS = """<style>
*,*::before,*::after{-webkit-tap-highlight-color:transparent;}
.content-area,.fs-body,.full-screen-overlay,.tab-content{-webkit-overflow-scrolling:touch;overscroll-behavior:contain;}
button,.btn,.nav-item,.post-action-btn,.post-dots-btn,.icon-btn{transition:transform .12s ease;}
button:active,.btn:active,.nav-item:active,.post-action-btn:active,.post-dots-btn:active{transform:scale(.94);}
"""
s = rep(s, "<style>", GLOBAL_CSS, "0-103 전역 CSS 삽입")

# ---------- B. 커뮤니티 카드 CSS 재정렬 ----------
OLD_CARD_CSS = """.post-row{padding:14px 4px;border-bottom:1px solid var(--border-color);cursor:pointer;}
.post-row-top{display:flex;align-items:center;gap:8px;}
.post-meta{flex:1;min-width:0;}
.post-meta-line1{display:flex;align-items:baseline;gap:6px;flex-wrap:wrap;}
.post-meta-line1 .nick{font-size:13px;font-weight:700;color:var(--primary);cursor:pointer;}
.post-meta-line1 .tagxs{font-size:11px;color:var(--text-muted);}
.post-time{font-size:11px;color:var(--text-muted);white-space:nowrap;}
.post-dots-btn{background:none;border:none;color:var(--text-muted);font-size:14px;cursor:pointer;padding:4px 6px;}
.post-preview{font-size:13px;color:var(--text-main);margin:8px 0 8px 0;line-height:1.4;overflow:hidden;text-overflow:ellipsis;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;line-clamp:2;}
.post-actions{display:flex;gap:16px;align-items:center;}
.post-action-btn{background:none;border:none;font-size:12px;color:var(--text-muted);display:flex;align-items:center;gap:5px;cursor:pointer;font-weight:600;}
.post-action-btn.liked{color:var(--danger);}
.post-action-btn.liked i{color:var(--danger);}"""

NEW_CARD_CSS = """.community-feed{padding:6px 0;}
.post-row{background:var(--bg-card);border:1px solid var(--border-color);border-radius:16px;padding:14px;margin:10px 12px;box-shadow:0 1px 4px rgba(0,0,0,.05);cursor:pointer;}
.post-row:active{transform:scale(.98);}
.post-row-top{display:flex;align-items:center;gap:9px;}
.post-meta{flex:1;min-width:0;}
.post-meta-line1{display:flex;align-items:baseline;gap:6px;flex-wrap:wrap;}
.post-meta-line1 .nick{font-size:14px;font-weight:800;color:var(--text-main);cursor:pointer;}
.post-meta-line1 .tagxs{font-size:11px;color:var(--text-muted);}
.post-time{font-size:11px;color:var(--text-muted);white-space:nowrap;}
.post-dots-btn{background:none;border:none;color:var(--text-muted);font-size:14px;cursor:pointer;padding:4px 6px;}
.post-preview{font-size:14px;color:var(--text-main);margin:10px 0;line-height:1.5;overflow:hidden;text-overflow:ellipsis;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;line-clamp:2;}
.post-actions{display:flex;gap:16px;align-items:center;margin-top:10px;padding-top:10px;border-top:1px solid var(--border-color);}
.post-action-btn{background:none;border:none;font-size:12px;color:var(--text-muted);display:flex;align-items:center;gap:5px;cursor:pointer;font-weight:600;}
.post-action-btn.liked{color:var(--danger);}
.post-action-btn.liked i{color:var(--danger);}"""

s = rep(s, OLD_CARD_CSS, NEW_CARD_CSS, "0-103 카드 CSS 재정렬")

# ---------- B-2. 미디어(이미지/동영상) 모서리·여백 ----------
OLD_MEDIA = """    const mediaHtml = (p.photo && !p.filtered && !p.deleted) ? (p.mediaType==='video'
      ? `<video src="${p.photo}" muted controls playsinline style="width:100%;max-height:260px;border-radius:10px;display:block;margin:8px auto;object-fit:cover;"></video>`
      : `<img src="${p.photo}" style="width:100%;max-height:260px;border-radius:10px;display:block;margin:8px auto;object-fit:cover;" onclick="event.stopPropagation();openPostDetailScreen('${p.id}')">`) : '';"""

NEW_MEDIA = """    const mediaHtml = (p.photo && !p.filtered && !p.deleted) ? (p.mediaType==='video'
      ? `<video src="${p.photo}" muted controls playsinline style="width:100%;max-height:280px;border-radius:14px;display:block;margin:10px 0;object-fit:cover;"></video>`
      : `<img src="${p.photo}" style="width:100%;max-height:280px;border-radius:14px;display:block;margin:10px 0;object-fit:cover;" onclick="event.stopPropagation();openPostDetailScreen('${p.id}')">`) : '';"""

s = rep(s, OLD_MEDIA, NEW_MEDIA, "0-103 미디어 스타일")

# ---------- B-3. 프로필 사진 크기(36px -> 44px) ----------
OLD_AVATAR = """<span onclick="event.stopPropagation();openProfileDetailScreen('${p.authorId}')" style="cursor:pointer;">${avatarHtmlFor(postAuthorObj(p),'avatar-sm')}</span>"""
NEW_AVATAR = """<span onclick="event.stopPropagation();openProfileDetailScreen('${p.authorId}')" style="cursor:pointer;">${avatarHtmlFor(postAuthorObj(p),'avatar-md')}</span>"""
s = rep(s, OLD_AVATAR, NEW_AVATAR, "0-103 카드 프로필 사진 크기")

with io.open(P, "w", encoding="utf-8", newline="\n") as f:
    f.write(s)

# ---------- JS 문법 검사 ----------
def js_errors(html):
    import re, tempfile
    bad = []
    blocks = re.findall(r'<script(?![^>]*\bsrc=)(?![^>]*\btype=)[^>]*>(.*?)</script>', html, re.S)
    for i, code in enumerate(blocks):
        fd, path = tempfile.mkstemp(suffix=".js")
        os.close(fd)
        try:
            with io.open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(code)
            r = subprocess.run(["node", "--check", path], capture_output=True)
            if r.returncode != 0:
                bad.append((i, r.stderr.decode("utf-8", "ignore")))
        finally:
            os.remove(path)
    return bad

errs = js_errors(s)
if errs:
    shutil.copyfile(bak, P)
    os.remove(bak)
    for i, msg in errs:
        print("script block %d error:\n%s" % (i, msg))
    raise SystemExit("[실패] JS 문법 오류. 원래 파일로 복구함.")

os.remove(bak)
print("[적용됨] 0-103: 전역 터치/스크롤 자연스러움 + 커뮤니티 카드 재정렬(니터즈 스타일, 색 유지)")