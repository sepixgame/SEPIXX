import json
import os
from datetime import datetime
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

# --- تنظیمات ---
CHANNEL_ID_1 = "@sepix_shop"
CHANNEL_ID_2 = "@sepix_trust"
GROUP_ID = "@sepix_gap"
ADMIN_ID = 826685726
BOT_USERNAME = "sepix_codm_bot"
DB_FILE = "users.json"
BOT_TOKEN = os.environ.get("BOT_TOKEN")  # امن‌تر برای سرور

# --- بارگذاری کاربران ---
def load_users():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    print("⚠️ فایل users.json ساختار درستی ندارد. بازنویسی می‌شود.")
                    return {}
                for uid in data:
                    data[uid]["invites"] = set(data[uid].get("invites", []))
                    data[uid]["daily"] = data[uid].get("daily", {})
                return data
        except Exception as e:
            print(f"⚠️ خطا در خواندن فایل users.json: {e}. بازنویسی می‌شود.")
            return {}
    else:
        with open(DB_FILE, "w") as f:
            json.dump({}, f)
        return {}

# --- ذخیره کاربران ---
def save_users():
    with open(DB_FILE, "w") as f:
        json.dump({
            uid: {
                "points": user.get("points", 0),
                "invites": list(user.get("invites", [])),
                "daily": user.get("daily", {})
            } for uid, user in users.items()
        }, f, indent=2)

users = load_users()

# --- چک کردن عضویت کاربر ---
async def is_user_member(context: ContextTypes.DEFAULT_TYPE, user_id: int, channel: str) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        print(f"خطا در بررسی عضویت در {channel}: {e}")
        return False

async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return

    member1 = await is_user_member(context, user.id, CHANNEL_ID_1)
    member2 = await is_user_member(context, user.id, CHANNEL_ID_2)

    if member1 and member2:
        await update.callback_query.answer("✅ شما در هر دو کانال عضو هستید!")
        await show_main_menu(update, context)
    else:
        await update.callback_query.answer("⛔ لطفاً در هر دو کانال عضو شوید.", show_alert=True)

# --- منوی اصلی ---
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("🎁 دریافت لینک دعوت")],
        [KeyboardButton("👥 امتیاز من"), KeyboardButton("🆘 پشتیبانی")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("به منوی اصلی خوش آمدید 👇", reply_markup=reply_markup)

# --- استارت ---
async def start_with_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return

    uid = str(user.id)
    args = context.args

    if uid not in users:
        users[uid] = {"points": 0, "invites": set(), "daily": {}}
        if args:
            ref_id = args[0]
            if ref_id != uid and ref_id in users:
                if uid not in users[ref_id]["invites"]:
                    users[ref_id]["invites"].add(uid)
                    users[ref_id]["points"] += 10
                    await context.bot.send_message(
                        chat_id=int(ref_id),
                        text=f"🎉 کاربر جدیدی از طریق لینک دعوت شما عضو شد!\nشما ۱۰ امتیاز دریافت کردید."
                    )
        save_users()

    # ارسال دکمه بررسی عضویت
    keyboard = [
        [InlineKeyboardButton("✅ عضوم شدم", callback_data="check_membership")],
        [InlineKeyboardButton("🔗 کانال اول", url=f"https://t.me/{CHANNEL_ID_1[1:]}")],
        [InlineKeyboardButton("🔗 کانال دوم", url=f"https://t.me/{CHANNEL_ID_2[1:]}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "برای ادامه ابتدا باید در دو کانال زیر عضو شوید:\nسپس روی دکمه «عضو شدم» کلیک کنید.",
        reply_markup=reply_markup
    )

# --- مدیریت پیام‌ها ---
async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = str(update.effective_user.id)

    if text == "🎁 دریافت لینک دعوت":
        await update.message.reply_text(f"🔗 لینک دعوت شما:\nhttps://t.me/{BOT_USERNAME}?start={uid}")
    elif text == "👥 امتیاز من":
        points = users.get(uid, {}).get("points", 0)
        await update.message.reply_text(f"🏆 امتیاز فعلی شما: {points}")
    elif text == "🆘 پشتیبانی":
        await update.message.reply_text("برای پشتیبانی به آی‌دی زیر پیام دهید:\n@MR_sepix")
    else:
        await update.message.reply_text("دستور نامعتبر است. از منوی زیر انتخاب کنید.")

# --- اجرای ربات ---
if __name__ == "__main__":
    if not BOT_TOKEN:
        print("❌ توکن ربات در متغیر BOT_TOKEN یافت نشد.")
        exit(1)

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_with_referral))
    app.add_handler(CommandHandler("invite", lambda u, c: u.message.reply_text("از منوی ربات گزینه «🎁 دریافت لینک دعوت» را بزنید.")))
    app.add_handler(CallbackQueryHandler(check_membership, pattern="check_membership"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))

    print("✅ ربات با موفقیت اجرا شد.")
    app.run_polling()
