import json
import os
import re
import threading
import time
import telebot
from telebot import types

TOKEN = "8834039334:AAEjkdnuE_u3CNr-7O5xRg0rdbSHjVeos4g"

# آیدی عددی دقیق شما (رئیس شاهد)
ADMIN_ID = 8173349543

bot = telebot.TeleBot(TOKEN)

# ----------------- دیتابیس دائمی (ذخیره در فایل) -----------------
DB_FILE = "database.json"


def load_data():
  if os.path.exists(DB_FILE):
    try:
      with open(DB_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        return (
            {int(k): v for k, v in data.get("user_points", {}).items()},
            set(data.get("all_users", [])),
            set(data.get("invited_users", [])),
            set(data.get("claimed_daily", [])),
            {int(k): v for k, v in data.get("user_lang", {}).items()},
        )
    except Exception as e:
      print(f"خطا در خواندن دیتابیس: {e}")
  return {}, set(), set(), set(), {}


def save_data():
  data = {
      "user_points": user_points,
      "all_users": list(all_users),
      "invited_users": list(invited_users),
      "claimed_daily": list(claimed_daily),
      "user_lang": user_lang,
  }
  try:
    with open(DB_FILE, "w", encoding="utf-8") as f:
      json.dump(data, f, ensure_ascii=False, indent=4)
  except Exception as e:
    print(f"خطا در ذخیره‌سازی دیتابیس: {e}")


# بارگیری اطلاعات هنگام اجرای ربات
user_points, all_users, invited_users, claimed_daily, user_lang = load_data()

# دیتابیس‌های موقت حافظه
user_sessions = {}
waiting_for_support = set()
waiting_for_file = set()
waiting_for_broadcast = {}

BOT_USERNAME = bot.get_me().username


# تابع اختصاصی بررسی ادمین بودن
def is_admin(user_id):
  return str(user_id) == str(ADMIN_ID) or user_id == ADMIN_ID


# ----------------- متون سه‌زبانه -----------------
TEXTS = {
    "fa": {
        "welcome": (
            "✨ سلام {name} عزیز! به ربات خوش آمدید.\n\n📋 **مشخصات حساب"
            " شما:**\n👤 **نام:** {name}\n🆔 **یوزرنیم:** {username}\n🔢 **آیدی"
            " عددی:** `{id}`\n💎 **موجودی امتیاز:** `{points}` امتیاز\n\n💡 *هزینه"
            " هر بار رنگ‌آمیزی فایل: ۱۰ امتیاز*"
        ),
        "btn_color": "🎨 تغییر رنگ کیبورد",
        "btn_support": "📞 پشتیبانی",
        "btn_daily": "🎁 سکه روزانه",
        "btn_buy": "💳 خرید امتیاز",
        "btn_info": "👤 اطلاعات من / لینک دعوت",
        "btn_lang": "🌐 تغییر زبان / ژبه بدلول / Change Language",
        "daily_success": (
            "🎉 **پاداش روزانه!** ۲ امتیاز به حساب شما اضافه شد."
        ),
        "daily_already": (
            "⚠️ شما پاداش امروز را قبلاً دریافت کرده‌اید! فردا دوباره تلاش"
            " کنید."
        ),
        "buy_text": (
            "💳 ━━━━━━━━━━━━━━━━━━ 💳\n✨ **لیست قیمت‌های خرید امتیاز**"
            " ✨\n━━━━━━━━━━━━━━━━━━━━\n\n💎 **۱۰ امتیاز** 👈 **۵۰"
            " افغانی**\n💎 **۲۰ امتیاز** 👈 **۷۰ افغانی**\n💎 **۳۰"
            " امتیاز** 👈 **۸۰ افغانی**\n\n━━━━━━━━━━━━━━━━━━━━\n📩 **جهت"
            " سفارش و خرید امتیاز، به پشتیبانی پیام دهید.**"
        ),
        "info_text": (
            "👤 **اطلاعات حساب:**\nآیدی: `{id}`\nامتیاز: `{points}`\n\n🔗 **لینک"
            " دعوت شما:**\n`https://t.me/{bot}?start=ref_{id}`\n\n🎁 با دعوت"
            " هر دوست ۲ امتیاز بگیرید!"
        ),
        "send_file_req": (
            "📂 **لطفاً اکنون فایل پایتون (.py) خود را ارسال کنید:**"
        ),
        "low_points": (
            "❌ **امتیاز شما کافی نیست!** (حداقل ۱۰ امتیاز لازم است)"
        ),
        "select_lang": (
            "لطفاً زبان خود را انتخاب کنید / مهرباني وکړئ خپله ژبه وټاکئ /"
            " Please select your language:"
        ),
    },
    "ps": {
        "welcome": (
            "✨ سلام {name} ګرانه! ربات ته ښه راغلاست.\n\n📋 **ستاسو د حساب"
            " مشخصات:**\n👤 **نوم:** {name}\n🆔 **یوزرنیم:** {username}\n🔢"
            " **عددي آئي ډي:** `{id}`\n💎 **امتیازونه:** `{points}` امتیاز"
        ),
        "btn_color": "🎨 د کیبورډ رنګ بدلول",
        "btn_support": "📞 ملاتړ (پشتیبانی)",
        "btn_daily": "🎁 ورځنۍ سکه",
        "btn_buy": "💳 د امتیازونو پیرود",
        "btn_info": "👤 زما معلومات / د بلنې لینک",
        "btn_lang": "🌐 تغییر زبان / ژبه بدلول / Change Language",
        "daily_success": "🎉 ۲ وړیا امتیازونه ستاسو حساب ته اضافه شول!",
        "daily_already": "⚠️ تاسو نننۍ جایزه مخکې ترلاسه کړې ده!",
        "buy_text": (
            "💳 ━━━━━━━━━━━━━━━━━━ 💳\n✨ **د امتیازونو د اخیستلو نرخونه**"
            " ✨\n━━━━━━━━━━━━━━━━━━━━\n\n💎 **۱۰ امتیازونه** 👈 **۵۰"
            " افغانۍ**\n💎 **۲۰ امتیازونه** 👈 **۷۰ افغانۍ**\n💎 **۳۰"
            " امتیازونه** 👈 **۸۰ افغانۍ**\n\n━━━━━━━━━━━━━━━━━━━━\n📩 **د"
            " اخیستلو لپاره د پشتیبانۍ برخې ته پیام واستوئ.**"
        ),
        "info_text": (
            "👤 **ستاسو معلومات:**\nآئي ډي: `{id}`\nامتیازونه: `{points}`\n\n🔗"
            " **ستاسو د بلنې لینک:**\n`https://t.me/{bot}?start=ref_{id}`"
        ),
        "send_file_req": (
            "📂 **مهرباني وکړئ خپل د پایتون (.py) فایل واستوئ:**"
        ),
        "low_points": (
            "❌ **ستاسو امتیازونه کافي ندي!** (لږترلږه ۱۰ امتیازونه پکار دي)"
        ),
        "select_lang": "مهرباني وکړئ خپله ژبه وټاکئ:",
    },
    "en": {
        "welcome": (
            "✨ Welcome {name}!\n\n📋 **Account Details:**\n👤 **Name:**"
            " {name}\n🆔 **Username:** {username}\n🔢 **ID:** `{id}`\n💎"
            " **Points:** `{points}`"
        ),
        "btn_color": "🎨 Change Keyboard Color",
        "btn_support": "📞 Support",
        "btn_daily": "🎁 Daily Bonus",
        "btn_buy": "💳 Buy Points",
        "btn_info": "👤 My Info / Referral Link",
        "btn_lang": "🌐 Change Language",
        "daily_success": "🎉 You got 2 free points!",
        "daily_already": "⚠️ You have already claimed today's bonus!",
        "buy_text": (
            "💳 ━━━━━━━━━━━━━━━━━━ 💳\n✨ **Points Price List**"
            " ✨\n━━━━━━━━━━━━━━━━━━━━\n\n💎 **10 Points** 👈 **50 AFN**\n💎"
            " **20 Points** 👈 **70 AFN**\n💎 **30 Points** 👈 **80"
            " AFN**\n\n━━━━━━━━━━━━━━━━━━━━\n📩 **To purchase points, please"
            " contact support.**"
        ),
        "info_text": (
            "👤 **Your Info:**\nID: `{id}`\nPoints: `{points}`\n\n🔗 **Referral"
            " Link:**\n`https://t.me/{bot}?start=ref_{id}`"
        ),
        "send_file_req": "📂 **Please send your Python (.py) file now:**",
        "low_points": "❌ **Not enough points!** (10 points required)",
        "select_lang": "Please select your language:",
    },
}


def get_points(user_id):
  if user_id not in user_points:
    user_points[user_id] = 20
    save_data()
  return user_points[user_id]


def get_lang(user_id):
  return user_lang.get(user_id, "fa")


# ----------------- تابع حذف خودکار پیام‌ها -----------------
def auto_delete_messages(chat_id, message_ids, delay=30):
  def delete_job():
    time.sleep(delay)
    for msg_id in message_ids:
      try:
        bot.delete_message(chat_id, msg_id)
      except Exception:
        pass

  threading.Thread(target=delete_job).start()


# ----------------- کیبورد اصلی ربات -----------------
def main_keyboard(user_id):
  lang = get_lang(user_id)
  t = TEXTS[lang]

  markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
  btn_color = types.KeyboardButton(t["btn_color"])
  btn_support = types.KeyboardButton(t["btn_support"])
  btn_daily = types.KeyboardButton(t["btn_daily"])
  btn_buy = types.KeyboardButton(t["btn_buy"])
  btn_info = types.KeyboardButton(t["btn_info"])
  btn_lang = types.KeyboardButton(t["btn_lang"])

  markup.add(btn_color)
  markup.add(btn_support, btn_daily)
  markup.add(btn_info, btn_buy)
  markup.add(btn_lang)
  return markup


# ----------------- دستور /add برای افزودن امتیاز -----------------
@bot.message_handler(commands=["add"])
def add_points_cmd(message):
  if not is_admin(message.chat.id):
    bot.reply_to(message, "❌ شما دسترسی به این دستور را ندارید!")
    return

  try:
    args = message.text.split()
    target_id = int(args[1])
    amount = int(args[2])

    current = get_points(target_id)
    new_total = current + amount
    user_points[target_id] = new_total
    save_data()

    bot.reply_to(
        message,
        f"✅ **تعداد `{amount}` امتیاز به کاربر `{target_id}` اضافه"
        f" شد.**\n💎 **موجودی کل جدید:** `{new_total}` امتیاز",
        parse_mode="Markdown",
    )
    try:
      bot.send_message(
          target_id,
          f"🎉 **تبریک!**\nتعداد `{amount}` امتیاز از طرف مدیریت به حساب شما"
          f" اضافه شد.\n💎 **موجودی کل جدید شما:** `{new_total}` امتیاز",
          parse_mode="Markdown",
      )
    except Exception:
      pass
  except Exception:
    bot.reply_to(
        message,
        "⚠️ **طرز استفاده درست:**\n`/add 8173349543 10`",
        parse_mode="Markdown",
    )


# ----------------- پنل مدیریت اختصاصی /admin -----------------
@bot.message_handler(commands=["admin"])
def admin_panel(message):
  if not is_admin(message.chat.id):
    bot.reply_to(message, "❌ شما دسترسی به پنل مدیریت ندارید!")
    return

  total_users = len(all_users)
  text = (
      "📊 **منوی مدیریت رئیس شاهد:**\n\n"
      f"🟢 **کل کاربران فعال:** `{total_users}` نفر\n"
      "🔴 **وضعیت کنونی سیستم:** 🟢 روشن و فعال\n\n"
      "📌 **راهنمای اضافه کردن امتیاز:**\n"
      "برای اضافه کردن امتیاز به یک کاربر دستور زیر را بفرستید:\n"
      "`/add USER_ID AMOUNT`\n"
      "مثال: `/add 8173349543 10`"
  )

  markup = types.InlineKeyboardMarkup(row_width=1)
  btn_text_bc = types.InlineKeyboardButton(
      "📝 ارسال پیام دلخواه به همه", callback_data="bc_text", style="primary"
  )
  btn_fwd_bc = types.InlineKeyboardButton(
      "🔄 فوروارد پیام به همه", callback_data="bc_fwd", style="primary"
  )
  markup.add(btn_text_bc, btn_fwd_bc)

  bot.send_message(
      message.chat.id, text, reply_markup=markup, parse_mode="Markdown"
  )


# handler دکمه‌های همگانی
@bot.callback_query_handler(func=lambda call: call.data in ["bc_text", "bc_fwd"])
def handle_admin_broadcast_choice(call):
  if not is_admin(call.message.chat.id):
    return

  bot.answer_callback_query(call.id)
  if call.data == "bc_text":
    waiting_for_broadcast[call.message.chat.id] = "text"
    bot.send_message(
        call.message.chat.id,
        "✍️ **لطفاً متن پیام دلخواه خود را ارسال کنید:**",
        parse_mode="Markdown",
    )
  else:
    waiting_for_broadcast[call.message.chat.id] = "fwd"
    bot.send_message(
        call.message.chat.id,
        "🔄 **لطفاً پیامی را که می‌خواهید فوروارد شود ارسال کنید:**",
        parse_mode="Markdown",
    )


# پردازش ارسال همگانی
@bot.message_handler(
    func=lambda m: is_admin(m.chat.id) and m.chat.id in waiting_for_broadcast
)
def process_admin_broadcast(message):
  mode = waiting_for_broadcast.pop(message.chat.id)
  success = 0
  failed = 0

  bot.send_message(message.chat.id, "⏳ در حال ارسال به تمامی کاربران...")

  for uid in list(all_users):
    try:
      if mode == "text":
        bot.send_message(uid, message.text, parse_mode="Markdown")
      else:
        bot.forward_message(uid, message.chat.id, message.message_id)
      success += 1
      time.sleep(0.04)
    except Exception:
      failed += 1

  bot.send_message(
      message.chat.id,
      f"✅ **عملیات پایان یافت!**\n\n🟢 **موفق:** `{success}`\n🔴"
      f" **ناموفق:** `{failed}`",
      parse_mode="Markdown",
  )


# ----------------- دستور /start -----------------
@bot.message_handler(commands=["start"])
def start_cmd(message):
  chat_id = message.chat.id
  user = message.from_user
  text_args = message.text.split()

  is_new = chat_id not in all_users
  all_users.add(chat_id)

  if is_new and len(text_args) > 1 and text_args[1].startswith("ref_"):
    try:
      ref_id = int(text_args[1].replace("ref_", ""))
      if ref_id != chat_id and chat_id not in invited_users:
        invited_users.add(chat_id)
        user_points[ref_id] = get_points(ref_id) + 2
        bot.send_message(
            ref_id,
            "🎉 یک کاربر با لینک شما عضو شد! ۲ امتیاز دریافت کردید.\n💎"
            f" **موجودی:** `{user_points[ref_id]}`",
            parse_mode="Markdown",
        )
    except Exception:
      pass

  save_data()
  lang = get_lang(chat_id)
  t = TEXTS[lang]
  points = get_points(chat_id)

  welcome_msg = t["welcome"].format(
      name=user.first_name or "کاربر",
      username=f"@{user.username}" if user.username else "ندارد",
      id=chat_id,
      points=points,
  )

  bot.send_message(
      chat_id,
      welcome_msg,
      reply_markup=main_keyboard(chat_id),
      parse_mode="Markdown",
  )


# ----------------- مدیریت کلیک روی دکمه‌های اصلی و پاسخ پشتیبانی -----------------
@bot.message_handler(func=lambda m: True)
def handle_text_buttons(message):
  chat_id = message.chat.id
  text = message.text
  lang = get_lang(chat_id)
  t = TEXTS[lang]

  # پاسخ‌دهی مستقیم ادمین به پیام پشتیبانی (Reply)
  if is_admin(chat_id) and message.reply_to_message:
    reply_text = message.reply_to_message.text or ""
    match = re.search(r"آیدی:\s*`?(\d+)`?", reply_text)
    if match:
      target_id = int(match.group(1))
      try:
        bot.send_message(
            target_id,
            f"📩 **پاسخ پشتیبانی:**\n\n{message.text}",
            parse_mode="Markdown",
        )
        bot.reply_to(message, "✅ پاسخ شما با موفقیت برای کاربر ارسال شد.")
        return
      except Exception as e:
        bot.reply_to(message, f"❌ خطا در ارسال پاسخ: {e}")
        return

  # تغییر زبان
  if text in [
      TEXTS["fa"]["btn_lang"],
      TEXTS["ps"]["btn_lang"],
      TEXTS["en"]["btn_lang"],
  ]:
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            "🇦🇫 دری / فارسی", callback_data="setlang_fa", style="primary"
        ),
        types.InlineKeyboardButton(
            "🇦🇫 پښتو", callback_data="setlang_ps", style="primary"
        ),
        types.InlineKeyboardButton(
            "🇬🇧 English", callback_data="setlang_en", style="primary"
        ),
    )
    bot.send_message(chat_id, t["select_lang"], reply_markup=markup)
    return

  # سکه روزانه (۲ امتیاز)
  if text in [
      TEXTS["fa"]["btn_daily"],
      TEXTS["ps"]["btn_daily"],
      TEXTS["en"]["btn_daily"],
  ]:
    if chat_id in claimed_daily:
      bot.send_message(chat_id, t["daily_already"])
    else:
      claimed_daily.add(chat_id)
      user_points[chat_id] = get_points(chat_id) + 2
      save_data()
      bot.send_message(chat_id, t["daily_success"])
    return

  # خرید امتیاز
  if text in [
      TEXTS["fa"]["btn_buy"],
      TEXTS["ps"]["btn_buy"],
      TEXTS["en"]["btn_buy"],
  ]:
    bot.send_message(chat_id, t["buy_text"], parse_mode="Markdown")
    return

  # اطلاعات من / لینک دعوت
  if text in [
      TEXTS["fa"]["btn_info"],
      TEXTS["ps"]["btn_info"],
      TEXTS["en"]["btn_info"],
  ]:
    info = t["info_text"].format(
        id=chat_id, points=get_points(chat_id), bot=BOT_USERNAME
    )
    bot.send_message(chat_id, info, parse_mode="Markdown")
    return

  # پشتیبانی
  if text in [
      TEXTS["fa"]["btn_support"],
      TEXTS["ps"]["btn_support"],
      TEXTS["en"]["btn_support"],
  ]:
    waiting_for_support.add(chat_id)
    bot.send_message(
        chat_id, "📥 لطفاً پیام خود را بنویسید تا به مدیر ارسال شود:"
    )
    return

  # تغییر رنگ کیبورد
  if text in [
      TEXTS["fa"]["btn_color"],
      TEXTS["ps"]["btn_color"],
      TEXTS["en"]["btn_color"],
  ]:
    if get_points(chat_id) < 10:
      bot.send_message(chat_id, t["low_points"])
      return
    waiting_for_file.add(chat_id)
    bot.send_message(chat_id, t["send_file_req"], parse_mode="Markdown")
    return

  # اگر در حالت پشتیبانی بود
  if chat_id in waiting_for_support:
    waiting_for_support.remove(chat_id)
    user = message.from_user
    fwd_text = (
        f"📩 **پیام پشتیبانی از طرف:** {user.first_name}\n🆔 **آیدی:**"
        f" `{chat_id}`\n\n💬 **متن:**\n{message.text}"
    )
    bot.send_message(ADMIN_ID, fwd_text, parse_mode="Markdown")
    bot.send_message(chat_id, "✅ پیام شما به پشتیبانی ارسال شد.")


# callback تغییر زبان
@bot.callback_query_handler(func=lambda call: call.data.startswith("setlang_"))
def callback_set_language(call):
  chat_id = call.message.chat.id
  selected = call.data.replace("setlang_", "")
  user_lang[chat_id] = selected
  save_data()
  bot.answer_callback_query(call.id, "✅ Done")
  bot.delete_message(chat_id, call.message.message_id)

  bot.send_message(
      chat_id, "✅ Language updated!", reply_markup=main_keyboard(chat_id)
  )


# ----------------- دریافت فایل و رنگ‌آمیزی -----------------
@bot.message_handler(content_types=["document"])
def handle_file(message):
  chat_id = message.chat.id
  if chat_id not in waiting_for_file:
    return

  if not message.document.file_name.endswith(".py"):
    bot.reply_to(message, "⚠️ لطفاً فقط فایل پایتون (.py) بفرستید.")
    return

  waiting_for_file.remove(chat_id)
  file_info = bot.get_file(message.document.file_id)
  downloaded_file = bot.download_file(file_info.file_path)

  file_name = message.document.file_name
  file_content = downloaded_file.decode("utf-8")

  # الگوی هوشمند برای شناسایی دکمه‌های یک‌خطی و چندخطی
  matches = re.findall(
      r"types\.InlineKeyboardButton\s*\((.*?)\)",
      file_content,
      flags=re.DOTALL,
  )

  if not matches:
    bot.reply_to(message, "⚠️ هیچ دکمه شیشه‌ای در فایل یافت نشد!")
    return

  user_points[chat_id] -= 10
  save_data()

  user_sessions[chat_id] = {
      "file_name": file_name,
      "file_content": file_content,
      "buttons": matches,
      "current_index": 0,
      "styles": [],
  }
  bot.send_message(
      chat_id,
      f"✅ فایل آنالیز شد. ۱۰ امتیاز کسر گردید.\nتعداد دکمه‌ها: `{len(matches)}`",
      parse_mode="Markdown",
  )
  ask_button_color(chat_id)


def ask_button_color(chat_id):
  session = user_sessions[chat_id]
  index = session["current_index"]
  total = len(session["buttons"])
  btn_raw = session["buttons"][index]

  btn_label_match = re.search(r"['\"]([^'\"]+)['\"]", btn_raw)
  btn_label = (
      btn_label_match.group(1) if btn_label_match else f"دکمه {index + 1}"
  )

  markup = types.InlineKeyboardMarkup(row_width=3)
  markup.add(
      types.InlineKeyboardButton(
          "🔴 قرمز", callback_data="color_danger", style="danger"
      ),
      types.InlineKeyboardButton(
          "🟢 سبز", callback_data="color_success", style="success"
      ),
      types.InlineKeyboardButton(
          "🔵 آبی", callback_data="color_primary", style="primary"
      ),
  )
  bot.send_message(
      chat_id,
      f"🎨 **رنگ دکمه ({index + 1} از {total}):** `{btn_label}`",
      reply_markup=markup,
      parse_mode="Markdown",
  )


@bot.callback_query_handler(func=lambda call: call.data.startswith("color_"))
def process_color_choice(call):
  chat_id = call.message.chat.id
  if chat_id not in user_sessions:
    return

  session = user_sessions[chat_id]
  session["styles"].append(f'style="{call.data.replace("color_", "")}"')
  session["current_index"] += 1

  bot.delete_message(chat_id, call.message.message_id)

  if session["current_index"] < len(session["buttons"]):
    ask_button_color(chat_id)
  else:
    build_and_send_final_file(chat_id)


def build_and_send_final_file(chat_id):
  session = user_sessions[chat_id]
  content = session["file_content"]
  styles = session["styles"]
  file_name = session["file_name"]

  btn_counter = 0

  def replace_button(match):
    nonlocal btn_counter
    btn_inner = match.group(1)

    # پاک‌سازی استایل‌های قبلی
    btn_inner = re.sub(
        r',\s*style\s*=\s*["\'].*?["\']', "", btn_inner, flags=re.DOTALL
    )

    assigned_style = styles[btn_counter]
    btn_counter += 1
    return f"types.InlineKeyboardButton({btn_inner.strip()}," f" {assigned_style})"

  # جایگزینی دکمه‌ها در تمام خطوط
  new_content = re.sub(
      r"types\.InlineKeyboardButton\s*\((.*?)\)",
      replace_button,
      content,
      flags=re.DOTALL,
  )
  out_filename = f"colored_{file_name}"

  with open(out_filename, "w", encoding="utf-8") as f:
    f.write(new_content)

  final_text = (
      "✨ **فایل شما با موفقیت آماده شد!** ✨\n"
      "━━━━━━━━━━━━━━━━━━\n"
      "👑 **این فایل توسط رئیس شاهد ساخته شد**\n"
      "━━━━━━━━━━━━━━━━━━\n"
      "⚠️ **توجه:** فایل و این پیام پس از **۳۰ ثانیه** پاک خواهند شد!"
  )

  msg1 = bot.send_message(chat_id, final_text, parse_mode="Markdown")
  with open(out_filename, "rb") as f:
    msg2 = bot.send_document(chat_id, f)

  auto_delete_messages(chat_id, [msg1.message_id, msg2.message_id], delay=30)

  if os.path.exists(out_filename):
    os.remove(out_filename)
  del user_sessions[chat_id]


print("ربات آنلاین شد! دیتابیس پایدار فعال است...")
bot.infinity_polling()
