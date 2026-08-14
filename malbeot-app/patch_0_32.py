# 0-32: 관리자 신고관리 화면에 상태(전체/미처리/처리완료) 필터 + 닉네임 검색 추가

path = "public/index.html"
with open(path, "r", encoding="utf-8") as f:
    h = f.read()

# 1) 상태/검색 변수 추가
old_var = "let adminReportFilter = 'post';"
assert old_var in h, "adminReportFilter 변수를 찾을 수 없습니다"
new_var = old_var + "\nlet adminReportStatusFilter = 'all'; // 0-32: 전체/pending/resolved\nlet adminReportSearchKeyword = ''; // 0-32: 신고자/피신고자 닉네임 검색"
h = h.replace(old_var, new_var)

# 2) 신고관리 화면 상단에 상태 드롭다운 + 검색창 추가 (탈리 박스 바로 위)
old_ui = '''      <div id="adminReportsTab">
        <div style="display:flex;gap:8px;margin-bottom:16px;">'''
assert old_ui in h, "adminReportsTab 마크업을 찾을 수 없습니다"

new_ui = '''      <div id="adminReportsTab">
        <div style="display:flex;gap:8px;margin-bottom:10px;">
          <select id="adminReportStatusSelect" class="form-input" style="flex:0 0 110px;" onchange="onAdminReportStatusChange(this.value)">
            <option value="all">전체 상태</option>
            <option value="pending">미처리만</option>
            <option value="resolved">처리완료만</option>
          </select>
          <input id="adminReportSearchInput" class="form-input" style="flex:1;" placeholder="신고자/피신고자 닉네임 검색" oninput="onAdminReportSearchInput(this.value)">
        </div>
        <div style="display:flex;gap:8px;margin-bottom:16px;">'''

h = h.replace(old_ui, new_ui)

# 3) 핸들러 함수 추가 + renderAdminReports 필터링 로직 확장
old_filter_fn = '''function filterAdminReports(type){
  adminReportFilter = type;
  renderAdminReports();
}'''
assert old_filter_fn in h, "filterAdminReports 함수를 찾을 수 없습니다"

new_filter_fn = '''function filterAdminReports(type){
  adminReportFilter = type;
  renderAdminReports();
}
// 0-32: 상태 필터/닉네임 검색 변경 핸들러
function onAdminReportStatusChange(value){
  adminReportStatusFilter = value;
  renderAdminReports();
}
function onAdminReportSearchInput(value){
  adminReportSearchKeyword = (value || '').trim();
  renderAdminReports();
}'''

h = h.replace(old_filter_fn, new_filter_fn)

# 4) renderAdminReports의 list 필터링에 상태/검색 조건 추가
old_list_line = "  const list = adminReportsData.filter(r=>r.type===adminReportFilter);"
assert old_list_line in h, "renderAdminReports의 필터 라인을 찾을 수 없습니다"

new_list_line = '''  // 0-32: 종류 필터에 상태 필터 + 닉네임(신고자/피신고자) 검색까지 함께 적용
  const kw = adminReportSearchKeyword.toLowerCase();
  const list = adminReportsData.filter(r=>{
    if (r.type !== adminReportFilter) return false;
    if (adminReportStatusFilter !== 'all' && r.status !== adminReportStatusFilter) return false;
    if (kw && !((r.reporterNickname||'').toLowerCase().includes(kw) || (r.accusedNickname||'').toLowerCase().includes(kw))) return false;
    return true;
  });'''

h = h.replace(old_list_line, new_list_line)

with open(path, "w", encoding="utf-8") as f:
    f.write(h)

print("✅ 0-32 패치 적용 완료: 관리자 신고관리에 상태 필터 + 닉네임 검색 추가")