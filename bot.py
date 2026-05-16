import os
import logging
from datetime import timedelta
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

AUDIO_DAY1 = "CQACAgIAAxkBAANtagh5cIL3yA1nQR8rKLAqadhzdY4AAqWfAAIIvUhIiI1CwUPzu4w7BA"
AUDIO_DAY2 = "CQACAgIAAxkBAANuagh5hFRO-fCMyBCUahQCJrjWnPEAAqefAAIIvUhI2o2YSisvMhc7BA"
AUDIO_DAY3 = "CQACAgIAAxkBAANvagh5jD1k50uSW-VmT9OinlJTLaYAAqmfAAIIvUhIw0Or60pgtFE7BA"

LINK_GROUP = "https://t.me/+2v5c8znsaONjY2Fi"
LINK_COURSE = "https://vetatina-hub.github.io/kvantoviy-vzlet/"

QUESTIONS = [
    {
        "text": "1️⃣ Когда тебе плохо, что ты делаешь в первую очередь?",
        "options": [
            "А) Ищу, кто меня выслушает и поддержит",
            "Б) Стараюсь разобраться сам(а) и решить",
            "В) Думаю, как не расстроить близких",
            "Г) Злюсь, что этого не должно было случиться"
        ]
    },
    {
        "text": "2️⃣ Как ты относишься к просьбам о помощи?",
        "options": [
            "А) Мне важно, чтобы мне помогли — иначе чувствую себя одиноким(ой)",
            "Б) Лучше сам(а) — так надёжнее",
            "В) Стесняюсь просить, боюсь быть в тягость",
            "Г) Считаю, что заслуживаю помощи, но редко её получаю"
        ]
    },
    {
        "text": "3️⃣ Что ты чувствуешь в отношениях чаще всего?",
        "options": [
            "А) Страх потерять близкого человека",
            "Б) Усталость от того, что всё на мне",
            "В) Тревогу — а вдруг я недостаточно хорош(а)?",
            "Г) Ощущение, что меня не ценят так, как я того достоин(на)"
        ]
    },
    {
        "text": "4️⃣ Как ты реагируешь на конфликт?",
        "options": [
            "А) Стараюсь помириться как можно быстрее — не выношу напряжения",
            "Б) Замыкаюсь, справляюсь сам(а) со своей болью",
            "В) Извиняюсь, даже если не виноват(а)",
            "Г) Чувствую несправедливость и долго не могу отпустить"
        ]
    },
    {
        "text": "5️⃣ Что тебе больше всего мешает двигаться вперёд?",
        "options": [
            "А) Страх остаться без поддержки",
            "Б) Привычка всё тянуть на себе",
            "В) Желание быть удобным(ой) для всех",
            "Г) Ощущение, что окружающие не дотягивают до тебя"
        ]
    },
    {
        "text": "6️⃣ Какое желание у тебя самое глубокое?",
        "options": [
            "А) Чтобы меня любили и не уходили",
            "Б) Наконец выдохнуть и не быть за всё ответственным(ой)",
            "В) Быть собой и не бояться осуждения",
            "Г) Получить то, чего действительно заслуживаю"
        ]
    }
]

RESULTS = {
    "А": {
        "title": "💙 Ищущий(ая) тепло",
        "text": "Ты глубоко чувствующий человек, для которого близость и принятие — главная ценность. Твоя сила — в умении любить. Но страх потери иногда заставляет цепляться там, где нужно отпустить. Венера поможет тебе найти опору внутри себя."
    },
    "Б": {
        "title": "💪 Сам(а) справлюсь",
        "text": "Ты привык(ла) быть сильным(ой) и надёжным(ой). Несёшь много — и делаешь это достойно. Но за этой силой прячется усталость и желание, чтобы кто-то наконец позаботился о тебе. Пора научиться принимать, а не только отдавать."
    },
    "В": {
        "title": "🌸 Быть хорошим(ей)",
        "text": "Ты чуткий(ая), внимательный(ая), всегда думаешь о других. Твоя доброта — это дар. Но где-то внутри живёт страх: а если я не понравлюсь? Венера поможет тебе полюбить себя таким(ой), какой ты есть — без масок."
    },
    "Г": {
        "title": "👑 Я достоин(на) большего",
        "text": "Ты знаешь себе цену — и это прекрасно. Ты чувствуешь несоответствие между тем, что имеешь, и тем, чего заслуживаешь. Венера поможет убрать внутренние блоки и открыть путь к тому, что тебе действительно принадлежит."
    },
    "АГ": {
        "title": "✨ Ищущий(ая) признания",
        "text": "Тебе важно и тепло, и признание — ты хочешь быть любимым(ой) и ценимым(ой) одновременно. Это глубокая потребность, которая ведёт к большой любви. Венера поможет тебе привлекать людей, которые видят твою настоящую ценность."
    },
    "БГ": {
        "title": "🛡️ Несущий(ая) броню",
        "text": "Ты сильный(ая) снаружи и ранимый(ая) внутри. Научился(ась) защищаться, но за бронёй скрывается желание, чтобы тебя наконец увидели и оценили. Венера поможет снять защиту там, где она уже не нужна."
    },
    "ВБ": {
        "title": "🕊️ Несущий(ая) мир один(а)",
        "text": "Ты держишь гармонию вокруг себя, часто в ущерб себе. Несёшь тяжесть отношений и при этом боишься быть собой. Венера поможет тебе найти баланс между заботой о других и любовью к себе."
    }
}

Q1, Q2, Q3, Q4, Q5, Q6 = range(6)


def get_keyboard(options):
    return ReplyKeyboardMarkup([[opt] for opt in options], resize_keyboard=True, one_time_keyboard=True)


def get_group_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🌸 Войти в Пространство трансформации", url=LINK_GROUP)
    ]])


def get_course_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌸 Войти в Пространство трансформации", url=LINK_GROUP)],
        [InlineKeyboardButton("✨ Узнать о курсе Квантовый взлёт", url=LINK_COURSE)]
    ])


def determine_result(answers):
    counts = {"А": 0, "Б": 0, "В": 0, "Г": 0}
    for a in answers:
        letter = a[0]
        if letter in counts:
            counts[letter] += 1

    max_count = max(counts.values())
    leaders = [k for k, v in counts.items() if v == max_count]

    if len(leaders) == 1:
        return RESULTS.get(leaders[0], RESULTS["А"])

    pair = "".join(sorted(leaders[:2]))
    if pair in RESULTS:
        return RESULTS[pair]

    return RESULTS[leaders[0]]


async def send_day1(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "🌿 День 1. Практика для тебя\n\n"
            "«Родители — источник силы, а не боли»\n\n"
            "Когда мы смотрим на родителей через боль, обиду или сравнение — "
            "мы бессознательно закрываем главный источник энергии: "
            "силы жизни, уверенности, денег, любви и здоровья.\n\n"
            "Не потому что родители идеальны.\n"
            "А потому что мы через них пришли в этот мир. "
            "И поток идёт только через признание.\n\n"
            "Послушай практику 👇 и позволь потоку включиться."
        )
    )
    await context.bot.send_audio(chat_id=chat_id, audio=AUDIO_DAY1)
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "✨ Если во время практики было тепло, мурашки, ком в горле или слёзы — "
            "это значит, что поток начал включаться.\n\n"
            "Завтра пришлю вторую практику 💙\n\n"
            "А пока — присоединяйся в наше бесплатное пространство, "
            "где такие практики проходят вживую:"
        ),
        reply_markup=get_group_keyboard()
    )


async def send_day2(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "🌿 День 2. Практика для тебя\n\n"
            "«Отец. Принятие. Масштаб»\n\n"
            "Можно сколько угодно работать над собой, повышать доход, строить стратегию.\n"
            "Но если внутри ты выше отца — масштаб будет упираться в потолок.\n\n"
            "Потому что отец — это первая опора. "
            "Это энергия структуры, денег, защиты и движения вперёд.\n\n"
            "Когда отец в сердце — человек не воюет.\n"
            "Он идёт. Спокойно. С достоинством. Без доказательств.\n\n"
            "Послушай практику 👇"
        )
    )
    await context.bot.send_audio(chat_id=chat_id, audio=AUDIO_DAY2)
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "После настоящего принятия отца резко растёт доход — "
            "уходит скрытая конкуренция, снимается запрет «не быть больше него», "
            "возвращается опора за спиной.\n\n"
            "Завтра пришлю последнюю практику ✨"
        ),
        reply_markup=get_group_keyboard()
    )


async def send_day3(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "🌿 День 3. Практика для тебя\n\n"
            "«Деньги по-женски»\n\n"
            "Деньги по-женски — это не про напряжение и бег.\n"
            "Это про состояние. Про мягкость. Про внутренний поток.\n\n"
            "Когда человек в своей природе — деньги приходят не за усилие, "
            "а за присутствие. За энергию. За чистоту.\n\n"
            "Послушай практику 👇 и проговори вслух:\n\n"
            "«Я выбираю лёгкость. Я позволяю себе изобилие.\n"
            "Мой поток приносит мне доход естественно.\n"
            "Я доверяю — и деньги идут. Я в своём.»"
        )
    )
    await context.bot.send_audio(chat_id=chat_id, audio=AUDIO_DAY3)
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "🌟 Ты прошёл(а) три дня — это уже начало пути!\n\n"
            "Если чувствуешь, что хочешь идти глубже — "
            "Квантовый взлёт открыт для тебя.\n\n"
            "Там мы работаем с этим мягко, бережно и глубоко — "
            "через законы квантового поля и системные расстановки."
        ),
        reply_markup=get_course_keyboard()
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["answers"] = []
    await update.message.reply_text(
        "Привет! 🌟 Я помогу тебе узнать, какой паттерн управляет твоей жизнью и отношениями.\n\n"
        "Отвечай честно — здесь нет правильных или неправильных ответов. "
        "Это займёт всего 2 минуты 💫\n\n" + QUESTIONS[0]["text"],
        reply_markup=get_keyboard(QUESTIONS[0]["options"])
    )
    return Q1


async def q1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["answers"].append(update.message.text)
    await update.message.reply_text(QUESTIONS[1]["text"], reply_markup=get_keyboard(QUESTIONS[1]["options"]))
    return Q2


async def q2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["answers"].append(update.message.text)
    await update.message.reply_text(QUESTIONS[2]["text"], reply_markup=get_keyboard(QUESTIONS[2]["options"]))
    return Q3


async def q3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["answers"].append(update.message.text)
    await update.message.reply_text(QUESTIONS[3]["text"], reply_markup=get_keyboard(QUESTIONS[3]["options"]))
    return Q4


async def q4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["answers"].append(update.message.text)
    await update.message.reply_text(QUESTIONS[4]["text"], reply_markup=get_keyboard(QUESTIONS[4]["options"]))
    return Q5


async def q5(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["answers"].append(update.message.text)
    await update.message.reply_text(QUESTIONS[5]["text"], reply_markup=get_keyboard(QUESTIONS[5]["options"]))
    return Q6


async def q6(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["answers"].append(update.message.text)
    answers = context.user_data.get("answers", [])
    result = determine_result(answers)
    chat_id = update.effective_chat.id

    await update.message.reply_text(
        f"🔮 Твой тип: {result['title']}\n\n{result['text']}\n\n"
        f"Я подготовила для тебя практику на каждый день — она поможет начать работу прямо сейчас. "
        f"Завтра пришлю первую 🌟\n\n"
        f"А пока — присоединяйся в бесплатное пространство, "
        f"где практики проходят вживую с разборами и медитациями:",
        reply_markup=get_group_keyboard()
    )

    context.job_queue.run_once(send_day1, when=timedelta(hours=24), chat_id=chat_id, name=f"day1_{chat_id}")
    context.job_queue.run_once(send_day2, when=timedelta(hours=48), chat_id=chat_id, name=f"day2_{chat_id}")
    context.job_queue.run_once(send_day3, when=timedelta(hours=72), chat_id=chat_id, name=f"day3_{chat_id}")

    return ConversationHandler.END


async def get_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.voice:
        await update.message.reply_text(f"file_id: {update.message.voice.file_id}")
    elif update.message.audio:
        await update.message.reply_text(f"file_id: {update.message.audio.file_id}")
    elif update.message.document:
        await update.message.reply_text(f"file_id: {update.message.document.file_id}")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("До встречи! 🌸", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            Q1: [MessageHandler(filters.TEXT & ~filters.COMMAND, q1)],
            Q2: [MessageHandler(filters.TEXT & ~filters.COMMAND, q2)],
            Q3: [MessageHandler(filters.TEXT & ~filters.COMMAND, q3)],
            Q4: [MessageHandler(filters.TEXT & ~filters.COMMAND, q4)],
            Q5: [MessageHandler(filters.TEXT & ~filters.COMMAND, q5)],
            Q6: [MessageHandler(filters.TEXT & ~filters.COMMAND, q6)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.AUDIO | filters.VOICE | filters.Document.ALL, get_file_id))
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
