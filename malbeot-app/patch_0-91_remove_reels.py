# -*- coding: utf-8 -*-
# 0-91: 말벗릴스(스토리) 기능 종료 - 화면에서 진입점을 모두 제거
#  - 커뮤니티 상단 서브탭(일상이야기/말벗릴스) 제거 -> 커뮤니티는 일상이야기만 남음
#  - 프로필 화면의 "내 스토리" 섹션 제거
#  - 온보딩/탈퇴 안내 문구에서 스토리·릴스 표현 정리
#  - 서버: 릴스 피드는 빈 목록으로 응답, 새 글/수정 시 릴스 유형으로는 저장되지 않게 고정
#  * 기존 릴스 게시물 데이터는 삭제하지 않고 그대로 보존(나중에 되살리거나 새 기능에 재활용 가능)

import io

def read(p):
    with io.open(p, "r", encoding="utf-8") as f:
        return f.read()

def write(p, s):
    with io.open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(s)

def rep(s, old, new, label):
    n = s.count(old)
    if n != 1:
        raise SystemExit("[실패] %s : 매칭 %d곳(1곳이어야 함). 수정 없이 중단." % (label, n))
    return s.replace(old, new, 1)

# ---------------- public/index.html ----------------
hp = "public/index.html"
h = read(hp)

h = rep(h, """      <div class="community-subtabs">
        <button type="button" class="community-subtab-btn active" data-logtype="story" onclick="switchCommunitySubtab('story')">일상이야기</button>
        <button type="button" class="community-subtab-btn" data-logtype="log" onclick="switchCommunitySubtab('log')">말벗릴스</button>
      </div>
""", "", "html: 커뮤니티 서브탭 제거")

h = rep(h, """      <div class="profile-posts-title profile-section-header" id="profileStoriesScrollHeader" onclick="toggleProfileMiniList('profileStoriesScroll')">
        <span>내 스토리 <span class="profile-count" id="profileStoriesScrollCount">(0개)</span></span>
        <i class="fa-solid fa-chevron-down accordion-arrow" id="profileStoriesScrollArrow" style="display:none;"></i>
      </div>
      <div class="profile-posts-scroll" id="profileStoriesScroll"><div style="text-align:center;color:var(--text-muted);font-size:12px;padding:16px;">불러오는 중...</div></div>
""", "", "html: 프로필 내 스토리 섹션 제거")

h = rep(h, "말벗스토리로 일상을 공유해요", "커뮤니티에서 일상을 공유해요", "html: 온보딩 문구")
h = rep(h, "작성한 게시글/스토리/릴스가 모두 삭제되며", "작성한 게시글이 모두 삭제되며", "html: 탈퇴 안내 문구")
write(hp, h)
print("[적용됨] public/index.html :: 커뮤니티 서브탭 / 프로필 내 스토리 / 안내 문구")

# ---------------- server.js ----------------
sp = "server.js"
s = read(sp)

s = rep(s, """      let raw = await getRawPosts();
      raw = raw.filter(p => p.logType === 'log' &&""",
"""      // 0-91: 말벗릴스 종료 - 기존 릴스 데이터는 보존하되 피드는 항상 빈 목록으로 응답
      if (true) return cb({ success: true, stories: [] });
      let raw = await getRawPosts();
      raw = raw.filter(p => p.logType === 'log' &&""", "server: 릴스 피드 비우기")

s = rep(s, "photo: imageBlocked ? '' : (data.photo || ''), logType: data.logType || 'story',",
           "photo: imageBlocked ? '' : (data.photo || ''), logType: 'story',", "server: 새 글 유형 고정")

s = rep(s, "post.logType = data.logType || post.logType || 'story';",
           "post.logType = post.logType || 'story'; // 0-91: 말벗릴스 종료로 유형 변경 불가", "server: 글 수정 유형 고정")
write(sp, s)
print("[적용됨] server.js :: 릴스 피드 비우기 / 유형 고정")
print("0-91 패치 완료.")