[33mcommit 62a408c9084cec426dd37b1008c565c7fd709e27[m[33m ([m[1;36mHEAD[m[33m -> [m[1;32mmain[m[33m, [m[1;31morigin/main[m[33m, [m[1;31morigin/HEAD[m[33m)[m
Author: yeonjun030303-png <yeonjun030303@gmail.com>
Date:   Tue Aug 4 01:48:47 2026 +0000

    feat: 앱 내 미니 알림 - 채팅/좋아요/댓글/팔로우 카테고리별 온오프, 클릭시 이동, 채팅 알림 프로필사진 추가, 댓글 좋아요 알림 신설

 malbeot-app/public/index.html | 77 [32m++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++[m[31m---------------[m
 malbeot-app/server.js         |  8 [32m+++++++[m[31m-[m
 2 files changed, 69 insertions(+), 16 deletions(-)

[33mcommit 29845d6ef5cf92383696811ad0986c9a735a871b[m
Author: yeonjun030303-png <yeonjun030303@gmail.com>
Date:   Tue Aug 4 01:45:26 2026 +0000

    feat: 팔로우 시 알림 발송 추가

 malbeot-app/fix_notify_server.py | 33 [32m+++++++++++++++++++++++++++++++++[m
 malbeot-app/server.js            |  4 [32m++++[m
 2 files changed, 37 insertions(+)

[33mcommit 2e99850bedc0b70c98c22ac4fc5560d3fde31670[m
Author: yeonjun030303-png <yeonjun030303@gmail.com>
Date:   Tue Aug 4 01:26:22 2026 +0000

    fix: 클라이언트에서 삭제된 게시글/댓글 문구 표시 (관리자삭제/본인삭제 구분)

 malbeot-app/public/index.html | 18 [32m++++++++++++[m[31m------[m
 1 file changed, 12 insertions(+), 6 deletions(-)
