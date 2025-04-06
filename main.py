import telebot
from telebot import types
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import json
import uuid

# Bot konfiguratsiyasi
TOKEN = "7290637755:AAGvGnOKGQBANL3HWvZqK7_4Fp7vhWZAMDs"  # Tokenni o‘zingiz bilan almashtiring
ADMIN_ID = 646102582  # Admin ID ni o‘zingizning ID bilan almashtiring
JOIN_GROUP_ID = "-1002235754489"  # Guruh ID
JOIN_GROUP_LINK = "https://t.me/+WcoB4ebLDghmNmUy"  # Guruh linki
CHEK_SHIKOYAT_GROUP_ID = "-1002651086083"  # Chek va shikoyat guruh ID
CHEK_TOPIC_ID = "3"  # Chek topic ID
SHIKOYAT_TOPIC_ID = "5"  # Shikoyat topic ID
bot = telebot.TeleBot(TOKEN)

# Ma'lumotlar bazasi konfiguratsiyasi
DB_CONFIG = {
    "host": "localhost",
    "database": "hamidovic_bot",
    "user": "postgres",  # O‘zingizning DB username bilan almashtiring
    "password": "8888",  # O‘zingizning DB parol bilan almashtiring
    "port": "5432"
}

# Ma'lumotlar bazasi ulanishi
def get_db_connection():
    try:
        return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

# Ma'lumotlar bazasini ishga tushirish
def init_db():
    conn = get_db_connection()
    if not conn:
        return
    cur = conn.cursor()
    cur.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'users') THEN
                CREATE TABLE users (
                    user_id VARCHAR(20) PRIMARY KEY,
                    lang VARCHAR(2) DEFAULT 'uz',
                    group_joined BOOLEAN DEFAULT FALSE,
                    blocked BOOLEAN DEFAULT FALSE,
                    first_start TIMESTAMP,
                    vip BOOLEAN DEFAULT FALSE,
                    premium BOOLEAN DEFAULT FALSE,
                    premium_expiry TIMESTAMP,
                    balance INTEGER DEFAULT 0,
                    last_menu VARCHAR(50)
                );
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'usage_logs') THEN
                CREATE TABLE usage_logs (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(20),
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    duration INTEGER
                );
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'complaints') THEN
                CREATE TABLE complaints (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(20),
                    text TEXT,
                    date TIMESTAMP,
                    viewed BOOLEAN DEFAULT FALSE,
                    replied BOOLEAN DEFAULT FALSE
                );
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'cheques') THEN
                CREATE TABLE cheques (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(20),
                    photo VARCHAR(255),
                    date TIMESTAMP,
                    amount INTEGER,
                    status VARCHAR(10) DEFAULT 'pending',
                    is_premium BOOLEAN DEFAULT FALSE
                );
            END IF;
        END $$;
    """)
    conn.commit()
    cur.close()
    conn.close()

init_db()

# Yordamchi funksiyalar
def get_user_lang(user_id):
    conn = get_db_connection()
    if not conn:
        return "uz"
    cur = conn.cursor()
    cur.execute("SELECT lang FROM users WHERE user_id = %s", (str(user_id),))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result["lang"] if result else "uz"

def update_last_menu(user_id, menu):
    conn = get_db_connection()
    if not conn:
        return
    cur = conn.cursor()
    cur.execute("UPDATE users SET last_menu = %s WHERE user_id = %s", (menu, str(user_id)))
    conn.commit()
    cur.close()
    conn.close()

def get_last_menu(user_id):
    conn = get_db_connection()
    if not conn:
        return ""
    cur = conn.cursor()
    cur.execute("SELECT last_menu FROM users WHERE user_id = %s", (str(user_id),))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result["last_menu"] if result else ""

def get_group_joined(user_id):
    conn = get_db_connection()
    if not conn:
        return False
    cur = conn.cursor()
    cur.execute("SELECT group_joined FROM users WHERE user_id = %s", (str(user_id),))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result["group_joined"] if result else False

def set_group_joined(user_id, status):
    conn = get_db_connection()
    if not conn:
        return
    cur = conn.cursor()
    cur.execute("UPDATE users SET group_joined = %s WHERE user_id = %s", (status, str(user_id)))
    conn.commit()
    cur.close()
    conn.close()

def is_user_blocked(user_id):
    conn = get_db_connection()
    if not conn:
        return False
    cur = conn.cursor()
    cur.execute("SELECT blocked FROM users WHERE user_id = %s", (str(user_id),))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result["blocked"] if result else False

def set_user_blocked(user_id, status):
    if user_id == ADMIN_ID:
        return False
    conn = get_db_connection()
    if not conn:
        return False
    cur = conn.cursor()
    cur.execute("UPDATE users SET blocked = %s WHERE user_id = %s", (status, str(user_id)))
    conn.commit()
    cur.close()
    conn.close()
    return True

def is_vip_user(user_id):
    conn = get_db_connection()
    if not conn:
        return False
    cur = conn.cursor()
    cur.execute("SELECT vip FROM users WHERE user_id = %s", (str(user_id),))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result["vip"] if result else False

def set_vip_user(user_id, status):
    conn = get_db_connection()
    if not conn:
        return False
    cur = conn.cursor()
    cur.execute("UPDATE users SET vip = %s WHERE user_id = %s", (status, str(user_id)))
    conn.commit()
    cur.close()
    conn.close()
    return True

def is_premium_user(user_id):
    conn = get_db_connection()
    if not conn:
        return False
    cur = conn.cursor()
    cur.execute("SELECT premium, premium_expiry FROM users WHERE user_id = %s", (str(user_id),))
    result = cur.fetchone()
    cur.close()
    conn.close()
    if result and result["premium"] and result["premium_expiry"] > datetime.now():
        return True
    return False

def set_premium_user(user_id, months):
    conn = get_db_connection()
    if not conn:
        return False
    expiry = datetime.now() + timedelta(days=months * 30)
    cur = conn.cursor()
    cur.execute("UPDATE users SET premium = TRUE, premium_expiry = %s WHERE user_id = %s", (expiry, str(user_id)))
    conn.commit()
    cur.close()
    conn.close()
    return True

def is_user_in_group(user_id):
    try:
        member = bot.get_chat_member(JOIN_GROUP_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def log_usage_start(user_id):
    conn = get_db_connection()
    if not conn:
        return
    cur = conn.cursor()
    cur.execute("INSERT INTO usage_logs (user_id, start_time) VALUES (%s, %s)", (str(user_id), datetime.now()))
    conn.commit()
    cur.close()
    conn.close()

def log_usage_end(user_id):
    conn = get_db_connection()
    if not conn:
        return
    cur = conn.cursor()
    cur.execute("SELECT id, start_time FROM usage_logs WHERE user_id = %s AND end_time IS NULL ORDER BY start_time DESC LIMIT 1", (str(user_id),))
    log = cur.fetchone()
    if log:
        duration = int((datetime.now() - log["start_time"]).total_seconds())
        cur.execute("UPDATE usage_logs SET end_time = %s, duration = %s WHERE id = %s", (datetime.now(), duration, log["id"]))
        conn.commit()
    cur.close()
    conn.close()

def get_user_balance(user_id):
    conn = get_db_connection()
    if not conn:
        return 0
    cur = conn.cursor()
    cur.execute("SELECT balance FROM users WHERE user_id = %s", (str(user_id),))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result["balance"] if result else 0

def update_user_balance(user_id, amount, increase=True):
    conn = get_db_connection()
    if not conn:
        return
    cur = conn.cursor()
    if increase:
        cur.execute("UPDATE users SET balance = balance + %s WHERE user_id = %s", (amount, str(user_id)))
    else:
        cur.execute("UPDATE users SET balance = balance - %s WHERE user_id = %s", (amount, str(user_id)))
    conn.commit()
    cur.close()
    conn.close()

# Til tarjimasi
translations = {
    "uz": {
        "welcome": "🎉 Xush kelibsiz!\nBotdan foydalanish uchun guruhga qo‘shiling:",
        "blocked": "🚫 Botdan foydalanish taqiqlangan!",
        "main_menu": "🏠 Bosh menyu:",
        "back": "🔙 Orqaga",
        "join_group": "Botdan foydalanish uchun guruhga qo‘shiling:",
        "group_button": "🌐 Guruhga kirish",
        "check_subscription": "✅ Tekshirish",
        "not_joined": "⚠️ Guruhda emassiz! Qo‘shiling!",
        "joined": "🎉 Guruhga qo‘shildingiz! Bot ochiq!",
        "rating": "🏆 Bugungi Top 15:",
        "action_canceled": "🚫 Harakat bekor qilindi!",
        "users_list": "👥 Foydalanuvchilar ro‘yxati:",
        "no_data": "ℹ️ Ma‘lumot yo‘q!",
        "complaints_new": "📩 Yangi shikoyatlar",
        "complaints_viewed": "✅ O‘qilganlar",
        "complaints_replied": "✉️ Javob berilganlar",
        "settings": "⚙️ Sozlamalar",
        "change_lang": "🌐 Tilni o‘zgartirish",
        "lang_changed": "✅ Til yangilandi!",
        "premium_prompt": "💎 Premium obunaga ega bo‘lish uchun quyidagi tariflardan birini tanlang:",
        "premium_price": "💎 Tanlangan tarif: {plan}\n💰 Narx: {price} so‘m",
        "payment": "💳 To‘lov qilish",
        "premium_cheques": "💎 Premium uchun to‘lovlar",
        "balance": "💰 Hisobingiz: {balance} so‘m",
        "top_up_balance": "💸 Balansni oshirish"
    },
    "ru": {
        "welcome": "🎉 Добро пожаловать!\nПрисоединитесь к группе для использования бота:",
        "blocked": "🚫 Доступ к боту запрещен!",
        "main_menu": "🏠 Главное меню:",
        "back": "🔙 Назад",
        "join_group": "Присоединитесь к группе для использования бота:",
        "group_button": "🌐 Вступить в группу",
        "check_subscription": "✅ Проверить",
        "not_joined": "⚠️ Вы не в группе! Вступите!",
        "joined": "🎉 Вы в группе! Бот доступен!",
        "rating": "🏆 Топ-15 сегодня:",
        "action_canceled": "🚫 Действие отменено!",
        "users_list": "👥 Список пользователей:",
        "no_data": "ℹ️ Данные отсутствуют!",
        "complaints_new": "📩 Новые жалобы",
        "complaints_viewed": "✅ Прочитанные",
        "complaints_replied": "✉️ Отвеченные",
        "settings": "⚙️ Настройки",
        "change_lang": "🌐 Сменить язык",
        "lang_changed": "✅ Язык обновлен!",
        "premium_prompt": "💎 Подпишитесь на Premium, выбрав один из тарифов:",
        "premium_price": "💎 Выбранный тариф: {plan}\n💰 Цена: {price} сум",
        "payment": "💳 Оплатить",
        "premium_cheques": "💎 Оплаты за Premium",
        "balance": "💰 Ваш баланс: {balance} сум",
        "top_up_balance": "💸 Пополнить баланс"
    },
    "en": {
        "welcome": "🎉 Welcome!\nJoin the group to use the bot:",
        "blocked": "🚫 You’re banned from the bot!",
        "main_menu": "🏠 Main Menu:",
        "back": "🔙 Back",
        "join_group": "Join the group to use the bot:",
        "group_button": "🌐 Join Group",
        "check_subscription": "✅ Check",
        "not_joined": "⚠️ You’re not in the group! Join now!",
        "joined": "🎉 You’ve joined! Bot unlocked!",
        "rating": "🏆 Today’s Top 15:",
        "action_canceled": "🚫 Action canceled!",
        "users_list": "👥 Users List:",
        "no_data": "ℹ️ No data found!",
        "complaints_new": "📩 New Complaints",
        "complaints_viewed": "✅ Viewed",
        "complaints_replied": "✉️ Replied",
        "settings": "⚙️ Settings",
        "change_lang": "🌐 Change Language",
        "lang_changed": "✅ Language updated!",
        "premium_prompt": "💎 Subscribe to Premium by choosing a plan:",
        "premium_price": "💎 Selected plan: {plan}\n💰 Price: {price} so‘m",
        "payment": "💳 Pay",
        "premium_cheques": "💎 Premium Payments",
        "balance": "💰 Your balance: {balance} so‘m",
        "top_up_balance": "💸 Top up balance"
    }
}

# Asosiy menyu
def get_base_markup(lang, is_admin=False, user_id=None):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        "💰 Balans" if not is_admin else None,
        translations[lang]["settings"],
        "📩 SMS Prank" if (is_admin or (user_id and is_vip_user(user_id))) else None,
        "📢 Shikoyatlar" if not is_admin else None
    ]
    buttons = [b for b in buttons if b]
    if is_admin:
        buttons.append("👨‍💼 Admin Paneli")
    markup.add(*buttons)
    return markup

# Start buyrug‘i
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    if is_user_blocked(user_id):
        bot.send_message(message.chat.id, translations[lang]["blocked"], reply_markup=get_base_markup(lang))
        return
    conn = get_db_connection()
    if not conn:
        bot.send_message(message.chat.id, "⚠️ Serverda muammo!", reply_markup=get_base_markup(lang))
        return
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id = %s", (str(user_id),))
    user = cur.fetchone()
    if not user:
        cur.execute("INSERT INTO users (user_id, first_start, balance) VALUES (%s, %s, %s)", (str(user_id), datetime.now(), 0))
        conn.commit()
    cur.close()
    conn.close()

    if user_id == ADMIN_ID or is_user_in_group(user_id):
        set_group_joined(user_id, True)
        log_usage_start(user_id)
        show_main_menu(message)
    else:
        show_group_join(message)

# Reyting
@bot.message_handler(commands=['rating'])
def show_rating(message):
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    today = datetime.now().date()
    conn = get_db_connection()
    if not conn:
        bot.send_message(message.chat.id, "⚠️ Serverda muammo!", reply_markup=get_base_markup(lang, user_id == ADMIN_ID, user_id))
        return
    cur = conn.cursor()
    cur.execute("""
        SELECT u.user_id, SUM(ul.duration) as total_duration
        FROM users u
        LEFT JOIN usage_logs ul ON u.user_id = ul.user_id
        WHERE ul.start_time::date = %s AND u.blocked = FALSE AND u.user_id != %s
        GROUP BY u.user_id
        HAVING SUM(ul.duration) > 0
        ORDER BY total_duration DESC
        LIMIT 15
    """, (today, str(ADMIN_ID)))
    top_users = cur.fetchall()
    cur.close()
    conn.close()

    markup = get_base_markup(lang, user_id == ADMIN_ID, user_id)
    if not top_users:
        bot.send_message(message.chat.id, translations[lang]["no_data"], reply_markup=markup)
        return

    response = f"{translations[lang]['rating']}\n\n"
    for i, user in enumerate(top_users, 1):
        try:
            user_info = bot.get_chat(int(user["user_id"]))
            duration = user["total_duration"] or 0
            hours = duration // 3600
            minutes = (duration % 3600) // 60
            seconds = duration % 60
            time_str = f"{hours} soat {minutes} daq {seconds} sek" if hours else f"{minutes} daq {seconds} sek"
            response += f"{i}. {user_info.first_name} (@{user_info.username or 'N/A'}) - {time_str}\n"
        except:
            response += f"{i}. ID: {user['user_id']} - Xato\n"
    update_last_menu(user_id, "rating")
    bot.send_message(message.chat.id, response, reply_markup=markup)

# Premium
@bot.message_handler(commands=['premium'])
def show_premium_plans(message):
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("1 oy", callback_data="premium_1"),
        types.InlineKeyboardButton("3 oy", callback_data="premium_3"),
        types.InlineKeyboardButton("6 oy", callback_data="premium_6"),
        types.InlineKeyboardButton("1 yil", callback_data="premium_12")
    )
    update_last_menu(user_id, "premium_plans")
    bot.send_message(message.chat.id, translations[lang]["premium_prompt"], reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("premium_"))
def handle_premium_plan(call):
    lang = get_user_lang(call.from_user.id)
    months = int(call.data.split("_")[1])
    prices = {1: 10000, 3: 25000, 6: 45000, 12: 80000}
    plan_names = {1: "1 oy", 3: "3 oy", 6: "6 oy", 12: "1 yil"}
    price = prices[months]
    plan = plan_names[months]

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(translations[lang]["payment"], callback_data=f"pay_premium_{months}"))
    markup.add(types.InlineKeyboardButton("🔙 Tariflarga qaytish", callback_data="back_to_premium"))

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=translations[lang]["premium_price"].format(plan=plan, price=price),
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "back_to_premium")
def back_to_premium_plans(call):
    show_premium_plans(call.message)
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_premium_"))
def handle_premium_payment(call):
    lang = get_user_lang(call.from_user.id)
    months = int(call.data.split("_")[2])
    update_last_menu(call.from_user.id, f"pay_premium_{months}")
    card_details = "💳 Kartalar:\n👤 Jahongir Hamidov\n1️⃣ 9860 6004 0534 2657 (Humo)\n2️⃣ 5614 6849 0998 2207 (Uzcard)\n3️⃣ 9860 3501 0503 7757 (Humo)\n📸 Chekni yuboring:"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(translations[lang]["back"])
    bot.send_message(call.message.chat.id, card_details, reply_markup=markup)
    bot.register_next_step_handler(call.message, save_premium_cheque, months)

def save_premium_cheque(message, months):
    lang = get_user_lang(message.from_user.id)
    user_id = message.from_user.id
    if message.text == translations[lang]["back"]:
        bot.send_message(message.chat.id, translations[lang]["action_canceled"], reply_markup=get_base_markup(lang, user_id == ADMIN_ID, user_id))
        show_premium_plans(message)
        return
    if message.content_type != 'photo':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(translations[lang]["back"])
        bot.send_message(message.chat.id, "❌ Chek rasmini yuboring!", reply_markup=markup)
        bot.register_next_step_handler(message, save_premium_cheque, months)
        return
    conn = get_db_connection()
    if not conn:
        bot.send_message(message.chat.id, "⚠️ Serverda muammo!", reply_markup=get_base_markup(lang, user_id == ADMIN_ID, user_id))
        return
    cur = conn.cursor()
    cur.execute("INSERT INTO cheques (user_id, photo, date, is_premium) VALUES (%s, %s, %s, TRUE)", (str(user_id), message.photo[-1].file_id, datetime.now()))
    conn.commit()
    cur.close()
    conn.close()

    user_info = bot.get_chat(user_id)
    cheque_msg = (
        f"👤 *Ism*: {user_info.first_name or 'N/A'}\n"
        f"📛 *Username*: @{user_info.username or 'N/A'}\n"
        f"🆔 *ID*: {user_id}\n"
        f"⭐ *VIP*: {'Ha' if is_vip_user(user_id) else 'Yo‘q'}\n"
        f"💎 *Premium*: {'Ha' if is_premium_user(user_id) else 'Yo‘q'}\n"
        f">Premium obuna uchun chek ({months} oy)"
    )
    bot.send_photo(CHEK_SHIKOYAT_GROUP_ID, message.photo[-1].file_id, caption=cheque_msg, message_thread_id=CHEK_TOPIC_ID, parse_mode="Markdown")

    bot.send_message(message.chat.id, "✅ Chek qabul qilindi! Admin tasdiqlashini kuting.", reply_markup=get_base_markup(lang, user_id == ADMIN_ID, user_id))
    update_last_menu(user_id, "main_menu")

# Guruhga qo‘shilish
def show_group_join(message):
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(translations[lang]["group_button"], url=JOIN_GROUP_LINK))
    markup.add(types.InlineKeyboardButton(translations[lang]["check_subscription"], callback_data="check_group"))
    update_last_menu(user_id, "group_join")
    bot.send_message(message.chat.id, translations[lang]["join_group"], reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_group")
def check_group_membership(call):
    user_id = call.from_user.id
    lang = get_user_lang(user_id)
    if user_id == ADMIN_ID or is_user_in_group(user_id):
        set_group_joined(user_id, True)
        log_usage_start(user_id)
        bot.send_message(call.message.chat.id, translations[lang]["joined"], reply_markup=get_base_markup(lang, user_id == ADMIN_ID, user_id))
        show_main_menu(call.message)
    else:
        set_group_joined(user_id, False)
        bot.send_message(call.message.chat.id, translations[lang]["not_joined"], reply_markup=get_base_markup(lang, user_id == ADMIN_ID, user_id))
        show_group_join(call.message)

# Bosh menyu
def show_main_menu(message):
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    markup = get_base_markup(lang, user_id == ADMIN_ID, user_id)
    update_last_menu(user_id, "main_menu")
    bot.send_message(message.chat.id, translations[lang]["main_menu"], reply_markup=markup)

# Balans (Oddiy userlar)
@bot.message_handler(func=lambda message: message.text == "💰 Balans" and message.from_user.id != ADMIN_ID)
def balance_menu(message):
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    balance = get_user_balance(user_id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(translations[lang]["top_up_balance"], translations[lang]["back"])
    update_last_menu(user_id, "balance")
    bot.send_message(message.chat.id, translations[lang]["balance"].format(balance=balance), reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == translations[get_user_lang(message.from_user.id)]["top_up_balance"])
def top_up_balance(message):
    lang = get_user_lang(message.from_user.id)
    card_details = "💳 Kartalar:\n👤 Jahongir Hamidov\n1️⃣ 9860 6004 0534 2657 (Humo)\n2️⃣ 5614 6849 0998 2207 (Uzcard)\n3️⃣ 9860 3501 0503 7757 (Humo)\n📸 Chekni yuboring:"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(translations[lang]["back"])
    update_last_menu(message.from_user.id, "top_up_balance_input")
    bot.send_message(message.chat.id, card_details, reply_markup=markup)
    bot.register_next_step_handler(message, save_cheque)

def save_cheque(message):
    lang = get_user_lang(message.from_user.id)
    user_id = message.from_user.id
    if message.text == translations[lang]["back"]:
        bot.send_message(message.chat.id, translations[lang]["action_canceled"], reply_markup=get_base_markup(lang, user_id == ADMIN_ID, user_id))
        balance_menu(message)
        return
    if message.content_type != 'photo':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(translations[lang]["back"])
        bot.send_message(message.chat.id, "❌ Chek rasmini yuboring!", reply_markup=markup)
        bot.register_next_step_handler(message, save_cheque)
        return
    conn = get_db_connection()
    if not conn:
        bot.send_message(message.chat.id, "⚠️ Serverda muammo!", reply_markup=get_base_markup(lang, user_id == ADMIN_ID, user_id))
        return
    cur = conn.cursor()
    cur.execute("INSERT INTO cheques (user_id, photo, date, is_premium) VALUES (%s, %s, %s, FALSE)", (str(user_id), message.photo[-1].file_id, datetime.now()))
    conn.commit()
    cur.close()
    conn.close()

    user_info = bot.get_chat(user_id)
    cheque_msg = (
        f"👤 *Ism*: {user_info.first_name or 'N/A'}\n"
        f"📛 *Username*: @{user_info.username or 'N/A'}\n"
        f"🆔 *ID*: {user_id}\n"
        f"⭐ *VIP*: {'Ha' if is_vip_user(user_id) else 'Yo‘q'}\n"
        f"💎 *Premium*: {'Ha' if is_premium_user(user_id) else 'Yo‘q'}\n"
        f">Balansni oshirish uchun chek"
    )
    bot.send_photo(CHEK_SHIKOYAT_GROUP_ID, message.photo[-1].file_id, caption=cheque_msg, message_thread_id=CHEK_TOPIC_ID, parse_mode="Markdown")

    bot.send_message(message.chat.id, "✅ Chek qabul qilindi!", reply_markup=get_base_markup(lang, user_id == ADMIN_ID, user_id))
    update_last_menu(user_id, "main_menu")

# SMS Prank
@bot.message_handler(func=lambda message: message.text == "📩 SMS Prank" and (message.from_user.id == ADMIN_ID or is_vip_user(message.from_user.id)))
def sms_prank_menu(message):
    lang = get_user_lang(message.from_user.id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📞 Oddiy SMS", "📚 kontrakt.edu.uz")
    markup.add(translations[lang]["back"])
    update_last_menu(message.from_user.id, "sms_prank")
    bot.send_message(message.chat.id, "📩 SMS Prank bo‘limi:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "📞 Oddiy SMS" and (message.from_user.id == ADMIN_ID or is_vip_user(message.from_user.id)))
def sms_prank_oddiy(message):
    lang = get_user_lang(message.from_user.id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(translations[lang]["back"])
    update_last_menu(message.from_user.id, "sms_prank_oddiy")
    bot.send_message(message.chat.id, "📞 Raqamni yuboring (masalan: +998901234567):", reply_markup=markup)
    bot.register_next_step_handler(message, process_sms_prank)

def process_sms_prank(message):
    lang = get_user_lang(message.from_user.id)
    user_id = message.from_user.id
    if message.text == translations[lang]["back"]:
        bot.send_message(message.chat.id, translations[lang]["action_canceled"], reply_markup=get_base_markup(lang, user_id == ADMIN_ID, user_id))
        sms_prank_menu(message)
        return
    if message.content_type != 'text' or not message.text.startswith("+998") or not message.text[1:].isdigit() or len(message.text) != 13:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(translations[lang]["back"])
        bot.send_message(message.chat.id, "❌ Noto‘g‘ri raqam! (+998901234567 formatida)", reply_markup=markup)
        bot.register_next_step_handler(message, process_sms_prank)
        return
    bot.send_message(message.chat.id, "✅ SMS prank yuborildi!", reply_markup=get_base_markup(lang, user_id == ADMIN_ID, user_id))
    update_last_menu(user_id, "main_menu")

@bot.message_handler(func=lambda message: message.text == "📚 kontrakt.edu.uz" and (message.from_user.id == ADMIN_ID or is_vip_user(message.from_user.id)))
def kontrakt_edu_menu(message):
    lang = get_user_lang(message.from_user.id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(translations[lang]["back"])
    update_last_menu(message.from_user.id, "kontrakt_edu")
    bot.send_message(message.chat.id, "Salom! Telefon raqamingizni 99888XXXXXXX formatida kiriting:", reply_markup=markup)
    bot.register_next_step_handler(message, get_phone_number)

def get_phone_number(message):
    lang = get_user_lang(message.from_user.id)
    if message.text == translations[lang]["back"]:
        bot.send_message(message.chat.id, translations[lang]["action_canceled"], reply_markup=get_base_markup(lang, message.from_user.id == ADMIN_ID, message.from_user.id))
        sms_prank_menu(message)
        return
    if not (message.text.isdigit() and len(message.text) == 12 and message.text.startswith("998")):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(translations[lang]["back"])
        bot.send_message(message.chat.id, "Noto‘g‘ri format! Iltimos, 99888XXXXXXX shaklida kiriting:", reply_markup=markup)
        bot.register_next_step_handler(message, get_phone_number)
    else:
        phone_number = message.text
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(translations[lang]["back"])
        bot.send_message(message.chat.id, "Necha marta yuborilsin? (1 dan 6 gacha):", reply_markup=markup)
        bot.register_next_step_handler(message, send_sms_request, phone_number)

def send_sms_request(message, phone_number):
    lang = get_user_lang(message.from_user.id)
    user_id = message.from_user.id
    if message.text == translations[lang]["back"]:
        bot.send_message(message.chat.id, translations[lang]["action_canceled"], reply_markup=get_base_markup(lang, user_id == ADMIN_ID, user_id))
        kontrakt_edu_menu(message)
        return
    if not (message.text.isdigit() and 1 <= int(message.text) <= 6):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(translations[lang]["back"])
        bot.send_message(message.chat.id, "Iltimos, 1 dan 6 gacha son kiriting:", reply_markup=markup)
        bot.register_next_step_handler(message, send_sms_request, phone_number)
        return
    
    attempts = int(message.text)
    url = "https://kontrakt-api.edu.uz/Account/SendSMSCode"
    headers = {
        "Sec-Ch-Ua-Platform": "\"Linux\"",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "application/json, text/plain, */*",
        "Sec-Ch-Ua": "\"Chromium\";v=\"133\", \"Not(A:Brand\";v=\"99\"",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "Origin": "https://kontrakt.edu.uz",
        "Sec-Fetch-Site": "same-site",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": "https://kontrakt.edu.uz/",
        "Accept-Encoding": "gzip, deflate, br"
    }

    for _ in range(attempts):
        request_id = str(uuid.uuid4())
        cookies = {"requestId": request_id}
        data = {
            "phonenumber": f"+{phone_number[:3]}-{phone_number[3:5]}-{phone_number[5:]}",
            "password": "52898000120044",
            "passwordconfirm": "52898000120044",
            "smscode": ""
        }

        try:
            response = requests.post(url, headers=headers, cookies=cookies, data=json.dumps(data))
            if response.status_code == 200:
                bot.send_message(message.chat.id, f"✅ SMS kodi yuborildi!\nRequest ID: {request_id}", reply_markup=get_base_markup(lang, user_id == ADMIN_ID, user_id))
            else:
                bot.send_message(message.chat.id, f"❌ Xatolik yuz berdi\nStatus Code: {response.status_code}\nResponse: {response.text}", reply_markup=get_base_markup(lang, user_id == ADMIN_ID, user_id))
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Xatolik: {str(e)}", reply_markup=get_base_markup(lang, user_id == ADMIN_ID, user_id))

    update_last_menu(user_id, "main_menu")

# Shikoyatlar (Oddiy userlar)
@bot.message_handler(func=lambda message: message.text == "📢 Shikoyatlar" and message.from_user.id != ADMIN_ID)
def complaints_menu(message):
    lang = get_user_lang(message.from_user.id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(translations[lang]["back"])
    update_last_menu(message.from_user.id, "complaints_user_input")
    bot.send_message(message.chat.id, "✍️ Shikoyatingizni yozing:", reply_markup=markup)
    bot.register_next_step_handler(message, save_complaint)

def save_complaint(message):
    lang = get_user_lang(message.from_user.id)
    user_id = message.from_user.id
    if message.text == translations[lang]["back"]:
        bot.send_message(message.chat.id, translations[lang]["action_canceled"], reply_markup=get_base_markup(lang, user_id == ADMIN_ID, user_id))
        show_main_menu(message)
        return
    if message.content_type != 'text':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(translations[lang]["back"])
        bot.send_message(message.chat.id, "❌ Matn yuboring!", reply_markup=markup)
        bot.register_next_step_handler(message, save_complaint)
        return
    conn = get_db_connection()
    if not conn:
        bot.send_message(message.chat.id, "⚠️ Serverda muammo!", reply_markup=get_base_markup(lang, user_id == ADMIN_ID, user_id))
        return
    cur = conn.cursor()
    cur.execute("INSERT INTO complaints (user_id, text, date) VALUES (%s, %s, %s)", (str(user_id), message.text, datetime.now()))
    conn.commit()
    cur.close()
    conn.close()

    user_info = bot.get_chat(user_id)
    complaint_msg = (
        f"👤 *Ism*: {user_info.first_name or 'N/A'}\n"
        f"📛 *Username*: @{user_info.username or 'N/A'}\n"
        f"🆔 *ID*: {user_id}\n"
        f"⭐ *VIP*: {'Ha' if is_vip_user(user_id) else 'Yo‘q'}\n"
        f"💎 *Premium*: {'Ha' if is_premium_user(user_id) else 'Yo‘q'}\n"
        f">{message.text}"
    )
    bot.send_message(CHEK_SHIKOYAT_GROUP_ID, complaint_msg, message_thread_id=SHIKOYAT_TOPIC_ID, parse_mode="Markdown")

    bot.send_message(message.chat.id, "✅ Shikoyatingiz yuborildi!", reply_markup=get_base_markup(lang, user_id == ADMIN_ID, user_id))
    update_last_menu(user_id, "main_menu")

# Admin paneli
@bot.message_handler(func=lambda message: message.text == "👨‍💼 Admin Paneli" and message.from_user.id == ADMIN_ID)
def admin_panel(message):
    lang = get_user_lang(message.from_user.id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📜 Cheklar", "📢 Shikoyatlar")
    markup.add("🚫 Bloklanganlar", translations[lang]["users_list"])
    markup.add(translations[lang]["premium_cheques"])
    markup.add(translations[lang]["back"])
    update_last_menu(message.from_user.id, "admin_panel")
    bot.send_message(message.chat.id, "👨‍💼 Admin Paneli:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "📜 Cheklar")
def view_cheques_menu(message):
    lang = get_user_lang(message.from_user.id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("✅ Tasdiqlangan", "⏳ Kutilmoqda", "❌ Rad etilgan")
    markup.add(translations[lang]["back"])
    update_last_menu(message.from_user.id, "view_cheques")
    bot.send_message(message.chat.id, "📜 Cheklar:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == translations[get_user_lang(message.from_user.id)]["premium_cheques"])
def view_premium_cheques_menu(message):
    lang = get_user_lang(message.from_user.id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("✅ Tasdiqlangan", "⏳ Kutilmoqda", "❌ Rad etilgan")
    markup.add(translations[lang]["back"])
    update_last_menu(message.from_user.id, "view_premium_cheques")
    bot.send_message(message.chat.id, translations[lang]["premium_cheques"], reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in ["✅ Tasdiqlangan", "⏳ Kutilmoqda", "❌ Rad etilgan"])
def show_cheques(message):
    lang = get_user_lang(message.from_user.id)
    status_map = {"✅ Tasdiqlangan": "approved", "⏳ Kutilmoqda": "pending", "❌ Rad etilgan": "rejected"}
    status = status_map[message.text]
    conn = get_db_connection()
    if not conn:
        bot.send_message(message.chat.id, "⚠️ Serverda muammo!", reply_markup=get_base_markup(lang, True, message.from_user.id))
        return
    cur = conn.cursor()
    is_premium = "view_premium_cheques" in get_last_menu(message.from_user.id)
    cur.execute("SELECT * FROM cheques WHERE status = %s AND is_premium = %s ORDER BY date DESC", (status, is_premium))
    cheques = cur.fetchall()
    cur.close()
    conn.close()

    markup = get_base_markup(lang, True, message.from_user.id)
    update_last_menu(message.from_user.id, f"show_cheques_{status}_{'premium' if is_premium else 'regular'}")

    if not cheques:
        bot.send_message(message.chat.id, translations[lang]["no_data"], reply_markup=markup)
        return

    for cheque in cheques:
        try:
            user = bot.get_chat(int(cheque["user_id"]))
            cheque_msg = (
                f"👤 *Ism*: {user.first_name or 'N/A'}\n"
                f"📛 *Username*: @{user.username or 'N/A'}\n"
                f"🆔 *ID*: {cheque['user_id']}\n"
                f"⭐ *VIP*: {'Ha' if is_vip_user(cheque['user_id']) else 'Yo‘q'}\n"
                f"💎 *Premium*: {'Ha' if is_premium_user(cheque['user_id']) else 'Yo‘q'}\n"
                f">{ 'Premium obuna uchun chek' if cheque['is_premium'] else 'Balansni oshirish uchun chek' }\n"
                f"📅 *Sana*: {cheque['date']}\n"
                f"💰 *Miqdor*: {cheque['amount'] or 'N/A'} so‘m"
            )
            bot.send_photo(message.chat.id, cheque["photo"], caption=cheque_msg, parse_mode="Markdown")
            if status == "pending":
                markup_inline = types.InlineKeyboardMarkup()
                markup_inline.add(
                    types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{cheque['id']}"),
                    types.InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_{cheque['id']}")
                )
                bot.send_message(message.chat.id, "Tanlang:", reply_markup=markup_inline)
        except:
            bot.send_message(message.chat.id, f"❌ Chek ID: {cheque['id']} xato!", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith(("approve_", "reject_")))
def handle_cheque_action(call):
    action, cheque_id = call.data.split("_")
    cheque_id = int(cheque_id)
    conn = get_db_connection()
    if not conn:
        bot.send_message(call.message.chat.id, "⚠️ Serverda muammo!", reply_markup=get_base_markup(get_user_lang(call.from_user.id), True, call.from_user.id))
        return
    cur = conn.cursor()
    cur.execute("SELECT * FROM cheques WHERE id = %s AND status = 'pending'", (cheque_id,))
    cheque = cur.fetchone()
    if not cheque:
        bot.send_message(call.message.chat.id, "⚠️ Chek topilmadi!", reply_markup=get_base_markup(get_user_lang(call.from_user.id), True, call.from_user.id))
        cur.close()
        conn.close()
        return
    if action == "approve":
        update_last_menu(call.from_user.id, f"cheque_amount_input_{cheque_id}")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(translations[get_user_lang(call.from_user.id)]["back"])
        bot.send_message(call.message.chat.id, "💰 Miqdor (so‘m):", reply_markup=markup)
        bot.register_next_step_handler(call.message, set_cheque_amount, cheque)
    else:
        cur.execute("UPDATE cheques SET status = 'rejected' WHERE id = %s", (cheque_id,))
        conn.commit()
        bot.send_message(cheque["user_id"], "❌ Chekingiz rad etildi!", reply_markup=get_base_markup(get_user_lang(cheque["user_id"]), False, cheque["user_id"]))
        bot.send_message(call.message.chat.id, "✅ Chek rad etildi!", reply_markup=get_base_markup(get_user_lang(call.from_user.id), True, call.from_user.id))
    cur.close()
    conn.close()

def set_cheque_amount(message, cheque):
    lang = get_user_lang(message.from_user.id)
    user_id = message.from_user.id
    if message.text == translations[lang]["back"]:
        bot.send_message(message.chat.id, translations[lang]["action_canceled"], reply_markup=get_base_markup(lang, user_id == ADMIN_ID, user_id))
        if cheque["is_premium"]:
            view_premium_cheques_menu(message)
        else:
            view_cheques_menu(message)
        return
    if message.content_type != 'text' or not message.text.isdigit():
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(translations[lang]["back"])
        bot.send_message(message.chat.id, "❌ Faqat son!", reply_markup=markup)
        bot.register_next_step_handler(message, set_cheque_amount, cheque)
        return
    amount = int(message.text)
    conn = get_db_connection()
    if not conn:
        bot.send_message(message.chat.id, "⚠️ Serverda muammo!", reply_markup=get_base_markup(lang, user_id == ADMIN_ID, user_id))
        return
    cur = conn.cursor()
    cur.execute("UPDATE cheques SET amount = %s, status = 'approved' WHERE id = %s", (amount, cheque["id"]))
    if cheque["is_premium"]:
        months = {10000: 1, 25000: 3, 45000: 6, 80000: 12}.get(amount, 1)
        set_premium_user(cheque["user_id"], months)
        bot.send_message(cheque["user_id"], f"✅ Premium obuna tasdiqlandi! {months} oy davomida botdan to‘liq foydalaning!", reply_markup=get_base_markup(lang, False, cheque["user_id"]))
    else:
        cur.execute("UPDATE users SET balance = balance + %s WHERE user_id = %s", (amount, str(cheque["user_id"])))
        bot.send_message(cheque["user_id"], f"✅ Chekingiz tasdiqlandi! +{amount} so‘m", reply_markup=get_base_markup(lang, False, cheque["user_id"]))
    conn.commit()
    cur.close()
    conn.close()
    bot.send_message(message.chat.id, "✅ Chek tasdiqlandi!", reply_markup=get_base_markup(lang, user_id == ADMIN_ID, user_id))
    update_last_menu(user_id, "view_cheques")

# Admin: Shikoyatlar
@bot.message_handler(func=lambda message: message.text == "📢 Shikoyatlar" and message.from_user.id == ADMIN_ID)
def admin_complaints_menu(message):
    lang = get_user_lang(message.from_user.id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(translations[lang]["complaints_new"], translations[lang]["complaints_viewed"], translations[lang]["complaints_replied"])
    markup.add(translations[lang]["back"])
    update_last_menu(message.from_user.id, "admin_complaints")
    bot.send_message(message.chat.id, "📢 Shikoyatlar:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in [translations[get_user_lang(message.from_user.id)]["complaints_new"], translations[get_user_lang(message.from_user.id)]["complaints_viewed"], translations[get_user_lang(message.from_user.id)]["complaints_replied"]])
def view_complaints(message):
    lang = get_user_lang(message.from_user.id)
    filter_map = {
        translations[lang]["complaints_new"]: "viewed = FALSE AND replied = FALSE",
        translations[lang]["complaints_viewed"]: "viewed = TRUE AND replied = FALSE",
        translations[lang]["complaints_replied"]: "replied = TRUE"
    }
    filter_condition = filter_map[message.text]
    conn = get_db_connection()
    if not conn:
        bot.send_message(message.chat.id, "⚠️ Serverda muammo!", reply_markup=get_base_markup(lang, True, message.from_user.id))
        return
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM complaints WHERE {filter_condition} ORDER BY date DESC")
    complaints = cur.fetchall()
    cur.close()
    conn.close()

    markup = get_base_markup(lang, True, message.from_user.id)
    update_last_menu(message.from_user.id, f"view_complaints_{message.text}")

    if not complaints:
        bot.send_message(message.chat.id, translations[lang]["no_data"], reply_markup=markup)
        return

    for complaint in complaints:
        try:
            user = bot.get_chat(int(complaint["user_id"]))
            complaint_msg = (
                f"👤 *Ism*: {user.first_name or 'N/A'}\n"
                f"📛 *Username*: @{user.username or 'N/A'}\n"
                f"🆔 *ID*: {complaint['user_id']}\n"
                f"⭐ *VIP*: {'Ha' if is_vip_user(complaint['user_id']) else 'Yo‘q'}\n"
                f"💎 *Premium*: {'Ha' if is_premium_user(complaint['user_id']) else 'Yo‘q'}\n"
                f">{complaint['text']}\n"
                f"📅 *Sana*: {complaint['date']}"
            )
            bot.send_message(message.chat.id, complaint_msg, parse_mode="Markdown")
            markup_inline = types.InlineKeyboardMarkup()
            if not complaint["viewed"]:
                markup_inline.add(types.InlineKeyboardButton("✅ O‘qildi", callback_data=f"mark_read_{complaint['id']}"))
            if not complaint["replied"]:
                markup_inline.add(types.InlineKeyboardButton("✉️ Javob berish", callback_data=f"reply_{complaint['id']}"))
            if complaint["user_id"] != str(ADMIN_ID):
                markup_inline.add(types.InlineKeyboardButton("🚫/✅ Bloklash", callback_data=f"toggle_block_{complaint['user_id']}"))
            bot.send_message(message.chat.id, "Tanlang:", reply_markup=markup_inline)
        except:
            bot.send_message(message.chat.id, f"❌ Shikoyat ID: {complaint['id']} xato!", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith(("mark_read_", "reply_", "toggle_block_")))
def handle_complaint_action(call):
    parts = call.data.split("_", 1)
    action, value = parts
    lang = get_user_lang(ADMIN_ID)
    conn = get_db_connection()
    if not conn:
        bot.send_message(call.message.chat.id, "⚠️ Serverda muammo!", reply_markup=get_base_markup(lang, True, call.from_user.id))
        return

    if action == "mark_read":
        complaint_id = int(value)
        cur = conn.cursor()
        cur.execute("UPDATE complaints SET viewed = TRUE WHERE id = %s", (complaint_id,))
        conn.commit()
        cur.close()
        conn.close()
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=call.message.text + "\n✅ O‘qildi", reply_markup=None, parse_mode="Markdown")

    elif action == "reply":
        complaint_id = int(value)
        update_last_menu(ADMIN_ID, f"complaint_reply_input_{complaint_id}")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(translations[lang]["back"])
        bot.send_message(call.message.chat.id, "✉️ Javobingiz:", reply_markup=markup)
        bot.register_next_step_handler(call.message, send_reply, complaint_id)

    elif action == "toggle_block":
        user_id = int(value)
        blocked = is_user_blocked(user_id)
        if set_user_blocked(user_id, not blocked):
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=call.message.text + f"\n{'🚫 Bloklandi' if not blocked else '✅ Blok ochildi'}", reply_markup=None, parse_mode="Markdown")

def send_reply(message, complaint_id):
    lang = get_user_lang(message.from_user.id)
    user_id = message.from_user.id
    if message.text == translations[lang]["back"]:
        bot.send_message(message.chat.id, translations[lang]["action_canceled"], reply_markup=get_base_markup(lang, user_id == ADMIN_ID, user_id))
        admin_complaints_menu(message)
        return
    if message.content_type != 'text':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(translations[lang]["back"])
        bot.send_message(message.chat.id, "❌ Matn yuboring!", reply_markup=markup)
        bot.register_next_step_handler(message, send_reply, complaint_id)
        return
    conn = get_db_connection()
    if not conn:
        bot.send_message(message.chat.id, "⚠️ Serverda muammo!", reply_markup=get_base_markup(lang, user_id == ADMIN_ID, user_id))
        return
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM complaints WHERE id = %s", (complaint_id,))
    target_user_id = cur.fetchone()["user_id"]
    cur.execute("UPDATE complaints SET viewed = TRUE, replied = TRUE WHERE id = %s", (complaint_id,))
    conn.commit()
    cur.close()
    conn.close()
    bot.send_message(target_user_id, f"✉️ Admin javobi: {message.text}", reply_markup=get_base_markup(get_user_lang(target_user_id), False, target_user_id))
    bot.send_message(message.chat.id, "✅ Javob yuborildi!", reply_markup=get_base_markup(lang, True, message.from_user.id))
    update_last_menu(message.from_user.id, "admin_complaints")

# Bloklanganlar
@bot.message_handler(func=lambda message: message.text == "🚫 Bloklanganlar" and message.from_user.id == ADMIN_ID)
def blocked_users_menu(message):
    lang = get_user_lang(message.from_user.id)
    conn = get_db_connection()
    if not conn:
        bot.send_message(message.chat.id, "⚠️ Serverda muammo!", reply_markup=get_base_markup(lang, True, message.from_user.id))
        return
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE blocked = TRUE ORDER BY first_start DESC")
    blocked_users = cur.fetchall()
    cur.close()
    conn.close()

    markup = get_base_markup(lang, True, message.from_user.id)
    update_last_menu(message.from_user.id, "blocked_users")

    if not blocked_users:
        bot.send_message(message.chat.id, translations[lang]["no_data"], reply_markup=markup)
        return

    for user in blocked_users:
        try:
            user_info = bot.get_chat(int(user["user_id"]))
            markup_inline = types.InlineKeyboardMarkup()
            markup_inline.add(types.InlineKeyboardButton("✅ Blokdan chiqarish", callback_data=f"toggle_block_{user['user_id']}"))
            bot.send_message(message.chat.id, f"👤 @{user_info.username or 'N/A'} (ID: {user['user_id']})", reply_markup=markup_inline)
        except:
            bot.send_message(message.chat.id, f"❌ ID: {user['user_id']} xato!", reply_markup=markup)

# Foydalanuvchilar ro‘yxati
@bot.message_handler(func=lambda message: message.text == translations[get_user_lang(message.from_user.id)]["users_list"] and message.from_user.id == ADMIN_ID)
def users_list_menu(message, page=1):
    lang = get_user_lang(message.from_user.id)
    conn = get_db_connection()
    if not conn:
        bot.send_message(message.chat.id, "⚠️ Serverda muammo!", reply_markup=get_base_markup(lang, True, message.from_user.id))
        return
    cur = conn.cursor()
    cur.execute("SELECT user_id, vip, premium FROM users WHERE first_start IS NOT NULL AND user_id != %s ORDER BY first_start DESC", (str(ADMIN_ID),))
    all_users = cur.fetchall()
    cur.close()
    conn.close()

    if not all_users:
        bot.send_message(message.chat.id, translations[lang]["no_data"], reply_markup=get_base_markup(lang, True, message.from_user.id))
        return

    per_page = 5
    total_pages = (len(all_users) + per_page - 1) // per_page
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, len(all_users))
    users = all_users[start_idx:end_idx]

    markup = get_base_markup(lang, True, message.from_user.id)
    update_last_menu(message.from_user.id, f"users_list_page_{page}")

    inline_markup = types.InlineKeyboardMarkup()
    for user in users:
        try:
            user_info = bot.get_chat(int(user["user_id"]))
            status_mark = " ⭐" if user["vip"] else " 💎" if user["premium"] else ""
            inline_markup.add(types.InlineKeyboardButton(f"{user_info.first_name or 'N/A'} (ID: {user['user_id']}){status_mark}", callback_data=f"user_{user['user_id']}"))
        except:
            inline_markup.add(types.InlineKeyboardButton(f"ID: {user['user_id']} (Xato)", callback_data=f"user_{user['user_id']}"))

    pagination_row = []
    if page > 1:
        pagination_row.append(types.InlineKeyboardButton("⬅️ Oldingi", callback_data=f"users_page_{page-1}"))
    if page < total_pages:
        pagination_row.append(types.InlineKeyboardButton("Keyingi ➡️", callback_data=f"users_page_{page+1}"))
    if pagination_row:
        inline_markup.add(*pagination_row)

    bot.send_message(message.chat.id, translations[lang]["users_list"], reply_markup=markup)
    bot.send_message(message.chat.id, f"📄 Sahifa {page}/{total_pages}", reply_markup=inline_markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("users_page_"))
def handle_users_pagination(call):
    page = int(call.data.split("_")[2])
    users_list_menu(call.message, page)
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("user_"))
def show_user_details(call):
    user_id = int(call.data.split("_")[1])
    lang = get_user_lang(ADMIN_ID)
    try:
        user_info = bot.get_chat(user_id)
        base_text = (
            f"👤 *Ism*: {user_info.first_name or 'N/A'}\n"
            f"🆔 *ID*: {user_id}\n"
            f"📛 *Username*: @{user_info.username or 'N/A'}"
        )

        markup_inline = types.InlineKeyboardMarkup(row_width=2)
        markup_inline.add(
            types.InlineKeyboardButton("💰 Hisob", callback_data=f"view_balance_{user_id}"),
            types.InlineKeyboardButton("⭐ VIP Holati", callback_data=f"toggle_vip_{user_id}")
        )
        markup_inline.add(
            types.InlineKeyboardButton("📊 Faollik", callback_data=f"view_activity_{user_id}"),
            types.InlineKeyboardButton("🚫/✅ Blok Holati", callback_data=f"toggle_block_{user_id}")
        )
        markup_inline.add(types.InlineKeyboardButton("💎 Premium Holati", callback_data=f"toggle_premium_{user_id}"))
        markup_inline.add(types.InlineKeyboardButton("🔙 Orqaga", callback_data=f"back_to_users_{user_id}"))

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=base_text,
            reply_markup=markup_inline,
            parse_mode="Markdown"
        )
        update_last_menu(ADMIN_ID, f"user_details_{user_id}")
    except:
        bot.send_message(call.message.chat.id, f"❌ ID: {user_id} xato!", reply_markup=get_base_markup(lang, True, call.from_user.id))

@bot.callback_query_handler(func=lambda call: call.data.startswith(("view_balance_", "toggle_vip_", "view_activity_", "toggle_block_", "toggle_premium_", "back_to_users_")))
def handle_user_action(call):
    parts = call.data.split("_")
    action = parts[0]
    user_id = int(parts[-1])
    lang = get_user_lang(ADMIN_ID)
    try:
        user_info = bot.get_chat(user_id)
        base_text = (
            f"👤 *Ism*: {user_info.first_name or 'N/A'}\n"
            f"🆔 *ID*: {user_id}\n"
            f"📛 *Username*: @{user_info.username or 'N/A'}"
        )

        if action == "view_balance":
            balance = get_user_balance(user_id)
            text = f"{base_text}\n💰 Hisob: {balance} so‘m"
            markup_inline = types.InlineKeyboardMarkup(row_width=2)
            markup_inline.add(
                types.InlineKeyboardButton("➕ Qo‘shish", callback_data=f"increase_balance_{user_id}"),
                types.InlineKeyboardButton("➖ Ayirish", callback_data=f"decrease_balance_{user_id}")
            )
            markup_inline.add(types.InlineKeyboardButton("🔙 Orqaga", callback_data=f"back_to_user_{user_id}"))
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=markup_inline,
                parse_mode="Markdown"
            )
            update_last_menu(ADMIN_ID, f"view_balance_{user_id}")

        elif action == "toggle_vip":
            vip = is_vip_user(user_id)
            if set_vip_user(user_id, not vip):
                vip_status = "⭐ VIP" if not vip else "🚫 Oddiy"
                text = f"{base_text}\n{vip_status}"
                markup_inline = types.InlineKeyboardMarkup()
                markup_inline.add(types.InlineKeyboardButton("🔙 Orqaga", callback_data=f"back_to_user_{user_id}"))
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=text,
                    reply_markup=markup_inline,
                    parse_mode="Markdown"
                )
                update_last_menu(ADMIN_ID, f"toggle_vip_{user_id}")

        elif action == "view_activity":
            conn = get_db_connection()
            if not conn:
                bot.send_message(call.message.chat.id, "⚠️ Serverda muammo!", reply_markup=get_base_markup(lang, True, call.from_user.id))
                return
            cur = conn.cursor()
            cur.execute("SELECT start_time, duration FROM usage_logs WHERE user_id = %s ORDER BY start_time DESC LIMIT 5", (str(user_id),))
            logs = cur.fetchall()
            cur.close()
            conn.close()
            usage_text = "📊 Faollik:\n"
            if not logs:
                usage_text += translations[lang]["no_data"]
            else:
                for log in logs:
                    start = log["start_time"].strftime("%Y-%m-%d %H:%M")
                    duration = log["duration"] or 0
                    hours = duration // 3600
                    minutes = (duration % 3600) // 60
                    seconds = duration % 60
                    time_str = f"{hours} soat {minutes} daq {seconds} sek" if hours else f"{minutes} daq {seconds} sek"
                    usage_text += f"- {start}: {time_str}\n"
            text = f"{base_text}\n{usage_text}"
            markup_inline = types.InlineKeyboardMarkup()
            markup_inline.add(types.InlineKeyboardButton("🔙 Orqaga", callback_data=f"back_to_user_{user_id}"))
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=markup_inline,
                parse_mode="Markdown"
            )
            update_last_menu(ADMIN_ID, f"view_activity_{user_id}")

        elif action == "toggle_block":
            blocked = is_user_blocked(user_id)
            if set_user_blocked(user_id, not blocked):
                block_status = "🚫 Bloklangan" if not blocked else "✅ Faol"
                text = f"{base_text}\n{block_status}"
                markup_inline = types.InlineKeyboardMarkup()
                markup_inline.add(types.InlineKeyboardButton("🔙 Orqaga", callback_data=f"back_to_user_{user_id}"))
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=text,
                    reply_markup=markup_inline,
                    parse_mode="Markdown"
                )
                update_last_menu(ADMIN_ID, f"toggle_block_{user_id}")

        elif action == "toggle_premium":
            premium = is_premium_user(user_id)
            conn = get_db_connection()
            if not conn:
                bot.send_message(call.message.chat.id, "⚠️ Serverda muammo!", reply_markup=get_base_markup(lang, True, call.from_user.id))
                return
            cur = conn.cursor()
            cur.execute("UPDATE users SET premium = %s WHERE user_id = %s", (not premium, str(user_id)))
            conn.commit()
            cur.close()
            conn.close()
            premium_status = "💎 Premium" if not premium else "🚫 Premium emas"
            text = f"{base_text}\n{premium_status}"
            markup_inline = types.InlineKeyboardMarkup()
            markup_inline.add(types.InlineKeyboardButton("🔙 Orqaga", callback_data=f"back_to_user_{user_id}"))
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=markup_inline,
                parse_mode="Markdown"
            )
            update_last_menu(ADMIN_ID, f"toggle_premium_{user_id}")

        elif action == "back_to_user":
            text = base_text
            markup_inline = types.InlineKeyboardMarkup(row_width=2)
            markup_inline.add(
                types.InlineKeyboardButton("💰 Hisob", callback_data=f"view_balance_{user_id}"),
                types.InlineKeyboardButton("⭐ VIP Holati", callback_data=f"toggle_vip_{user_id}")
            )
            markup_inline.add(
                types.InlineKeyboardButton("📊 Faollik", callback_data=f"view_activity_{user_id}"),
                types.InlineKeyboardButton("🚫/✅ Blok Holati", callback_data=f"toggle_block_{user_id}")
            )
            markup_inline.add(types.InlineKeyboardButton("💎 Premium Holati", callback_data=f"toggle_premium_{user_id}"))
            markup_inline.add(types.InlineKeyboardButton("🔙 Orqaga", callback_data=f"back_to_users_{user_id}"))
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=markup_inline,
                parse_mode="Markdown"
            )
            update_last_menu(ADMIN_ID, f"user_details_{user_id}")

        elif action == "back_to_users":
            conn = get_db_connection()
            if not conn:
                bot.send_message(call.message.chat.id, "⚠️ Serverda muammo!", reply_markup=get_base_markup(lang, True, call.from_user.id))
                return
            cur = conn.cursor()
            cur.execute("SELECT user_id, vip, premium FROM users WHERE first_start IS NOT NULL AND user_id != %s ORDER BY first_start DESC", (str(ADMIN_ID),))
            all_users = cur.fetchall()
            cur.close()
            conn.close()

            page = int(call.message.text.split("Sahifa ")[1].split("/")[0]) if "Sahifa" in call.message.text else 1
            per_page = 5
            total_pages = (len(all_users) + per_page - 1) // per_page
            start_idx = (page - 1) * per_page
            end_idx = min(start_idx + per_page, len(all_users))
            users = all_users[start_idx:end_idx]

            inline_markup = types.InlineKeyboardMarkup()
            for user in users:
                try:
                    user_info = bot.get_chat(int(user["user_id"]))
                    status_mark = " ⭐" if user["vip"] else " 💎" if user["premium"] else ""
                    inline_markup.add(types.InlineKeyboardButton(f"{user_info.first_name or 'N/A'} (ID: {user['user_id']}){status_mark}", callback_data=f"user_{user['user_id']}"))
                except:
                    inline_markup.add(types.InlineKeyboardButton(f"ID: {user['user_id']} (Xato)", callback_data=f"user_{user['user_id']}"))

            pagination_row = []
            if page > 1:
                pagination_row.append(types.InlineKeyboardButton("⬅️ Oldingi", callback_data=f"users_page_{page-1}"))
            if page < total_pages:
                pagination_row.append(types.InlineKeyboardButton("Keyingi ➡️", callback_data=f"users_page_{page+1}"))
            if pagination_row:
                inline_markup.add(*pagination_row)

            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"📄 Sahifa {page}/{total_pages}",
                reply_markup=inline_markup
            )
            update_last_menu(ADMIN_ID, f"users_list_page_{page}")

    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ Xatolik: {str(e)}", reply_markup=get_base_markup(lang, True, call.from_user.id))

@bot.callback_query_handler(func=lambda call: call.data.startswith(("increase_balance_", "decrease_balance_")))
def handle_balance_change(call):
    action, user_id = call.data.split("_", 1)
    user_id = int(user_id)
    lang = get_user_lang(ADMIN_ID)
    increase = action == "increase_balance"
    update_last_menu(ADMIN_ID, f"{action}_input_{user_id}")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(translations[lang]["back"])
    bot.send_message(call.message.chat.id, f"💰 Miqdor (so‘m):", reply_markup=markup)
    bot.register_next_step_handler(call.message, process_balance_change, user_id, increase)

def process_balance_change(message, user_id, increase):
    lang = get_user_lang(message.from_user.id)
    if message.text == translations[lang]["back"]:
        bot.send_message(message.chat.id, translations[lang]["action_canceled"], reply_markup=get_base_markup(lang, True, message.from_user.id))
        user_info = bot.get_chat(user_id)
        base_text = (
            f"👤 *Ism*: {user_info.first_name or 'N/A'}\n"
            f"🆔 *ID*: {user_id}\n"
            f"📛 *Username*: @{user_info.username or 'N/A'}"
        )
        markup_inline = types.InlineKeyboardMarkup(row_width=2)
        markup_inline.add(
            types.InlineKeyboardButton("💰 Hisob", callback_data=f"view_balance_{user_id}"),
            types.InlineKeyboardButton("⭐ VIP Holati", callback_data=f"toggle_vip_{user_id}")
        )
        markup_inline.add(
            types.InlineKeyboardButton("📊 Faollik", callback_data=f"view_activity_{user_id}"),
            types.InlineKeyboardButton("🚫/✅ Blok Holati", callback_data=f"toggle_block_{user_id}")
        )
        markup_inline.add(types.InlineKeyboardButton("💎 Premium Holati", callback_data=f"toggle_premium_{user_id}"))
        markup_inline.add(types.InlineKeyboardButton("🔙 Orqaga", callback_data=f"back_to_users_{user_id}"))
        bot.send_message(
            chat_id=message.chat.id,
            text=base_text,
            reply_markup=markup_inline,
            parse_mode="Markdown"
        )
        update_last_menu(ADMIN_ID, f"user_details_{user_id}")
        return
    if message.content_type != 'text' or not message.text.isdigit():
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(translations[lang]["back"])
        bot.send_message(message.chat.id, "❌ Faqat son!", reply_markup=markup)
        bot.register_next_step_handler(message, process_balance_change, user_id, increase)
        return
    amount = int 
    message.text
    update_user_balance(user_id, amount, increase)
    action_text = "➕ Qo‘shildi" if increase else "➖ Ayirildi"
    user_info = bot.get_chat(user_id)
    base_text = (
        f"👤 *Ism*: {user_info.first_name or 'N/A'}\n"
        f"🆔 *ID*: {user_id}\n"
        f"📛 *Username*: @{user_info.username or 'N/A'}\n"
        f"💰 Hisob: {get_user_balance(user_id)} so‘m\n"
        f"{action_text}: {amount} so‘m"
    )
    markup_inline = types.InlineKeyboardMarkup()
    markup_inline.add(types.InlineKeyboardButton("🔙 Orqaga", callback_data=f"back_to_user_{user_id}"))
    bot.send_message(
        message.chat.id,
        base_text,
        reply_markup=markup_inline,
        parse_mode="Markdown"
    )
    update_last_menu(ADMIN_ID, f"main_menu")
    bot.send_message(user_id, f"💰 Admin hisobingizni yangiladi: {action_text} {amount} so‘m", reply_markup=get_base_markup(lang, False, user_id))

# Sozlamalar
@bot.message_handler(func=lambda message: message.text == translations[get_user_lang(message.from_user.id)]["settings"])
def settings_menu(message):
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(translations[lang]["change_lang"])
    markup.add(translations[lang]["back"])
    update_last_menu(user_id, "settings")
    bot.send_message(message.chat.id, translations[lang]["settings"], reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == translations[get_user_lang(message.from_user.id)]["change_lang"])
def change_language(message):
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("🇺🇿 Uz", callback_data="lang_uz"),
        types.InlineKeyboardButton("🇷🇺 Ru", callback_data="lang_ru"),
        types.InlineKeyboardButton("🇺🇸 En", callback_data="lang_en")
    )
    update_last_menu(user_id, "change_language")
    bot.send_message(message.chat.id, translations[lang]["change_lang"], reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("lang_"))
def handle_language_change(call):
    lang = call.data.split("_")[1]
    user_id = call.from_user.id
    conn = get_db_connection()
    if not conn:
        bot.send_message(call.message.chat.id, "⚠️ Serverda muammo!", reply_markup=get_base_markup(get_user_lang(user_id), user_id == ADMIN_ID, user_id))
        return
    cur = conn.cursor()
    cur.execute("UPDATE users SET lang = %s WHERE user_id = %s", (lang, str(user_id)))
    conn.commit()
    cur.close()
    conn.close()
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=translations[lang]["lang_changed"],
        reply_markup=None
    )
    if user_id == ADMIN_ID:
        admin_panel(call.message)
    else:
        show_main_menu(call.message)

# Orqaga tugmasi
@bot.message_handler(func=lambda message: message.text == translations[get_user_lang(message.from_user.id)]["back"])
def handle_back(message):
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    last_menu = get_last_menu(user_id)

    input_states = [
        "sms_prank_oddiy", "kontrakt_edu", "top_up_balance_input", "complaints_user_input",
        "cheque_amount_input", "complaint_reply_input", "increase_balance_input",
        "decrease_balance_input", "pay_premium_1", "pay_premium_3", "pay_premium_6",
        "pay_premium_12"
    ]

    if any(last_menu.startswith(state) for state in input_states):
        bot.send_message(message.chat.id, translations[lang]["action_canceled"], reply_markup=get_base_markup(lang, user_id == ADMIN_ID, user_id))

    menu_map = {
        "main_menu": show_main_menu,
        "group_join": show_group_join,
        "sms_prank": show_main_menu,
        "sms_prank_oddiy": sms_prank_menu,
        "kontrakt_edu": sms_prank_menu,
        "balance": show_main_menu,
        "top_up_balance_input": balance_menu,
        "admin_panel": show_main_menu,
        "view_cheques": admin_panel,
        "view_premium_cheques": admin_panel,
        "show_cheques_pending_regular": view_cheques_menu,
        "show_cheques_approved_regular": view_cheques_menu,
        "show_cheques_rejected_regular": view_cheques_menu,
        "show_cheques_pending_premium": view_premium_cheques_menu,
        "show_cheques_approved_premium": view_premium_cheques_menu,
        "show_cheques_rejected_premium": view_premium_cheques_menu,
        "complaints_user_input": show_main_menu,
        "admin_complaints": admin_panel,
        "view_complaints_" + translations[lang]["complaints_new"]: admin_complaints_menu,
        "view_complaints_" + translations[lang]["complaints_viewed"]: admin_complaints_menu,
        "view_complaints_" + translations[lang]["complaints_replied"]: admin_complaints_menu,
        "blocked_users": admin_panel,
        "users_list_page_": admin_panel,
        "settings": show_main_menu,
        "change_language": settings_menu,
        "premium_plans": show_main_menu,
        "rating": show_main_menu,
        "pay_premium_": show_premium_plans,
        "cheque_amount_input_": lambda msg: view_premium_cheques_menu(msg) if "premium" in last_menu else view_cheques_menu(msg),
        "complaint_reply_input_": admin_complaints_menu,
        "increase_balance_input_": lambda msg: show_user_details_inline(msg, user_id),
        "decrease_balance_input_": lambda msg: show_user_details_inline(msg, user_id),
        "user_details_": lambda msg: users_list_menu(msg, page=1),
        "view_balance_": lambda msg: show_user_details_inline(msg, user_id),
        "toggle_vip_": lambda msg: show_user_details_inline(msg, user_id),
        "view_activity_": lambda msg: show_user_details_inline(msg, user_id),
        "toggle_block_": lambda msg: show_user_details_inline(msg, user_id),
        "toggle_premium_": lambda msg: show_user_details_inline(msg, user_id)
    }

    def show_user_details_inline(msg, uid):
        try:
            user_info = bot.get_chat(uid)
            base_text = (
                f"👤 *Ism*: {user_info.first_name or 'N/A'}\n"
                f"🆔 *ID*: {uid}\n"
                f"📛 *Username*: @{user_info.username or 'N/A'}"
            )
            markup_inline = types.InlineKeyboardMarkup(row_width=2)
            markup_inline.add(
                types.InlineKeyboardButton("💰 Hisob", callback_data=f"view_balance_{uid}"),
                types.InlineKeyboardButton("⭐ VIP Holati", callback_data=f"toggle_vip_{uid}")
            )
            markup_inline.add(
                types.InlineKeyboardButton("📊 Faollik", callback_data=f"view_activity_{uid}"),
                types.InlineKeyboardButton("🚫/✅ Blok Holati", callback_data=f"toggle_block_{uid}")
            )
            markup_inline.add(types.InlineKeyboardButton("💎 Premium Holati", callback_data=f"toggle_premium_{uid}"))
            markup_inline.add(types.InlineKeyboardButton("🔙 Orqaga", callback_data=f"back_to_users_{uid}"))
            bot.send_message(
                msg.chat.id,
                base_text,
                reply_markup=markup_inline,
                parse_mode="Markdown"
            )
            update_last_menu(ADMIN_ID, f"user_details_{uid}")
        except Exception as e:
            bot.send_message(msg.chat.id, f"❌ Xatolik: {str(e)}", reply_markup=get_base_markup(lang, True, msg.from_user.id))

    for menu_key, menu_func in menu_map.items():
        if last_menu.startswith(menu_key) or last_menu == menu_key:
            menu_func(message)
            break
    else:
        show_main_menu(message)

# Botni ishga tushirish
if __name__ == "__main__":
    try:
        print("Bot ishga tushdi...")
        bot.polling(none_stop=True, interval=0)
    except Exception as e:
        print(f"Bot polling error: {e}")