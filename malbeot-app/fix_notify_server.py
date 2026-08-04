import re

path = "server.js"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = """      await saveUser(user);
      await saveUser(target);
      cb && cb({ success: true, following: !isFollowing });
      broadcastUsers();
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 특정 유저를 팔로우하는 사람 목록 (제3자도 조회 가능)"""
new = """      await saveUser(user);
      await saveUser(target);
      if (!isFollowing) {
        const followerName = user.nickname || '누군가';
        notifyUser(targetId, { type: 'follow', userId: user.id, title: followerName, body: '나를 팔로우하였습니다' });
      }
      cb && cb({ success: true, following: !isFollowing });
      broadcastUsers();
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 특정 유저를 팔로우하는 사람 목록 (제3자도 조회 가능)"""
assert content.count(old) == 1, f"user:follow 매치 {content.count(old)}건"
content = content.replace(old, new)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Done - server.js updated")