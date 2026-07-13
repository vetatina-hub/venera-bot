# -*- coding: utf-8 -*-
"""
course.py — курс «Квантовый взлёт» в боте @venera_tatina_bot
Версия 2: пилот Урок 1 + пауза + прогресс учениц + срок доступа 4 месяца

Правила доступа:
- /add @username — доступ на 4 месяца (та же команда продлевает и снимает паузу)
- /pause @username — точечная пауза для одной ученицы
- За 2 недели до конца срока бот сам присылает напоминание
- Срок вышел или пауза → вежливое сообщение + кнопка «Написать Венере»
"""

import os
import asyncio
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

# ============ НАСТРОЙКИ ============

ADMIN_USERNAME = "vetatina"          # админ курса — Венера (username без @)
ACCESS_DAYS = 120                    # срок доступа: 4 месяца (3 мес курс + 1 мес повторение)
REMIND_BEFORE_DAYS = 14              # напоминание за 2 недели до конца

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
            # Новые колонки (добавятся один раз, старые данные не пострадают)
            cur.execute("ALTER TABLE course_students ADD COLUMN IF NOT EXISTS active BOOLEAN DEFAULT TRUE")
            cur.execute("ALTER TABLE course_students ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP WITH TIME ZONE")
            cur.execute("ALTER TABLE course_students ADD COLUMN IF NOT EXISTS reminder_sent BOOLEAN DEFAULT FALSE")
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


# ============ ДОСТУП ============

def is_admin(update: Update) -> bool:
    user = update.effective_user
    return bool(user and user.username and user.username.lower() == ADMIN_USERNAME.lower())


def get_student_status(update: Update) -> str:
    """Возвращает: 'ok' — доступ открыт · 'paused' — на паузе ·
    'expired' — срок вышел · 'none' — не в списке"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    username = (user.username or "").lower() if user else ""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, active, expires_at FROM course_students "
                "WHERE chat_id = %s OR (username IS NOT NULL AND LOWER(username) = %s)",
                (chat_id, username)
            )
            row = cur.fetchone()
            if not row:
                return "none"
            # Запоминаем chat_id, если ученица была добавлена по username
            cur.execute(
                "UPDATE course_students SET chat_id = %s WHERE id = %s AND chat_id IS NULL",
                (chat_id, row["id"])
            )
            conn.commit()
    if not row["active"]:
        return "paused"
    if row["expires_at"] and row["expires_at"] < datetime.now(timezone.utc):
        return "expired"
    return "ok"


async def deny_message(bot, chat_id: int, status: str):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💫 Написать Венере", url=LINK_VENERA)]
    ])
    if status == "paused":
        text = ("🌸 Доступ к курсу сейчас на паузе.\n\n"
                "Напиши Венере — она всё подскажет 👇")
    elif status == "expired":
        text = ("🌸 Срок доступа к курсу «Квантовый взлёт» завершился.\n\n"
                "Хочешь продлить и продолжить путь? Напиши Венере 👇")
    else:
        text = ("✨ Курс «Квантовый взлёт» доступен ученицам Академии.\n\n"
                "Хочешь присоединиться? Напиши Венере лично 👇")
    await bot.send_message(chat_id, text, reply_markup=kb)


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


# ============ УЧЕНИЦА ============

async def cmd_kurs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вход в курс: /kurs"""
    chat_id = update.effective_chat.id
    status = get_student_status(update)
    if status != "ok" and not is_admin(update):
        await deny_message(context.bot, chat_id, status)
        return
    await update.message.reply_text(
        "🚀 Добро пожаловать в «Квантовый взлёт»!\n\nОткрываю твой урок..."
    )
    await send_lesson(context.bot, chat_id, 1)


async def cb_dz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кнопка «📝 Домашнее задание»"""
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    status = get_student_status(update)
    if status != "ok" and not is_admin(update):
        await deny_message(context.bot, chat_id, status)
        return
    lesson_num = int(query.data.split("_")[-1])
    lesson = LESSONS.get(lesson_num)
    if not lesson or not lesson.get("dz"):
        await query.message.reply_text("В этом уроке нет домашнего задания 😊")
        return
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Сделала", callback_data=f"crs_done_{lesson_num}")],
    ])
    await context.bot.send_document(
        chat_id=chat_id,
        document=lesson["dz"],
        caption=lesson["dz_caption"],
        reply_markup=kb
    )


async def cb_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кнопка «✅ Сделала»"""
    query = update.callback_query
    await query.answer("Умница! 🎉")
    chat_id = query.message.chat_id
    status = get_student_status(update)
    if status != "ok" and not is_admin(update):
        await deny_message(context.bot, chat_id, status)
        return
    lesson_num = int(query.data.split("_")[-1])
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


# ============ АДМИН (только Венера) ============

async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Дать/продлить доступ: /add @username (4 месяца с этого момента)"""
    if not is_admin(update):
        return
    if not context.args:
        await update.message.reply_text(
            "Как дать доступ ученице:\n/add @username\n\nНапример: /add @anna_k\n\n"
            "Эта же команда снимает паузу и продлевает срок ещё на 4 месяца."
        )
        return
    username = context.args[0].lstrip("@").lower()
    expires = datetime.now(timezone.utc) + timedelta(days=ACCESS_DAYS)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM course_students WHERE LOWER(username) = %s", (username,))
            row = cur.fetchone()
            if row:
                cur.execute(
                    "UPDATE course_students SET active = TRUE, expires_at = %s, reminder_sent = FALSE WHERE id = %s",
                    (expires, row["id"])
                )
                verb = "продлён"
            else:
                cur.execute(
                    "INSERT INTO course_students (username, active, expires_at) VALUES (%s, TRUE, %s)",
                    (username, expires)
                )
                verb = "открыт"
            conn.commit()
    await update.message.reply_text(
        f"✅ Доступ для @{username} {verb} до {expires.strftime('%d.%m.%Y')}\n\n"
        f"Передайте ей: открыть @venera_tatina_bot и отправить команду /kurs"
    )


async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Поставить на паузу: /pause @username (только эту ученицу)"""
    if not is_admin(update):
        return
    if not context.args:
        await update.message.reply_text(
            "Как поставить доступ на паузу:\n/pause @username\n\nНапример: /pause @anna_k\n\n"
            "Вернуть доступ: /add @username"
        )
        return
    username = context.args[0].lstrip("@").lower()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM course_students WHERE LOWER(username) = %s", (username,))
            row = cur.fetchone()
            if not row:
                await update.message.reply_text(f"@{username} нет в списке учениц. Список: /students")
                return
            cur.execute("UPDATE course_students SET active = FALSE WHERE id = %s", (row["id"],))
            conn.commit()
    await update.message.reply_text(
        f"⏸ Доступ для @{username} поставлен на паузу.\n"
        f"Остальных учениц это не затрагивает.\n\n"
        f"Вернуть доступ: /add @{username} — прогресс сохранён."
    )


async def cmd_students(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список учениц с прогрессом: /students"""
    if not is_admin(update):
        return
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT s.username, s.chat_id, s.active, s.expires_at,
                       (SELECT MAX(lesson) FROM course_progress p
                        WHERE p.chat_id = s.chat_id AND p.done = TRUE) AS last_lesson
                FROM course_students s
                ORDER BY s.added_at
            """)
            rows = cur.fetchall()
    if not rows:
        await update.message.reply_text("Список учениц пока пуст. Дать доступ: /add @username")
        return
    now = datetime.now(timezone.utc)
    lines = []
    for i, r in enumerate(rows, 1):
        name = f"@{r['username']}" if r["username"] else str(r["chat_id"])
        if r["last_lesson"]:
            progress = f"Урок {r['last_lesson']} пройден"
        elif r["chat_id"]:
            progress = "заходила, уроки не завершала"
        else:
            progress = "ещё не заходила"
        if not r["active"]:
            status = "⏸ на паузе"
        elif r["expires_at"] and r["expires_at"] < now:
            status = "⛔ срок истёк"
        else:
            status = "✅ активна"
            if r["expires_at"]:
                status += f" до {r['expires_at'].strftime('%d.%m.%Y')}"
        lines.append(f"{i}. {name} · {progress} · {status}")
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


# ============ НАПОМИНАНИЯ О СРОКЕ (будильник курса) ============

async def course_loop(bot):
    """Раз в час проверяет: у кого до конца доступа осталось 14 дней —
    и присылает напоминание (один раз каждой)."""
    logger.info("✅ Будильник курса запущен")
    while True:
        try:
            now = datetime.now(timezone.utc)
            remind_edge = now + timedelta(days=REMIND_BEFORE_DAYS)
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id, chat_id, expires_at FROM course_students
                        WHERE active = TRUE AND reminder_sent = FALSE
                          AND chat_id IS NOT NULL AND expires_at IS NOT NULL
                          AND expires_at > %s AND expires_at <= %s
                    """, (now, remind_edge))
                    rows = cur.fetchall()
                for row in rows:
                    try:
                        await bot.send_message(
                            row["chat_id"],
                            f"🔔 Нежное напоминание: доступ к курсу «Квантовый взлёт» "
                            f"открыт до {row['expires_at'].strftime('%d.%m.%Y')}.\n\n"
                            f"Самое время завершить свой путь героя ✨"
                        )
                        with conn.cursor() as cur2:
                            cur2.execute(
                                "UPDATE course_students SET reminder_sent = TRUE WHERE id = %s",
                                (row["id"],)
                            )
                        conn.commit()
                        logger.info(f"🔔 Напоминание о сроке → {row['chat_id']}")
                    except Exception as e:
                        logger.error(f"Ошибка напоминания для {row['chat_id']}: {e}")
        except Exception as e:
            logger.error(f"Ошибка в course_loop: {e}")
        await asyncio.sleep(3600)


# ============ ПОДКЛЮЧЕНИЕ К БОТУ ============

def register(app: Application):
    """Вызывается из bot.py одной строкой"""
    init_course_db()
    app.add_handler(CommandHandler("kurs", cmd_kurs))
    app.add_handler(CommandHandler("add", cmd_add))
    app.add_handler(CommandHandler("pause", cmd_pause))
    app.add_handler(CommandHandler("students", cmd_students))
    app.add_handler(CommandHandler("test", cmd_test))
    app.add_handler(CallbackQueryHandler(cb_dz, pattern=r"^crs_dz_\d+$"))
    app.add_handler(CallbackQueryHandler(cb_done, pattern=r"^crs_done_\d+$"))
    app.add_handler(CallbackQueryHandler(cb_balance, pattern=r"^crs_balance$"))
    logger.info("✅ Курс «Квантовый взлёт» подключён")
