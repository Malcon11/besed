import os
import random
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import re
import time
from collections import Counter, defaultdict

# --- НАСТРОЙКИ ---
GROUP_TOKEN = os.environ.get('VK_GROUP_TOKEN')
GROUP_ID = int(os.environ.get('VK_GROUP_ID'))

# ВПИСИ СЮДА СВОЙ ID (узнай на regvk.com/id). Только ты сможешь менять настройки.
CREATOR_ID = 111111111  

# --- ДАННЫЕ БОТА (ПОЛНЫЕ СПИСКИ) ---
RULES = (
    "📜 Правила нашей беседы:\n"
    "1. Уважайте друг друга. Никакого оскорбления участников.\n"
    "2. Никакого спама, рекламы и ссылок на подозрительные ресурсы.\n"
    "3. Флуд только в умеренных количествах.\n"
    "4. Шутки шутками, но знайте меру.\n"
    "5. Бот здесь для веселья, не пытайтесь его сломать 😉\n\n"
    "За нарушение — предупреждение, затем мут или исключение."
)

JOKES = [
    "Почему программисты путают Хэллоуин и Рождество? Потому что 31 OCT = 25 DEC.",
    "Уборка — это перемещение пыли с одного места на другое с целью создания иллюзии порядка.",
    "Я не ленивый, я просто в режиме энергосбережения.",
    "Оптимист видит стакан наполовину полным. Пессимист — наполовину пустым. Инженер видит стакан, который в два раза больше, чем нужно.",
    "Моя любимая форма правления — лежание.",
    "Уборка — это просто перекладывание хлама в более аккуратные стопки.",
    "Я не спорю, я просто объясняю, почему я прав.",
    "Сон для слабаков. Но я очень слаб.",
    "Если долго смотреть на холодильник, голод не исчезнет, но ты потратишь много электричества.",
    "Я не храплю. Это просто мой организм издает звуки работающих механизмов.",
    "Диета — это научно доказанный способ потратить деньги на продукты, которые тебе не нравятся.",
    "Опыт — это просто название, которое мы даем своим ошибкам.",
    "Я не ленивый, я просто очень мотивирован на ничегонеделание.",
    "Мозг — замечательная вещь. Он начинает работать еще до того, как ты открываешь глаза, чтобы придумать оправдание, почему вставать не нужно."
]

FACTS = [
    "У осьминогов три сердца, синяя кровь и девять мозгов.",
    "Винный бокал по форме напоминает королевскую лилию.",
    "У страусов глаза больше, чем их мозг.",
    "В оригинальном тексте «Красной Шапочки» волк съел не только бабушку, но и девочку.",
    "На Кипре существует традиция катать сыры по холму на Пасху.",
    "У улитки около 25 000 зубов.",
    "Сердце кита бьется всего 9 раз в минуту.",
    "В мире существует арбузный мед (нардек).",
    "Вомбаты производят помет кубической формы.",
    "У осьминога нет ни одной косточки в теле.",
    "Самый большой замок в мире находится в Польше, а не в Великобритании.",
    "Медуза Turritopsis dohrnii биологически бессмертна — она может возвращаться к стадии полипа.",
    "У кенгуру не бывает дождя внутри сумки.",
    "В Албании покачивание головой из стороны в сторону означает «да», а кивок — «нет»."
]

# --- СЛОВАРИ СОСТОЯНИЯ (Глобальная память бота) ---
muted_users = {}
guess_games = {}
chat_settings = {}  # {peer_id: {'welcome_text': str}}
chat_karma = defaultdict(int)  # {user_id: karma_points}
karma_titles = {100: "Местный Мем-Лорд", 500: "Официальный Прокрастинатор Чата", 1000: "Легенда Оффтопа"}

found_items = {}  # {peer_id: {'item': str, 'owner_id': int, 'expires': time}}
word_stats = defaultdict(Counter)  # {peer_id: Counter({'слово': count})}

santa_active = False
santa_pairs = {}  # {peer_id: {giver_id: receiver_id}}
santa_log = {}  # {peer_id: {giver_id: [msg1, msg2]}}

# --- ЛОГИКА БОТА ---

ITEMS = ["Счастливый билетик", "Древний свиток 'Ctrl+C'", "Бутерброд с колбасой", "Кристалл маны", "Проклятая мышка", "Чеширский сыр"]

def get_random_ship(mention1, name1, mention2, name2):
    ships = [
        f"{mention1} + {mention2} — идеальный союз! Назовем вас {name1[0].upper()}{name2[0].upper()}! 💖",
        f"Ого, искрит между {mention1} и {mention2}! Держитесь подальше от легковоспламеняющихся предметов.",
        f"{name1} и {name2} на одной волне. Частота вашей романтики — 420 МГц.",
        f"Вни
Узнать ID страницы или группы ВКонтакте — Regvk.Com
regvk.com


мание! Зафиксирована химическая реакция между {mention1} и {mention2}.",
        f"Самый крепкий пейринг в этой беседе: {mention1} x {mention2}."
    ]
    return random.choice(ships)

def get_current_welcome(peer_id: int) -> str:
    default_templates = [
        "{mention}, добро пожаловать в наш дурдом! 🏚️ Шутки за 300 и бесконечный оффтоп.",
        "Привет, {mention}! Мы тут шипперим незнакомцев и травим байки. {name}, ты с нами?",
        "{mention} присоединился! Кто-нибудь, выдайте человеку плед и какао.",
        "О, {mention}! Заходи, у нас тут весело. Главное правило: не воспринимать всерьез команду !шиппермейкер."
    ]
    if peer_id in chat_settings and 'welcome_text' in chat_settings[peer_id]:
        return chat_settings[peer_id]['welcome_text']
    return random.choice(default_templates)

def get_welcome_message(user_mention: str, user_name: str, peer_id: int) -> str:
    template = get_current_welcome(peer_id)
    return template.format(mention=user_mention, name=user_name)

def parse_mention(text: str):
    match = re.search(r'$$id(\d+)\|.*?$$', text)
    if match: return int(match.group(1))
    match = re.search(r'@id(\d+)', text)
    if match: return int(match.group(1))
    return None

def generate_ai_reply(text: str, user_name: str) -> str:
    text = text.lower()
    greetings = ["привет", "здарова", "hello", "hi", "ку", "салам"]
    bye = ["пока", "до завтра", "спокойной ночи", "бб"]
    thanks = ["спасибо", "спс", "благодарю"]
    
    if any(word in text for word in greetings):
        return random.choice(["Привет-привет!", "Здарова!", "Ку!", "Слушаю тебя внимательно."])
    elif any(word in text for word in bye):
        return random.choice(["Пока! Возвращайся за шутками.", "До связи!", "Спокойной ночи! 😴"])
    elif any(word in text for word in thanks):
        return random.choice(["Всегда пожалуйста!", "Обращайся!", "🤝"])
    elif "как дела" in text or "что делаешь" in text:
        return "Слушаю вашу беседу и жду команды. Могу рассказать шутку или зашипперить кого-нибудь!"
    elif "бот" in text and ("ты" in text or "вы" in text):
        return "Я — бот-помощник для этой беседы. Мои команды начинаются с восклицательного знака. Напиши !команды, чтобы узнать список."
    elif "погода" in text:
        return "Я не умею смотреть погоду, но могу предсказать: сегодня будет отличный день для мемов!"
    elif "любишь" in text:
        return "Больше всего я люблю, когда люди смеются и используют команду !шиппермейкер."
    else:
        return random.choice([
            "Интересная мысль. Расскажи подробнее?",
            "Я тут, чтобы шутить и шипперить, но поговорить тоже люблю!",
            "Это глубокий вопрос. Дай мне секунду подумать... А, нет, я просто бот, вот шутка: !шутка"
        ])

def drop_random_item(peer_id: int):
    if peer_id in found_items and time.time() < found_items[peer_id]['expires']:
        return None  # Вещь уже лежит
    item = random.choice(ITEMS)
    expires = time.time() + 7200  # Лежит 2 часа
    found_items[peer_id] = {'item': item, 'owner_id': None, 'expires': expires}
    return item

def claim_item(vk, peer_id: int, from_id: int, user_name: str):
    if peer_id not in found_items:
        return False
    item = found_items[peer_id]['item']
    if found_items[peer_id]['owner_id'] is not None:
        return False  # Уже кто-то взял
    
    found_items[peer_id]['owner_id'] = from_id
    chat_karma[from_id] += 10
    vk.messages.send(peer_id=peer_id, random_id=random.randint(1, 999999), 
                   message=f"🎉 {user_name} поймал(а) **{item}**! Магия бота усилена на 1 час. (+10 к карме)")
    return True

def update_word_stats(peer_id: int, text: str):
    words = re.findall(r"\b[а-яa-z]+\b", text.lower())
    for word in words:
        if len(word) > 3 and not word.startswith('http'):
            word_stats[peer_id][word] += 1

def get_local_meme(peer_id: int, user_id: int, user_name: str):
    if peer_id not in word_stats or not word_stats[peer_id


]:
        return None
    common_words = word_stats[peer_id].most_common(5)
    if not common_words:
        return None
    
    word, count = random.choice(common_words)
    templates = [
        f"{user_name}, ты написал(а) слово «{word}» уже {count} раз. Это диагноз или привычка?",
        f"Локальный факт: слово «{word}» встречается здесь чаще, чем здравый смысл.",
        f"{user_name}, напоминаю: ты используешь «{word}» слишком часто. Вот тебе !факт для разнообразия.",
        f"Статистика бота: {user_name} — главный проповедник слова «{word}» в этой беседе."
    ]
    return random.choice(templates)

def start_secret_santa(vk, peer_id: int, from_id: int):
    global santa_active, santa_pairs, santa_log
    try:
        chat_users = vk.messages.getConversationMembers(peer_id=peer_id)
        profiles = [p for p in chat_users['profiles'] if p['id'] != vk_session.user_id['id']]
        ids = [p['id'] for p in profiles]
        
        if len(ids) < 3:
            vk.messages.send(peer_id=peer_id, random_id=random.randint(1, 999999), 
                           message="❌ Нужно минимум 3 живых участника для Тайного Санты.")
            return
        
        random.shuffle(ids)
        pairs = {}
        log = {}
        for i, uid in enumerate(ids):
            receiver = ids[(i + 1) % len(ids)]
            pairs[uid] = receiver
            log[uid] = []
        
        santa_active = True
        santa_pairs[peer_id] = pairs
        santa_log[peer_id] = log
        
        vk.messages.send(peer_id=peer_id, random_id=random.randint(1, 999999), 
                       message="🎅 Тайный Санта 2.0: Тайный сталкер запущен! Каждый получил цель. У вас есть неделя, чтобы незаметно поддерживать свою цель. Через неделю я раскрою карты!")
    except Exception as e:
        print(f"Ошибка Санты: {e}")
        vk.messages.send(peer_id=peer_id, random_id=random.randint(1, 999999), message="❌ Не удалось запустить Санту.")

def log_santa_action(peer_id: int, from_id: int, target_id: int, action_text: str):
    if not santa_active or peer_id not in santa_log:
        return False
    if santa_pairs[peer_id].get(from_id) != target_id:
        return False
    
    santa_log[peer_id][from_id].append(action_text)
    return True

def end_secret_santa(vk, peer_id: int):
    global santa_active, santa_pairs, santa_log
    if peer_id not in santa_log:
        return
    
    lines = ["🎁 Итоги Тайного Санты 2.0:"]
    for giver, receiver in santa_pairs[peer_id].items():
        try:
            giver_info = vk.users.get(user_ids=giver)[0]
            receiver_info = vk.users.get(user_ids=receiver)[0]
            actions = santa_log[peer_id][giver]
            action_text = ", ".join(actions) if actions else "просто наблюдал(а) издалека"
            lines.append(f"🎭 [id{giver}|{giver_info['first_name']}] следил(а) за [id{receiver}|{receiver_info['first_name']}]. Подвиги: {action_text}.")
        except Exception:
            continue
    
    vk.messages.send(peer_id=peer_id, random_id=random.randint(1, 999999), message="\n".join(lines))
    santa_active = False
    santa_pairs.pop(peer_id, None)
    santa_log.pop(peer_id, None)

def check_karma_title(vk, peer_id: int, user_id: int, user_name: str):
    karma = chat_karma[user_id]
    for threshold, title in sorted(karma_titles.items(), reverse=True):
        if karma >= threshold:
            try:
                vk.messages.removeChatUser(chat_id=peer_id - 2000000000, user_id=user_id)
                time.sleep(0.1)
                vk.messages.addChatUser(chat_id=peer_id - 2000000000, user_id=user_id)
                vk.messages.send(peer_id=peer_id, random_id=random.randint(1, 999999), 
                               message=f"🏆 {user_name} достиг(ла) нового уровня! Титул: **{title}**!")
            except Exception:
                vk.messages.send(peer_id=peer_id, random_id=random.randint(1, 999999), 
                               message=f"🏆 {user_name} достиг(ла) нового уровня!


Титул: **{title}** (Роль выдать не удалось, дай мне права)")
            break

def main():
    if not GROUP_TOKEN:
        print("Ошибка: Не найден токен группы в переменной VK_GROUP_TOKEN")
        return

    vk_session = vk_api.VkApi(token=GROUP_TOKEN)
    vk = vk_session.get_api()
    longpoll = VkBotLongPoll(vk_session, GROUP_ID)

    print("Бот запущен. Уникальные механики активны.")

    while True:
        for event in longpoll.listen():
            current_time = int(time.time())
            to_remove = [uid for uid, t in muted_users.items() if current_time >= t]
            for uid in to_remove: del muted_users[uid]

            # Чистка просроченных вещей
            expired_items = [p for p, data in found_items.items() if data['expires'] < current_time]
            for p in expired_items: 
                if found_items[p]['owner_id'] is None:
                    found_items.pop(p, None)

            if event.type == VkBotEventType.MESSAGE_NEW:
                if not event.obj.get('action'):
                    from_id = event.obj['from_id']
                    peer_id = event.obj['peer_id']
                    text = event.obj['text'].strip()
                    
                    if from_id in muted_users: continue

                    try:
                        user_info = vk.users.get(user_ids=from_id, fields='first_name')[0]
                        user_name = user_info['first_name']
                        user_mention = f"[id{from_id}|{user_name}]"
                    except Exception:
                        user_name = "друг"
                        user_mention = f"id{from_id}"

                    # Обновляем статистику слов для мем-пака
                    update_word_stats(peer_id, text)

                    # --- КОМАНДЫ ---
                    if text == '!