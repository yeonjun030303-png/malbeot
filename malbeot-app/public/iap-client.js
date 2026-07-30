// ============================================================
// 인앱결제 클라이언트 코드
// public 폴더 등 정적 파일 경로에 이 파일을 두고,
// 결제 버튼이 있는 HTML 페이지에서 <script src="/iap-client.js"></script>로 불러오세요.
//
// 참고: 지금 사이트는 번들러(webpack 등) 없이 순수 HTML/JS 구조라서,
// npm 패키지를 import로 바로 못 씁니다. 대신 Capacitor가 앱 안에서
// window.Capacitor.Plugins 전역 객체로 플러그인을 자동으로 노출해주는
// 방식을 사용합니다 (번들러 불필요).
// ============================================================

const REVENUECAT_API_KEY = "test_BiowcjPwUTqpLGIhUDBXXmuoZaL"; // RevenueCat 대시보드에서 발급받은 키 (테스트/샌드박스용)

let iapReady = false;

async function initIAP() {
  // 웹 브라우저(PC/모바일 웹)에서는 Capacitor 네이티브 브릿지가 없으므로 결제 기능 자체가 비활성화됩니다.
  if (!window.Capacitor || !window.Capacitor.isNativePlatform || !window.Capacitor.isNativePlatform()) {
    console.log("[IAP] 앱(네이티브) 환경이 아니므로 결제 기능을 사용할 수 없습니다.");
    return;
  }

  // ⚠️ 버그 수정: 이 플러그인의 실제 등록 이름은 "CapacitorPurchases"가 아니라 "Purchases"예요.
  // (import { Purchases } from '@revenuecat/purchases-capacitor' 할 때 쓰는 그 이름과 동일)
  const Purchases = window.Capacitor.Plugins.Purchases;
  if (!Purchases) {
    console.error("[IAP] 결제 플러그인을 찾을 수 없습니다. npx cap sync를 다시 실행했는지 확인하세요.");
    return;
  }

  await Purchases.configure({ apiKey: REVENUECAT_API_KEY });
  iapReady = true;
  console.log("[IAP] 초기화 완료");
}

// 구매 버튼에서 호출하는 함수
// productId: RevenueCat/Play Console에 등록한 상품 ID (예: "premium_monthly")
async function buyItem(productId) {
  if (!iapReady) {
    alert("결제 시스템이 아직 준비되지 않았습니다. 잠시 후 다시 시도해주세요.");
    return;
  }

  const Purchases = window.Capacitor.Plugins.Purchases;

  try {
    const offeringsResult = await Purchases.getOfferings();
    const current = offeringsResult.offerings && offeringsResult.offerings.current;

    if (!current || !current.availablePackages || current.availablePackages.length === 0) {
      alert("현재 구매 가능한 상품이 없습니다. RevenueCat/Play Console 설정을 확인하세요.");
      return;
    }

    // productId와 매칭되는 패키지 찾기 (없으면 첫 번째 패키지 사용)
    const targetPackage =
      current.availablePackages.find((p) => p.product && p.product.identifier === productId) ||
      current.availablePackages[0];

    // ⚠️ 버전에 따라 파라미터 이름이 다를 수 있어요 (aPackage 또는 packageToPurchase).
    // 설치된 @revenuecat/purchases-capacitor 버전의 타입 정의(node_modules 안 .d.ts)나
    // RevenueCat 공식 문서에서 정확한 이름을 한 번 확인해주세요.
    const purchaseResult = await Purchases.purchasePackage({ packageToPurchase: targetPackage });

    // ⚠️ 중요: 지금 이 alert 하나로 끝나면 실제로는 유저의 "쌀"이 하나도 충전되지 않아요.
    // 결제 성공 여부는 RevenueCat이 서버로 보내는 웹훅으로 서버가 직접 확인하고,
    // 그 웹훅을 받은 서버가 Firebase에서 해당 유저의 points를 올려줘야 진짜로 충전됩니다.
    // (클라이언트가 "성공했다"고 우기는 것만으로 포인트를 주면, 조작에 취약해져요.)
    alert("구매가 완료되었습니다!");
    console.log("[IAP] 구매 성공:", purchaseResult);

    // 필요하면 여기서 서버에 구매 완료를 알리는 API를 호출해서
    // DB에 "프리미엄 사용자" 상태를 저장하세요.
    // fetch('/api/purchase-complete', { method: 'POST', ... })
  } catch (err) {
    if (err && err.userCancelled) {
      console.log("[IAP] 사용자가 결제를 취소함");
      return;
    }
    console.error("[IAP] 구매 실패:", err);
    alert("결제 중 문제가 발생했습니다: " + (err.message || "알 수 없는 오류"));
  }
}

// 로그인 성공 직후 index.html에서 이 함수를 호출해서, RevenueCat 계정을 우리 서버의 유저 id와 연결해야 함.
// 이렇게 해야 서버(server.js의 /api/revenuecat-webhook)가 결제 완료 알림을 받았을 때
// "어느 유저"에게 쌀을 지급할지 알 수 있음 (app_user_id로 매칭됨).
async function linkIAPUser(userId) {
  if (!iapReady || !userId) return;
  const Purchases = window.Capacitor.Plugins.Purchases;
  try {
    // ⚠️ 버전에 따라 파라미터 형태가 다를 수 있어요 (문자열 하나만 받는 버전도 있음).
    // 에러가 나면 @revenuecat/purchases-capacitor 문서에서 logIn 시그니처를 확인해주세요.
    await Purchases.logIn({ appUserID: String(userId) });
    console.log("[IAP] 유저 연결 완료:", userId);
  } catch (err) {
    console.error("[IAP] 유저 연결 실패:", err);
  }
}
window.linkIAPUser = linkIAPUser;
window.buyItem = buyItem;

// 페이지 로드 시 자동 초기화 (익명으로 우선 초기화되고, 로그인 후 linkIAPUser로 계정이 연결됨)
document.addEventListener("DOMContentLoaded", initIAP);