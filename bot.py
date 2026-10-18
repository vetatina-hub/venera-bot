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
LINK_KASPI_MONEY = "https://pay.kaspi.kz/pay/pyquwzeb"  # оплата Денежного взлёта, 4 990 ₸

# ===== ТЕКСТЫ ТРЁХ ПУТЕЙ ПОСЛЕ РЕЗУЛЬТАТА (можно править прямо здесь) =====
PATHS_TEXT = (
    "🌿 А что дальше?\n\n"
    "Вот три пути. Выбери тот, что откликается:\n\n"
    "💰 Денежный взлёт — 4 990 ₸\n"
    "Курс по финансовой грамотности: от финансового хаоса к ясности и контролю. "
    "Больше 20 уроков с заданиями: наводишь порядок в долгах, доходах и расходах "
    "и находишь свои идеи роста дохода — самостоятельно, в своём темпе.\n\n"
    "🎯 Индивидуальный разбор — 35 000 ₸\n"
    "Личная работа с Венерой над одним твоим запросом. Мы находим корень блока — ту точку "
    "в твоей семье и роду, откуда он растёт, — и убираем его в квантовом поле. "
    "Не борьба со следствиями, а работа с причиной. Один запрос — один разбор, поэтому результат глубже.\n\n"
    "🌀 Пространство трансформации — бесплатно\n"
    "Закрытая группа Венеры: живые практики и разборы в квантовом поле. Можно просто наблюдать — "
    "даже как фигура ты получаешь свою трансформацию в моменте. Лучший способ познакомиться "
    "с Венерой и её работой без вложений.\n\n"
    "Нажми на кнопку — расскажу подробнее 👇"
)

TEXT_MONEY = (
    "💰 Денежный взлёт — 4 990 ₸\n\n"
    "Курс по финансовой грамотности: от финансового хаоса к ясности, порядку и контролю. "
    "Больше 20 уроков с заданиями — каждый урок опирается на предыдущий.\n\n"
    "Что внутри:\n"
    "• честный список долгов и как договориться и с теми, кому ты должна, и с теми, кто должен тебе;\n"
    "• план закрытия долгов «от мелкого к крупному» и система накопления;\n"
    "• твой реальный доход, полный список расходов и баланс: в плюсе ты или в минусе;\n"
    "• 7 идей дохода без вложений и ежедневные действия на рост дохода;\n"
    "• состояние, в котором деньги приходят, и законы квантового поля о деньгах — с медитациями.\n\n"
    "Подойдёт, если:\n"
    "• в деньгах хаос, и хочется навести порядок;\n"
    "• есть долги или кредиты, и хочется жить без них;\n"
    "• хочешь понимать свои реальные доходы и расходы.\n\n"
    "Оплатить можно по кнопке ниже. После оплаты напиши Венере — она откроет доступ к курсу 👇"
)

TEXT_RAZBOR = (
    "🎯 Индивидуальный разбор — 35 000 ₸\n\n"
    "Личная работа с Венерой над одним твоим запросом: деньги, отношения, реализация.\n\n"
    "Как это устроено:\n"
    "• ты называешь один запрос — то, что болит сильнее всего;\n"
    "• мы находим корень: какая семейная программа за ним стоит и откуда она пришла в твою жизнь;\n"
    "• убираем этот корень в квантовом поле.\n\n"
    "Почему один запрос — один разбор: у любой темы один корень, а всё остальное — его следствия. "
    "Когда работаем с корнем, а не со следствиями, результат глубже.\n\n"
    "Подойдёт, если:\n"
    "• ты уже видишь свой блок и хочешь личного внимания, а не общей программы;\n"
    "• тебе важно разобраться именно в своей истории.\n\n"
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
        "Это подарок после теста: короткая аудио-практика примерно на 10 минут.\n\n"
        "Как её слушать:\n"
        "• найди 10 минут, когда тебя никто не отвлечёт;\n"
        "• надень наушники;\n"
        "• сядь удобно и прямо (лёжа легко уснуть);\n"
        "• закрой глаза и просто слушай — ничего не нужно делать «правильно».\n\n"
        "Если появится тепло, слёзы, зевота или сопротивление — это нормально. "
        "Не оценивай, просто наблюдай.\n\n"
        "Что она даёт: помогает мягко посмотреть на родителей без обиды и сравнения "
        "и вернуть себе опору, через которую приходят сила и деньги.\n\n"
        "Практика — следующим сообщением 👇\n\n"
        "А если хочется быть среди людей, которые проходят такие практики вместе, "
        "заходи в Пространство трансформации: там бесплатно, живые практики и разборы 🌿"
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
        "🎧 Вторая практика: «Деньги по-женски»\n\n"
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

CAPTION_DAY3 = """🌟 Вторая практика: «Деньги по-женски»

Доброе утро ☀️

Деньги по-женски — это не про напряжение и бег.
Это про состояние. Про мягкость. Про внутренний поток.

Квант-утверждение (проговори вслух):
«Я выбираю лёгкость.
Я позволяю себе изобилие и поддержку.
Мой поток приносит мне доход естественно.
Я доверяю — и деньги идут.
Я в своём.»

Это уже начало пути 🌟"""

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
            "Программа «лучше я, чем ты»: бессознательное желание взять чужую ношу, "
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
            cur.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id SERIAL PRIMARY KEY,
                    chat_id BIGINT NOT NULL,
                    kind TEXT NOT NULL,
                    source TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_sources (
                    chat_id BIGINT PRIMARY KEY,
                    source TEXT
                )
            """)
            conn.commit()
    logger.info("DB инициализирована")


def get_admin_chat():
    """Чат Венеры, куда бот присылает заявки (задаётся командой /admin)"""
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT value FROM settings WHERE key = 'admin_chat'")
                row = cur.fetchone()
                return int(row["value"]) if row else None
    except Exception as e:
        logger.error(f"Не удалось прочитать admin_chat: {e}")
        return None


def set_admin_chat(chat_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO settings (key, value) VALUES ('admin_chat', %s) "
                "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                (str(chat_id),)
            )
            conn.commit()


def set_source(chat_id: int, source: str):
    """Запоминает, откуда пришёл человек: reels, ads, dengi или organic"""
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO user_sources (chat_id, source) VALUES (%s, %s) "
                    "ON CONFLICT (chat_id) DO UPDATE SET source = EXCLUDED.source",
                    (chat_id, source)
                )
                conn.commit()
    except Exception as e:
        logger.error(f"set_source: {e}")


def log_event(chat_id: int, kind: str):
    """Записывает событие для статистики. Ошибки не мешают работе бота."""
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT source FROM user_sources WHERE chat_id = %s", (chat_id,))
                row = cur.fetchone()
                source = row["source"] if row else "organic"
                cur.execute(
                    "INSERT INTO events (chat_id, kind, source) VALUES (%s, %s, %s)",
                    (chat_id, kind, source)
                )
                conn.commit()
    except Exception as e:
        logger.error(f"log_event: {e}")


def who(user) -> str:
    if user is None:
        return "—"
    name = " ".join(x for x in [user.first_name, user.last_name] if x) or "Без имени"
    uname = f"@{user.username}" if user.username else "без username"
    return f"{name} ({uname}, id {user.id})"


async def notify_admin(bot, text: str):
    """Присылает Венере сообщение о клиенте. Ошибки не мешают работе бота."""
    chat = get_admin_chat()
    if not chat:
        return
    try:
        await bot.send_message(chat_id=chat, text=text)
    except Exception as e:
        logger.error(f"Не удалось отправить уведомление админу: {e}")


def schedule_user(chat_id: int):
    now = datetime.now(timezone.utc)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM scheduled_messages WHERE chat_id = %s AND sent = FALSE", (chat_id,))
            # 1 — практика в подарок, через 10 минут
            cur.execute(
                "INSERT INTO scheduled_messages (chat_id, day, send_at) VALUES (%s, %s, %s)",
                (chat_id, 1, now + timedelta(minutes=10))
            )
            # 2 — «что заметила», второй тест и приглашения, через 24 часа
            cur.execute(
                "INSERT INTO scheduled_messages (chat_id, day, send_at) VALUES (%s, %s, %s)",
                (chat_id, 2, now + timedelta(hours=24))
            )
            # 3 — вторая практика, мягкий рассказ о Денежном взлёте, Пространство и диагностика, через 72 часа
            cur.execute(
                "INSERT INTO scheduled_messages (chat_id, day, send_at) VALUES (%s, %s, %s)",
                (chat_id, 3, now + timedelta(hours=72))
            )
            conn.commit()
    logger.info(f"Запланированы сообщения для {chat_id}")


DAY2_CHECKIN = (
    "Как ты? 🌿\n\n"
    "Что ты заметила за этот день — в мыслях, в теле, в отношениях с деньгами или близкими? "
    "Иногда самое важное видно именно в мелочах.\n\n"
    "Если интересно, есть второй короткий тест: «Скрытая денежная программа». "
    "10 вопросов, около 3 минут. Он показывает, какая программа из семьи может стоять "
    "за твоим отношением к деньгам.\n\n"
    "А чтобы увидеть, что стоит именно за твоей ситуацией, есть личная диагностика. "
    "Пока идёт акция, она бесплатная."
)

DAY3_MONEY_SOFT = (
    "Если хочется навести порядок в деньгах на практике, есть курс по финансовой "
    "грамотности «Денежный взлёт» — 4 990 ₸. В нём уроки с заданиями про долги, доходы и "
    "расходы, идеи роста дохода и медитации. Проходишь сама, в своём темпе.\n\n"
    "А если хочется увидеть, что стоит именно за твоей ситуацией, есть бесплатная "
    "диагностика. Или просто загляни в Пространство трансформации 👇"
)


async def send_day_message(bot, chat_id: int, day: int):
    try:
        if day == 1:
            await bot.send_message(chat_id=chat_id, text=DAY_INTRO[1])
            await asyncio.sleep(1)
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
            await bot.send_message(
                chat_id=chat_id,
                text=DAY2_CHECKIN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔎 Пройти тест про деньги", callback_data="ml_start")],
                    [InlineKeyboardButton("💰 Денежный взлёт — 4 990 ₸", callback_data="path_money")],
                    [InlineKeyboardButton("🔎 Записаться на диагностику", callback_data="diag_signup")],
                    [InlineKeyboardButton("🌀 Пространство в Telegram", url=LINK_GROUP)],
                ])
            )
        elif day == 3:
            await bot.send_message(chat_id=chat_id, text=DAY_INTRO[3])
            await asyncio.sleep(1)
            await bot.send_audio(
                chat_id=chat_id,
                audio=AUDIO_DAY3,
                caption=CAPTION_DAY3,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🌀 Пространство в Telegram", url=LINK_GROUP)],
                ])
            )
            await asyncio.sleep(2)
            await bot.send_message(
                chat_id=chat_id,
                text=DAY3_MONEY_SOFT,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💰 Денежный взлёт — 4 990 ₸", callback_data="path_money")],
                    [InlineKeyboardButton("🔎 Записаться на диагностику", callback_data="diag_signup")],
                    [InlineKeyboardButton("🌀 Пространство в Telegram", url=LINK_GROUP)],
                ])
            )
        else:
            # дни 4 и далее из старой серии больше не отправляются автоматически
            # (практики «Отец» и «Судьба» сохранены как бонус для Пространства)
            logger.info(f"Пропущено старое сообщение дня {day} для {chat_id}")
            return
        logger.info(f"✅ Отправлено сообщение {day} → {chat_id}")
    except Exception as e:
        logger.error(f"❌ Ошибка отправки {day} для {chat_id}: {e}")


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
    chat_id = update.effective_chat.id
    src = args[0] if args and args[0] in ("reels", "ads", "dengi") else "organic"
    set_source(chat_id, src)
    log_event(chat_id, "start")
    if args and args[0] == "dengi":
        await ml_begin_from_message(update, context)
        return ConversationHandler.END
    if args and args[0] in ("reels", "ads"):
        await update.message.reply_text(
            "✨ Привет! Раз ты здесь — что-то из видео зацепило.\n\n"
            "Пройди короткий тест — узнаешь, где сейчас твой главный блок: в деньгах, "
            "в отношениях или в жизни в целом. И откуда он идёт.\n\n"
            "Около 3 минут. Начнём? 👇",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Начать", callback_data="reels_start")
            ]])
        )
        return GREETING
    return await send_first_question(update, context)


async def send_first_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ut_begin_message(update, context)
    return ConversationHandler.END


async def greeting_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await ut_begin_callback(query, context)
    return ConversationHandler.END


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
    context.user_data["first_result"] = result_key

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
            "🎧 Через 10 минут я пришлю тебе первую аудио-практику — не уходи далеко!"
        )
    )

    # 3) Приглашение на второй тест
    await asyncio.sleep(2)
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "🔎 Хочешь узнать, откуда это идёт?\n\n"
            "Есть второй короткий тест: 10 вопросов, около 3 минут. Первый показал, как ты ведёшь себя "
            "с деньгами, а второй покажет скрытую программу из семьи и рода, которая за этим стоит."
        ),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔎 Пройти второй тест", callback_data="ml_start")
        ]])
    )

    # 4) Три пути
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
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("💰 Хочу Денежный взлёт", callback_data="want_money")]])
    elif query.data == "path_razbor":
        text = TEXT_RAZBOR
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🎯 Записаться на разбор", callback_data="want_razbor")]])
    else:
        text = TEXT_SPACE
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🌀 Пространство в Telegram", url=LINK_GROUP)],
            [InlineKeyboardButton("🌀 Пространство в WhatsApp", url=LINK_GROUP_WA)],
        ])
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=kb)


# ======================================================================
# ВТОРОЙ ТЕСТ «СКРЫТАЯ ДЕНЕЖНАЯ ПРОГРАММА» (10 вопросов → 1 из 12 программ)
#
# • тест называет программу и показывает, откуда она, но НЕ даёт выхода из неё
#   (способ работы — в личном разборе);
# • профессиональные термины метода в текстах не используются — только
#   «программа» и «сценарий»;
# • все тексты теста лежат в этом блоке — их можно править прямо здесь.
#
# Запуск: команда /dengi, ссылка t.me/venera_tatina_bot?start=dengi
# или кнопка «Пройти второй тест» после первого теста.
# ======================================================================
from collections import Counter

ML_LETTERS = ["А", "Б", "В", "Г"]

# ===== вступление =====
ML_INTRO = (
    "🔎 Скрытая денежная программа\n\n"
    "Первый тест показал, как ты ведёшь себя с деньгами. Этот покажет, откуда это идёт: "
    "какая программа из семьи и рода стоит за твоим блоком.\n\n"
    "10 вопросов, около 3 минут. Отвечай не думая — выбирай то, что откликнулось первым."
)

# ===== вопросы: (текст, [(ответ, номер программы), ...]) =====
ML_QUESTIONS = [
    (
        "Когда ты представляешь, что зарабатываешь намного больше, чем сейчас, что откликается первым?",
        [
            ("«У нас в семье так не было — это не для нас»", 4),
            ("Неловкость: вдруг рядом с моим успехом кому-то станет хуже", 6),
            ("Страх выделиться: что скажут люди, не начнут ли завидовать", 11),
            ("Чувство, что лёгких денег не бывает — придётся работать на износ", 8),
        ],
    ),
    (
        "Что чаще всего происходит с деньгами в твоей жизни?",
        [
            ("Приходят и почти сразу уходят, будто жгут руки", 7),
            ("Уходят на чужие нужды, проблемы и долги близких", 2),
            ("Когда сумма близка к крупной, что-то случается и всё рушится", 5),
            ("Я повторяю те же денежные решения и ошибки, что делали мои родители", 9),
        ],
    ),
    (
        "Как ты работаешь?",
        [
            ("До изнеможения, а когда отдыхаю, чувствую вину", 8),
            ("Беру на себя ответственность за результат других: команды, клиентов, близких", 3),
            ("Не показываю свои результаты: лучше тихо, чтобы не завидовали", 11),
            ("Ровно так, как принято в моей семье: выше планку не ставлю", 4),
        ],
    ),
    (
        "Что отзывается, когда ты думаешь о том, чтобы зарабатывать больше, чем партнёр или твои родители?",
        [
            ("Неудобно перед мамой или папой: нельзя быть выше них", 9),
            ("Страх, что отношения не выдержат: или семья, или деньги", 10),
            ("Вина: у моих близких так не получилось, а я буду «выше»", 6),
            ("Я иду по тому же пути, что и мама: у неё было так, значит, и у меня так", 1),
        ],
    ),
    (
        "Какая мысль про деньги тебе знакома?",
        [
            ("«Богатство не для праведных, скромность чище»", 12),
            ("«Мне хватит малого, лишнего не нужно»", 7),
            ("«Деньги достаются только тяжёлым трудом»", 8),
            ("«От больших денег одни беды»", 5),
        ],
    ),
    (
        "Какой ты была в детстве, в семье?",
        [
            ("Той, кто берёг и поддерживал родителей, чувствовал их настроение", 2),
            ("Взрослой не по годам: рано взяла на себя ответственность", 3),
            ("Очень похожей на маму или папу, в том числе по судьбе", 1),
            ("В семье есть человек, о котором не говорят: исключённый, потерявший всё, пропавший", 5),
        ],
    ),
    (
        "Что ты чувствуешь, когда получаешь крупную сумму?",
        [
            ("Вину или неловкость: за что мне столько", 6),
            ("Желание быстрее потратить или раздать", 7),
            ("Хочется скрыть, чтобы никто не узнал и не позавидовал", 11),
            ("Чувство, что я обязана поделиться, иначе несправедливо", 3),
        ],
    ),
    (
        "Что бы ты почувствовала, если бы стала зарабатывать в три раза больше, чем когда-либо зарабатывали твои родители?",
        [
            ("Стыд и ощущение, что я их предаю", 9),
            ("Страх, что за это накажут или что это «неправильно»", 12),
            ("Тревогу, что отдалюсь от близких и партнёра", 10),
            ("Мне станет легче, но я буду беспокоиться, что им тяжело, и понесу их тяжесть", 2),
        ],
    ),
    (
        "Какая фраза внутри звучит громче всего?",
        [
            ("«Не высовывайся»", 11),
            ("«Мы так никогда не жили»", 4),
            ("«Порядочные люди живут скромно»", 12),
            ("«Лучше потерплю я, лишь бы им было хорошо»", 3),
        ],
    ),
    (
        "Какой сценарий повторяется в твоей жизни?",
        [
            ("Как у мамы или бабушки: те же отношения, те же долги, та же судьба", 1),
            ("Рост обрывается, когда до результата остаётся один шаг", 5),
            ("Чужая тяжесть ощущается как своя, и я несу её", 2),
            ("Когда растут деньги, начинаются проблемы в отношениях, и наоборот", 10),
        ],
    ),
]

# ===== 12 программ: название, как проявляется, откуда идёт, чего стоит =====
ML_PROGRAMS = {
    1: {
        "title": "Повторяю судьбу своих",
        "how": (
            "Ты бессознательно повторяешь путь мамы, папы или кого-то из рода: в деньгах, в отношениях, "
            "в том, как проживаешь трудные периоды. Что-то в твоей жизни звучит как эхо чужой судьбы: "
            "«как у мамы», «как у бабушки»."
        ),
        "origin": (
            "Для ребёнка быть похожим на своих значит принадлежать. Если «я как вы», меня не исключат. "
            "Поэтому повторение судьбы часто выглядит не как проблема, а как верность."
        ),
        "cost": "Твой собственный денежный путь остаётся непрожитым: ты живёшь по уже написанному сценарию.",
    },
    2: {
        "title": "Несу чужое",
        "how": (
            "Ты берёшь на себя чужие нужды, чужую тяжесть и чужие долги, финансовые и эмоциональные. "
            "Деньги уходят туда, где кому-то из близких «хуже», а твои цели откладываются."
        ),
        "origin": (
            "Из детской любви: «я сделаю за тебя, чтобы тебе стало легче». Ребёнок часто чувствует, что может "
            "облегчить жизнь родителям, если возьмёт часть их ноши."
        ),
        "cost": "Ты устаёшь и остаёшься без ресурса, а тем, кого ты несёшь, не становится по-настоящему легче.",
    },
    3: {
        "title": "Лучше я, чем ты",
        "how": (
            "Ты готова пожертвовать своими деньгами, временем и мечтами, лишь бы близким было хорошо. "
            "Берёшь ответственность за чужой результат (детей, команды, клиентов) и тянешь больше, чем следует."
        ),
        "origin": (
            "Это самая глубокая форма детской любви: «пусть будет тяжело мне, но не тебе». "
            "Ребёнок бессознательно предлагает себя вместо другого."
        ),
        "cost": (
            "Не хватает денег и сил на собственную жизнь. Жертва становится привычной ролью, "
            "а другим не даётся права нести своё."
        ),
    },
    4: {
        "title": "Выше нельзя",
        "how": (
            "Внутри стоит потолок: «столько, сколько у нас, достаточно», «выше не положено». "
            "Доход растёт до определённой планки и останавливается или откатывается обратно."
        ),
        "origin": (
            "Принадлежность через равенство. Если в роду жили скромно, бессознательно кажется, что жить лучше "
            "значит выйти из круга своих. Это равнение вниз."
        ),
        "cost": (
            "Возможности есть, но ты не позволяешь себе ими воспользоваться. "
            "Планку ниже твоих возможностей держишь ты сама."
        ),
    },
    5: {
        "title": "Деньги — это беда",
        "how": (
            "Рядом с крупными деньгами и большим успехом появляется тревога, будто вот-вот что-то рухнет. "
            "Богатство связывается с бедой, потерями, чьей-то трагедией."
        ),
        "origin": (
            "Если в роду кого-то исключили, забыли, осудили (разорившегося, ушедшего, того, о ком молчат), "
            "система «помнит» об этом. Деньги и успех могут быть связаны в памяти рода с чьей-то судьбой."
        ),
        "cost": "Ты бессознательно сама обрываешь рост на подходе к большому, чтобы не повторить чужую судьбу.",
    },
    6: {
        "title": "Мне нельзя быть успешнее",
        "how": (
            "Когда у тебя получается, появляется неловкость или вина: «а как же другие», «мне повезло, а им нет». "
            "Ты занижаешь цену, дарить хочется чаще, чем получать."
        ),
        "origin": (
            "Из связи «моя удача — чужая неудача». Если кому-то из близких не удалось, "
            "твой успех кажется несправедливым по отношению к ним."
        ),
        "cost": (
            "Ты не позволяешь себе по-настоящему получать и радоваться. "
            "А вина не делает легче тем, с кем ты «солидарна»."
        ),
    },
    7: {
        "title": "Мне хватит малого",
        "how": (
            "Деньги «жгут руки»: приходят и сразу уходят, хочется скорее потратить или раздать. "
            "Внутри звучит: «мне хватит малого», «лишнего не нужно»."
        ),
        "origin": (
            "Верность тем, кто жил в нужде. Для системы «держаться вместе» может означать держаться на одном уровне."
        ),
        "cost": "Ты не накапливаешь и не растёшь, потому что остаться с деньгами значит отдалиться от своих.",
    },
    8: {
        "title": "Деньги только тяжёлым трудом",
        "how": (
            "Деньги даются только тяжёлым трудом, «на износ». Если стало легко, появляется тревога или вина, "
            "будто ты делаешь что-то неправильное. Лёгкие способы заработать кажутся недостойными."
        ),
        "origin": (
            "В семье, где выживали трудом и страданием, труд и страдание часто равны ценности и любви: "
            "«достойный человек тяжело работает»."
        ),
        "cost": "Ты сама делаешь путь к деньгам тяжелее, чем он мог бы быть, и не даёшь себе отдыха и лёгкости.",
    },
    9: {
        "title": "Не могу быть выше родителей",
        "how": (
            "Тебе трудно зарабатывать больше, чем зарабатывали родители, особенно тот, с кем у тебя особая связь. "
            "Или ты повторяешь их денежные ошибки: те же долги, те же решения."
        ),
        "origin": (
            "Ребёнок, который превзошёл родителя, бессознательно чувствует: «я нарушаю порядок», «я предаю». "
            "Остаться на их уровне становится способом сохранить близость."
        ),
        "cost": "У тебя есть свой потолок в деньгах и ощущение, что стоишь на тормозе, которого сама не видишь.",
    },
    10: {
        "title": "Или семья, или деньги",
        "how": (
            "Внутри живёт сценарий «или семья, или деньги»: рост дохода пугает потерей отношений, "
            "а отношения «съедают» энергию на дело. Деньги и любовь не складываются вместе."
        ),
        "origin": (
            "Если у мамы или бабушки счастье в браке и достаток не уживались, ребёнок усваивает: "
            "за успех платят одиночеством или конфликтом."
        ),
        "cost": "Ты выбираешь между важными вещами там, где выбора могло бы и не быть.",
    },
    11: {
        "title": "Не высовывайся",
        "how": (
            "Тебе неловко проявляться: ты не показываешь результаты, не называешь цену вслух, "
            "откладываешь посты и предложения. Лучше «тихо», чтобы не завидовали."
        ),
        "origin": (
            "В некоторых семьях выделиться опасно: это вызывает зависть, осуждение или беду. "
            "«Не высовывайся» — это забота, которая когда-то защищала."
        ),
        "cost": "Люди, которым ты могла бы помочь, не узнают о тебе, а доход остаётся ниже твоих возможностей.",
    },
    12: {
        "title": "Богатство — это нечистое",
        "how": (
            "Где-то глубоко звучит: «бедность чище», «богатые не бывают добрыми», «за изобилие накажут». "
            "Деньги и совесть будто спорят друг с другом."
        ),
        "origin": (
            "Речь не о вере как таковой, а о том, как в семье усваивались установки о достатке: "
            "что скромность праведна, а богатство греховно. Они передаются незаметно, как часть воспитания, "
            "и становятся внутренним запретом."
        ),
        "cost": "Тебе трудно получать больше, не чувствуя внутренней вины, и деньги остаются «нечистыми» в твоих глазах.",
    },
}

# ===== «мостик» с первым тестом: строка зависит от типа из первого теста =====
ML_BRIDGES = {
    "А": "Первый тест показал: ты ждёшь тепла и разрешения снаружи. Второй показывает, чьё «можно» на самом деле ты ждёшь из своего рода.",
    "Б": "Первый тест показал, что ты держишь всё сама. Второй показывает, чью ношу ты несёшь и от чьей поддержки закрылась.",
    "В": "Первый тест показал, что ты ставишь других выше себя. Второй показывает, кому и за что ты этим верна.",
    "Г": "Первый тест показал: ты знаешь, что можешь больше, но упираешься в стену. Второй показывает, что стоит за этой стеной.",
    "АГ": "Первый тест показал, что твоя ценность зависит от оценки. Второй показывает, чьё признание ты ищешь и кому остаёшься верна.",
    "БГ": "Первый тест показал, что ты закрылась, чтобы не было больно. Второй показывает, что именно охраняет твоя броня.",
    "ВБ": "Первый тест показал, что ты берёшь на себя всё. Второй показывает, чьё именно ты несёшь.",
}

# ===== последняя строка для всех результатов (без выхода из программы) =====
ML_CLOSING = (
    "Как эта программа работает именно у тебя и откуда она в твоём роду, можно разобрать на личном разборе. "
    "А чтобы деньги не просто приходили, но и оставались, в курсе «Денежный взлёт» "
    "ты наводишь порядок в долгах, доходах и расходах."
)

def ml_question_text(i: int) -> str:
    text, options = ML_QUESTIONS[i]
    answers = "\n\n".join(f"{ML_LETTERS[k]}) {label}" for k, (label, _) in enumerate(options))
    return f"Вопрос {i + 1} из {len(ML_QUESTIONS)}\n\n{text}\n\n{answers}\n\n👇 Выбери букву"


def ml_keyboard(i: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(letter, callback_data=f"ml{i}_{letter}") for letter in ML_LETTERS
    ]])


def ml_reset(context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ml"] = {"i": 0, "answers": []}


def ml_rank_programs(answers):
    """answers — список номеров программ. Возвращает [(программа, баллы), ...] от главной к менее важной."""
    counts = Counter(answers)
    first_seen = {}
    for idx, p in enumerate(answers):
        first_seen.setdefault(p, idx)
    return sorted(counts.items(), key=lambda kv: (-kv[1], first_seen[kv[0]]))


def ml_build_result_text(answers, first_result=None) -> str:
    ranking = ml_rank_programs(answers)
    main_id, main_score = ranking[0]
    prog = ML_PROGRAMS[main_id]

    parts = [f"✨ Твоя скрытая денежная программа:\n«{prog['title']}»"]
    bridge = ML_BRIDGES.get(first_result or "")
    if bridge:
        parts.append(bridge)
    parts.append(f"🔒 Как это проявляется\n{prog['how']}")
    parts.append(f"🌱 Откуда это часто идёт\n{prog['origin']}")
    parts.append(f"🪙 Чего это стоит\n{prog['cost']}")

    if len(ranking) > 1:
        second_id, second_score = ranking[1]
        close = main_score == second_score or (main_score - second_score == 1 and second_score >= 2)
        if close:
            parts.append(f"Рядом звучит и программа «{ML_PROGRAMS[second_id]['title']}».")
    return "\n\n".join(parts)


async def ml_finish(query, context: ContextTypes.DEFAULT_TYPE):
    st = context.user_data.get("ml", {})
    answers = st.get("answers", [])
    first_result = context.user_data.get("first_result")
    chat_id = query.message.chat_id
    log_event(chat_id, "test2_done")

    await query.edit_message_text(ml_build_result_text(answers, first_result))
    await asyncio.sleep(2)
    await context.bot.send_message(chat_id=chat_id, text=ML_CLOSING)
    await asyncio.sleep(2)
    await context.bot.send_message(chat_id=chat_id, text=PATHS_TEXT, reply_markup=paths_keyboard())
    context.user_data.pop("ml", None)


async def ml_begin_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск из команды /dengi или из ссылки ?start=dengi"""
    ml_reset(context)
    await update.message.reply_text(ML_INTRO + "\n\n━━━━━━━━━━━━━━━━━━\n\n" + ml_question_text(0),
                                    reply_markup=ml_keyboard(0))


async def ml_cmd_dengi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ml_begin_from_message(update, context)


async def ml_begin_from_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск кнопкой «Пройти второй тест» после первого теста"""
    query = update.callback_query
    await query.answer()
    ml_reset(context)
    await query.edit_message_text(ML_INTRO + "\n\n━━━━━━━━━━━━━━━━━━\n\n" + ml_question_text(0),
                                  reply_markup=ml_keyboard(0))


async def ml_on_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data  # например «ml3_Б»
    i = int(data[2:data.index("_")])
    letter = data[data.index("_") + 1:]

    st = context.user_data.get("ml")
    if not st or st["i"] != i:
        # старая кнопка или тест уже завершён — тихо игнорируем
        return
    program_id = ML_QUESTIONS[i][1][ML_LETTERS.index(letter)][1]
    st["answers"].append(program_id)
    st["i"] = i + 1

    if st["i"] < len(ML_QUESTIONS):
        await query.edit_message_text(ml_question_text(st["i"]), reply_markup=ml_keyboard(st["i"]))
    else:
        await ml_finish(query, context)


def ml_register(app):
    """Подключение второго теста к боту (вызывается из main)"""
    app.add_handler(CommandHandler("dengi", ml_cmd_dengi))
    app.add_handler(CallbackQueryHandler(ml_begin_from_button, pattern="^ml_start$"))
    app.add_handler(CallbackQueryHandler(ml_on_answer, pattern="^ml[0-9]+_[АБВГ]$"))



# ======================================================================
# ЕДИНЫЙ ТЕСТ «СКРЫТАЯ ПРОГРАММА» — главный вход из рилсов и из /start
# 8 коротких вопросов про деньги и отношения, пятый вариант «Ничего не подходит».
# Результат: скрытая программа (название, как видно в деньгах и в отношениях,
# откуда идёт, чего стоит), шаг-наблюдение и приглашение на диагностику.
# Выхода из программы тест не даёт — это работа личной диагностики и разбора.
# Тексты программ лежат выше (ML_PROGRAMS), здесь — вопросы и дополнения.
# ======================================================================
UT_LETTERS = ["А", "Б", "В", "Г", "Д"]

UT_INTRO = (
    "Привет! 👋\n\n"
    "Я помогу тебе увидеть, где сейчас твой главный блок — в деньгах, в отношениях "
    "или в жизни в целом — и откуда он идёт.\n\n"
    "8 коротких вопросов, около 3 минут. Отвечай не думая. "
    "Если ни один вариант не подходит — выбирай Д и можешь написать своими словами."
)

UT_QUESTIONS = [
    (
        "Когда я думаю, что мою жизнь можно сделать намного лучше — в деньгах, в отношениях, во всём, — что откликается первым?",
        [
            ("«У нас в семье так не было»", 4),
            ("Неловко: вдруг рядом кому-то станет хуже", 6),
            ("Страх выделиться: что скажут люди", 11),
            ("Лёгкой жизни не бывает, придётся пахать", 8),
        ],
    ),
    (
        "Как я обычно живу и работаю?",
        [
            ("До изнеможения, а отдыхать совестно", 8),
            ("Тяну ответственность за всех вокруг", 3),
            ("Не показываю результаты: лучше тихо", 11),
            ("Как принято в семье, планку выше не ставлю", 4),
        ],
    ),
    (
        "Что отзывается, когда я думаю стать успешнее партнёра или родителей?",
        [
            ("Неудобно перед мамой или папой", 9),
            ("Страх: или семья, или успех", 10),
            ("Вина: у близких так не получилось", 6),
            ("Иду тем же путём, что мама", 1),
        ],
    ),
    (
        "Какая мысль про деньги и достаток мне знакома?",
        [
            ("«Богатство — не для праведных»", 12),
            ("«Мне хватит малого»", 7),
            ("«Всё достаётся только тяжёлым трудом»", 8),
            ("«От больших денег одни беды»", 5),
        ],
    ),
    (
        "Какой я была в детстве, в семье?",
        [
            ("Берегла и поддерживала родителей", 2),
            ("Взрослой не по годам", 3),
            ("Очень похожей на маму или папу", 1),
            ("В семье есть тот, о ком молчат", 5),
        ],
    ),
    (
        "Что я чувствую, когда получаю что-то большое: деньги, успех, подарок?",
        [
            ("Вину: за что мне столько", 6),
            ("Хочется быстрее потратить или раздать", 7),
            ("Хочется скрыть, чтобы не позавидовали", 11),
            ("Чувство долга: нужно поделиться", 3),
        ],
    ),
    (
        "Что я почувствую, если стану жить намного лучше, чем жили мои родители?",
        [
            ("Стыд, будто предаю их", 9),
            ("Страх, что накажут или что это неправильно", 12),
            ("Тревогу, что отдалюсь от близких", 10),
            ("Беспокойство за них, понесу их тяжесть", 2),
        ],
    ),
    (
        "Какой сценарий повторяется в моей жизни?",
        [
            ("Как у мамы или бабушки", 1),
            ("Рост обрывается за шаг до результата", 5),
            ("Чужая тяжесть ощущается как своя", 2),
            ("Растут деньги — рушатся отношения, и наоборот", 10),
        ],
    ),
]

# как программа проявляется в отношениях
UT_REL = {
    1: "В отношениях это может звучать как знакомый сценарий: те же роли, те же конфликты, будто ты уже видела это раньше.",
    2: "В отношениях ты становишься опорой для всех и редко позволяешь поддержать себя.",
    3: "В отношениях ты уступаешь, терпишь и жертвуешь своим, лишь бы другому было хорошо.",
    4: "В отношениях ты соглашаешься на «так же, как у всех» и не позволяешь себе большего счастья.",
    5: "В отношениях это может звучать как «когда всё слишком хорошо, жди беды»: ты сама обрываешь близость на подходе к счастью.",
    6: "В отношениях ты не позволяешь себе быть счастливее, чем близкие.",
    7: "В отношениях ты довольствуешься малым и не просишь большего.",
    8: "В отношениях ты привыкла «заслуживать» любовь трудом и заботой, а когда всё идёт легко, настораживаешься.",
    9: "В отношениях ты можешь не позволять себе стать счастливее или успешнее, чем были твои родители.",
    10: "В отношениях пугает, что твой рост разрушит близость, и ты выбираешь между важным.",
    11: "В отношениях ты прячешь свои желания и не говоришь о них вслух.",
    12: "В отношениях ты можешь стыдиться желания радости и роскоши, будто хотеть большего неправильно.",
}

# маленький шаг-наблюдение (не способ снять программу)
UT_STEPS = {
    1: "Сегодня заметь одну ситуацию с деньгами или близкими, в которой ты поступаешь «как у мамы» или «как у бабушки». Просто заметь, без оценки.",
    2: "Заметь сегодня, в какой момент ты берёшь на себя чужое: чужую заботу, чужую просьбу, чужой долг. Ничего не меняй, только отметь.",
    3: "Сегодня заметь, где ты уступаешь или терпишь ради другого. Спроси себя: чего хочу я?",
    4: "Заметь сегодня фразу «это не для нас» или «выше не положено», если она прозвучит внутри или снаружи.",
    5: "Заметь сегодня момент, когда рядом с хорошим развитием появляется тревога «сейчас что-то случится».",
    6: "Заметь, где ты занижаешь цену, отказываешься от подарка или извиняешься за свой успех.",
    7: "Сегодня заметь, на что уходят твои деньги в первые часы после того, как ты их получила.",
    8: "Заметь, в какой момент тебе становится тревожно или совестно, когда всё идёт легко.",
    9: "Заметь сегодня, в чём ты остаёшься на уровне родителей, хотя могла бы больше. Только наблюдай.",
    10: "Заметь сегодня, когда появляется мысль «или так, или так» про деньги и отношения.",
    11: "Заметь, о чём ты сегодня промолчала, чтобы не выделяться.",
    12: "Заметь, когда в тебе звучит «хорошие люди живут скромно». Просто отметь, откуда этот голос.",
}

# твоя сила в этой программе
UT_STRENGTH = {
    1: "Глубокая связь с родом и умение быть верной своим.",
    2: "Чуткость и способность быть опорой для других.",
    3: "Огромная способность любить и заботиться.",
    4: "Умение ценить стабильность и опираться на проверенное.",
    5: "Осторожность и острое чувство риска, которое когда-то защищало.",
    6: "Справедливость и чуткость к другим людям.",
    7: "Умение обходиться малым и не цепляться за вещи.",
    8: "Трудолюбие, выносливость и умение доводить дело до конца.",
    9: "Глубокая любовь и уважение к родителям.",
    10: "Ценность близости: для тебя отношения по-настоящему важны.",
    11: "Тактичность и умение не создавать лишних конфликтов.",
    12: "Совестливость и честность перед собой.",
}

# как эта программа звучит внутри
UT_VOICE = {
    1: "«Я, наверное, как мама», «Так, видимо, и должно быть».",
    2: "«Я не могу бросить, им же тяжело».",
    3: "«Пусть лучше мне, чем им».",
    4: "«Нам хватает и так», «Зачем мне больше».",
    5: "«Когда слишком хорошо, обязательно что-то случится».",
    6: "«Мне повезло больше, чем другим, это неправильно».",
    7: "«Мне много не нужно».",
    8: "«Лёгкое не может быть настоящим».",
    9: "«Я не вправе быть выше них».",
    10: "«Если выберу своё, потеряю близких».",
    11: "«Лучше не привлекать внимание».",
    12: "«Порядочный человек не стремится к богатству».",
}

# если человек не выбрал ни одного ответа (везде «Другое») — всё равно даём реальный результат
UT_GENERAL = {
    "title": "Несколько программ сразу",
    "strength": "Ты не соглашаешься на готовые ответы и внимательно относишься к себе.",
    "how": (
        "Когда ни один из вариантов не откликается, это часто значит, что в твоей жизни "
        "переплетается сразу несколько причин, а не одна. Деньги могут упираться и в усталость, "
        "и в страх выделиться, и в чужие ожидания одновременно."
    ),
    "rel": (
        "В отношениях это может выглядеть так: ты то отдаёшь слишком много, то закрываешься, "
        "и сама не всегда понимаешь, что именно происходит."
    ),
    "voice": "«У меня не так, как у всех» или «Я не понимаю, что именно мне мешает».",
    "origin": (
        "Когда в роду и семье много разных историй, программы накладываются друг на друга "
        "и их трудно увидеть изнутри."
    ),
    "cost": "Ты тратишь много сил, не видя, на что именно они уходят.",
    "step": "Сегодня запиши три ситуации, где ты чувствуешь, что упираешься в стену, и что ты в этот момент чувствуешь в теле.",
}

UT_NO_MATCH = (
    "✨ Твой результат\n\n"
    "Похоже, ни один вариант не откликнулся, и это нормально: у каждого свой путь, "
    "и общие вопросы не всегда попадают в него.\n\n"
    "Именно поэтому самое точное — личная диагностика: она показывает твою ситуацию, "
    "а не общую картину."
)

UT_CTA = (
    "🔎 А что именно блокирует у тебя — деньги, отношения или что-то другое?\n\n"
    "У каждого это своё, и увидеть это можно только в личной диагностике.\n\n"
    "Пока идёт акция, диагностика бесплатная (обычно 10 000 ₸). Места ограничены."
)


def ut_question_text(i: int) -> str:
    text, options = UT_QUESTIONS[i]
    lines = [f"{UT_LETTERS[k]}) {label}" for k, (label, _) in enumerate(options)]
    lines.append("Д) Другое — можно написать своими словами")
    return f"Вопрос {i + 1} из {len(UT_QUESTIONS)}\n\n{text}\n\n" + "\n\n".join(lines) + "\n\n👇 Выбери букву"


def ut_keyboard(i: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(letter, callback_data=f"ut{i}_{letter}") for letter in UT_LETTERS
    ]])


def ut_reset(context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ut"] = {"i": 0, "answers": []}


async def ut_begin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ut_reset(context)
    log_event(update.effective_chat.id, "test_start")
    await update.message.reply_text(
        UT_INTRO + "\n\n━━━━━━━━━━━━━━━━━━\n\n" + ut_question_text(0),
        reply_markup=ut_keyboard(0)
    )


async def ut_begin_callback(query, context: ContextTypes.DEFAULT_TYPE):
    ut_reset(context)
    log_event(query.message.chat_id, "test_start")
    await query.edit_message_text(
        "Ответь на 8 коротких вопросов, около 3 минут. Отвечай не думая. "
        "Если ни один вариант не подходит — выбирай Д и можешь написать своими словами.\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n" + ut_question_text(0),
        reply_markup=ut_keyboard(0)
    )


async def ut_finish(query, context: ContextTypes.DEFAULT_TYPE):
    st = context.user_data.get("ut", {})
    answers = st.get("answers", [])
    chat_id = query.message.chat_id
    user = query.from_user

    # практики планируем сразу, чтобы они не потерялись
    schedule_user(chat_id)
    log_event(chat_id, "test_done")

    # всегда даём реальный результат
    if answers:
        ranking = ml_rank_programs(answers)
        main_id, main_score = ranking[0]
        context.user_data["result_program"] = main_id
        p = ML_PROGRAMS[main_id]
        data = {
            "title": p["title"], "strength": UT_STRENGTH[main_id], "how": p["how"], "rel": UT_REL[main_id],
            "voice": UT_VOICE[main_id], "origin": p["origin"], "cost": p["cost"], "step": UT_STEPS[main_id],
        }
        second = None
        if len(ranking) > 1:
            second_id, second_score = ranking[1]
            if main_score == second_score or (main_score - second_score == 1 and second_score >= 2):
                second = ML_PROGRAMS[second_id]["title"]
    else:
        context.user_data["result_program"] = None
        data = UT_GENERAL
        second = None

    head = "✨ Твой результат\n\n"
    if 0 < len(answers) < 3:
        head += "Ты ответила не на все вопросы, поэтому это предварительный результат.\n\n"
    await query.edit_message_text(
        head + f"Скрытая программа: «{data['title']}»\n\n"
        f"💫 Твоя сила\n{data['strength']}\n\n"
        f"🔒 В деньгах\n{data['how']}\n\n"
        f"💞 В отношениях\n{data['rel']}"
    )

    part2 = (
        f"🗣 Как это звучит внутри\n{data['voice']}\n\n"
        f"🌱 Откуда это часто идёт\n{data['origin']}\n\n"
        f"🪙 Чего это стоит\n{data['cost']}"
    )
    if second:
        part2 += f"\n\nРядом звучит и программа «{second}»."
    part2 += "\n\nЭто не приговор, а программа. Когда она названа, её уже видно, и это первый шаг."
    await asyncio.sleep(2)
    await context.bot.send_message(chat_id=chat_id, text=part2)

    await asyncio.sleep(2)
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"✅ Твой шаг на сегодня — наблюдение\n\n{data['step']}\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🎧 Через 10 минут я пришлю тебе первую аудио-практику — не уходи далеко!"
        )
    )

    await asyncio.sleep(2)
    await context.bot.send_message(
        chat_id=chat_id,
        text=UT_CTA,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔎 Записаться на диагностику", callback_data="diag_signup")
        ]])
    )

    notes = context.user_data.pop("ut_notes", [])
    await notify_admin(
        context.bot,
        "✅ Прошла тест\n" + who(user) + f"\nПрограмма: «{data['title']}»"
        + (" (предварительно, мало ответов)" if 0 < len(answers) < 3 else "")
        + f"\nОтветов по программам: {len(answers)} из {len(UT_QUESTIONS)}"
        + (f"\nСвоими словами: {' | '.join(notes)[:600]}" if notes else "")
    )
    context.user_data.pop("ut", None)


async def ut_on_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data  # например «ut3_Б»
    i = int(data[2:data.index("_")])
    letter = data[data.index("_") + 1:]

    st = context.user_data.get("ut")
    if not st or st["i"] != i:
        return  # старая кнопка или тест уже завершён
    if letter != "Д":
        program_id = UT_QUESTIONS[i][1][UT_LETTERS.index(letter)][1]
        st["answers"].append(program_id)
    elif not st.get("hint_shown"):
        st["hint_shown"] = True
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Если хочешь, напиши своими словами, как у тебя на самом деле. Я передам это Венере 💫 Тест идёт дальше."
        )
    st["i"] = i + 1

    if st["i"] < len(UT_QUESTIONS):
        await query.edit_message_text(ut_question_text(st["i"]), reply_markup=ut_keyboard(st["i"]))
    else:
        await ut_finish(query, context)


async def diag_signup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    log_event(query.message.chat_id, "diag")
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=(
            "Отлично! 💫\n\n"
            "Напиши Венере слово «диагностика» и выбери одну тему: деньги, отношения, "
            "состояние или реализация. На одну диагностику берётся один запрос, "
            "и она подтвердит удобное время."
        ),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("💬 Написать Венере", url=LINK_VENERA)
        ]])
    )
    await notify_admin(context.bot, "🔔 Хочет бесплатную диагностику\n" + who(query.from_user))


async def want_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    log_event(query.message.chat_id, query.data)
    if query.data == "want_money":
        what, label = "Денежный взлёт", "Денежный взлёт"
        text = (
            "Отлично! 💫\n\n"
            "Стоимость Денежного взлёта — 4 990 ₸.\n\n"
            "Нажми кнопку «Оплатить», в Kaspi введи сумму 4 990 и подтверди оплату. "
            "После оплаты напиши Венере, и она откроет тебе доступ к курсу."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Оплатить 4 990 ₸ (Kaspi)", url=LINK_KASPI_MONEY)],
            [InlineKeyboardButton("💬 Написать Венере", url=LINK_VENERA)],
        ])
    else:
        what, label = "индивидуальный разбор", "разбор"
        text = "Отлично! 💫 Напиши Венере — она подберёт время и уточнит твой запрос."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("💬 Написать Венере", url=LINK_VENERA)]])
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=text,
        reply_markup=kb
    )
    await notify_admin(context.bot, f"🔔 Хочет: {what}\n" + who(query.from_user))


async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Венера пишет боту /admin один раз — бот запоминает, куда присылать заявки"""
    user = update.effective_user
    if user and user.username and user.username.lower() == "vetatina":
        set_admin_chat(update.effective_chat.id)
        await update.message.reply_text(
            "Готово ✅ Теперь я буду присылать сюда сообщения: кто прошёл тест, "
            "кто хочет диагностику, Денежный взлёт или разбор."
        )


def _is_admin(update: Update) -> bool:
    user = update.effective_user
    return bool(user and user.username and user.username.lower() == "vetatina")


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сводка для Венеры: сколько людей и на каких шагах. Только для @vetatina."""
    if not _is_admin(update):
        return
    astana = timezone(timedelta(hours=5))
    now = datetime.now(astana)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    periods = [
        ("Сегодня", today_start),
        ("7 дней", now - timedelta(days=7)),
        ("Всего", datetime(2000, 1, 1, tzinfo=timezone.utc)),
    ]
    rows = [
        ("start", "Открыли бота"),
        ("test_start", "Начали тест"),
        ("test_done", "Прошли тест"),
        ("test2_done", "Прошли второй тест"),
        ("diag", "Хотят диагностику"),
        ("want_money", "Хотят Денежный взлёт"),
        ("want_razbor", "Хотят разбор"),
    ]
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                counts = {}
                for pname, since in periods:
                    cur.execute(
                        "SELECT kind, COUNT(DISTINCT chat_id) AS n FROM events "
                        "WHERE created_at >= %s GROUP BY kind", (since,)
                    )
                    counts[pname] = {r["kind"]: r["n"] for r in cur.fetchall()}
                cur.execute(
                    "SELECT source, kind, COUNT(DISTINCT chat_id) AS n FROM events "
                    "WHERE kind IN ('start','test_done','diag') GROUP BY source, kind"
                )
                by_source = {}
                for r in cur.fetchall():
                    by_source.setdefault(r["source"] or "organic", {})[r["kind"]] = r["n"]
    except Exception as e:
        logger.error(f"stats: {e}")
        await update.message.reply_text("Не получилось собрать статистику. Посмотри логи в Railway.")
        return

    lines = ["📊 Статистика бота (считаются люди, не нажатия)\n"]
    header = "                         " + "  ".join(p for p, _ in periods)
    for kind, label in rows:
        vals = [str(counts[p].get(kind, 0)) for p, _ in periods]
        lines.append(f"{label}: " + " / ".join(vals))
    lines.append("\n(Сегодня / 7 дней / Всего)")
    names = {"reels": "Рилсы", "ads": "Реклама", "dengi": "Тест про деньги", "organic": "Без ссылки"}
    if by_source:
        lines.append("\n🔗 Откуда пришли (всего): открыли / прошли тест / диагностика")
        for src, d in sorted(by_source.items(), key=lambda x: -x[1].get("start", 0)):
            lines.append(f"{names.get(src, src)}: {d.get('start', 0)} / {d.get('test_done', 0)} / {d.get('diag', 0)}")
    await update.message.reply_text("\n".join(lines))


async def ut_free_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пока идёт тест, всё, что человек пишет своими словами, сохраняется и уходит Венере"""
    if not update.message or not update.message.text:
        return
    if not context.user_data.get("ut"):
        return
    text = update.message.text.strip()
    context.user_data.setdefault("ut_notes", []).append(text)
    await update.message.reply_text("Записала 🙂 Продолжай — выбери букву.")
    await notify_admin(
        context.bot,
        "💬 Написала своими словами во время теста\n" + who(update.effective_user) + f"\n«{text[:500]}»"
    )


def ut_register(app):
    app.add_handler(CallbackQueryHandler(ut_on_answer, pattern="^ut[0-9]+_[АБВГД]$"))
    app.add_handler(CallbackQueryHandler(diag_signup, pattern="^diag_signup$"))
    app.add_handler(CallbackQueryHandler(want_callback, pattern="^want_(money|razbor)$"))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    # отдельная группа, чтобы не мешать остальным обработчикам текста
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ut_free_text), group=5)


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

    # Второй тест «Скрытая денежная программа» (блок выше, перед main)
    ml_register(app)
    ut_register(app)

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
