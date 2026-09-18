# 말벗 앱 인수인계서 v13 (2026-09-17 작성)

> 다음 세션 재개 순서: **① 수정해야할 목록 → ② 애플 초안** 순으로 진행

---

## ① 수정해야할 목록 (우선순위 순)

### 🥇 최우선 — 신규 UI 버그 3건 (2026-09-17 리포트)

**1. 채팅 키보드 뜰 때 레이아웃 밀림 (전송하기 버튼 화면 밖으로)**
- 증상: 키보드 없을 때는 화면이 딱 맞게 잘 보임(스샷 4번). 키보드를 누르면 화면 전체가 쏠리면서 전송하기 버튼이 한 화면에 같이 안 보임(스샷 3번)
- 원하는 동작: 카카오톡처럼 — 나머지 화면은 그대로 있고, 입력창(메시지 입력+전송버튼)만 키보드 바로 위로 올라가야 함
- 코드 위치: `public/index.html`
  - `.app-container{height:100vh;height:100dvh;...}` (27~32번째 줄 부근)
  - `.chat-input-bar{...}` (223번째 줄, `position:relative`로 되어있음, 채팅창 하단에 flex 아이템으로 배치됨)
- 의심 원인: iOS WKWebView(Capacitor)에서 키보드가 뜰 때 `100dvh`가 기대만큼 줄어들지 않거나 타이밍이 어긋나서, 컨테이너 전체가 안 줄어들고 화면이 밀리는 것으로 추정
- 다음 세션 시도해볼 방향:
  - `window.visualViewport`의 `resize`/`scroll` 이벤트를 감지해서, 키보드가 떴을 때 `.app-container`의 실제 높이를 `visualViewport.height`로 JS에서 직접 맞춰주는 방식(순수 CSS dvh에만 의존하지 않기)
  - 또는 `.chat-input-bar`를 `position:fixed`로 바꾸고 `visualViewport` 값 기준으로 `bottom` 값을 JS로 매 리사이즈마다 계산해서 넣어주는 방식
  - Capacitor 쪽에서 `Keyboard` 플러그인(`@capacitor/keyboard`)이 설치되어 있는지 확인 — 설치돼 있다면 `resize` 모드를 `'native'`가 아니라 `'body'`나 `'ionic'`으로 바꿔보는 것도 검토

**2. 화면 확대(핀치줌) 후 축소가 안 되는 버그**
- 증상: 채팅창에서 (단체톡방 만들기로 추정되는) 조작을 하다가 화면이 확대된 채로 고정됨. 이후 다른 페이지/설정에 들어가도 계속 확대된 상태 유지, 축소 불가
- 원하는 동작: 기본적으로 화면이 한 화면에 딱 맞게 들어와야 함. 자세히 보려고 확대하는 것은 가능해도 되지만, 손을 떼면 스프링처럼 원래 배율로 돌아와야 함(고정 확대 상태로 남으면 안 됨)
- 코드 위치: `public/index.html` 5번째 줄
  ```html
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  ```
  → 현재 `maximum-scale`/`user-scalable` 제한이 전혀 없어서, 실수로 핀치/더블탭이 걸리면 브라우저(WebView) 자체 확대가 그대로 유지됨(SPA라 페이지 이동해도 리셋 안 됨)
- 다음 세션 시도해볼 방향 (2단계 제안):
  - **1단계(가장 확실한 즉시 수정)**: viewport meta에 `maximum-scale=1.0, user-scalable=no` 추가 → 실수로 확대되는 사고 자체를 원천 차단. 다만 이렇게 하면 "확대해서 자세히 보기" 자체가 완전히 불가능해짐
  - **2단계(요청하신 "스프링처럼 원위치" 동작)**: 이건 브라우저 기본 핀치줌으로는 구현이 안 되는 커스텀 기능임(웹 표준에 없음) — 사진 전체화면 뷰어(0-72에서 만든 마우스휠 확대 기능과 유사한 방식)처럼 JS로 직접 pinch 제스처를 감지해서 `transform: scale()`을 주고, `touchend` 시 애니메이션으로 scale을 1로 되돌리는 커스텀 구현이 필요함 → 별도 기능 개발 항목으로 다음 세션에 논의 필요(우선 1단계로 사고부터 막고, 2단계는 원하면 이어서 진행)

**3. 프로필 화면 최초 진입 시 상단에 쏠리고 렉 걸림 (재진입하면 정상)**
- 증상: 프로필 화면에 처음 들어가면 화면이 위로 쏠려 보이고 렉 걸리며 하단 탭도 안 보임. 뒤로가기 후 다시 들어가면 정상화됨(원하는 위치로 내려가고 렉 없음)
- 코드 위치: `public/index.html`
  - `#profileDetailScreen` (902번째 줄), `.full-screen-overlay{position:absolute;inset:0;...}` (122번째 줄)
  - `openFullScreen()` 함수(1677번째 줄) — `classList.add('active')`만 하고 스크롤 위치나 강제 리플로우 처리가 없음
  - 헤더가 `position:absolute;top:0` (903번째 줄)로 커버사진 위에 겹쳐지는 구조라, 컨테이너 실제 높이가 늦게 확정되면 첫 렌더링이 찌그러져 보일 수 있음
- 의심 원인: 앱 콜드스타트 직후 `100dvh` 값이 WKWebView에서 아직 제대로 안정화되기 전에 첫 프로필 화면이 열려서, `.app-container` 높이가 잘못 계산된 채로 렌더링됐다가, 화면 전환(뒤로가기→재진입)을 거치며 강제 리플로우가 일어나 정상화되는 것으로 추정 — 100vh/100dvh 이중 지정 자체가 WKWebView에서 타이밍 이슈를 일으키는 경우가 실제로 있음
- 다음 세션 시도해볼 방향:
  - `--vh` 같은 커스텀 CSS 변수를 JS(`window.visualViewport` 또는 `window.innerHeight`)로 계산해서 `load` 시점과 `resize` 시점마다 갱신 → CSS의 `100dvh` 의존을 줄이는 방식으로 전환
  - 재현 조건을 좀 더 명확히 하기(앱을 완전히 껐다 켠 직후에만 발생하는지, 아니면 세션 중 아무 때나 발생하는지) — 재현되면 개발자도구 콘솔/Safari 원격 디버깅 켜고 확인 권장

### 🥈 기존 미착수 항목 (변동 없음, memory `/areas/malbeot-app.md` 참고)
1. 채팅방 안 점3개→프로필 목록에서 이름/사진 클릭시 해당 프로필로 이동 (다음 착수 예정 지점이었음)
2. AdMob 광고 슬롯 (계정 준비 후 진행 예정, 보류 중)
3. 채팅방 나가서 목록으로 돌아갈 때 화면 검게 변하며 렉 걸리는 버그
4. 채팅창 내 설정버튼/나가기버튼 삭제(중복 기능이라)
5. 채팅창 상대 프로필사진 클릭 → 겹쳐서 뜨고 뒤로가기 시 채팅창 복귀(현재는 목록으로 잘못 나감)
6. 프로필 사진 추가 등록 시 미리보기 스트립에 즉시 반영 안 되는 문제, 전화번호 옆 안내문구 추가
7. "코드부터 열게 해야함" 메모 — 의미 불명확, 확인 필요
8. 추가사진 순서 저장 후 재로드시 꼬이는 버그(재테스트 필요 — 위 3건 UI버그 수정과 무관하니 후순위)

---

## ② 애플한테 쓸 초안 (TestFlight/App Store Connect 상태 확인용)

> 상황: 2026-09-09에 "Add for Review" 클릭 시 카테고리 에러로 막혀 Apple 지원팀에 문의(케이스 ID 102957418548), 9/11 답변은 문의 내용과 무관한 "TestFlight 빌드 1 승인" 안내만 옴, 9/12 재문의 발송함. 이후 저장소에 "iOS 빌드 번호 1→2 (App Store Connect 중복 버전 거부 문제 해결)" 커밋이 존재하는 것으로 보아, 별도로 **빌드 중복 거부 에러**도 있었고 빌드 번호를 2로 올려 대응한 것으로 보임. **다음 세션에서 먼저 확인할 것: 이 문서 하단 [확인 필요] 항목들.**

### 이메일 초안 (kickoff030303@gmail.com → Apple Developer Support 앞)

```
제목: Follow-up on Case ID 102957418548 — "Add for Review" Category Error Still Unresolved

Hello,

I'm following up on my previous support case (Case ID: 102957418548) regarding
my app "말벗 - 마음을 나누는 친구" (Bundle ID: com.cnsstudiokorea.malbeot,
App Store Connect App ID: 6809701233).

The issue I originally reported is still unresolved: when I click "Add for
Review," I receive the error "You must select a primary category for your
app," even though the Primary Category is correctly set to "Social
Networking" on the App Information page (confirmed multiple times over
several days, including after a hard refresh and in a private browsing
window).

The reply I received on 9/11 addressed a different topic (confirmation that
TestFlight Build 1 was approved for external testing) and did not resolve
the category error I originally asked about. I sent a follow-up
clarification on 9/12 but have not received a response addressing the
original issue.

Could someone please look into why "Add for Review" is rejecting a category
that is already correctly set, and confirm what steps I need to take to
successfully submit my app for App Review?

Account details:
- Apple ID: owner@cnsstudiokorea.com
- Team ID: 6M4NZY53VP
- App Store Connect App ID: 6809701233

Thank you for your help.

Best regards,
C&S STUDIO
```

### [확인 필요] 다음 세션이 먼저 할 일
1. kickoff030303@gmail.com에 9/12 재문의에 대한 Apple 답변이 왔는지 확인
2. "iOS 빌드 번호 1→2" 커밋이 실제로 어떤 에러(중복 버전 거부)에 대한 대응이었는지, 그 에러가 "Add for Review" 카테고리 에러와 같은 건인지 별개인지 본인에게 확인
3. 현재 "테스트플라이트에 오류가 있다"고 한 것이 위 카테고리 에러의 연장인지, 빌드 2 업로드 후 새로 발생한 다른 에러인지 확인 — 다르다면 에러 메시지 원문/스크린샷 받아서 별도로 진단
4. 위 확인 결과에 따라 초안 이메일 내용을 실제 최신 상황에 맞게 수정해서 발송
