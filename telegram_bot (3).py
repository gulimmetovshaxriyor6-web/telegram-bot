"""
Telegram Guruh Nazorat Boti
============================
Qoidalar:
  1. Guruhga yangi odam qo'shilganda — kim qo'shgan bo'lsa, uning hisobiga +1
  2. Siz qo'shgan YOKI boshqalar qo'shgan — farqi yo'q, guruhga 5 ta yangi odam
     qo'shilishiga hissa qo'shgan foydalanuvchi yozish huquqini oladi
  3. Reklama havolasi tashlansa — o'chiriladi, foydalanuvchi jim qilinadi
"""

import logging
import re
import json
import os
from datetime import datetime

from telegram import Update, ChatPermissions
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ChatMemberHandler,
    filters,
    ContextTypes,
)

# ──────────────────────────────────────────────
# SOZLAMALAR — faqat shu ikki qatorni o'zgartiring
BOT_TOKEN        = "8784737027:AAHL5XYXbwp8mZ4bwYabvOKDtvqIhXceyTU"   # @BotFather dan
GROUP_ID         = -1001234567890          # Guruh ID (manfiy son)
REQUIRED_INVITES = 5                       # Nechta odam qo'shish kerak
# ──────────────────────────────────────────────

DATA_FILE = "user_data.json"

AD_PATTERNS = [
    r"https?://",
    r"t\.me/[a-zA-Z0-9_]+",
    r"@[a-zA-Z0-9_]{5,}",
    r"bit\.ly/", r"tinyurl\.com/", r"goo\.gl/",
    r"\+\d{10,}",
    r"wa\.me/", r"viber\.com/", r"join\.me/",
]

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    handlers=[logging.FileHandler("bot.log", encoding="utf-8"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ─── MA'LUMOTLAR ──────────────────────────────

def load() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"users": {}}

def save(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user(data: dict, uid: int) -> dict:
    key = str(uid)
    if key not in data["users"]:
        data["users"][key] = {
            "name":       "",
            "invites":    0,      # Bu foydalanuvchi qo'shgan odamlar soni
            "can_write":  False,
            "warned":     0,
            "joined":     datetime.now().isoformat(),
        }
    return data["users"][key]

def is_ad(text: str) -> bool:
    if not text:
        return False
    for p in AD_PATTERNS:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False

# ─── YANGI A'ZO ───────────────────────────────

async def on_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Guruhga yangi odam qo'shilganda ishga tushadi.
    Kim qo'shgan bo'lsa (from_user) — uning invite soniga +1 qo'shiladi.
    Yangi kelgan odam ham cheklanadi — u ham 5 ta qo'shishi kerak.
    """
    msg = update.message
    if not msg:
        return

    chat_id  = msg.chat_id
    adder    = msg.from_user   # Kim qo'shdi

    for new_user in msg.new_chat_members:
        if new_user.is_bot:
            continue

        data = load()

        # ── Yangi a'zoni cheklash ──
        new_u = get_user(data, new_user.id)
        new_u["name"] = new_user.first_name or str(new_user.id)

        if not new_u["can_write"]:
            try:
                await context.bot.restrict_chat_member(
                    chat_id=chat_id,
                    user_id=new_user.id,
                    permissions=ChatPermissions(
                        can_send_messages=False,
                        can_send_media_messages=False,
                        can_send_other_messages=False,
                        can_add_web_page_previews=False,
                    )
                )
                logger.info(f"Cheklandi: {new_user.id} ({new_user.first_name})")
            except Exception as e:
                logger.warning(f"Cheklash xatosi: {e}")

        # ── Kim qo'shdi — uning hisobiga +1 ──
        if adder and adder.id != new_user.id and not adder.is_bot:
            adder_u = get_user(data, adder.id)
            adder_u["name"]     = adder.first_name or str(adder.id)
            adder_u["invites"] += 1
            total               = adder_u["invites"]
            logger.info(f"{adder.id} ({adder.first_name}) qo'shdi, jami: {total}")

            # 5 taga yetdimi?
            if total >= REQUIRED_INVITES and not adder_u["can_write"]:
                adder_u["can_write"] = True
                try:
                    await context.bot.restrict_chat_member(
                        chat_id=chat_id,
                        user_id=adder.id,
                        permissions=ChatPermissions(
                            can_send_messages=True,
                            can_send_media_messages=True,
                            can_send_other_messages=True,
                            can_add_web_page_previews=True,
                        )
                    )
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=(
                            f"🎉 *{adder_u['name']}* endi guruhga yozishi mumkin!\n"
                            f"✅ {REQUIRED_INVITES} ta odam qo'shdi — tabriklaymiz! 🚀"
                        ),
                        parse_mode="Markdown"
                    )
                    logger.info(f"Ruxsat berildi: {adder.id}")
                except Exception as e:
                    logger.warning(f"Ruxsat berish xatosi: {e}")

        save(data)

        # ── Yangi a'zoga xabar ──
        remaining = max(0, REQUIRED_INVITES - new_u["invites"])
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"👋 *{new_user.first_name}* guruhga xush keldi!\n\n"
                    f"⚠️ Guruhga yozish uchun *{REQUIRED_INVITES} ta yangi odam* "
                    f"qo'shishingiz kerak.\n"
                    f"📊 Hozircha: *{new_u['invites']}/{REQUIRED_INVITES}*\n\n"
                    f"Do'stlaringizni guruhga qo'shing va yozish huquqini qozonin! 🔓"
                ),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Xush kelibsiz xabar xatosi: {e}")

# ─── XABAR TEKSHIRISH ─────────────────────────

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Har bir xabarni tekshirish"""
    if not update.message or not update.effective_user:
        return

    uid      = update.effective_user.id
    chat_id  = update.effective_chat.id
    text     = update.message.text or update.message.caption or ""
    name     = update.effective_user.first_name or "Foydalanuvchi"

    # Adminlarni o'tkazib yuborish
    try:
        m = await context.bot.get_chat_member(chat_id, uid)
        if m.status in ("administrator", "creator"):
            return
    except:
        pass

    data = load()
    user = get_user(data, uid)

    # ── 1. Reklama tekshirish ──
    if is_ad(text):
        try:
            await update.message.delete()
        except:
            pass

        user["warned"]   += 1
        user["can_write"] = False
        save(data)

        try:
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=uid,
                permissions=ChatPermissions(
                    can_send_messages=False,
                    can_send_media_messages=False,
                    can_send_other_messages=False,
                    can_add_web_page_previews=False,
                )
            )
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"Iltimos, *{name}* reklama tarqatmang!\n\n"
                    f"🚫 Xabaringiz o'chirildi va siz vaqtincha jim qilindingiz.\n"
                    f"📌 Bu guruhda reklama va havolalar qat'iyan taqiqlangan!"
                ),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Reklama o'chirish xatosi: {e}")
        return

    # ── 2. Yozish huquqi tekshirish ──
    if not user["can_write"]:
        try:
            await update.message.delete()
        except:
            pass

        invites   = user["invites"]
        remaining = max(0, REQUIRED_INVITES - invites)
        save(data)

        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"Kechirasiz! *{name}*, siz guruhga yozish uchun avval "
                    f"*{REQUIRED_INVITES} ta odam qo'shishingiz* zarur!\n\n"
                    f"📊 Hozirgi holat: *{invites}/{REQUIRED_INVITES}* ta qo'shilgan\n"
                    f"⏳ Yana *{remaining}* ta qo'shishingiz kerak."
                ),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Xabar yuborish xatosi: {e}")

# ─── KOMANDALAR ───────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🤖 *Guruh Nazorat Boti*\n\n"
        f"📋 *Qoidalar:*\n"
        f"• Guruhga yozish uchun *{REQUIRED_INVITES} ta odam* qo'shing\n"
        f"• Reklama havolalari avtomatik o'chiriladi\n\n"
        f"📌 /mening_holatim — qancha odam qo'shganingizni ko'ring",
        parse_mode="Markdown"
    )

async def cmd_holat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/mening_holatim — shaxsiy holat"""
    data      = load()
    user      = get_user(data, update.effective_user.id)
    invites   = user["invites"]
    remaining = max(0, REQUIRED_INVITES - invites)
    holat     = "✅ Yozish ruxsati bor!" if user["can_write"] else f"⏳ Yana *{remaining}* ta odam qo'shing"

    await update.message.reply_text(
        f"👤 *{update.effective_user.first_name}*\n\n"
        f"👥 Qo'shgan odamlar: *{invites}/{REQUIRED_INVITES}*\n"
        f"📊 Holat: {holat}",
        parse_mode="Markdown"
    )

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/stats — admin uchun statistika"""
    chat_id = update.effective_chat.id
    try:
        m = await context.bot.get_chat_member(chat_id, update.effective_user.id)
        if m.status not in ("administrator", "creator"):
            await update.message.reply_text("⛔ Faqat adminlar!")
            return
    except:
        return

    data      = load()
    total     = len(data["users"])
    can_write = sum(1 for u in data["users"].values() if u.get("can_write"))
    warned    = sum(1 for u in data["users"].values() if u.get("warned", 0) > 0)

    await update.message.reply_text(
        f"📊 *Statistika*\n\n"
        f"👥 Jami: *{total}*\n"
        f"✅ Yozishi mumkin: *{can_write}*\n"
        f"⏳ Kutayotgan: *{total - can_write}*\n"
        f"⚠️ Ogohlantirish olgan: *{warned}*",
        parse_mode="Markdown"
    )

async def cmd_unlock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/unlock — admin qo'lda qulfdan chiqarish (reply qilib)"""
    chat_id = update.effective_chat.id
    try:
        m = await context.bot.get_chat_member(chat_id, update.effective_user.id)
        if m.status not in ("administrator", "creator"):
            await update.message.reply_text("⛔ Faqat adminlar!")
            return
    except:
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("ℹ️ Foydalanuvchi xabariga reply qilib /unlock yozing!")
        return

    target_id = update.message.reply_to_message.from_user.id
    data      = load()
    u         = get_user(data, target_id)
    u["can_write"] = True
    save(data)

    try:
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=target_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            )
        )
        await update.message.reply_text("✅ Foydalanuvchi qulfdan chiqarildi!")
    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {e}")

async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /add <user_id> <son> — admin qo'lda taklif soni qo'shish
    Misol: /add 123456789 3
    """
    chat_id = update.effective_chat.id
    try:
        m = await context.bot.get_chat_member(chat_id, update.effective_user.id)
        if m.status not in ("administrator", "creator"):
            await update.message.reply_text("⛔ Faqat adminlar!")
            return
    except:
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Ishlatish: /add <user_id> <son>\nMisol: /add 123456789 3")
        return

    try:
        tid    = int(args[0])
        amount = int(args[1])
    except ValueError:
        await update.message.reply_text("❌ Noto'g'ri format! Misol: /add 123456789 3")
        return

    data = load()
    u    = get_user(data, tid)
    u["invites"] += amount

    unlocked = False
    if u["invites"] >= REQUIRED_INVITES and not u["can_write"]:
        u["can_write"] = True
        unlocked = True
        try:
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=tid,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                )
            )
        except:
            pass

    save(data)
    await update.message.reply_text(
        f"✅ {tid} ga *{amount}* ta qo'shildi.\n"
        f"📊 Jami: *{u['invites']}/{REQUIRED_INVITES}*\n"
        f"{'✅ Endi yozishi mumkin!' if unlocked else ('✅ Allaqachon yozishi mumkin edi.' if u['can_write'] else '⏳ Hali yozolmaydi.')}",
        parse_mode="Markdown"
    )

# ─── MAIN ─────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",            cmd_start))
    app.add_handler(CommandHandler("mening_holatim",   cmd_holat))
    app.add_handler(CommandHandler("stats",            cmd_stats))
    app.add_handler(CommandHandler("unlock",           cmd_unlock))
    app.add_handler(CommandHandler("add",              cmd_add))

    # Yangi a'zo qo'shilganda (StatusUpdate)
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_member))

    # Barcha xabarlarni tekshirish
    app.add_handler(MessageHandler(filters.TEXT | filters.CAPTION, on_message))

    logger.info("✅ Bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
