import re

INDEX = "public/index.html"
SERVER = "server.js"

def read(p):
    with open(p, encoding='utf-8') as f:
        return f.read()

def write(p, s):
    with open(p, 'w', encoding='utf-8') as f:
        f.write(s)

def replace_once(content, old, new, label):
    count = content.count(old)
    if count != 1:
        raise SystemExit(f"[실패] {label}: old_str가 {count}번 발견됨(1번이어야 함). 패치를 중단합니다.")
    return content.replace(old, new, 1)

# ==================== server.js ====================
s = read(SERVER)

# --- 0-57/0-59: 유저 생성시 joinedAt(가입일)/onboardingSeen(온보딩 시청여부) 필드 추가 ---
s = replace_once(s,
    "        profileUpdatedAt: Date.now(),\n"
    "        followingIds: [], followerIds: [], profileLikedBy: [], notifyKeywords: []\n"
    "      };",
    "        profileUpdatedAt: Date.now(), joinedAt: Date.now(), onboardingSeen: false,\n"
    "        followingIds: [], followerIds: [], profileLikedBy: [], notifyKeywords: []\n"
    "      };",
    "0-57 유저생성(전화번호 가입 - 레거시) joinedAt 필드 추가")

s = replace_once(s,
    "        profileUpdatedAt: Date.now(),\n"
    "        deviceId: data.deviceId || null, lastIp: getClientIp(socket),\n"
    "        followingIds: [], followerIds: [], profileLikedBy: [], notifyKeywords: []\n"
    "      };",
    "        profileUpdatedAt: Date.now(), joinedAt: Date.now(), onboardingSeen: false,\n"
    "        deviceId: data.deviceId || null, lastIp: getClientIp(socket),\n"
    "        followingIds: [], followerIds: [], profileLikedBy: [], notifyKeywords: []\n"
    "      };",
    "0-57 유저생성(카카오 가입) joinedAt 필드 추가")

# --- 0-58: 단체채팅방 검색결과에 생성일(createdAt) 포함 ---
s = replace_once(s,
    ".map(meta => ({ roomId: meta.roomId, title: meta.title, intro: meta.intro, memberCount: (meta.memberIds || []).length, inviteCode: meta.inviteCode }))",
    ".map(meta => ({ roomId: meta.roomId, title: meta.title, intro: meta.intro, memberCount: (meta.memberIds || []).length, inviteCode: meta.inviteCode, createdAt: meta.createdAt || 0 }))",
    "0-58 group:search 결과에 createdAt 추가")

# --- 0-57 관리자 통계 + 0-59 온보딩 시청여부 저장 핸들러를 admin:abuse:ban_user 뒤, disconnect 앞에 삽입 ---
anchor = (
    "      broadcastUsers();\n"
    "      cb && cb({ success: true });\n"
    "    } catch (e) { console.error(e); cb && cb({ success: false }); }\n"
    "  });\n"
    "\n"
    "  socket.on('disconnect', async () => {\n"
)
new_handlers = (
    "      broadcastUsers();\n"
    "      cb && cb({ success: true });\n"
    "    } catch (e) { console.error(e); cb && cb({ success: false }); }\n"
    "  });\n"
    "\n"
    "  // 0-57: 관리자 통계 대시보드 - 가입자/결제/신고처리율 요약\n"
    "  socket.on('admin:stats:get', async (data, cb) => {\n"
    "    try {\n"
    "      const requester = await getUser(socketToUser[socket.id]);\n"
    "      if (!requester || !isAdmin(requester)) return cb && cb({ success: false });\n"
    "      const allUsers = await getAllUsers();\n"
    "      const userList = Object.values(allUsers);\n"
    "      const totalUsers = userList.length;\n"
    "      const kstDateStr = (d) => new Date(d).toLocaleDateString('sv-SE', { timeZone: 'Asia/Seoul' });\n"
    "      const todayStr = kstDateStr(Date.now());\n"
    "      const dayBuckets = {};\n"
    "      for (let i = 6; i >= 0; i--) {\n"
    "        const d = new Date(Date.now() - i * 24 * 60 * 60 * 1000);\n"
    "        dayBuckets[kstDateStr(d)] = 0;\n"
    "      }\n"
    "      let todaySignups = 0;\n"
    "      userList.forEach(u => {\n"
    "        const joined = u.joinedAt || u.profileUpdatedAt;\n"
    "        if (!joined) return;\n"
    "        const dStr = kstDateStr(joined);\n"
    "        if (dStr === todayStr) todaySignups++;\n"
    "        if (Object.prototype.hasOwnProperty.call(dayBuckets, dStr)) dayBuckets[dStr]++;\n"
    "      });\n"
    "      const signupsByDay = Object.keys(dayBuckets).map(date => ({ date, count: dayBuckets[date] }));\n"
    "\n"
    "      const purchaseSnap = await db.ref('purchaseHistory').once('value');\n"
    "      const purchaseAll = purchaseSnap.val() || {};\n"
    "      let totalPayments = 0, monthPayments = 0;\n"
    "      const thisMonth = kstMonthStr(new Date());\n"
    "      Object.values(purchaseAll).forEach(userPurchases => {\n"
    "        Object.values(userPurchases || {}).forEach(p => {\n"
    "          totalPayments++;\n"
    "          if (kstMonthStr(new Date(p.at || 0)) === thisMonth) monthPayments++;\n"
    "        });\n"
    "      });\n"
    "\n"
    "      const reportsSnap = await db.ref('reports').once('value');\n"
    "      const reportsAll = Object.values(reportsSnap.val() || {});\n"
    "      const totalReports = reportsAll.length;\n"
    "      const resolvedReports = reportsAll.filter(r => r.status === 'resolved').length;\n"
    "      const resolveRate = totalReports ? Math.round((resolvedReports / totalReports) * 100) : 0;\n"
    "\n"
    "      cb && cb({\n"
    "        success: true,\n"
    "        totalUsers, todaySignups, signupsByDay,\n"
    "        totalPayments, monthPayments,\n"
    "        totalReports, resolvedReports, resolveRate\n"
    "      });\n"
    "    } catch (e) { console.error(e); cb && cb({ success: false }); }\n"
    "  });\n"
    "\n"
    "  // 0-59: 신규가입자 온보딩 튜토리얼 - 시청/건너뛰기 모두 '봤음'으로 저장(다음 로그인부터 안 뜸)\n"
    "  socket.on('user:onboarding_seen', async (data, cb) => {\n"
    "    try {\n"
    "      const userId = socketToUser[socket.id];\n"
    "      if (!userId) return cb && cb({ success: false });\n"
    "      const user = await getUser(userId);\n"
    "      if (!user) return cb && cb({ success: false });\n"
    "      user.onboardingSeen = true;\n"
    "      await saveUser(user);\n"
    "      cb && cb({ success: true });\n"
    "    } catch (e) { console.error(e); cb && cb({ success: false }); }\n"
    "  });\n"
    "\n"
    "  socket.on('disconnect', async () => {\n"
)
s = replace_once(s, anchor, new_handlers, "0-57/0-59 admin:stats:get + user:onboarding_seen 핸들러 삽입")

write(SERVER, s)
print("[OK] server.js 패치 완료")

# ==================== public/index.html ====================
h = read(INDEX)

# --- 0-57: 관리자 탭 버튼에 "통계" 추가 ---
h = replace_once(h,
    '        <button id="adminTabSubBtn" class="btn btn-secondary" style="flex:0 0 auto;white-space:nowrap;" onclick="switchAdminTab(\'sub\')">구독관리</button>\n'
    '      </div>',
    '        <button id="adminTabSubBtn" class="btn btn-secondary" style="flex:0 0 auto;white-space:nowrap;" onclick="switchAdminTab(\'sub\')">구독관리</button>\n'
    '        <button id="adminTabStatsBtn" class="btn btn-secondary" style="flex:0 0 auto;white-space:nowrap;" onclick="switchAdminTab(\'stats\')">통계</button>\n'
    '      </div>',
    "0-57 관리자 통계 탭 버튼 추가")

# --- 0-57: adminStatsTab 패널 HTML 추가 ---
h = replace_once(h,
    '        <div id="adminSubSearchResults"></div>\n'
    '      </div>\n'
    '    </div>\n'
    '  </div>\n'
    '\n'
    '  <div id="blockedListScreen" class="full-screen-overlay">',
    '        <div id="adminSubSearchResults"></div>\n'
    '      </div>\n'
    '      <div id="adminStatsTab" class="hidden">\n'
    '        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:16px;">\n'
    '          <div style="padding:14px;border:1px solid var(--border-color);border-radius:10px;text-align:center;">\n'
    '            <div id="statTotalUsers" style="font-size:22px;font-weight:700;">-</div>\n'
    '            <div style="font-size:12px;color:var(--text-muted);">총 가입자</div>\n'
    '          </div>\n'
    '          <div style="padding:14px;border:1px solid var(--border-color);border-radius:10px;text-align:center;">\n'
    '            <div id="statTodaySignups" style="font-size:22px;font-weight:700;">-</div>\n'
    '            <div style="font-size:12px;color:var(--text-muted);">오늘 신규가입</div>\n'
    '          </div>\n'
    '          <div style="padding:14px;border:1px solid var(--border-color);border-radius:10px;text-align:center;">\n'
    '            <div id="statTotalPayments" style="font-size:22px;font-weight:700;">-</div>\n'
    '            <div style="font-size:12px;color:var(--text-muted);">누적 결제/지급 건수</div>\n'
    '          </div>\n'
    '          <div style="padding:14px;border:1px solid var(--border-color);border-radius:10px;text-align:center;">\n'
    '            <div id="statMonthPayments" style="font-size:22px;font-weight:700;">-</div>\n'
    '            <div style="font-size:12px;color:var(--text-muted);">이번달 결제/지급</div>\n'
    '          </div>\n'
    '          <div style="padding:14px;border:1px solid var(--border-color);border-radius:10px;text-align:center;">\n'
    '            <div id="statTotalReports" style="font-size:22px;font-weight:700;">-</div>\n'
    '            <div style="font-size:12px;color:var(--text-muted);">누적 신고 건수</div>\n'
    '          </div>\n'
    '          <div style="padding:14px;border:1px solid var(--border-color);border-radius:10px;text-align:center;">\n'
    '            <div id="statResolveRate" style="font-size:22px;font-weight:700;">-</div>\n'
    '            <div style="font-size:12px;color:var(--text-muted);">신고 처리율</div>\n'
    '          </div>\n'
    '        </div>\n'
    '        <div style="font-size:13px;font-weight:700;margin-bottom:8px;">최근 7일 신규가입</div>\n'
    '        <div id="statSignupChart" style="display:flex;align-items:flex-end;gap:6px;height:100px;padding:0 4px;"></div>\n'
    '      </div>\n'
    '    </div>\n'
    '  </div>\n'
    '\n'
    '  <div id="blockedListScreen" class="full-screen-overlay">',
    "0-57 adminStatsTab 패널 HTML 추가")

# --- 0-59: 온보딩 튜토리얼 모달 HTML 추가 (scrollTopBtn 앞) ---
h = replace_once(h,
    '  <div id="scrollTopBtn" onclick="scrollActiveContainerToTop()"><i class="fa-solid fa-arrow-up"></i></div>',
    '  <div id="onboardingTutorialScreen" class="modal-overlay">\n'
    '    <div class="modal-box" style="max-width:340px;padding:0;overflow:hidden;">\n'
    '      <div id="onboardingSlides" style="position:relative;">\n'
    '        <div class="onboarding-slide" data-step="0" style="padding:36px 24px 20px;text-align:center;">\n'
    '          <div style="font-size:48px;margin-bottom:16px;"><i class="fa-solid fa-comments" style="color:var(--primary);"></i></div>\n'
    '          <div style="font-size:17px;font-weight:700;margin-bottom:10px;">오픈채팅으로 만나보세요</div>\n'
    '          <div style="font-size:13px;color:var(--text-muted);line-height:1.6;">관심사가 맞는 사람들과 단체로 자유롭게 대화할 수 있어요. 채팅 탭에서 직접 방을 만들거나 검색해서 참여해보세요.</div>\n'
    '        </div>\n'
    '        <div class="onboarding-slide hidden" data-step="1" style="padding:36px 24px 20px;text-align:center;">\n'
    '          <div style="font-size:48px;margin-bottom:16px;"><i class="fa-solid fa-images" style="color:var(--primary);"></i></div>\n'
    '          <div style="font-size:17px;font-weight:700;margin-bottom:10px;">말벗스토리로 일상을 공유해요</div>\n'
    '          <div style="font-size:13px;color:var(--text-muted);line-height:1.6;">사진과 글로 일상을 나누고, 다른 사람들과 공감·댓글로 소통해보세요.</div>\n'
    '        </div>\n'
    '        <div class="onboarding-slide hidden" data-step="2" style="padding:36px 24px 20px;text-align:center;">\n'
    '          <div style="font-size:48px;margin-bottom:16px;"><i class="fa-solid fa-gem" style="color:var(--primary);"></i></div>\n'
    '          <div style="font-size:17px;font-weight:700;margin-bottom:10px;">구독으로 더 많은 기능을 이용해요</div>\n'
    '          <div style="font-size:13px;color:var(--text-muted);line-height:1.6;">골드·플래티넘 구독을 하면 방문자 전체 목록, 좋아요 누른 사람 목록 등을 확인할 수 있어요.</div>\n'
    '        </div>\n'
    '      </div>\n'
    '      <div style="display:flex;justify-content:center;gap:6px;padding-bottom:14px;">\n'
    '        <span id="onbDot0" class="onboarding-dot active"></span>\n'
    '        <span id="onbDot1" class="onboarding-dot"></span>\n'
    '        <span id="onbDot2" class="onboarding-dot"></span>\n'
    '      </div>\n'
    '      <div style="display:flex;border-top:1px solid var(--border-color);">\n'
    '        <button type="button" style="flex:1;padding:14px;background:none;border:none;color:var(--text-muted);font-size:14px;cursor:pointer;" onclick="skipOnboarding()">건너뛰기</button>\n'
    '        <button type="button" id="onboardingNextBtn" style="flex:1;padding:14px;background:none;border:none;border-left:1px solid var(--border-color);color:var(--primary);font-weight:700;font-size:14px;cursor:pointer;" onclick="nextOnboardingStep()">다음</button>\n'
    '      </div>\n'
    '    </div>\n'
    '  </div>\n'
    '\n'
    '  <div id="scrollTopBtn" onclick="scrollActiveContainerToTop()"><i class="fa-solid fa-arrow-up"></i></div>',
    "0-59 온보딩 튜토리얼 모달 HTML 추가")

# --- 0-59: 온보딩 점(dot) CSS 추가 ---
h = replace_once(h,
    ".settings-accordion-body.open{display:block;}",
    ".settings-accordion-body.open{display:block;}\n"
    ".onboarding-dot{width:6px;height:6px;border-radius:50%;background:var(--border-color);}\n"
    ".onboarding-dot.active{background:var(--primary);width:16px;border-radius:3px;}",
    "0-59 온보딩 dot CSS 추가")

# --- 0-57: switchAdminTab 함수에 stats 탭 로직 추가 ---
h = replace_once(h,
    "function switchAdminTab(tab){\n"
    "  const rBtn = document.getElementById('adminTabReportsBtn');\n"
    "  const cBtn = document.getElementById('adminTabChatsBtn');\n"
    "  const aBtn = document.getElementById('adminTabAbuseBtn');\n"
    "  const pBtn = document.getElementById('adminTabPhoneBtn');\n"
    "  const sBtn = document.getElementById('adminTabSubBtn');\n"
    "  rBtn.style.background = tab==='reports' ? 'var(--primary)' : '';\n"
    "  rBtn.style.color = tab==='reports' ? '#fff' : '';\n"
    "  cBtn.style.background = tab==='chats' ? 'var(--primary)' : '';\n"
    "  cBtn.style.color = tab==='chats' ? '#fff' : '';\n"
    "  aBtn.style.background = tab==='abuse' ? 'var(--primary)' : '';\n"
    "  aBtn.style.color = tab==='abuse' ? '#fff' : '';\n"
    "  pBtn.style.background = tab==='phone' ? 'var(--primary)' : '';\n"
    "  pBtn.style.color = tab==='phone' ? '#fff' : '';\n"
    "  sBtn.style.background = tab==='sub' ? 'var(--primary)' : '';\n"
    "  sBtn.style.color = tab==='sub' ? '#fff' : '';\n"
    "  document.getElementById('adminReportsTab').classList.toggle('hidden', tab!=='reports');\n"
    "  document.getElementById('adminChatsTab').classList.toggle('hidden', tab!=='chats');\n"
    "  document.getElementById('adminAbuseTab').classList.toggle('hidden', tab!=='abuse');\n"
    "  document.getElementById('adminPhoneTab').classList.toggle('hidden', tab!=='phone');\n"
    "  document.getElementById('adminSubTab').classList.toggle('hidden', tab!=='sub');\n"
    "  if (tab==='reports') loadAdminReports();\n"
    "  else if (tab==='chats') loadAdminChatRooms();\n"
    "  else if (tab==='phone') loadAdminPhoneRequests();\n"
    "  else if (tab==='sub') { loadAdminSubscriptionDefaultList(); }\n"
    "  else loadAdminAbuse();\n"
    "}\n",
    "function switchAdminTab(tab){\n"
    "  const rBtn = document.getElementById('adminTabReportsBtn');\n"
    "  const cBtn = document.getElementById('adminTabChatsBtn');\n"
    "  const aBtn = document.getElementById('adminTabAbuseBtn');\n"
    "  const pBtn = document.getElementById('adminTabPhoneBtn');\n"
    "  const sBtn = document.getElementById('adminTabSubBtn');\n"
    "  const stBtn = document.getElementById('adminTabStatsBtn');\n"
    "  rBtn.style.background = tab==='reports' ? 'var(--primary)' : '';\n"
    "  rBtn.style.color = tab==='reports' ? '#fff' : '';\n"
    "  cBtn.style.background = tab==='chats' ? 'var(--primary)' : '';\n"
    "  cBtn.style.color = tab==='chats' ? '#fff' : '';\n"
    "  aBtn.style.background = tab==='abuse' ? 'var(--primary)' : '';\n"
    "  aBtn.style.color = tab==='abuse' ? '#fff' : '';\n"
    "  pBtn.style.background = tab==='phone' ? 'var(--primary)' : '';\n"
    "  pBtn.style.color = tab==='phone' ? '#fff' : '';\n"
    "  sBtn.style.background = tab==='sub' ? 'var(--primary)' : '';\n"
    "  sBtn.style.color = tab==='sub' ? '#fff' : '';\n"
    "  stBtn.style.background = tab==='stats' ? 'var(--primary)' : '';\n"
    "  stBtn.style.color = tab==='stats' ? '#fff' : '';\n"
    "  document.getElementById('adminReportsTab').classList.toggle('hidden', tab!=='reports');\n"
    "  document.getElementById('adminChatsTab').classList.toggle('hidden', tab!=='chats');\n"
    "  document.getElementById('adminAbuseTab').classList.toggle('hidden', tab!=='abuse');\n"
    "  document.getElementById('adminPhoneTab').classList.toggle('hidden', tab!=='phone');\n"
    "  document.getElementById('adminSubTab').classList.toggle('hidden', tab!=='sub');\n"
    "  document.getElementById('adminStatsTab').classList.toggle('hidden', tab!=='stats');\n"
    "  if (tab==='reports') loadAdminReports();\n"
    "  else if (tab==='chats') loadAdminChatRooms();\n"
    "  else if (tab==='phone') loadAdminPhoneRequests();\n"
    "  else if (tab==='sub') { loadAdminSubscriptionDefaultList(); }\n"
    "  else if (tab==='stats') { loadAdminStats(); }\n"
    "  else loadAdminAbuse();\n"
    "}\n"
    "// 0-57: 관리자 통계 대시보드 - 가입자/결제/신고처리율 요약 조회+렌더\n"
    "function loadAdminStats(){\n"
    "  socket.emit('admin:stats:get', {}, (res)=>{\n"
    "    if (!res || !res.success) return;\n"
    "    document.getElementById('statTotalUsers').textContent = res.totalUsers.toLocaleString();\n"
    "    document.getElementById('statTodaySignups').textContent = res.todaySignups.toLocaleString();\n"
    "    document.getElementById('statTotalPayments').textContent = res.totalPayments.toLocaleString();\n"
    "    document.getElementById('statMonthPayments').textContent = res.monthPayments.toLocaleString();\n"
    "    document.getElementById('statTotalReports').textContent = res.totalReports.toLocaleString();\n"
    "    document.getElementById('statResolveRate').textContent = res.resolveRate + '%';\n"
    "    const chart = document.getElementById('statSignupChart');\n"
    "    const maxCount = Math.max(1, ...res.signupsByDay.map(d=>d.count));\n"
    "    chart.innerHTML = res.signupsByDay.map(d=>{\n"
    "      const barH = Math.max(4, Math.round((d.count / maxCount) * 90));\n"
    "      const label = d.date.slice(5).replace('-', '/');\n"
    "      return `<div style=\"flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:100%;\">"
    "<div style=\"font-size:11px;color:var(--text-muted);margin-bottom:2px;\">${d.count}</div>"
    "<div style=\"width:100%;background:var(--primary);border-radius:4px 4px 0 0;height:${barH}px;\"></div>"
    "<div style=\"font-size:10px;color:var(--text-muted);margin-top:4px;\">${label}</div></div>`;\n"
    "    }).join('');\n"
    "  });\n"
    "}\n",
    "0-57 switchAdminTab에 stats 분기 + loadAdminStats 함수 추가")

# --- 0-58: groupSearchDebounce 옆에 정렬용 전역변수 추가 ---
h = replace_once(h,
    "let groupSearchDebounce = null;",
    "let groupSearchDebounce = null;\nlet lastPublicRoomsForSort = []; // 0-58: 오픈채팅 검색결과 정렬 변경시 재사용",
    "0-58 lastPublicRoomsForSort 전역변수 추가")

# --- 0-58: 공개 단체채팅방 검색결과 렌더링을 정렬 가능한 구조로 교체 ---
h = replace_once(h,
    "      if (publicRooms.length){\n"
    "        const label = document.createElement('div');\n"
    "        label.style.cssText = 'padding:8px 4px 4px;font-size:12px;color:var(--text-muted);font-weight:700;';\n"
    "        label.textContent = '공개 단체채팅방';\n"
    "        resultBox.appendChild(label);\n"
    "      }\n"
    "      publicRooms.forEach(r=>{\n"
    "        const wrap = document.createElement('div'); wrap.className='chat-row-wrap';\n"
    "        wrap.innerHTML = `<div class=\"chat-row-fg\" style=\"cursor:default;\">\n"
    "          <div class=\"avatar-sm\" style=\"display:flex;align-items:center;justify-content:center;background:var(--bg-secondary,#eee);\"><i class=\"fa-solid fa-users\"></i></div>\n"
    "          <div class=\"chat-row-text\">\n"
    "            <div class=\"chat-row-nick\">${escapeHtml(r.title)} <span style=\"color:var(--text-muted);font-weight:400;\">${r.memberCount}</span></div>\n"
    "            <div class=\"chat-row-last\">${escapeHtml(r.intro||'')}</div>\n"
    "          </div>\n"
    "          <button type=\"button\" class=\"btn btn-primary btn-sm\">입장</button>\n"
    "        </div>`;\n"
    "        wrap.querySelector('button').addEventListener('click', ()=>{ joinGroupByInviteCode(r.inviteCode); });\n"
    "        resultBox.appendChild(wrap);\n"
    "      });\n"
    "    });\n"
    "  }, 300);\n"
    "}\n",
    "      if (publicRooms.length){\n"
    "        const headerWrap = document.createElement('div');\n"
    "        headerWrap.style.cssText = 'display:flex;align-items:center;justify-content:space-between;padding:8px 4px 4px;';\n"
    "        headerWrap.innerHTML = `<span style=\"font-size:12px;color:var(--text-muted);font-weight:700;\">공개 단체채팅방</span>\n"
    "          <select id=\"publicRoomSortSelect\" style=\"font-size:12px;padding:4px 6px;border:1px solid var(--border-color);border-radius:6px;background:var(--bg-input);color:inherit;\" onchange=\"sortPublicRoomResults(this.value)\">\n"
    "            <option value=\"relevance\">관련도순</option>\n"
    "            <option value=\"members\">인원수 많은순</option>\n"
    "            <option value=\"newest\">최신 생성순</option>\n"
    "          </select>`;\n"
    "        resultBox.appendChild(headerWrap);\n"
    "        const publicContainer = document.createElement('div');\n"
    "        publicContainer.id = 'publicRoomResultsContainer';\n"
    "        resultBox.appendChild(publicContainer);\n"
    "        lastPublicRoomsForSort = publicRooms;\n"
    "        renderPublicRoomList(publicRooms, publicContainer);\n"
    "      }\n"
    "    });\n"
    "  }, 300);\n"
    "}\n"
    "// 0-58: 공개 단체채팅방 검색결과 목록을 그리는 헬퍼(정렬 변경시 재사용)\n"
    "function renderPublicRoomList(rooms, container){\n"
    "  container.innerHTML = '';\n"
    "  rooms.forEach(r=>{\n"
    "    const wrap = document.createElement('div'); wrap.className='chat-row-wrap';\n"
    "    wrap.innerHTML = `<div class=\"chat-row-fg\" style=\"cursor:default;\">\n"
    "      <div class=\"avatar-sm\" style=\"display:flex;align-items:center;justify-content:center;background:var(--bg-secondary,#eee);\"><i class=\"fa-solid fa-users\"></i></div>\n"
    "      <div class=\"chat-row-text\">\n"
    "        <div class=\"chat-row-nick\">${escapeHtml(r.title)} <span style=\"color:var(--text-muted);font-weight:400;\">${r.memberCount}</span></div>\n"
    "        <div class=\"chat-row-last\">${escapeHtml(r.intro||'')}</div>\n"
    "      </div>\n"
    "      <button type=\"button\" class=\"btn btn-primary btn-sm\">입장</button>\n"
    "    </div>`;\n"
    "    wrap.querySelector('button').addEventListener('click', ()=>{ joinGroupByInviteCode(r.inviteCode); });\n"
    "    container.appendChild(wrap);\n"
    "  });\n"
    "}\n"
    "// 0-58: 정렬 옵션 변경시 서버 재검색 없이 이미 받은 결과만 다시 정렬\n"
    "function sortPublicRoomResults(sortBy){\n"
    "  const container = document.getElementById('publicRoomResultsContainer');\n"
    "  if (!container) return;\n"
    "  let sorted = lastPublicRoomsForSort.slice();\n"
    "  if (sortBy==='members') sorted.sort((a,b)=> b.memberCount - a.memberCount);\n"
    "  else if (sortBy==='newest') sorted.sort((a,b)=> (b.createdAt||0) - (a.createdAt||0));\n"
    "  renderPublicRoomList(sorted, container);\n"
    "}\n",
    "0-58 공개 단체채팅방 검색결과 정렬 기능")

# --- 0-59: 온보딩 관련 JS 함수 추가 ---
h = replace_once(h,
    "function clearGroupSearch(){",
    "// 0-59: 신규가입자 온보딩 튜토리얼\n"
    "let onboardingStep = 0;\n"
    "function showOnboardingTutorial(){\n"
    "  onboardingStep = 0;\n"
    "  renderOnboardingStep();\n"
    "  openModal('onboardingTutorialScreen');\n"
    "}\n"
    "function renderOnboardingStep(){\n"
    "  document.querySelectorAll('.onboarding-slide').forEach(el=>{\n"
    "    el.classList.toggle('hidden', Number(el.dataset.step) !== onboardingStep);\n"
    "  });\n"
    "  for (let i=0;i<3;i++){\n"
    "    document.getElementById('onbDot'+i).classList.toggle('active', i===onboardingStep);\n"
    "  }\n"
    "  document.getElementById('onboardingNextBtn').textContent = onboardingStep===2 ? '시작하기' : '다음';\n"
    "}\n"
    "function nextOnboardingStep(){\n"
    "  if (onboardingStep < 2){ onboardingStep++; renderOnboardingStep(); }\n"
    "  else finishOnboarding();\n"
    "}\n"
    "function skipOnboarding(){ finishOnboarding(); }\n"
    "function finishOnboarding(){\n"
    "  closeModal('onboardingTutorialScreen');\n"
    "  if (currentUser) currentUser.onboardingSeen = true;\n"
    "  saveSession();\n"
    "  socket.emit('user:onboarding_seen', {});\n"
    "}\n"
    "function clearGroupSearch(){",
    "0-59 온보딩 튜토리얼 JS 함수 추가")

# --- 0-59: 신규가입 완료 시점(submitKakaoSignup)에 온보딩 트리거 ---
h = replace_once(h,
    "  socket.emit('auth:kakao_complete_profile', kakaoData, (res)=>{\n"
    "    if (res.success){ currentUser = res.user; saveSession(res.token); closeModal('authModal'); initApp(); }\n",
    "  socket.emit('auth:kakao_complete_profile', kakaoData, (res)=>{\n"
    "    if (res.success){ currentUser = res.user; saveSession(res.token); closeModal('authModal'); initApp(); if (!currentUser.onboardingSeen) setTimeout(showOnboardingTutorial, 400); }\n",
    "0-59 회원가입 완료시 온보딩 트리거")

write(INDEX, h)
print("[OK] public/index.html 패치 완료")
print("[완료] 0-57(관리자 통계) + 0-58(오픈채팅 정렬) + 0-59(온보딩 튜토리얼) 패치 적용 성공")