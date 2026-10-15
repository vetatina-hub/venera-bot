import os
import logging
import asyncio
import course
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
LINK_GROUP_WA = "https://chat.whatsapp.com/JdXSf1uFlpwJZwUWBv8GbR"
LINK_KVANT = "https://vetatina-hub.github.io/kvantoviy-vzlet/"
LINK_ALKHIM = "https://vetatina-hub.github.io/alkhimiya-deneg/"
LINK_VENERA = "https://t.me/vetatina"

# ===== ТЕКСТЫ ТРЁХ ПУТЕЙ ПОСЛЕ РЕЗУЛЬТАТА (можно править прямо здесь) =====
PATHS_TEXT = (
    "🌿 А что дальше?\n\n"
    "Вот три пути. Выбери тот, что откликается — подробности откроются по кнопке. "
    "Всё можно сделать и позже."
)

TEXT_MONEY = (
    "💰 Денежный взлёт — 4 990 ₸\n\n"
    "Курс для тех, кто хочет разобраться в своих отношениях с деньгами самостоятельно, "
    "в своём темпе.\n\n"
    "Внутри — 23 урока и практики. Шаг за шагом ты смотришь, какие лояльности и "
    "семейные сценарии мешают деньгам приходить и оставаться, и делаешь практики, "
    "которые возвращают тебе опору.\n\n"
    "Подойдёт, если:\n"
    "• ты уже увидела свой блок в тесте и хочешь работать с ним сама;\n"
    "• тебе удобны небольшие шаги каждый день;\n"
    "• хочешь начать с доступного формата, а не сразу с большого обучения.\n\n"
    "Чтобы получить доступ, напиши Венере — она подскажет, как оплатить, и откроет курс 👇"
)

TEXT_RAZBOR = (
    "🎯 Индивидуальный разбор — 35 000 ₸\n\n"
    "Личная работа с Венерой над одним твоим запросом. Мы смотрим, что именно держит "
    "тебя в этой теме — какая лояльность, какой семейный сценарий — и работаем с этим "
    "в квантовом поле.\n\n"
    "Подойдёт, если:\n"
    "• у тебя есть конкретный запрос: деньги, отношения, реализация;\n"
    "• тебе нужно личное внимание, а не общая программа.\n\n"
    "Один запрос — один разбор: так результат глубже.\n\n"
    "Чтобы записаться, напиши Венере 👇"
)

TEXT_SPACE = (
    "🌀 Пространство трансформации — бесплатно\n\n"
    "Группа, где Венера проводит живые практики и разборы в квантовом поле.\n\n"
    "Что там происходит:\n"
    "• объявления о практиках и разборах;\n"
    "• живая работа — даже если ты просто наблюдаешь как фигура, "
    "ты сама получаешь свою трансформацию в моменте;\n"
    "• ты знакомишься с Венерой и форматом её работы.\n\n"
    "Заходи туда, где тебе теплее: в Telegram или в WhatsApp 👇"
)

# ===== АНОНСЫ ПРАКТИК (приходят прямо перед аудио) =====
DAY_INTRO = {
    1: (
        "🎧 Первая практика: «Родители — источник силы, а не боли»\n\n"
        "Как её слушать:\n"
        "• найди 10 минут, когда тебя никто не отвлечёт;\n"
        "• надень наушники;\n"
        "• сядь удобно и прямо (лёжа легко уснуть);\n"
        "• закрой глаза и просто слушай — ничего не нужно делать «правильно».\n\n"
        "Если появится тепло, слёзы, зевота или сопротивление — это нормально. "
        "Не оценивай, просто наблюдай.\n\n"
        "Что она даёт: помогает мягко посмотреть на родителей без обиды и сравнения "
        "и вернуть себе опору, через которую приходят сила и деньги.\n\n"
        "Практика — следующим сообщением 👇"
    ),
    2: (
        "🎧 Практика Дня 2: «Отец. Принятие. Масштаб»\n\n"
        "Как слушать: наушники, тишина, сидя, глаза закрыты, около 10 минут.\n\n"
        "Эта практика про первую опору — отца. Она помогает увидеть, где внутри остался "
        "перекос, который ограничивает масштаб и доход.\n\n"
        "Если поднимутся чувства — пусть будут. Дыши и слушай.\n\n"
        "Практика — следующим сообщением 👇"
    ),
    3: (
        "🎧 Практика Дня 3: «Деньги по-женски»\n\n"
        "Она не про напряжение и бег, а про состояние: мягкость, лёгкость, доверие потоку.\n\n"
        "Как слушать: наушники, удобная поза, спокойное место. "
        "В конце повтори квант-утверждение вслух — своим голосом, без спешки.\n\n"
        "Практика — следующим сообщением 👇"
    ),
    4: (
        "🎧 Практика Дня 4: «Я беру свою судьбу в свои руки»\n\n"
        "Это последняя практика цикла и самая «взрослая»: про выбор и ответственность "
        "за свою жизнь.\n\n"
        "Как слушать: наушники, тишина, сидя, глаза закрыты, без спешки. "
        "После неё побудь минуту в тишине и заметь, что изменилось.\n\n"
        "Практика — следующим сообщением 👇"
    ),
}

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

Q1, Q2, Q3, Q4, Q5, Q6, GREETING = range(7)

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
            "Ты глубоко чувствуешь людей. Рядом с тёплым, поддерживающим человеком "
            "ты раскрываешься и многое можешь.\n\n"
            "💫 Твоя сила\n"
            "Чуткость, умение выстраивать доверие, способность слышать, что на самом деле нужно другим.\n\n"
            "🔒 Где блок в деньгах\n"
            "Для тебя деньги связаны с безопасностью и поддержкой. Поэтому важные денежные шаги — "
            "поднять цену, начать своё, попросить оплату — ты откладываешь, пока кто-то не скажет "
            "«можно, ты справишься». Пока разрешения нет, ты остаёшься на месте, даже когда уже готова.\n\n"
            "🌱 Что за этим часто стоит\n"
            "Детский опыт, когда тепло и безопасность нужно было искать рядом с кем-то. "
            "Опору, которую мы не получили, мы потом ищем в людях — и ждём её же в деньгах.\n\n"
            "Хорошая новость: опору можно построить внутри себя. Это не значит «справляйся одна». "
            "Это значит — самой давать себе разрешение."
        ),
        "step": (
            "Сегодня прими одно небольшое решение про деньги без чужого совета и одобрения. "
            "Например, реши, на что потратишь определённую сумму, или назови цену своей работы. "
            "Перед этим скажи вслух: «Мне можно выбирать самой»."
        ),
    },
    "Б": {
        "title": "Сама справлюсь 💪",
        "text": (
            "Ты сильная и самостоятельная. Привыкла опираться на себя и доводить дела до конца.\n\n"
            "💫 Твоя сила\n"
            "Дисциплина, воля, умение держать слово и брать ответственность.\n\n"
            "🔒 Где блок в деньгах\n"
            "Ты тянешь всё сама и трудно принимаешь помощь, подарки, поддержку — даже когда они идут "
            "от сердца. А деньги тоже поток, который ты получаешь. Когда внутри закрыто «брать», "
            "поток идёт тонкой струйкой, а силы уходят на то, чтобы держать всё в одиночку.\n\n"
            "🌱 Что за этим часто стоит\n"
            "Старая установка «на других рассчитывать нельзя». Когда-то она помогла справиться, "
            "а сегодня стала потолком: ты держишь на себе слишком много.\n\n"
            "Хорошая новость: уметь брать — такая же сила, как уметь давать. "
            "Ты можешь оставаться сильной и при этом не нести всё одна."
        ),
        "step": (
            "Сегодня попроси о небольшой помощи или прими её — без объяснений и оправданий. "
            "Скажи просто «спасибо». Заметь, что происходит внутри, когда ты принимаешь."
        ),
    },
    "В": {
        "title": "Быть хорошей 🌸",
        "text": (
            "Ты заботливая и отдающая. Чужие нужды для тебя нередко важнее собственных.\n\n"
            "💫 Твоя сила\n"
            "Щедрость, тепло, умение создавать вокруг себя уют и чувство «меня здесь любят».\n\n"
            "🔒 Где блок в деньгах\n"
            "Ты вкладываешь в других, а для себя денег «не остаётся». Тебе неловко назвать цену, "
            "взять оплату, потратить на себя. Внутри звучит: «я не должна быть в приоритете». "
            "Поэтому деньги приходят и уходят к другим.\n\n"
            "🌱 Что за этим часто стоит\n"
            "Опыт, когда любовь нужно было заслужить: быть удобной, правильной, не создавать проблем. "
            "Тогда забота о себе кажется эгоизмом.\n\n"
            "Хорошая новость: можно оставаться доброй и при этом ставить себя на первое место. "
            "Это не отнимает у других — это наполняет тебя, и тогда у тебя есть что давать."
        ),
        "step": (
            "Сегодня отложи небольшую сумму на себя — любую, хоть 1 000 ₸ — раньше, чем потратишь "
            "на других. И скажи себе: «Мне тоже можно»."
        ),
    },
    "Г": {
        "title": "Я достойна большего 👑",
        "text": (
            "Ты чувствуешь свою ценность и знаешь, что способна на большее. "
            "Внутри есть ясное «я хочу и могу».\n\n"
            "💫 Твоя сила\n"
            "Амбиции, самооценка, умение видеть масштаб.\n\n"
            "🔒 Где блок в деньгах\n"
            "Между «хочу» и «получаю» стоит стена. Ты делаешь шаги, а результат будто упирается "
            "в потолок. Часто на этом месте появляется злость: «почему не получается, я же достойна». "
            "Это нередко значит, что где-то внутри есть скрытый запрет, который сильнее желания.\n\n"
            "🌱 Что за этим часто стоит\n"
            "Верность семейному сценарию: «у нас так не было», «мы столько не жили», «не высовывайся». "
            "Тогда успех бессознательно кажется предательством своих.\n\n"
            "Хорошая новость: такие блоки можно найти и снять. Когда причина видна, "
            "энергия, которая шла на борьбу, возвращается тебе."
        ),
        "step": (
            "Возьми лист и запиши: чего я хочу в деньгах и что я делаю прямо сейчас, "
            "чтобы это произошло? Выбери один маленький шаг на сегодня и сделай его."
        ),
    },
    "АГ": {
        "title": "Ищущая признания ✨",
        "text": (
            "Ты хочешь и тепла, и признания своей ценности одновременно. "
            "Тебе важно, чтобы тебя видели и ценили.\n\n"
            "💫 Твоя сила\n"
            "Глубина чувств и амбиции: ты и чувствуешь, и стремишься вверх.\n\n"
            "🔒 Где блок в деньгах\n"
            "Твоё ощущение цены зависит от оценки других. Похвалили — ты на подъёме, "
            "промолчали — засомневалась. Поэтому цена и доход «качаются» вместе с настроением окружающих.\n\n"
            "🌱 Что за этим часто стоит\n"
            "Детская потребность быть увиденной. Пока она закрывается снаружи, "
            "внутренней опоры не хватает.\n\n"
            "Хорошая новость: ценность можно закрепить внутри, независимо от чужих оценок. "
            "Тогда цена и доход перестают «качаться»."
        ),
        "step": (
            "Сегодня сделай одно дело для себя — без публикации, лайков и отчёта кому-либо. "
            "Просто потому, что ты этого достойна."
        ),
    },
    "БГ": {
        "title": "Несущая броню 🛡️",
        "text": (
            "Ты сильная и знаешь себе цену, но закрылась от мира, чтобы больше не было больно.\n\n"
            "💫 Твоя сила\n"
            "Независимость, воля, умение держать удар.\n\n"
            "🔒 Где блок в деньгах\n"
            "Броня, которая защищает от боли, не пропускает и хорошее: деньги, любовь, поддержку. "
            "Ты можешь много зарабатывать и всё равно не чувствовать лёгкости, "
            "потому что «брать» и «доверять» для тебя небезопасно.\n\n"
            "🌱 Что за этим часто стоит\n"
            "Опыт, когда открываться было рискованно. Тогда выжить помогла сила, а мягкость пришлось спрятать.\n\n"
            "Хорошая новость: открыться можно, не теряя силы. Броня была нужна тогда, "
            "а сегодня ты вправе выбирать, когда её снимать."
        ),
        "step": (
            "Сегодня скажи одному близкому человеку одну честную фразу о том, что тебе нужно, "
            "— просто сказать, ничего не требуя. Позволь себе быть чуть мягче."
        ),
    },
    "ВБ": {
        "title": "Несущая мир одна 🕊️",
        "text": (
            "Ты берёшь на себя всё: заботу о других и ответственность за то, что происходит вокруг.\n\n"
            "💫 Твоя сила\n"
            "Стойкость, любовь, надёжность. На тебя можно положиться.\n\n"
            "🔒 Где блок в деньгах\n"
            "Ты несёшь чужое и не оставляешь места для своего. Много отдаёшь, мало получаешь, устаёшь. "
            "Деньги и силы уходят туда, где ты «спасаешь», а на собственную жизнь ресурса уже нет.\n\n"
            "🌱 Что за этим часто стоит\n"
            "Лояльность «лучше я, чем ты»: бессознательное желание взять чужую ношу, "
            "чтобы близким стало легче. Любовь здесь есть, но цена высокая.\n\n"
            "Хорошая новость: можно любить и поддерживать, не неся чужую судьбу. "
            "Каждый несёт своё — и тогда у тебя появляются силы на свою жизнь."
        ),
        "step": (
            "Сегодня откажи в одной небольшой просьбе или передай одно дело другому человеку. "
            "Это не эгоизм, а возвращение ответственности тем, кому она принадлежит."
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
    money_btn = [InlineKeyboardButton("💰 Денежный взлёт — 4 990 ₸", callback_data="path_money")]
    try:
        # Анонс: как слушать и что даёт практика (отдельным сообщением перед аудио)
        intro = DAY_INTRO.get(day)
        if intro:
            try:
                await bot.send_message(chat_id=chat_id, text=intro)
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"❌ Не отправился анонс дня {day} для {chat_id}: {e}")

        if day == 1:
            await bot.send_audio(
                chat_id=chat_id,
                audio=AUDIO_DAY1,
                caption=CAPTION_DAY1,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🌀 Пространство в Telegram", url=LINK_GROUP)],
                    [InlineKeyboardButton("🌀 Пространство в WhatsApp", url=LINK_GROUP_WA)],
                ])
            )
        elif day == 2:
            await bot.send_audio(
                chat_id=chat_id,
                audio=AUDIO_DAY2,
                caption=CAPTION_DAY2,
                reply_markup=InlineKeyboardMarkup([
                    money_btn,
                    [InlineKeyboardButton("🌀 Пространство в Telegram", url=LINK_GROUP)],
                    [InlineKeyboardButton("🌀 Пространство в WhatsApp", url=LINK_GROUP_WA)],
                    [InlineKeyboardButton("✨ Квантовый взлёт", url=LINK_KVANT)],
                ])
            )
        elif day == 3:
            await bot.send_audio(
                chat_id=chat_id,
                audio=AUDIO_DAY3,
                caption=CAPTION_DAY3,
                reply_markup=InlineKeyboardMarkup([
                    money_btn,
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
    # На кнопках только буквы — полный текст ответов лежит в самом сообщении,
    # чтобы на телефоне ничего не обрезалось
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(val, callback_data=val) for label, val in options
    ]])


def question_text(q):
    answers = "\n\n".join(label for label, val in q["options"])
    return q["text"] + "\n\n" + answers + "\n\n👇 Выбери букву"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if args and args[0] == "reels":
        await update.message.reply_text(
            "✨ Привет! Раз ты здесь — что-то из видео зацепило.\n\n"
            "Пройди короткий тест — узнаешь, где сейчас твой главный блок: в деньгах, "
            "отношениях, успехе или здоровье. И что с этим делать.\n\n"
            "2 минуты. Начнём? 👇",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Начать", callback_data="reels_start")
            ]])
        )
        return GREETING
    return await send_first_question(update, context)


async def send_first_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["answers"] = []
    q = QUESTIONS[0]
    await update.message.reply_text(
        "Привет! 👋\n\nЯ помогу тебе узнать твой денежный тип и понять, что мешает деньгам приходить.\n\n"
        "Ответь честно на 6 вопросов — без правильных или неправильных ответов.\n\n" + question_text(q),
        reply_markup=make_keyboard(q["options"])
    )
    return Q1


async def greeting_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["answers"] = []
    q = QUESTIONS[0]
    await query.edit_message_text(
        "Ответь честно на 6 вопросов — без правильных или неправильных ответов.\n\n" + question_text(q),
        reply_markup=make_keyboard(q["options"])
    )
    return Q1


async def handle_q(update: Update, context: ContextTypes.DEFAULT_TYPE, next_state: int, q_index: int):
    query = update.callback_query
    await query.answer()
    context.user_data.setdefault("answers", []).append(query.data)
    if q_index < len(QUESTIONS):
        q = QUESTIONS[q_index]
        await query.edit_message_text(question_text(q), reply_markup=make_keyboard(q["options"]))
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


def paths_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Денежный взлёт — 4 990 ₸", callback_data="path_money")],
        [InlineKeyboardButton("🎯 Индивидуальный разбор — 35 000 ₸", callback_data="path_razbor")],
        [InlineKeyboardButton("🌀 Пространство — бесплатно", callback_data="path_space")],
    ])


async def show_result(query, context: ContextTypes.DEFAULT_TYPE):
    answers = context.user_data.get("answers", [])
    result_key = determine_result(answers)
    result = RESULTS.get(result_key, RESULTS["А"])
    chat_id = query.message.chat_id

    # Планируем практики сразу, чтобы они не потерялись, даже если дальше что-то собьётся
    schedule_user(chat_id)

    # 1) Результат
    await query.edit_message_text(f"✨ Твой тип: {result['title']}\n\n{result['text']}")

    # 2) Шаг на сегодня + предупреждение о практике
    await asyncio.sleep(2)
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"✅ Твой шаг на сегодня\n\n{result['step']}\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🎧 Через пару минут я пришлю тебе первую аудио-практику — не уходи далеко!\n"
            "Впереди 4 дня практик, которые помогут мягко сдвинуть поле."
        )
    )

    # 3) Три пути
    await asyncio.sleep(2)
    await context.bot.send_message(
        chat_id=chat_id,
        text=PATHS_TEXT,
        reply_markup=paths_keyboard()
    )
    return ConversationHandler.END


async def path_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    if query.data == "path_money":
        text = TEXT_MONEY
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("💰 Хочу Денежный взлёт", url=LINK_VENERA)]])
    elif query.data == "path_razbor":
        text = TEXT_RAZBOR
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🎯 Записаться на разбор", url=LINK_VENERA)]])
    else:
        text = TEXT_SPACE
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🌀 Пространство в Telegram", url=LINK_GROUP)],
            [InlineKeyboardButton("🌀 Пространство в WhatsApp", url=LINK_GROUP_WA)],
        ])
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=kb)

def main():
    init_db()
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            GREETING: [CallbackQueryHandler(greeting_start, pattern="^reels_start$")],
            Q1: [CallbackQueryHandler(q1, pattern="^[АБВГ]$")],
            Q2: [CallbackQueryHandler(q2, pattern="^[АБВГ]$")],
            Q3: [CallbackQueryHandler(q3, pattern="^[АБВГ]$")],
            Q4: [CallbackQueryHandler(q4, pattern="^[АБВГ]$")],
            Q5: [CallbackQueryHandler(q5, pattern="^[АБВГ]$")],
            Q6: [CallbackQueryHandler(q6, pattern="^[АБВГ]$")],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    app.add_handler(conv)

    # Кнопки «Денежный взлёт / Разбор / Пространство»
    app.add_handler(CallbackQueryHandler(path_callback, pattern="^path_(money|razbor|space)$"))

    # ✅ Обработчик аудио — показывает file_id
    app.add_handler(MessageHandler(filters.AUDIO | filters.VOICE | filters.Document.ALL, handle_audio))

    # ✅ Курс «Квантовый взлёт» (весь код — в course.py)
    course.register(app)

    async def on_startup(app):
        asyncio.ensure_future(scheduler_loop(app.bot))
        asyncio.ensure_future(course.course_loop(app.bot))
        logger.info("✅ Планировщик запущен")

    app.post_init = on_startup

    logger.info("Бот запущен")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
