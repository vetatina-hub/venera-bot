# -*- coding: utf-8 -*-
"""
course.py — курс «Квантовый взлёт» в боте @venera_tatina_bot
Пилот: Модуль 1, Урок 1 «Путь героя»
Отдельный файл: если что-то ломается в курсе — чиним только здесь,
диагностика и воронка в bot.py не трогаются.
"""

import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

# ============ НАСТРОЙКИ ============

# Админ курса — Венера (по username в Telegram, без @)
ADMIN_USERNAME = "vetatina"

LINK_VENERA = "https://t.me/vetatina"

# ============ УРОКИ (пилот: только Урок 1) ============

LESSONS = {
    1: {
        "title": "Урок 1 · «Путь героя»",
        "video": "https://youtu.be/-usUL8WK6MU",
        "pdf": "BQACAgIAAxkBAAIBH2pU7Ivbsnmt2i0jzUff5_y1SzkwAAKdrAACSDKpShD6GQyi-JSRPAQ",
        "dz": "BQACAgIAAxkBAAIBImpU7ys83yoGP4Wl0dTgYQ3eDd_QAAK0rAACSDKpSs4KNtmbOqK7PAQ",
        "caption": (
            "📚 МОДУЛЬ 1 · Урок 1 «Путь героя»\n\n"
            "1️⃣ Посмотри видео урока по кнопке ниже\n"
            "2️⃣ Открой презентацию — она прикреплена к этому сообщению\n"
            "3️⃣ Когда посмотришь видео — нажми «📝 Домашнее задание»\n\n"
            "Твой путь героя начинается прямо сейчас ✨"
        ),
        "dz_caption": (
            "📝 Домашнее задание к Уроку 1\n\n"
            "Напиши системы, в которых ты состоишь, свою роль и цель "
            "в каждой из них. Подробно пиши под видео в чате.\n\n"
            "Когда выполнишь — нажми «✅ Сделала»"
        ),
        "done_text": (
            "🎉 Урок 1 «Путь героя» пройден!\n\n"
            "Ты сделала первый шаг — а первый шаг всегда самый важный.\n\n"
            "Урок 2 «Законы системы» появится совсем скоро. "
            "Я сообщу тебе, как только он будет готов 💫"
        ),
    },
}

# ============ БАЗА ДАННЫХ ============

def get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def init_course_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS course_students (
                    id SERIAL PRIMARY KEY,
                    username TEXT,
                    chat_id BIGINT,
                    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS course_progress (
                    id SERIAL PRIMARY KEY,
                    chat_id BIGINT NOT NULL,
                    lesson INT NOT NULL,
                    dz_done BOOLEAN DEFAULT FALSE,
                    done BOOLEAN DEFAULT FALSE,
                    done_at TIMESTAMP WITH TIME ZONE,
                    UNIQUE (chat_id, lesson)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS kvantiki (
                    chat_id BIGINT PRIMARY KEY,
                    balance INT DEFAULT 0
                )
            """)
            conn.commit()
    logger.info("✅ Таблицы курса готовы")


# ============ ПРОВЕРКА ДОСТУПА ============

def is_admin(update: Update) -> bool:
    user = update.effective_user
    return bool(user and user.username and user.username.lower() == ADMIN_USERNAME.lower())


def is_student(update: Update) -> bool:
    user = update.effective_user
    chat_id = update.effective_chat.id
    username = (user.username or "").lower() if user else ""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM course_students WHERE chat_id = %s OR (username IS NOT NULL AND LOWER(username) = %s)",
                (chat_id, username)
            )
            row = cur.fetchone()
            # Запоминаем chat_id, если ученица была добавлена по username
            if row:
                cur.execute(
                    "UPDATE course_students SET chat_id = %s WHERE id = %s AND chat_id IS NULL",
                    (chat_id, row["id"])
                )
                conn.commit()
    return bool(row)


def get_balance(chat_id: int) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT balance FROM kvantiki WHERE chat_id = %s", (chat_id,))
            row = cur.fetchone()
    return row["balance"] if row else 0


# ============ ОТПРАВКА УРОКА ============

async def send_lesson(bot, chat_id: int, lesson_num: int):
    lesson = LESSONS.get(lesson_num)
    if not lesson:
        await bot.send_message(chat_id, "Этот урок ещё готовится 💫")
        return
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Смотреть видео", url=lesson["video"])],
        [InlineKeyboardButton("📝 Домашнее задание", callback_data=f"crs_dz_{lesson_num}")],
        [InlineKeyboardButton("✨ Мои квантики", callback_data="crs_balance")],
    ])
    await bot.send_document(
        chat_id=chat_id,
        document=lesson["pdf"],
        caption=lesson["caption"],
        reply_markup=kb
    )
    logger.info(f"📚 Урок {lesson_num} отправлен → {chat_id}")


# ============ КОМАНДЫ УЧЕНИЦЫ ============

async def cmd_kurs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вход в курс: /kurs"""
    chat_id = update.effective_chat.id
    if not (is_student(update) or is_admin(update)):
        await update.message.reply_text(
            "✨ Курс «Квантовый взлёт» доступен ученицам Академии.\n\n"
            "Хочешь присоединиться? Напиши Венере лично 👇",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💫 Написать Венере", url=LINK_VENERA)]
            ])
        )
        return
    await update.message.reply_text(
        "🚀 Добро пожаловать в «Квантовый взлёт»!\n\nОткрываю твой урок..."
    )
    await send_lesson(context.bot, chat_id, 1)


async def cb_dz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кнопка «📝 Домашнее задание»"""
    query = update.callback_query
    await query.answer()
    lesson_num = int(query.data.split("_")[-1])
    lesson = LESSONS.get(lesson_num)
    if not lesson or not lesson.get("dz"):
        await query.message.reply_text("В этом уроке нет домашнего задания 😊")
        return
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Сделала", callback_data=f"crs_done_{lesson_num}")],
    ])
    await context.bot.send_document(
        chat_id=query.message.chat_id,
        document=lesson["dz"],
        caption=lesson["dz_caption"],
        reply_markup=kb
    )


async def cb_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кнопка «✅ Сделала»"""
    query = update.callback_query
    await query.answer("Умница! 🎉")
    lesson_num = int(query.data.split("_")[-1])
    chat_id = query.message.chat_id
    lesson = LESSONS.get(lesson_num)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO course_progress (chat_id, lesson, dz_done, done, done_at)
                VALUES (%s, %s, TRUE, TRUE, NOW())
                ON CONFLICT (chat_id, lesson)
                DO UPDATE SET dz_done = TRUE, done = TRUE, done_at = NOW()
            """, (chat_id, lesson_num))
            conn.commit()
    await context.bot.send_message(chat_id, lesson["done_text"])
    logger.info(f"✅ Урок {lesson_num} пройден → {chat_id}")


async def cb_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кнопка «✨ Мои квантики»"""
    query = update.callback_query
    await query.answer()
    balance = get_balance(query.message.chat_id)
    await query.message.reply_text(
        f"✨ Твой баланс: {balance} квантиков\n\n"
        f"Квантики начисляются за твои шаги в Академии и обмениваются "
        f"на диагностики, разборы и Иерархию.\n\n"
        f"Вопросы по балансу — у Венеры: @vetatina"
    )


# ============ КОМАНДЫ АДМИНА (только для Венеры) ============

async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавить ученицу: /add @username"""
    if not is_admin(update):
        return
    if not context.args:
        await update.message.reply_text(
            "Как добавить ученицу:\n/add @username\n\nНапример: /add @anna_k"
        )
        return
    username = context.args[0].lstrip("@").lower()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM course_students WHERE LOWER(username) = %s", (username,)
            )
            if cur.fetchone():
                await update.message.reply_text(f"@{username} уже в списке учениц ✅")
                return
            cur.execute(
                "INSERT INTO course_students (username) VALUES (%s)", (username,)
            )
            conn.commit()
    await update.message.reply_text(
        f"✅ @{username} добавлена!\n\n"
        f"Передайте ей: открыть @venera_tatina_bot и отправить команду /kurs"
    )


async def cmd_students(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список учениц: /students"""
    if not is_admin(update):
        return
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT username, chat_id FROM course_students ORDER BY added_at")
            rows = cur.fetchall()
    if not rows:
        await update.message.reply_text("Список учениц пока пуст. Добавьте: /add @username")
        return
    lines = []
    for i, r in enumerate(rows, 1):
        name = f"@{r['username']}" if r["username"] else str(r["chat_id"])
        mark = " · уже заходила в курс" if r["chat_id"] else ""
        lines.append(f"{i}. {name}{mark}")
    await update.message.reply_text("👩‍🎓 Ученицы курса:\n\n" + "\n".join(lines))


async def cmd_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Секретная проверка урока: /test 1"""
    if not is_admin(update):
        return
    num = 1
    if context.args:
        try:
            num = int(context.args[0])
        except ValueError:
            pass
    await update.message.reply_text(f"🔍 Проверка: отправляю урок {num}")
    await send_lesson(context.bot, update.effective_chat.id, num)


# ============ ПОДКЛЮЧЕНИЕ К БОТУ ============

def register(app: Application):
    """Вызывается из bot.py одной строкой"""
    init_course_db()
    app.add_handler(CommandHandler("kurs", cmd_kurs))
    app.add_handler(CommandHandler("add", cmd_add))
    app.add_handler(CommandHandler("students", cmd_students))
    app.add_handler(CommandHandler("test", cmd_test))
    app.add_handler(CallbackQueryHandler(cb_dz, pattern=r"^crs_dz_\d+$"))
    app.add_handler(CallbackQueryHandler(cb_done, pattern=r"^crs_done_\d+$"))
    app.add_handler(CallbackQueryHandler(cb_balance, pattern=r"^crs_balance$"))
    logger.info("✅ Курс «Квантовый взлёт» подключён")
