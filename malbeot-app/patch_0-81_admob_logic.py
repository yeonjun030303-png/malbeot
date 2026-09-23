path = "public/index.html"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1) openPostDetailScreen에 전면광고 호출 추가
old_post = "function openPostDetailScreen(id, focusComment){ currentPostId=id; commentUIContext='detail'; refreshPostDetail(focusComment); openFullScreen('postDetailScreen'); }"
new_post = "function openPostDetailScreen(id, focusComment){ currentPostId=id; commentUIContext='detail'; refreshPostDetail(focusComment); openFullScreen('postDetailScreen'); if (window.malbeotMaybeShowInterstitial) window.malbeotMaybeShowInterstitial(); }"

count_post = content.count(old_post)
if count_post != 1:
    raise SystemExit(f"[실패] openPostDetailScreen 매치 {count_post}개 (1개여야 함)")
content = content.replace(old_post, new_post, 1)

# 2) switchTab에 배너 갱신 호출 추가
old_tab = "document.querySelectorAll('.tab-content').forEach(c=>c.classList.toggle('active', c.id===tab));"
new_tab = old_tab + "\n  if (window.malbeotUpdateAdBannerForTab) window.malbeotUpdateAdBannerForTab(tab);"

count_tab = content.count(old_tab)
if count_tab != 1:
    raise SystemExit(f"[실패] switchTab 매치 {count_tab}개 (1개여야 함)")
content = content.replace(old_tab, new_tab, 1)

# 3) AdMob 초기화/배너/전면광고 스크립트 블록을 </body> 직전에 추가
anchor = "})();\n</script>\n</body>"
count_anchor = content.count(anchor)
if count_anchor != 1:
    raise SystemExit(f"[실패] </body> 직전 앵커 매치 {count_anchor}개 (1개여야 함)")

admob_script = anchor + """
<script>
(function(){
  var MALBEOT_BANNER_ID = 'ca-app-pub-1897610037138449/6722836306';
  var MALBEOT_INTERSTITIAL_ID = 'ca-app-pub-1897610037138449/5653297216';
  var MALBEOT_INTERSTITIAL_COOLDOWN_MS = 60 * 60 * 1000; // 1시간

  function isNative(){
    return !!(window.Capacitor && window.Capacitor.isNativePlatform && window.Capacitor.isNativePlatform());
  }
  function getAdMob(){
    return window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.AdMob;
  }

  var admobReady = false;
  var interstitialLoaded = false;
  var currentAdTab = null;

  function hasAdFreeSubscription(){
    var sub = window.currentUser && window.currentUser.subscription;
    return !!(sub && sub.tier && sub.expiresAt && sub.expiresAt > Date.now());
  }

  async function prepareInterstitial(){
    var AdMob = getAdMob();
    if (!AdMob || !admobReady) return;
    try {
      await AdMob.prepareInterstitial({ adId: MALBEOT_INTERSTITIAL_ID, isTesting: false });
      interstitialLoaded = true;
    } catch(e){ interstitialLoaded = false; console.warn('[AdMob] 전면광고 준비 실패', e); }
  }

  async function initAdMob(){
    if (!isNative()) return;
    var AdMob = getAdMob();
    if (!AdMob) return;
    try {
      var trackingInfo = await AdMob.trackingAuthorizationStatus();
      if (trackingInfo && trackingInfo.status === 'notDetermined') {
        await AdMob.requestTrackingAuthorization();
      }
    } catch(e){ console.warn('[AdMob] ATT 권한 요청 실패', e); }
    try {
      await AdMob.initialize({ initializeForTesting: false });
      admobReady = true;
      prepareInterstitial();
    } catch(e){ console.warn('[AdMob] 초기화 실패', e); }
  }

  // ===== 배너: 홈/채팅 탭 상단, 구독자(골드/플래티넘)는 제외 =====
  async function malbeotUpdateAdBannerForTab(tab){
    if (!isNative() || !admobReady) return;
    var AdMob = getAdMob();
    if (!AdMob) return;
    var shouldShow = (tab === 'tab-home' || tab === 'tab-chat') && !hasAdFreeSubscription();
    if (shouldShow){
      if (currentAdTab === tab) return;
      try {
        await AdMob.showBanner({ adId: MALBEOT_BANNER_ID, adSize: 'ADAPTIVE_BANNER', position: 'TOP_CENTER', isTesting: false });
        currentAdTab = tab;
      } catch(e){ console.warn('[AdMob] 배너 표시 실패', e); }
    } else if (currentAdTab){
      try { await AdMob.hideBanner(); } catch(e){}
      currentAdTab = null;
    }
  }
  window.malbeotUpdateAdBannerForTab = malbeotUpdateAdBannerForTab;

  // ===== 전면광고: 게시물 상세 진입 시, 시간당 최대 1회, 구독자 제외 =====
  async function malbeotMaybeShowInterstitial(){
    if (!isNative() || !admobReady || !interstitialLoaded) return;
    if (hasAdFreeSubscription()) return;
    var last = Number(localStorage.getItem('malbeotLastInterstitialAt') || 0);
    if (Date.now() - last < MALBEOT_INTERSTITIAL_COOLDOWN_MS) return;
    var AdMob = getAdMob();
    try {
      await AdMob.showInterstitial();
      localStorage.setItem('malbeotLastInterstitialAt', String(Date.now()));
      interstitialLoaded = false;
    } catch(e){ console.warn('[AdMob] 전면광고 표시 실패', e); }
  }
  window.malbeotMaybeShowInterstitial = malbeotMaybeShowInterstitial;

  document.addEventListener('DOMContentLoaded', function(){
    initAdMob().then(function(){
      var AdMob = getAdMob();
      if (!AdMob) return;
      try {
        AdMob.addListener('interstitialAdDismissed', function(){ prepareInterstitial(); });
        AdMob.addListener('interstitialAdFailedToLoad', function(){ interstitialLoaded = false; });
        AdMob.addListener('bannerAdSizeChanged', function(info){
          var h = (info && info.height) || 0;
          document.querySelectorAll('#homeAdBannerRow, #chatAdBannerRow').forEach(function(el){
            if (h) el.style.height = h + 'px';
          });
        });
      } catch(e){}
    });
  });
})();
</script>
</body>"""

content = content.replace(anchor, admob_script, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("[완료] AdMob 배너/전면광고 JS 로직 추가함 (openPostDetailScreen 1곳, switchTab 1곳, 초기화 스크립트 1블록)")
