# -*- coding: utf-8 -*-
"""
0-77 패치
1) 프로필 상세화면(별명/취미 등 뜨는 화면)에 좌우 화살표 버튼 추가 (PC용, 터치는 기존 스와이프 유지)
2) 대표사진 배지를 별표 -> 숫자(1)로 변경, 추가사진 하단 별표(지정) 버튼 제거하고
   상단 숫자 배지를 누르면 바로 대표사진으로 지정되도록 변경
3) 커뮤니티 탭 진입 시 하루 1번만 "매일 글 올리면 포인트 지급" 안내 미니알림 표시

사용법 (PowerShell, C:\malbeot 에서):
  python3 patch_0-77.py
"""
import pathlib
import sys

FILE = pathlib.Path("malbeot-app/public/index.html")

REPLACEMENTS = [
    (
        '                <span id="editPhotoBadgeMain" class="hidden photo-slot-badge" style="color:#ffd76b;"><i class="fa-solid fa-star"></i></span>',
        '                <span id="editPhotoBadgeMain" class="hidden photo-slot-badge" style="background:#ffd76b;color:#3a2a00;">1</span>',
    ),
    (
        "let profilePhotoIndex = 0;",
        "let profilePhotoIndex = 0;\n"
        "// 0-77: 마우스 포인터 기기(PC)인지 판별. 터치기기는 스와이프로 넘기고, PC는 좌우 화살표 버튼으로 넘기게 함\n"
        "const IS_TOUCH_DEVICE = !!(window.matchMedia && window.matchMedia('(pointer: coarse)').matches);",
    ),
    (
        "// 하루 한번(00시 기준 초기화, 로컬 기기 시각 기준), (투표) 카테고리를 처음 선택할 때만 안내창 표시\nfunction maybeShowVoteInfoAlert(){",
        "// 0-77: 하루 한번(00시 기준 초기화, 로컬 기기 시각 기준), 커뮤니티 탭에 그날 처음 들어올 때만 포인트 안내창 표시\n"
        "function maybeShowCommunityDailyAlert(){\n"
        "  const today = getLocalDateStr();\n"
        "  if (localStorage.getItem('malbeot_communityDailySeenDate') === today) return;\n"
        "  localStorage.setItem('malbeot_communityDailySeenDate', today);\n"
        "  showMiniAlert('매일 1번씩 글을 올리면 포인트를 지급해드려요!', [{label:'확인', primary:true}]);\n"
        "}\n"
        "// 하루 한번(00시 기준 초기화, 로컬 기기 시각 기준), (투표) 카테고리를 처음 선택할 때만 안내창 표시\n"
        "function maybeShowVoteInfoAlert(){",
    ),
    (
        "  if (tab==='tab-community') loadCommunityPosts();",
        "  if (tab==='tab-community') { loadCommunityPosts(); maybeShowCommunityDailyAlert(); }",
    ),
    (
        "function changeProfilePhoto(i){ profilePhotoIndex = i; if (currentProfileUserCache) renderProfileDetail(currentProfileUserCache); }",
        "function changeProfilePhoto(i){ profilePhotoIndex = i; if (currentProfileUserCache) renderProfileDetail(currentProfileUserCache); }\n"
        "// 0-77: 프로필 상세화면(별명/취미 등 표시되는 화면)에서 좌우 화살표 버튼으로 사진 넘기기\n"
        "function profilePhotoPrev(){ if (profilePhotoIndex > 0) changeProfilePhoto(profilePhotoIndex - 1); }\n"
        "function profilePhotoNext(){\n"
        "  if (!currentProfileUserCache) return;\n"
        "  const photos = (currentProfileUserCache.photos && currentProfileUserCache.photos.length) ? currentProfileUserCache.photos : [null];\n"
        "  if (profilePhotoIndex < photos.length - 1) changeProfilePhoto(profilePhotoIndex + 1);\n"
        "}",
    ),
    (
        '  document.getElementById(\'profileDetailBody\').innerHTML = `\n'
        '    <div class="profile-photo-wrap" style="display:flex;align-items:center;justify-content:center;background:${user.gender===\'female\'?\'var(--pink-light)\':\'var(--blue-light)\'};">\n'
        '      ${photoContent}\n'
        '      ${photos.length>1?`<div class="profile-photo-dots">${dots}</div>`:\'\'}',
        '  const showProfileArrows = photos.length>1 && !IS_TOUCH_DEVICE;\n'
        '  const profilePrevArrow = showProfileArrows ? `<div onclick="event.stopPropagation();profilePhotoPrev()" style="position:absolute;left:10px;top:50%;transform:translateY(-50%);z-index:3;color:#fff;font-size:16px;width:34px;height:34px;display:${profilePhotoIndex>0?\'flex\':\'none\'};align-items:center;justify-content:center;background:rgba(0,0,0,.35);border-radius:50%;cursor:pointer;"><i class="fa-solid fa-chevron-left"></i></div>` : \'\';\n'
        '  const profileNextArrow = showProfileArrows ? `<div onclick="event.stopPropagation();profilePhotoNext()" style="position:absolute;right:10px;top:50%;transform:translateY(-50%);z-index:3;color:#fff;font-size:16px;width:34px;height:34px;display:${profilePhotoIndex<photos.length-1?\'flex\':\'none\'};align-items:center;justify-content:center;background:rgba(0,0,0,.35);border-radius:50%;cursor:pointer;"><i class="fa-solid fa-chevron-right"></i></div>` : \'\';\n'
        '  document.getElementById(\'profileDetailBody\').innerHTML = `\n'
        '    <div class="profile-photo-wrap" style="display:flex;align-items:center;justify-content:center;background:${user.gender===\'female\'?\'var(--pink-light)\':\'var(--blue-light)\'};">\n'
        '      ${photoContent}\n'
        '      ${profilePrevArrow}\n'
        '      ${profileNextArrow}\n'
        '      ${photos.length>1?`<div class="profile-photo-dots">${dots}</div>`:\'\'}',
    ),
    (
        '      <span class="photo-slot-badge" onclick="event.stopPropagation();reorderExtraPhoto(${i})" title="누르면 순서를 맨 뒤로 보냅니다">${i+2}</span>\n'
        '      <span onclick="event.stopPropagation();setAsMainPhoto(${i})" style="position:absolute;bottom:-6px;left:-6px;background:rgba(0,0,0,.65);color:#ffd76b;border-radius:50%;width:20px;height:20px;display:flex;align-items:center;justify-content:center;font-size:10px;cursor:pointer;box-shadow:0 1px 4px rgba(0,0,0,.35);z-index:2;" title="대표사진으로 지정"><i class="fa-solid fa-star"></i></span>',
        '      <span class="photo-slot-badge" onclick="event.stopPropagation();setAsMainPhoto(${i})" title="누르면 대표사진(1번)으로 지정됩니다">${i+2}</span>',
    ),
]


def main():
    if not FILE.exists():
        print(f"파일을 찾을 수 없습니다: {FILE.resolve()}")
        print("C:\\malbeot 폴더에서 이 스크립트를 실행했는지 확인해주세요.")
        sys.exit(1)

    text = FILE.read_text(encoding="utf-8")
    applied = 0
    skipped = 0

    for i, (old, new) in enumerate(REPLACEMENTS, start=1):
        count = text.count(old)
        if count == 0:
            print(f"[{i}] 건너뜀 - 이미 적용됐거나 코드가 달라서 매칭되는 부분을 못 찾음")
            skipped += 1
            continue
        if count > 1:
            print(f"[{i}] 경고 - 매칭되는 부분이 {count}개라 첫 번째만 교체합니다")
        text = text.replace(old, new, 1)
        print(f"[{i}] 적용 완료")
        applied += 1

    FILE.write_text(text, encoding="utf-8")
    print(f"\n총 {applied}개 적용, {skipped}개 건너뜀 -> {FILE.resolve()}")
    print("\n다음 명령으로 커밋+푸시 해주세요:")
    print('  git add -A && git commit -m "0-77: 프로필 상세화면 좌우화살표 추가, 대표사진 배지 숫자로 변경, 커뮤니티 일일 포인트안내 추가" && git push')


if __name__ == "__main__":
    main()