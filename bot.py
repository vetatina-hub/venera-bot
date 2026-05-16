import os
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

QUESTIONS = [
    {
        "text": "1️⃣ Когда тебе плохо, что ты делаешь в первую очередь?",
        "options": [
            "А) Ищу, кто меня выслушает и поддержит",
            "Б) Стараюсь разобраться сама и решить",
            "В) Думаю, как не расстроить близких",
            "Г) Злюсь, что этого не должно было случиться"
        ]
    },
    {
        "text": "2️⃣ Как ты относишься к просьбам о помощи?",
        "options": [
            "А) Мне важно, чтобы мне помогли — иначе чувствую себя одинокой",
            "Б) Лучше сама — так надёжнее",
            "В) Стесняюсь просить, боюсь быть в тягость",
            "Г) Считаю, что заслуживаю помощи, но редко её получаю"
        ]
    },
    {
        "text": "3️⃣ Что ты чувствуешь в отношениях чаще всего?",
        "options": [
            "А) Страх потерять близкого человека",
            "Б) Усталость от того, что всё на мне",
            "В) Тревогу — а вдруг я недостаточно хороша?",
            "Г) Ощущение, что меня не ценят так, как я того достойна"
        ]
    },
    {
        "text": "4️⃣ Как ты реагируешь на конфликт?",
        "options": [
            "А) Стараюсь помириться как можно быстрее — не выношу напряжения",
            "Б) Замыкаюсь, справляюсь сама со своей болью",
            "В) Извиняюсь, даже если не виновата",
            "Г) Чувствую несправедливость и долго не могу отпустить"
        ]
    },
    {
        "text": "5️⃣ Что тебе больше всего мешает двигаться вперёд?",
        "options": [
            "А) Страх остаться без поддержки",
            "Б) Привычка всё тянуть на себе",
            "В) Желание быть удобной для всех",
            "Г) Ощущение, что окружающие не дотягивают до тебя"
        ]
    },
    {
        "text": "6️⃣ Какое желание у тебя самое глубокое?",
        "options": [
            "А) Чтобы меня любили и не уходили",
            "Б) Наконец выдохнуть и не быть за всё ответственной",
            "В) Быть собой и не бояться осуждения",
            "Г) Получить то, чего действительно заслуживаю"
        ]
    }
]

RESULTS = {
    "А": {
        "title": "💙 Ищущая тепло",
        "text": "Ты глубоко чувствующий человек, для которого близость и принятие — главная ценность. Твоя сила — в умении любить. Но страх потери иногда заставляет цепляться там, где нужно отпустить. Венера поможет тебе найти опору внутри себя."
    },
    "Б": {
        "title": "💪 Сама справлюсь",
        "text": "Ты привыкла быть сильной и надёжной. Несёшь много — и делаешь это достойно. Но за этой силой прячется усталость и желание, чтобы кто-то наконец позаботился о тебе. Пора научиться принимать, а не только отдавать."
    },
    "В": {
        "title": "🌸 Быть хорошей",
        "text": "Ты чуткая, внимательная, всегда думаешь о других. Твоя доброта — это дар. Но где-то внутри живёт страх: а если я не понравлюсь? Венера поможет тебе полюбить себя такой, какая ты есть — без масок."
    },
    "Г": {
        "title": "👑 Я достойна большего",
        "text": "Ты знаешь себе цену — и это прекрасно. Ты чувствуешь несоответствие между тем, что имеешь, и тем, чего заслуживаешь. Венера поможет убрать внутренние блоки и открыть путь к тому, что тебе действительно принадлежит."
    },
    "АГ": {
        "title": "✨ Ищущая признания",
        "text": "Тебе важно и тепло, и признание — ты хочешь быть любимой и ценимой одновременно. Это глубокая потребность, которая ведёт к большой любви. Венера поможет тебе привлекать людей, которые видят твою настоящую ценность."
    },
    "БГ": {
        "title": "🛡️ Несущая броню",
        "text": "Ты сильная снаружи и ранимая внутри. Научилась защищаться, но за бронёй скрывается желание, чтобы тебя наконец увидели и оценили. Венера поможет снять защиту там, где она уже не нужна."
    },
    "ВБ": {
        "title": "🕊️ Несущая мир одна",
        "text": "Ты держишь гармонию вокруг себя, часто в ущерб себе. Несёшь тяжесть отношений и при этом боишься быть собой. Венера поможет тебе найти баланс между заботой о других и любовью к себе."
    }
}

Q1, Q2, Q3, Q4, Q5, Q6 = range(6)


def get_keyboard(options):
    return ReplyKeyboardMarkup([[opt] for opt in options], resize_keyboard=True, one_time_keyboard=True)


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

    await update.message.reply_text(
        f"🔮 Твой тип: {result['title']}\n\n{result['text']}\n\n"
        f"Хочешь разобраться глубже и изменить эти паттерны?\n"
        f"Напиши Венере лично 👉 @vetatina",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


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
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

