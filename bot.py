import feedparser
import requests
import random
import time
import os
import socket
from datetime import datetime, timezone, timedelta

socket.setdefaulttimeout(10)  # chặn treo khi fetch RSS/Discord quá 10s
DISCORD_WEBHOOKS = [w.strip() for w in os.environ["DISCORD_WEBHOOK"].split(",") if w.strip()]
USERNAME = "trickcal_en"
VN_TZ = timezone(timedelta(hours=7))
ROLE_ID = os.environ.get("DISCORD_ROLE_ID", "1436532654479642685")  #trickal-ping role

MESSAGES = [
    "📢 Trickal_EN có thông báo mới! <a:Kommy_lick:1435193595438039040>"
]

RSS_SOURCES = [
    f"https://fxtwitter.com/{USERNAME}/feed.xml",
]

# Khung giờ an toàn (phút VN) — khớp lịch cron-job.org thực tế (tight+sparse: 9:00–19:40)
WINDOW = (8*60+55, 19*60+45)  # 8:55 - 19:45, có đệm 2 đầu — không đổi, không liên quan tới việc đổi RSS source

now_vn = datetime.now(VN_TZ)
total_min = now_vn.hour * 60 + now_vn.minute
in_window = WINDOW[0] <= total_min <= WINDOW[1]

if not in_window:
    print(f"Ngoài khung giờ ({now_vn.strftime('%H:%M')} VN) → thoát")
    exit()

print(f"Scan lúc {now_vn.strftime('%H:%M')} VN")

# Jitter — chỉ chờ SAU KHI đã xác nhận trong khung giờ, tránh gọi API đồng loạt đúng giây 0
jitter = random.uniform(5, 20)
print(f"Chờ {jitter:.1f}s trước khi fetch")
time.sleep(jitter)

# Đọc last_id
try:
    with open("last_id.txt") as f:
        last_id = f.read().strip()
except:
    last_id = ""

# Lấy RSS — chọn nguồn tươi nhất
def entry_time(entry):
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    return datetime.min.replace(tzinfo=timezone.utc)

best_entries = []
best_time = datetime.min.replace(tzinfo=timezone.utc)
for url in RSS_SOURCES:
    print(f"Thử: {url}")
    try:
        feed = feedparser.parse(url)
        if not feed.entries:
            print("❌ 0 bài")
            continue
        t = entry_time(feed.entries[0])
        print(f"✅ {len(feed.entries)} bài | mới nhất: {t.strftime('%m-%d %H:%M UTC')}")
        if t > best_time:
            best_time = t
            best_entries = feed.entries
    except Exception as e:
        print(f"❌ {e}")

if not best_entries:
    print("Tất cả nguồn thất bại")
    exit()

lag = (datetime.now(timezone.utc) - best_time).total_seconds()
print(f"DEBUG: bài mới nhất cũ hơn hiện tại {lag:.0f} giây")  # theo dõi vài lần để xem cache CDN có làm stale không — như đã bàn ở tin trước

print(f"DEBUG raw link: {best_entries[0].link} | raw id: {best_entries[0].id}")  # xoá sau khi đã xác nhận format ổn định

# Tìm bài mới
new_posts = []
for entry in best_entries:
    if entry.id == last_id:
        break
    new_posts.append(entry)
print(f"Bài mới: {len(new_posts)}")

if new_posts:
    for post in reversed(new_posts):
        link = post.link
        if "fxtwitter.com" not in link:
            for d in ["twitter.com", "x.com"]:
                link = link.replace(f"://{d}", "://fxtwitter.com")
        for i, webhook in enumerate(DISCORD_WEBHOOKS, 1):
            msg = random.choice(MESSAGES)
            r = requests.post(webhook, json={
            "content": f"{msg}\n{link}",
            "username": "Mochi FM",
            "allowed_mentions": {"parse": ["roles"]}
        }, timeout=10)
            print(f"Discord #{i}: {r.status_code} → {link}")
    with open("last_id.txt", "w") as f:
        f.write(best_entries[0].id)
    print("✅ Đã lưu last_id")
else:
    print("Không có bài mới")