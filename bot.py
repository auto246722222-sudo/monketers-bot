from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
import g4f
from g4f.client import Client
import requests
import time
import json
import os
import asyncio
import re
import random
from datetime import datetime

# ===== ТОКЕН БЕРЁТСЯ ИЗ ПЕРЕМЕННОЙ ОКРУЖЕНИЯ =====
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set!")
# =================================================

ADMIN_ID = 7164158684
TON_WALLET = "UQBDcTrdHskPmyA4EY2Q2T5hz7Md_T5iGfIWgwrWx-zITpsm"

DATA_FILE = "users.json"
SUBS_FILE = "subs.json"
PENDING_FILE = "pending.json"

client = Client()
user_histories = {}

GREETINGS = [
    "Рад помочь.",
    "Всегда на связи.",
    "Чем могу быть полезен?",
    "Спрашивайте, не стесняйтесь.",
    "Хорошего дня!"
]

def load_data(file):
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return {}

def save_data(data, file):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

def clean_reply(text):
    bad_patterns = [
        r'need proxies.*',
        r'cheaper than the market.*',
        r'https?://\S*proxy\S*',
        r'https?://op\.wtf',
        r'Need proxies\?',
        r'прокси.*дешевле',
        r'Proxy.*price',
        r'Proxies',
        r'buy proxies',
        r'лучшие прокси',
    ]
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        should_skip = False
        for pattern in bad_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                should_skip = True
                break
        if not should_skip and len(line.strip()) > 0:
            cleaned.append(line)
    result = '\n'.join(cleaned).strip()
    if len(result) < 5:
        return text[:200]
    return result

async def ask_ai(user_id, message, retry_count=0):
    if user_id not in user_histories:
        user_histories[user_id] = []

    user_histories[user_id].append({"role": "user", "content": message})
    messages = user_histories[user_id][-10:]

    models = ["gpt-3.5-turbo", "gpt-4o-mini", "gpt-4"]
    
    for model in models:
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.chat.completions.create,
                    model=model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1000,
                ),
                timeout=60
            )
            
            bot_reply = response.choices[0].message.content
            if bot_reply and len(bot_reply) > 10:
                bot_reply = clean_reply(bot_reply)
                user_histories[user_id].append({"role": "assistant", "content": bot_reply})
                return bot_reply
        except Exception as e:
            print(f"Ошибка {model}: {str(e)[:60]}")
            continue
    
    if retry_count < 2:
        await asyncio.sleep(5)
        return await ask_ai(user_id, message, retry_count + 1)
    return "⚠️ Нейросеть временно недоступна. Попробуйте через минуту."

def is_premium(user_id):
    subs = load_data(SUBS_FILE)
    return str(user_id) in subs and subs[str(user_id)] > time.time()

def get_days_left(user_id):
    subs = load_data(SUBS_FILE)
    if str(user_id) in subs:
        return max(0, int((subs[str(user_id)] - time.time()) // 86400))
    return 0

def send_message(chat_id, text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10
        )
    except:
        pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    greeting = random.choice(GREETINGS)
    await update.message.reply_text(
        f"<b>MONKETERS AI</b> — ваш надёжный чат-помощник.\n"
        f"{greeting}\n\n"
        f"👑 <b>Администратор:</b> @monketer\n"
        f"/help — список команд\n"
        f"/pay — тарифы подписки",
        parse_mode=ParseMode.HTML
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "<b>📌 Доступные команды</b>\n\n"
        "/start — Главное меню\n"
        "/status — Статус подписки\n"
        "/pay — Тарифы Monketers AI\n"
        "/clear — Очистить диалог\n"
        "/time — Текущее время\n"
        "/joke — Случайная шутка\n"
        "/help — Эта справка\n\n"
        "💬 <b>Просто напишите вопрос — я отвечу.</b>\n\n"
        "👑 <b>По всем вопросам:</b> @monketer",
        parse_mode=ParseMode.HTML
    )

async def time_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    await update.message.reply_text(
        f"🕒 <b>Monketers AI</b>: {now}\n⏰ Часовой пояс: Москва (UTC+3)\n\n👑 <b>Администратор:</b> @monketer",
        parse_mode=ParseMode.HTML
    )

async def joke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jokes = [
        "❓ Почему программисты путают Хэллоуин и Рождество? — Потому что 31 Oct = 25 Dec.",
        "⚡ Что говорит один бит другому? — Будь на моём месте!",
        "🐍 Почему Python — хороший язык? — Потому что в нём не бывает змей!",
        "🤖 Какое самое любимое время у бота? — Время обновлять базу знаний.",
    ]
    await update.message.reply_text(
        f"{random.choice(jokes)}\n\n👑 <b>Администратор:</b> @monketer",
        parse_mode=ParseMode.HTML
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid == ADMIN_ID:
        await update.message.reply_text(
            "👑 <b>Вы администратор Monketers AI.</b>\nБезлимитные запросы включены.\n\n👑 <b>Админ:</b> @monketer",
            parse_mode=ParseMode.HTML
        )
        return
    days = get_days_left(uid)
    if days > 0:
        expire_date = datetime.fromtimestamp(load_data(SUBS_FILE)[str(uid)]).strftime('%d.%m.%Y')
        await update.message.reply_text(
            f"✅ <b>Подписка активна</b>\nОсталось дней: {days}\n\n📅 Действует до: {expire_date}\n\n👑 <b>Администратор:</b> @monketer",
            parse_mode=ParseMode.HTML
        )
        return
    users = load_data(DATA_FILE)
    if str(uid) in users and users[str(uid)].get("trial_used"):
        await update.message.reply_text(
            "❌ <b>Подписка не активна</b>\n💎 Пополните баланс: /pay\n\n👑 <b>Администратор:</b> @monketer",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            "🎁 <b>Первый запрос — бесплатно</b>\nПросто напишите сообщение и оцените работу ИИ.\n💎 /pay\n\n👑 <b>Администратор:</b> @monketer",
            parse_mode=ParseMode.HTML
        )

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    name = update.effective_user.first_name
    if uid == ADMIN_ID:
        await update.message.reply_text(
            "👑 Вы администратор, подписка не нужна.\n\n👑 <b>Администратор:</b> @monketer",
            parse_mode=ParseMode.HTML
        )
        return
    args = context.args
    if not args:
        await update.message.reply_text(
            "<b>💰 Тарифы Monketers AI</b>\n\n"
            "/pay 1 — 1 месяц (5 TON)\n"
            "/pay 3 — 3 месяца (12 TON)\n"
            "/pay forever — бессрочно (30 TON)\n\n"
            "👑 <b>Администратор:</b> @monketer",
            parse_mode=ParseMode.HTML
        )
        return
    
    plan = args[0].lower()
    if plan == "1":
        price, days, pname = 5, 30, "1 месяц"
    elif plan == "3":
        price, days, pname = 12, 90, "3 месяца"
    elif plan == "forever":
        price, days, pname = 30, 3650, "Бессрочно"
    else:
        await update.message.reply_text(
            "❌ Неверная команда. Используйте /pay 1\n\n👑 <b>Администратор:</b> @monketer",
            parse_mode=ParseMode.HTML
        )
        return
    
    pid = f"{uid}_{int(time.time())}"
    pend = load_data(PENDING_FILE)
    pend[pid] = {
        "user_id": uid,
        "plan": pname,
        "price": price,
        "days": days,
        "status": "wait",
        "name": name
    }
    save_data(pend, PENDING_FILE)
    
    await update.message.reply_text(
        f"💰 <b>{pname}</b> | {price} TON\n\n"
        f"📤 Кошелёк TON:\n<code>{TON_WALLET}</code>\n"
        f"🆔 Код оплаты: <code>{pid}</code>\n\n"
        "После перевода введите:\n"
        f"<code>/confirm {pid}</code>\n\n"
        "👑 <b>Администратор:</b> @monketer",
        parse_mode=ParseMode.HTML
    )

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    name = update.effective_user.first_name
    args = context.args
    if not args:
        await update.message.reply_text(
            "📌 Используйте: /confirm КОД\n\n👑 <b>Администратор:</b> @monketer",
            parse_mode=ParseMode.HTML
        )
        return
    
    pid = args[0]
    pend = load_data(PENDING_FILE)
    if pid not in pend or pend[pid]["status"] != "wait":
        await update.message.reply_text(
            "❌ Код не найден или уже обработан.\n\n👑 <b>Администратор:</b> @monketer",
            parse_mode=ParseMode.HTML
        )
        return
    
    send_message(
        ADMIN_ID,
        f"💰 <b>ЗАЯВКА</b> от {name}\n📦 {pend[pid]['plan']}\n💰 {pend[pid]['price']} TON\n🆔 {pid}\n\n✅ /activate {uid}"
    )
    await update.message.reply_text(
        "✅ Заявка отправлена администратору. Ожидайте активации.\n\n👑 <b>Администратор:</b> @monketer",
        parse_mode=ParseMode.HTML
    )

async def activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID:
        await update.message.reply_text(
            "❌ Команда только для администратора.\n\n👑 <b>Администратор:</b> @monketer",
            parse_mode=ParseMode.HTML
        )
        return
    args = context.args
    if not args:
        await update.message.reply_text("/activate USER_ID")
        return
    
    target = args[0]
    pend = load_data(PENDING_FILE)
    for pid, p in pend.items():
        if str(p["user_id"]) == target and p["status"] == "wait":
            subs = load_data(SUBS_FILE)
            subs[target] = time.time() + p["days"] * 86400
            save_data(subs, SUBS_FILE)
            p["status"] = "completed"
            pend[pid] = p
            save_data(pend, PENDING_FILE)
            send_message(
                int(target),
                f"✅ <b>Подписка {p['plan']} активирована!</b>\n🤖 Доступ к Monketers AI открыт.\n\n👑 <b>Администратор:</b> @monketer"
            )
            await update.message.reply_text(f"✅ Активирована подписка {p['plan']} для {target}")
            return
    await update.message.reply_text(
        "❌ Ожидающих платежей не найдено.\n\n👑 <b>Администратор:</b> @monketer",
        parse_mode=ParseMode.HTML
    )

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in user_histories:
        user_histories[uid] = []
        await update.message.reply_text(
            "🗑️ История общения очищена.\n\n👑 <b>Администратор:</b> @monketer",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            "История диалога пуста.\n\n👑 <b>Администратор:</b> @monketer",
            parse_mode=ParseMode.HTML
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text
    if text.startswith('/'):
        return
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    if uid == ADMIN_ID or is_premium(uid):
        reply = await ask_ai(uid, text)
        await update.message.reply_text(reply)
        return
    
    users = load_data(DATA_FILE)
    if str(uid) not in users:
        users[str(uid)] = {"trial_used": False}
    
    if not users[str(uid)].get("trial_used", False):
        users[str(uid)]["trial_used"] = True
        save_data(users, DATA_FILE)
        reply = await ask_ai(uid, text)
        await update.message.reply_text(
            reply + "\n\n━━━━━━━━━━━━\n🎁 Бесплатный запрос использован.\n💎 /pay 1\n\n👑 <b>Администратор:</b> @monketer",
            parse_mode=ParseMode.HTML
        )
        return
    
    await update.message.reply_text(
        "❌ <b>Нет активной подписки</b>\n💎 Оформите доступ: /pay 1\n\n👑 <b>Администратор:</b> @monketer",
        parse_mode=ParseMode.HTML
    )

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("pay", pay))
    app.add_handler(CommandHandler("confirm", confirm))
    app.add_handler(CommandHandler("activate", activate))
    app.add_handler(CommandHandler("clear", clear_history))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("time", time_command))
    app.add_handler(CommandHandler("joke", joke_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("=" * 50)
    print("✅ MONKETERS AI — БОТ ЗАПУЩЕН НА ХОСТИНГЕ")
    print("▸ Чат-помощник, нейросеть GPT")
    print(f"▸ Админ: {ADMIN_ID}")
    print("=" * 50)
    
    app.run_polling()

if __name__ == "__main__":
    main()