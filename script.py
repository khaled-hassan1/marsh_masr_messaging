import os
import requests
import xml.etree.ElementTree as ET
import firebase_admin
from firebase_admin import credentials, messaging

# 1. إعدادات القناة و Firebase
CHANNEL_ID = "UC1e7MOlHXjOMpodPrag5lDw"
DB_FILE = "last_video_id.txt"

# فك تشفير مفتاح Firebase من الـ Environment Secrets
firebase_secret = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
if not firebase_secret:
    print("❌ Firebase Secret missing!")
    exit(1)

with open("firebase_creds.json", "w") as f:
    f.write(firebase_secret)

cred = credentials.Certificate("firebase_creds.json")
firebase_admin.initialize_app(cred)

def get_latest_youtube_video(channel_id):
    """جلب آخر فيديو عبر الـ RSS Feed المجاني من يوتيوب"""
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    response = requests.get(url)
    if response.status_code != 200:
        print("❌ Failed to fetch YouTube feed")
        return None
    
    root = ET.fromstring(response.content)
    # مساحات الأسماء في الـ XML
    ns = {'ns': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
    
    entry = root.find('ns:entry', ns)
    if entry is None:
        return None
        
    video_id = entry.find('yt:videoId', ns).text
    title = entry.find('ns:title', ns).text
    video_url = entry.find('ns:link', ns).attrib['href']
    # رابط الـ Poster بجودة عالية
    poster_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    
    return {
        "id": video_id,
        "title": title,
        "url": video_url,
        "poster": poster_url
    }

def send_fcm_notification(video):
    """إرسال الإشعار لـ Firebase متضمناً البيانات والصورة"""
    message = messaging.Message(
        notification=messaging.Notification(
            title="🎭 فيديو جديد من مسرح مصر!",
            body=video["title"],
            image=video["poster"] # جوجل ستعرض الصورة تلقائياً في الإشعار السحابي
        ),
        data={
            "payload": video["id"],          # الـ Video ID لتشغيله
            "target_url": video["url"],      # رابط الفيديو
            "target_title": video["title"],  # العنوان
            "poster_url": video["poster"]    # غلاف الفيديو
        },
        topic="masrah_masr"
    )
    response = messaging.send(message)
    print(f"✅ Successfully sent message: {response}")

# تشغيل الفحص
latest_video = get_latest_youtube_video(CHANNEL_ID)

if latest_video:
    # قراءة آخر فيديو تم إرساله لمنع التكرار
    last_saved_id = ""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            last_saved_id = f.read().strip()
            
    if latest_video["id"] != last_saved_id:
        print(f"🚀 New Video Detected: {latest_video['title']}")
        send_fcm_notification(latest_video)
        # تحديث الملف بالـ id الجديد
        with open(DB_FILE, "w") as f:
            f.write(latest_video["id"])
    else:
        print("😴 No new videos found.")