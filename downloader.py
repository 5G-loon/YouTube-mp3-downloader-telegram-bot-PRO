import yt_dlp
import os
import uuid
import logging
import glob
import time

# ایجاد پوشه دانلود در صورت عدم وجود
if not os.path.exists("downloads"):
    os.makedirs("downloads")

logging.basicConfig(
    filename='bot_errors.log',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def cleanup_old_files():
    """پاکسازی فایل‌های قدیمی‌تر از 1 ساعت برای جلوگیری از پر شدن دیسک"""
    now = time.time()
    for f in glob.glob("downloads/*"):
        if os.path.isfile(f) and (now - os.path.getmtime(f)) > 3600:
            try:
                os.remove(f)
            except:
                pass

def get_common_opts():
    """تنظیمات پایه yt-dlp برای دور زدن محدودیت‌های یوتیوب و سرورهای ابری"""
    return {
        'quiet': True,
        'no_warnings': True,
        'noprogress': True,
        'ffmpeg_location': '/usr/bin/ffmpeg',
        'socket_timeout': 30,
        'retries': 5,
        'extractor_retries': 5,
        'extractor_args': {
            'youtube': {
                # ⚠️ تغییر کلیدی راه‌حل اول: قرار دادن 'tv' در اولویت اول
                # کلاینت تلویزیون (tv) کمترین سخت‌گیری را در تشخیص ربات دارد
                'player_client': ['tv', 'web', 'mweb'],
                'player_skip': ['webpage'],
            }
        },
        'http_headers': {
            # استفاده از User-Agent استاندارد دسکتاپ برای پایداری بیشتر
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        },
        # کمک به دور زدن برخی محدودیت‌های SSL در سرورهای ابری مثل Railway
        'nocheckcertificate': True,
    }

def analyze_url(url):
    """تشخیص می‌دهد که لینک یک آهنگ است یا پلی‌لیست (حالت سبک و سریع)"""
    ydl_opts = {
        **get_common_opts(),
        'extract_flat': 'in_playlist',  # برای سرعت و پایداری بیشتر در پلی‌لیست‌ها
        'skip_download': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        is_playlist = info.get('_type') == 'playlist' or 'entries' in info
        
        if is_playlist:
            entries = info.get('entries', [])
            # فیلتر کردن entryهای خالی یا نامعتبر
            valid_entries = [e for e in entries if e]
            return {
                'is_playlist': True,
                'title': info.get('title', 'پلی‌لیست'),
                'count': len(valid_entries),
                'entries': valid_entries,
            }
        else:
            return {
                'is_playlist': False,
                'title': info.get('title', 'بدون عنوان'),
                'url': info.get('webpage_url', url),
            }

def download_single_mp3(url):
    """دانلود یک آهنگ تکی و تبدیل به MP3 با کیفیت 128kbps"""
    cleanup_old_files()
    unique_id = str(uuid.uuid4())[:8]
    outtmpl = f"downloads/{unique_id}.%(ext)s"
    
    ydl_opts = {
        **get_common_opts(),
        'outtmpl': outtmpl,
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '128',
        }],
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        mp3_file = filename.rsplit('.', 1)[0] + '.mp3'
        
        # بررسی وجود فایل نهایی (گاهی اوقات پسوند کمی متفاوت است)
        if not os.path.exists(mp3_file):
            base = filename.rsplit('.', 1)[0]
            for f in glob.glob(f"{base}*"):
                if os.path.isfile(f) and f.endswith('.mp3'):
                    return f, info.get('title', 'آهنگ')
        
        return mp3_file, info.get('title', 'آهنگ')
