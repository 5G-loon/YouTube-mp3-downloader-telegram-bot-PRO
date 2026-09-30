import telebot
from telebot import types
import config
import database
import downloader
import time
import os
import logging

bot = telebot.TeleBot(config.BOT_TOKEN)
user_states = {}
cancel_flags = set()

logging.basicConfig(
    filename='bot_errors.log',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ═══════════════════════════════════════════
# توابع کمکی و منوها
# ═══════════════════════════════════════════
def is_admin(user_id):
    return user_id == config.ADMIN_ID

def check_access(user_id):
    return database.get_user_status(user_id) == 'approved' or is_admin(user_id)

def main_reply_menu(is_adm=False):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🎵 دانلود آهنگ"), types.KeyboardButton("ℹ️ راهنما"))
    if is_adm:
        markup.add(types.KeyboardButton("👥 مدیریت کاربران"), types.KeyboardButton("📢 ارسال همگانی"))
        markup.add(types.KeyboardButton("📊 آمار"), types.KeyboardButton("🐞 دیباگ"))
    return markup

def main_inline_menu(is_adm=False):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🎵 دانلود آهنگ", callback_data="menu_single"))
    markup.add(types.InlineKeyboardButton("ℹ️ راهنما", callback_data="menu_help"))
    if is_adm:
        markup.add(types.InlineKeyboardButton("👥 مدیریت کاربران", callback_data="manage_users"))
        markup.add(types.InlineKeyboardButton("📢 ارسال همگانی", callback_data="menu_broadcast"))
        markup.add(types.InlineKeyboardButton("📊 آمار", callback_data="menu_stats"))
        markup.add(types.InlineKeyboardButton("🐞 دیباگ", callback_data="menu_debug"))
    return markup

def back_markup():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 برگشت به منو", callback_data="back_menu"))
    return markup

def cancel_markup():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ لغو و برگشت", callback_data="cancel_op"))
    return markup

def send_menu(user_id):
    bot.send_message(
        user_id,
        "🏠 <b>منوی اصلی:</b>\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        parse_mode="HTML",
        reply_markup=main_reply_menu(is_admin(user_id))
    )
    bot.send_message(
        user_id,
        "🎛 <b>منوی شیشه‌ای:</b>",
        parse_mode="HTML",
        reply_markup=main_inline_menu(is_admin(user_id))
    )

# ═══════════════════════════════════════════
# استارت و تایید کاربران (بدون استفاده از /)
# ═══════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == '/start')
def start_message(message):
    user_id = message.from_user.id
    username = message.from_user.username or "ندارد"
    first_name = message.from_user.first_name or "کاربر"
    status = database.get_user_status(user_id)

    if status == 'approved' or is_admin(user_id):
        send_menu(user_id)
    elif status == 'rejected':
        database.update_user_status(user_id, 'pending')
        bot.send_message(user_id, "⏳ درخواست استفاده شما مجدداً ثبت شد.\nلطفاً منتظر تایید مدیر بمانید...")
        send_admin_approval_request(user_id, username, first_name, "درخواست عضویت مجدد")
    else:
        if status is None:
            database.add_user(user_id, username, first_name)
        bot.send_message(user_id, "⏳ سلام! درخواست استفاده شما ثبت شد.\nلطفاً منتظر تایید مدیر بمانید...")
        send_admin_approval_request(user_id, username, first_name, "درخواست عضویت جدید")

def send_admin_approval_request(user_id, username, first_name, title):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ تایید کاربر", callback_data=f"approve_{user_id}"))
    markup.add(types.InlineKeyboardButton("❌ رد کردن کاربر", callback_data=f"reject_{user_id}"))
    admin_msg = (
        f"🔔 <b>{title}</b>\n"
        f"👤 نام: {first_name}\n🆔 آیدی: @{username}\n🔢 یوزر آی‌دی: <code>{user_id}</code>"
    )
    bot.send_message(config.ADMIN_ID, admin_msg, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_") or call.data.startswith("reject_"))
def admin_actions(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "شما ادمین نیستید!")
        return
    action, user_id = call.data.split("_")
    user_id = int(user_id)
    
    if action == "approve":
        database.update_user_status(user_id, 'approved')
        bot.send_message(user_id, "🎉 <b>حساب شما تایید شد!</b>\nاکنون می‌توانید از امکانات ربات استفاده کنید.", parse_mode="HTML")
        send_menu(user_id)
        bot.edit_message_text(f"✅ <b>کاربر تایید شد</b>\n🔢 یوزر آی‌دی: <code>{user_id}</code>", call.message.chat.id, call.message.message_id, parse_mode="HTML")
    elif action == "reject":
        database.update_user_status(user_id, 'rejected')
        bot.send_message(user_id, "❌ <b>درخواست شما رد شد.</b>")
        bot.edit_message_text(f"❌ <b>کاربر رد شد</b>\n🔢 یوزر آی‌دی: <code>{user_id}</code>", call.message.chat.id, call.message.message_id, parse_mode="HTML")

# ═══════════════════════════════════════════
# مدیریت کاربران (مخصوص ادمین)
# ═══════════════════════════════════════════
@bot.callback_query_handler(func=lambda call: call.data.startswith("manage_users") or call.data.startswith("user_page_") or call.data.startswith("toggle_ban_"))
def user_management_handler(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "دسترسی غیرمجاز!")
        return

    if call.data.startswith("toggle_ban_"):
        target_id = int(call.data.split("_")[2])
        current_status = database.get_user_status(target_id)
        new_status = 'rejected' if current_status == 'approved' else 'approved'
        database.update_user_status(target_id, new_status)
        show_users_page(call, 1) # بازگشت به صفحه اول پس از تغییر
        return

    if call.data.startswith("user_page_"):
        page = int(call.data.split("_")[2])
        show_users_page(call, page)
        return

    if call.data == "manage_users":
        show_users_page(call, 1)

def show_users_page(call, page):
    users, total_pages, current_page = database.get_users_paginated(page, 5)
    text = f"👥 <b>مدیریت کاربران</b>\n📄 صفحه <b>{current_page}</b> از <b>{total_pages}</b>\n\n"
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for user in users:
        uid, uname, fname, status = user
        name = fname or "بدون نام"
        username = f"@{uname}" if uname else "ندارد"
        
        if status == 'approved':
            btn_text = f"✅ {name} ({username}) | مسدود کردن ❌"
        else:
            btn_text = f"❌ {name} ({username}) | آزاد کردن ✅"
            
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"toggle_ban_{uid}"))

    nav_buttons = []
    if current_page > 1:
        nav_buttons.append(types.InlineKeyboardButton("◀️ قبلی", callback_data=f"user_page_{current_page-1}"))
    if current_page < total_pages:
        nav_buttons.append(types.InlineKeyboardButton("بعدی ▶️", callback_data=f"user_page_{current_page+1}"))
    if nav_buttons:
        markup.add(*nav_buttons)

    markup.add(types.InlineKeyboardButton("🔙 برگشت به منو", callback_data="back_menu"))

    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)
    except:
        bot.send_message(call.message.chat.id, text, parse_mode="HTML", reply_markup=markup)
    bot.answer_callback_query(call.id)

# ═══════════════════════════════════════════
# هندلرهای منوی شیشه‌ای (کالبک‌ها)
# ═══════════════════════════════════════════
@bot.callback_query_handler(func=lambda call: call.data in ("menu_single", "menu_help", "menu_broadcast", "menu_stats", "menu_debug", "back_menu", "cancel_op"))
def inline_menu_handler(call):
    user_id = call.from_user.id
    data = call.data

    if data == "back_menu":
        user_states.pop(user_id, None)
        cancel_flags.discard(user_id)
        try: bot.edit_message_text("↩️ به منوی اصلی برگشتید.", call.message.chat.id, call.message.message_id)
        except: pass
        send_menu(user_id)
        bot.answer_callback_query(call.id, "برگشتید ✅")
        return

    if data == "cancel_op":
        cancel_flags.add(user_id)
        user_states.pop(user_id, None)
        try: bot.edit_message_text("❌ عملیات لغو شد.", call.message.chat.id, call.message.message_id)
        except: pass
        send_menu(user_id)
        bot.answer_callback_query(call.id, "لغو شد ❌")
        return

    if not check_access(user_id):
        bot.answer_callback_query(call.id, "دسترسی غیرمجاز!")
        return

    if data == "menu_single":
        user_states[user_id] = 'waiting_single'
        bot.edit_message_text("🔗 <b>لینک ویدیوی یوتیوب را ارسال کنید:</b>", call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=back_markup())
    elif data == "menu_help":
        bot.send_message(user_id, help_text(), parse_mode="HTML", reply_markup=back_markup())
    elif data == "menu_broadcast":
        if not is_admin(user_id): return
        user_states[user_id] = 'waiting_broadcast'
        users = database.get_all_approved_users()
        bot.edit_message_text(f"📊 تعداد کاربران تایید شده: <b>{len(users)}</b> نفر\n📢 پیام خود را برای ارسال همگانی بفرستید:", call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=back_markup())
    elif data == "menu_stats":
        if not is_admin(user_id): return
        stats = database.get_stats()
        text = f"📊 <b>آمار ربات</b>\n👥 کل: <b>{stats['total']}</b>\n✅ تایید شده: <b>{stats['approved']}</b>\n⏳ در انتظار: <b>{stats['pending']}</b>\n❌ رد شده: <b>{stats['rejected']}</b>"
        bot.send_message(user_id, text, parse_mode="HTML", reply_markup=back_markup())
    elif data == "menu_debug":
        if not is_admin(user_id): return
        show_debug_log(user_id)
        
    bot.answer_callback_query(call.id)

def show_debug_log(user_id):
    log_file = 'bot_errors.log'
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
        if content:
            lines = content.strip().split('\n')
            last = '\n'.join(lines[-15:])
            bot.send_message(user_id, f"🐞 <b>15 خطای آخر:</b>\n<pre>{last}</pre>", parse_mode="HTML", reply_markup=back_markup())
        else:
            bot.send_message(user_id, "✅ هیچ خطایی ثبت نشده!", reply_markup=back_markup())
    else:
        bot.send_message(user_id, "✅ سرور تمیز است!", reply_markup=back_markup())

# ═══════════════════════════════════════════
# دکمه‌های معمولی (Reply)
# ═══════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text in ("🎵 دانلود آهنگ", "ℹ️ راهنما", "👥 مدیریت کاربران", "📢 ارسال همگانی", "📊 آمار", "🐞 دیباگ"))
def btn_handler(message):
    user_id = message.from_user.id
    text = message.text

    if not check_access(user_id) and text != "ℹ️ راهنما":
        bot.send_message(message.chat.id, "⛔️ دسترسی غیرمجاز. ابتدا دکمه استارت را بزنید.")
        return

    if text == "🎵 دانلود آهنگ":
        user_states[user_id] = 'waiting_single'
        bot.send_message(message.chat.id, "🔗 <b>لینک ویدیوی یوتیوب را ارسال کنید:</b>", parse_mode="HTML", reply_markup=back_markup())
    elif text == "ℹ️ راهنما":
        bot.send_message(message.chat.id, help_text(), parse_mode="HTML", reply_markup=back_markup())
    elif text == "👥 مدیریت کاربران" and is_admin(user_id):
        # ارسال یک پیام اولیه برای اینکه کالبک بعدی بتواند آن را ویرایش کند
        msg = bot.send_message(message.chat.id, "⏳ در حال بارگذاری لیست کاربران...", reply_markup=back_markup())
        # شبیه‌سازی کالبک برای استفاده از تابع مشترک
        call_obj = types.CallbackQuery(id="1", from_user=message.from_user, chat_instance="1", message=msg, data="manage_users")
        show_users_page(call_obj, 1)
    elif text == "📢 ارسال همگانی" and is_admin(user_id):
        user_states[user_id] = 'waiting_broadcast'
        users = database.get_all_approved_users()
        bot.send_message(message.chat.id, f"📊 تعداد کاربران تایید شده: <b>{len(users)}</b> نفر\n📢 پیام خود را بفرستید:", parse_mode="HTML", reply_markup=back_markup())
    elif text == "📊 آمار" and is_admin(user_id):
        stats = database.get_stats()
        txt = f"📊 <b>آمار ربات</b>\n👥 کل: <b>{stats['total']}</b>\n✅ تایید شده: <b>{stats['approved']}</b>\n⏳ در انتظار: <b>{stats['pending']}</b>\n❌ رد شده: <b>{stats['rejected']}</b>"
        bot.send_message(message.chat.id, txt, parse_mode="HTML", reply_markup=back_markup())
    elif text == "🐞 دیباگ" and is_admin(user_id):
        show_debug_log(user_id)

def help_text():
    return """
👋 <b>راهنمای ربات</b>
🎵 <b>دانلود آهنگ تکی:</b>
لینک یک ویدیو از یوتیوب را بفرستید تا فایل MP3 با کیفیت 128kbps دریافت کنید.

🔙 <b>دکمه برگشت:</b>
در تمام مراحل می‌توانید با دکمه «🔙 برگشت به منو» به منوی اصلی بازگردید.

⚠️ <b>نکته:</b>
• فقط لینک‌های یوتیوب پشتیبانی می‌شوند.
• حداکثر حجم هر فایل 50MB (محدودیت تلگرام) است.
"""

# ═══════════════════════════════════════════
# پردازش متن‌های ورودی
# ═══════════════════════════════════════════
@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.text.startswith('/'):
        bot.send_message(message.chat.id, "⚠️ لطفاً فقط از دکمه‌های پایین صفحه استفاده کنید.")
        return

    user_id = message.from_user.id
    state = user_states.get(user_id)

    if not check_access(user_id):
        bot.send_message(message.chat.id, "⛔️ دسترسی غیرمجاز.")
        return

    url = message.text.strip()

    if state == 'waiting_broadcast' and is_admin(user_id):
        user_states.pop(user_id, None)
        handle_broadcast(message)
        return

    if state == 'waiting_single':
        if "youtube.com" not in url and "youtu.be" not in url:
            bot.send_message(message.chat.id, "❌ لینک نامعتبر! فقط لینک‌های یوتیوب مجاز است.", reply_markup=back_markup())
            return
        process_single(message, url)
        return

# ═══════════════════════════════════════════
# دانلود آهنگ تکی
# ═══════════════════════════════════════════
def process_single(message, url):
    user_id = message.from_user.id
    user_states.pop(user_id, None)
    wait_msg = bot.send_message(message.chat.id, "⏳ <b>در حال پردازش...</b>\nلطفاً صبر کنید.", parse_mode="HTML", reply_markup=cancel_markup())
    
    try:
        file_path, title = downloader.download_single_mp3(url)
        if not os.path.exists(file_path):
            raise FileNotFoundError("فایل ایجاد نشد!")
        
        with open(file_path, 'rb') as f:
            bot.send_audio(message.chat.id, f, caption=f"🎵 {title}\n🎧 کیفیت: 128kbps", title=title[:60], performer="YouTube MP3")
        
        bot.delete_message(wait_msg.chat.id, wait_msg.message_id)
        os.remove(file_path)
    except Exception as e:
        try:
            bot.edit_message_text("❌ <b>خطا در دانلود!</b>\nلطفاً لینک را بررسی کرده و مجدد تلاش کنید.", wait_msg.chat.id, wait_msg.message_id, parse_mode="HTML", reply_markup=back_markup())
        except: pass
        logging.error(f"Single download error: {str(e)}")

# ═══════════════════════════════════════════
# ارسال همگانی
# ═══════════════════════════════════════════
def handle_broadcast(message):
    users = database.get_all_approved_users()
    if not users:
        bot.send_message(message.chat.id, "❌ هیچ کاربر تایید شده‌ای وجود ندارد!")
        return
    wait_msg = bot.send_message(message.chat.id, f"⏳ در حال ارسال به {len(users)} کاربر...")
    success = fail = 0
    for uid in users:
        try:
            bot.copy_message(uid, message.chat.id, message.message_id)
            success += 1
            time.sleep(0.1)
        except: fail += 1
    bot.edit_message_text(f"✅ <b>ارسال همگانی پایان یافت!</b>\n📤 موفق: <b>{success}</b>\n❌ ناموفق: <b>{fail}</b>", wait_msg.chat.id, wait_msg.message_id, parse_mode="HTML")

# ═══════════════════════════════════════════
# اجرای ربات
# ═══════════════════════════════════════════
if __name__ == "__main__":
    database.init_db()
    print("🚀 ربات در حال راه‌اندازی...")
    try:
        info = bot.get_me()
        print(f"✅ متصل شد: @{info.username}")
    except Exception as e:
        if "409" in str(e):
            print("❌ خطا: یک نمونه دیگر از ربات در حال اجراست!")
            import sys
            sys.exit(1)

    while True:
        try:
            print("🔄 دریافت پیام‌ها...")
            bot.infinity_polling(timeout=10, long_polling_timeout=50)
        except Exception as e:
            if "409" in str(e):
                print("⚠️ خطای 409 - صبر 30 ثانیه...")
                time.sleep(30)
            else:
                print(f"❌ خطا: {e}")
                logging.error(f"Main error: {e}")
                time.sleep(5)