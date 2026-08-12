# -*- coding: utf-8 -*-
"""
0-17: 차단한 사용자의 글(커뮤니티/홈)과 말벗스토리(릴스)를 목록에서 완전히 숨김
실행 위치: malbeot 저장소 루트 (malbeot-app 폴더가 보이는 곳)
사용법: python3 patch_0_17_block_hide_feed.py
"""
import os, sys

ROOT = os.getcwd()
APP = os.path.join(ROOT, "malbeot-app")
if not os.path.isdir(APP):
    print("!! malbeot-app 폴더를 찾을 수 없습니다. 저장소 루트에서 실행하세요."); sys.exit(1)

INDEX = os.path.join(APP, "public", "index.html")

def read(p):
    with open(p, encoding="utf-8") as f: return f.read()

def write(p, s):
    with open(p, "w", encoding="utf-8") as f: f.write(s)

def replace_once(content, old, new, label, path):
    if new in content:
        print(f"   (건너뜀-이미적용됨) {label}")
        return content
    if old not in content:
        print(f"!! 패치 실패: {label} ({path}) — 원본 텍스트 못찾음"); sys.exit(1)
    if content.count(old) != 1:
        print(f"!! 패치실패 1개 아님({content.count(old)}개): {label} ({path})"); sys.exit(1)
    print(f"   적용: {label}")
    return content.replace(old, new)

h = read(INDEX)

# 1) 공용 헬퍼 함수 추가 (renderPosts 바로 위)
h = replace_once(h,
"""function renderPosts(list){""",
"""// 내가 차단한 사용자가 작성한 글/스토리는 홈·커뮤니티·릴스 목록에서 아예 노출되지 않도록 걸러냄
function filterOutBlockedAuthors(list){
  const blockedIds = (currentUser && currentUser.blockedUserIds) || [];
  if (!blockedIds.length) return list || [];
  return (list || []).filter(p => !blockedIds.includes(p.authorId));
}
function renderPosts(list){""",
    "filterOutBlockedAuthors 헬퍼 함수 추가", INDEX)

# 2) loadCommunityPosts: 목록 렌더 전 차단 필터 적용
h = replace_once(h,
"""function loadCommunityPosts(){
  socket.emit('posts:get_list', getFilterValues(communitySortType), (res)=>{
    if (!res.success) return;
    const filtered = (res.posts||[]).filter(p => (p.logType||'story') === activeCommunityLogType);
    activeSearchQuery = '';
    renderPosts(filtered);
  });
}""",
"""function loadCommunityPosts(){
  socket.emit('posts:get_list', getFilterValues(communitySortType), (res)=>{
    if (!res.success) return;
    const filtered = filterOutBlockedAuthors((res.posts||[]).filter(p => (p.logType||'story') === activeCommunityLogType));
    activeSearchQuery = '';
    renderPosts(filtered);
  });
}""",
    "loadCommunityPosts 차단 필터 적용", INDEX)

# 3) handleCommunitySearchInput: 검색 결과에도 동일하게 차단 필터 적용
h = replace_once(h,
"""  socket.emit('posts:get_list', getFilterValues(communitySortType), (res)=>{
    if (!res.success) return;
    const filtered = (res.posts||[]).filter(p => (p.logType||'story') === activeCommunityLogType);
    const searched = filtered.filter(p=>{
      if ((p.content||'').includes(q)) return true;
      const comments = p.comments || [];
      return comments.some(c=>(c.content||'').includes(q));
    });
    renderPosts(searched);
  });""",
"""  socket.emit('posts:get_list', getFilterValues(communitySortType), (res)=>{
    if (!res.success) return;
    const filtered = filterOutBlockedAuthors((res.posts||[]).filter(p => (p.logType||'story') === activeCommunityLogType));
    const searched = filtered.filter(p=>{
      if ((p.content||'').includes(q)) return true;
      const comments = p.comments || [];
      return comments.some(c=>(c.content||'').includes(q));
    });
    renderPosts(searched);
  });""",
    "커뮤니티 검색 결과 차단 필터 적용", INDEX)

# 4) 말벗스토리(릴스) 피드에도 동일 필터 적용 (openStoryFeed)
h = replace_once(h,
"""function openStoryFeed(){
  socket.emit('stories:get_feed', {}, (res)=>{
    const stories = (res && res.stories) || [];
    storyState.list = stories; storyState.index = 0;
    openFullScreen('storyViewerScreen');
    renderStoryFrame();
  });
}""",
"""function openStoryFeed(){
  socket.emit('stories:get_feed', {}, (res)=>{
    const stories = filterOutBlockedAuthors((res && res.stories) || []);
    storyState.list = stories; storyState.index = 0;
    openFullScreen('storyViewerScreen');
    renderStoryFrame();
  });
}""",
    "말벗스토리 피드(openStoryFeed) 차단 필터 적용", INDEX)

write(INDEX, h)
print("\n✅ 0-17 패치 적용 완료 (public/index.html).")
print("다음: 브라우저에서 아무나 차단해보고 홈/커뮤니티/릴스 목록에서 그 사람 글이 안 보이는지 확인 후 git add -A && git commit && git push")