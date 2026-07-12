import os
import logging
import asyncio
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters,
    ContextTypes, ConversationHandler
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")

AUDIO_DAY1 = "CQACAgIAAxkBAANtagh5cIL3yA1nQR8rKLAqadhzdY4AAqWfAAIIvUhIiI1CwUPzu4w7BA"
AUDIO_DAY2 = "CQACAgIAAxkBAANuagh5hFRO-fCMyBCUahQCJrjWnPEAAqefAAIIvUhI2o2YSisvMhc7BA"
AUDIO_DAY3 = "CQACAgIAAxkBAANvagh5jD1k50uSW-VmT9OinlJTLaYAAqmfAAIIvUhIw0Or60pgtFE7BA"
AUDIO_DAY4 = "CQACAgIAAxkBAAIBEGpT4PdbiiBP2G1hm1pG70F0PJE_AAIesgAC4l-hSl1T0dFGMRZrPAQ"

LINK_GROUP = "https://t.me/+2v5c8znsaONjY2Fi"
LINK_KVANT = "https://vetatina-hub.github.io/kvantoviy-vzlet/"
LINK_ALKHIM = "https://vetatina-hub.github.io/alkhimiya-deneg/"
LINK_VENERA = "https://t.me/vetatina"

CAPTION_DAY1 = """🌟 Практика Дня 1: «Родители — источник силы, а не боли»

Всем исполнения ваших мечт ❤️

Когда мы смотрим на родителей через боль, обиду, недовольство или сравнение — мы бессознательно закрываем главный источник энергии, через который к нам приходит:

• сила жизни,
• уверенность,
• реализация,
• деньги,
• любовь,
• здоровье.

Не потому что родители идеальны.
А потому что мы через них пришли в этот мир. И поток идёт только через признание.

Как только мы отпускаем оценки и смотрим на факт:
«Они дали мне жизнь — самое дорогое» —
поток силы возвращается.

✨ Если во время практики было тепло, мурашки, слёзы или сопротивление —
это значит, что поток начал включаться.

Хочешь углубить это состояние? Присоединяйся в Пространство трансформации 🌿"""

CAPTION_DAY2 = """🌟 Практика Дня 2: «Отец. Принятие. Масштаб»

Доброе утро ☀️

Женщина может сколько угодно работать над самооценкой,
проходить тренинги, повышать чек, строить стратегию.

Но если внутри она выше отца —
масштаб будет упираться в потолок.

Потому что отец — это первая опора.
Это энергия структуры. Денег. Защиты. Движения вперёд.

Практика:
Закрой глаза. Представь отца. Скажи внутри:
«Папа, я вижу тебя. Ты дал мне жизнь.
Я беру от тебя силу и опору. Спасибо.»

Сделай три глубоких вдоха.

Квантовый взлёт — здесь мы убираем этот перекос навсегда 🌿"""

CAPTION_DAY3 = """🌟 Практика Дня 3: «Деньги по-женски»

Доброе утро ☀️

Деньги по-женски — это не про напряжение и бег.
Это про состояние. Про мягкость. Про внутренний поток.

Квант-утверждение (проговори вслух):
«Я выбираю лёгкость.
Я позволяю себе изобилие и поддержку.
Мой поток приносит мне доход естественно.
Я доверяю — и деньги идут.
Я в своём.»

Ты прошла три дня — это уже начало пути 🌟"""

CAPTION_DAY4 = """🌟 Практика Дня 4: «Я беру свою судьбу в свои руки»

Когда женщина говорит эту фразу — она возвращает себе то, что когда-то отдала:
силу, выбор, ответственность, направление своей жизни.

Эта фраза возвращает тебя:
• в свой путь
• в свою силу
• в свою взрослость
• в свой выбор

И ты начинаешь действовать иначе —
спокойно, уверенно, без страха что «делаешь что-то не так».

🔥 Если ты чувствуешь что наконец хочешь взять свою судьбу в свои руки —
но не понимаешь как это сделать глубоко и без боли —

напиши Венере лично 👇
Она посмотрит твою ситуацию и скажет что именно блокирует твой поток."""

Q1, Q2, Q3, Q4, Q5, Q6 = range(6)

QUESTIONS = [
    {
        "text": "1️⃣ Когда в жизни что-то идёт не так — ваша первая реакция?",
        "options": [
            ("А) Ищу поддержки и тепла рядом", "А"),
            ("Б) Беру себя в руки и действую сама", "Б"),
            ("В) Думаю, как сделать всё правильно", "В"),
            ("Г) Злюсь — я заслуживаю лучшего", "Г"),
        ],
    },
    {
        "text": "2️⃣ Как вы чаще всего относитесь к деньгам?",
        "options": [
            ("А) Хочу, чтобы кто-то помог разобраться", "А"),
            ("Б) Контролирую сама, никому не доверяю", "Б"),
            ("В) Трачу на других, себе — в последнюю очередь", "В"),
            ("Г) Уверена, что достойна большего, но что-то мешает", "Г"),
        ],
    },
    {
        "text": "3️⃣ Ваши отношения с близкими чаще всего:",
        "options": [
            ("А) Ищу принятия и близости", "А"),
            ("Б) Держу дистанцию, опираюсь на себя", "Б"),
            ("В) Стараюсь не создавать конфликтов", "В"),
            ("Г) Чувствую, что меня не ценят по достоинству", "Г"),
        ],
    },
    {
        "text": "4️⃣ Когда вам трудно — вы:",
        "options": [
            ("А) Ищу кого-то, кто выслушает", "А"),
            ("Б) Справляюсь в одиночку, не показываю слабость", "Б"),
            ("В) Продолжаю помогать другим, даже если самой тяжело", "В"),
            ("Г) Понимаю, что снова приходится доказывать свою ценность", "Г"),
        ],
    },
    {
        "text": "5️⃣ Ваша главная боль в теме денег:",
        "options": [
            ("А) Не знаю, как начать — хочу чьей-то помощи", "А"),
            ("Б) Устала тянуть всё сама, но не могу остановиться", "Б"),
            ("В) Вкладываю в других, а для себя — никак", "В"),
            ("Г) Знаю, чего хочу, но что-то постоянно блокирует", "Г"),
        ],
    },
    {
        "text": "6️⃣ Как вы принимаете важные решения?",
        "options": [
            ("А) Советуюсь, жду одобрения", "А"),
            ("Б) Решаю сама, не люблю зависеть", "Б"),
            ("В) Выбираю так, чтобы никого не обидеть", "В"),
            ("Г) Принимаю смело, знаю — я достойна большего", "Г"),
        ],
    },
]

RESULTS = {
    "А": {
        "title": "Ищущая тепло 💙",
        "text": (
            "Ты глубоко чувствующий человек, которому важны принятие и поддержка.\n\n"
            "Твоя сила — в чуткости и умении строить связи.\n"
            "Твой блок — ты ждёшь разрешения от других, чтобы двигаться вперёд.\n\n"
            "Квантовый взлёт даст тебе опору внутри — и деньги потекут из этой новой точки."
        ),
    },
    "Б": {
        "title": "Сама справлюсь 💪",
        "text": (
            "Ты сильная, самостоятельная, привыкла на всё опираться только на себя.\n\n"
            "Твоя сила — в дисциплине и воле.\n"
            "Твой блок — ты не умеешь принимать помощь и закрыта от потока.\n\n"
            "Квантовый взлёт научит тебя получать — и откроет новый уровень дохода."
        ),
    },
    "В": {
        "title": "Быть хорошей 🌸",
        "text": (
            "Ты заботливая и отдающая. Всегда думаешь о других раньше, чем о себе.\n\n"
            "Твоя сила — в щедрости и любви.\n"
            "Твой блок — ты не умеешь ставить себя на первое место.\n\n"
            "Квантовый взлёт вернёт тебе право быть главной в своей жизни."
        ),
    },
    "Г": {
        "title": "Я достойна большего 👑",
        "text": (
            "Ты чувствуешь свою ценность и знаешь, что заслуживаешь большего.\n\n"
            "Твоя сила — в амбициях и самооценке.\n"
            "Твой блок — между желанием и реальностью есть стена.\n\n"
            "Квантовый взлёт покажет корень блока и уберёт его из поля."
        ),
    },
    "АГ": {
        "title": "Ищущая признания ✨",
        "text": (
            "Ты хочешь и тепла, и признания своей ценности — сразу.\n\n"
            "Твоя сила — в глубине чувств и амбициях одновременно.\n"
            "Твой блок — ты зависишь от оценки других.\n\n"
            "Квантовый взлёт освободит тебя от этой зависимости."
        ),
    },
    "БГ": {
        "title": "Несущая броню 🛡️",
        "text": (
            "Ты сильная и знаешь себе цену, но закрылась от мира.\n\n"
            "Твоя сила — в независимости и воле.\n"
            "Твой блок — броня не пускает не только боль, но и деньги, и любовь.\n\n"
            "Квантовый взлёт поможет тебе открыться — не теряя силы."
        ),
    },
    "ВБ": {
        "title": "Несущая мир одна 🕊️",
        "text": (
            "Ты берёшь на себя всё — заботу о других и ответственность за мир вокруг.\n\n"
            "Твоя сила — в стойкости и любви.\n"
            "Твой блок — ты несёшь чужое и не оставляешь место для своего.\n\n"
            "Квантовый взлёт вернёт тебя на своё место — и освободит поток."
        ),
    },
}


def get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_messages (
                    id SERIAL PRIMARY KEY,
                    chat_id BIGINT NOT NULL,
                    day INT NOT NULL,
                    send_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    sent BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            conn.commit()
    logger.info("DB инициализирована")


def schedule_user(chat_id: int):
    now = datetime.now(timezone.utc)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM scheduled_messages WHERE chat_id = %s AND sent = FALSE", (chat_id,))
            # День 1 — через 2 минуты
            cur.execute(
                "INSERT INTO scheduled_messages (chat_id, day, send_at) VALUES (%s, %s, %s)",
                (chat_id, 1, now + timedelta(minutes=2))
            )
            # День 2 — через 24 часа
            cur.execute(
                "INSERT INTO scheduled_messages (chat_id, day, send_at) VALUES (%s, %s, %s)",
                (chat_id, 2, now + timedelta(hours=24))
            )
            # День 3 — через 48 часов
            cur.execute(
                "INSERT INTO scheduled_messages (chat_id, day, send_at) VALUES (%s, %s, %s)",
                (chat_id, 3, now + timedelta(hours=48))
            )
            # День 4 — через 72 часа
            cur.execute(
                "INSERT INTO scheduled_messages (chat_id, day, send_at) VALUES (%s, %s, %s)",
                (chat_id, 4, now + timedelta(hours=72))
            )
            conn.commit()
    logger.info(f"Запланированы практики для {chat_id}")


async def send_day_message(bot, chat_id: int, day: int):
    try:
        if day == 1:
            await bot.send_audio(
                chat_id=chat_id,
                audio=AUDIO_DAY1,
                caption=CAPTION_DAY1,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🌀 Войти в Пространство трансформации", url=LINK_GROUP)],
                ])
            )
        elif day == 2:
            await bot.send_audio(
                chat_id=chat_id,
                audio=AUDIO_DAY2,
                caption=CAPTION_DAY2,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🌀 Войти в Пространство трансформации", url=LINK_GROUP)],
                    [InlineKeyboardButton("✨ Квантовый взлёт", url=LINK_KVANT)],
                ])
            )
        elif day == 3:
            await bot.send_audio(
                chat_id=chat_id,
                audio=AUDIO_DAY3,
                caption=CAPTION_DAY3,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✨ Квантовый взлёт", url=LINK_KVANT)],
                ])
            )
        elif day == 4:
            kb4 = InlineKeyboardMarkup([
                [InlineKeyboardButton("💫 Написать Венере лично", url=LINK_VENERA)],
            ])
            try:
                await bot.send_audio(
                    chat_id=chat_id,
                    audio=AUDIO_DAY4,
                    caption=CAPTION_DAY4,
                    reply_markup=kb4
                )
            except Exception:
                # если file_id сохранён как документ — отправляем как документ
                await bot.send_document(
                    chat_id=chat_id,
                    document=AUDIO_DAY4,
                    caption=CAPTION_DAY4,
                    reply_markup=kb4
                )
        logger.info(f"✅ Отправлена практика дня {day} → {chat_id}")
    except Exception as e:
        logger.error(f"❌ Ошибка отправки дня {day} для {chat_id}: {e}")


# ✅ Логирование file_id любого аудио/файла отправленного боту
async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    media = msg.audio or msg.voice or msg.document
    if media:
        kind = "audio" if msg.audio else ("voice" if msg.voice else "document")
        logger.info(f"🎵 FILE_ID ({kind}): {media.file_id}")
        await msg.reply_text(f"Тип: {kind}\nfile_id:\n{media.file_id}")


async def scheduler_loop(bot):
    logger.info("✅ Планировщик практик запущен")
    while True:
        try:
            now = datetime.now(timezone.utc)
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id, chat_id, day FROM scheduled_messages
                        WHERE sent = FALSE AND send_at <= %s
                    """, (now,))
                    rows = cur.fetchall()

                for row in rows:
                    await send_day_message(bot, row["chat_id"], row["day"])
                    with conn.cursor() as cur2:
                        cur2.execute(
                            "UPDATE scheduled_messages SET sent = TRUE WHERE id = %s",
                            (row["id"],)
                        )
                    conn.commit()

        except Exception as e:
            logger.error(f"Ошибка в scheduler_loop: {e}")

        await asyncio.sleep(60)


def determine_result(answers: list) -> str:
    from collections import Counter
    c = Counter(answers)
    top = c.most_common()
    if not top:
        return "А"
    max_count = top[0][1]
    leaders = [k for k, v in c.items() if v == max_count]
    if len(leaders) == 1:
        return leaders[0]
    pair = tuple(sorted(leaders[:2]))
    combos = {("А", "Г"): "АГ", ("Б", "Г"): "БГ", ("Б", "В"): "ВБ"}
    return combos.get(pair, leaders[0])


def make_keyboard(options):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data=val)] for label, val in options
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["answers"] = []
    q = QUESTIONS[0]
    await update.message.reply_text(
        "Привет! 👋\n\nЯ помогу тебе узнать твой денежный тип и понять, что мешает деньгам приходить.\n\n"
        "Ответь честно на 6 вопросов — без правильных или неправильных ответов.\n\n" + q["text"],
        reply_markup=make_keyboard(q["options"])
    )
    return Q1


async def handle_q(update: Update, context: ContextTypes.DEFAULT_TYPE, next_state: int, q_index: int):
    query = update.callback_query
    await query.answer()
    context.user_data.setdefault("answers", []).append(query.data)
    if q_index < len(QUESTIONS):
        q = QUESTIONS[q_index]
        await query.edit_message_text(q["text"], reply_markup=make_keyboard(q["options"]))
        return next_state
    return await show_result(query, context)


async def q1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await handle_q(update, context, Q2, 1)

async def q2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await handle_q(update, context, Q3, 2)

async def q3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await handle_q(update, context, Q4, 3)

async def q4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await handle_q(update, context, Q5, 4)

async def q5(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await handle_q(update, context, Q6, 5)

async def q6(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.setdefault("answers", []).append(query.data)
    return await show_result(query, context)


async def show_result(query, context: ContextTypes.DEFAULT_TYPE):
    answers = context.user_data.get("answers", [])
    result_key = determine_result(answers)
    result = RESULTS.get(result_key, RESULTS["А"])

    text = (
        f"✨ Твой тип: {result['title']}\n\n"
        f"{result['text']}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎁 Уже через пару минут я пришлю тебе первую аудио практику — не уходи далеко!\n\n"
        f"Впереди 4 дня практик, которые помогут сдвинуть поле.\n\n"
        f"🌀 А ещё тебя ждёт Пространство трансформации — живой чат, где проходят разборы. "
        f"Ты можешь участвовать в них фигурой: стоя в поле, ты получаешь свои осознания "
        f"и свои трансформации — даже в чужом разборе. Вход свободный 👇"
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🌀 Войти в Пространство трансформации", url=LINK_GROUP)
        ]])
    )

    chat_id = query.message.chat_id
    schedule_user(chat_id)
    return ConversationHandler.END


def main():
    init_db()
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            Q1: [CallbackQueryHandler(q1)],
            Q2: [CallbackQueryHandler(q2)],
            Q3: [CallbackQueryHandler(q3)],
            Q4: [CallbackQueryHandler(q4)],
            Q5: [CallbackQueryHandler(q5)],
            Q6: [CallbackQueryHandler(q6)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    app.add_handler(conv)

    # ✅ Обработчик аудио — показывает file_id
    app.add_handler(MessageHandler(filters.AUDIO | filters.VOICE | filters.Document.ALL, handle_audio))

    async def on_startup(app):
        asyncio.ensure_future(scheduler_loop(app.bot))
        logger.info("✅ Планировщик запущен")

    app.post_init = on_startup

    logger.info("Бот запущен")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
