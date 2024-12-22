import os
import logging
from dotenv import load_dotenv
import openai
from flask import Flask, request, jsonify
from telegram import Update, Bot
from telegram.ext import Dispatcher, CallbackContext
from telegram.utils.request import Request
# Загрузить переменные из .env
load_dotenv()


# =============== Настройки логгера ===============
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# =============== Чтение переменных окружения ===============
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("Не установлен TELEGRAM_BOT_TOKEN в Environment Variables")

if not OPENAI_API_KEY:
    raise ValueError("Не установлен OPENAI_API_KEY в Environment Variables")

openai.api_key = OPENAI_API_KEY

# =============== Инициализация Flask ===============
app = Flask(__name__)

# =============== Настройка Telegram Bot ===============
# Создаём объект бота и диспетчер
bot = Bot(token=TELEGRAM_BOT_TOKEN, request=Request(con_pool_size=8))
dispatcher = Dispatcher(bot=bot, update_queue=None, use_context=True)

# =============== Хранение состояния диалогов в памяти (упрощённо) ===============
user_state = {}  
# user_state[user_id] = {
#   "history": [],  # список сообщений в формате [{"role": "user"/"assistant", "content": "..."}]
#   "stage": 1      # 1=Приветствие, 2=Выявление потребностей, 3=Презентация, 4=Доп.вопросы, 5=Обратная связь, 6=Закрытие
# }

# =============== System Prompt с логикой этапов ===============
SYSTEM_PROMPT = """
Ты — чат-бот туристической компании Family Place. Твоя цель — продавать однодневный тур в зоопарк Ньїредьгаза, следуя этапам:

Этап 1: Приветствие (краткое) и запрос разрешения задавать вопросы. (Если клиент не согласен - предложить короткую презентацию или переключить на менеджера.)
Этап 2: Выявление потребностей, задавай по одному вопросу за сообщение. Вопросы открытые, без возможности "нет". (Если клиент молчит или не хочет, дай краткую презентацию.)
Этап 3: Презентация (1) Отразить боль клиента, (2) Озвучить цену, (3) Обосновать преимущества. Используй максимум 2-3 сообщения.
Этап Доп. вопросов: "Есть ли еще вопросы?"
Этап Обратной связи: "Как вам предложение?"
Этап Закрытия сделки: предложить оплату, спросить способ (ПриватБанк/MonoBank), подтвердить оплату, отправить реквизиты.

Поддерживай дружественный и эмпатичный тон, называй ребёнка "ваша дитина", упоминай эмоции. Если клиент спрашивает про детали, отвечай кратко, не переходя к презентации раньше времени, если не завершён этап 2.

Если клиент долго не отвечает, при следующем сообщении можешь напомнить о туре. Если отказывается или сомневается, предложи "резерв на 24 часа" или "подключить менеджера".

Не выходи за рамки логики зоопарка Ньїредьгаза. Следуй структуре.
"""

# =============== Функция для общения с OpenAI ===============
def call_openai_api(user_id: int, user_text: str):
    """
    Отправляем user_text + system prompt + историю в OpenAI
    """
    # Инициализируем user_state для нового пользователя
    if user_id not in user_state:
        user_state[user_id] = {
            "history": [],
            "stage": 1
        }

    # Добавляем в историю сообщение от пользователя
    user_state[user_id]["history"].append({"role": "user", "content": user_text})

    # Формируем список messages для OpenAI: system + история
    messages_for_openai = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages_for_openai.extend(user_state[user_id]["history"])

    # Запрос к ChatCompletion
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages_for_openai,
            max_tokens=500,
            temperature=0.7
        )
        assistant_message = response["choices"][0]["message"]["content"]
        
        # Добавляем ответ ассистента в историю
        user_state[user_id]["history"].append({"role": "assistant", "content": assistant_message})

        return assistant_message

    except Exception as e:
        logging.error(f"OpenAI API error: {e}")
        return "Извините, произошла ошибка при обращении к ИИ. Попробуйте позже."

# =============== Обработка входящих апдейтов от Telegram ===============
def process_telegram_update(update: Update, context: CallbackContext):
    """
    Функция вызывается при каждом сообщении от пользователя
    """
    if update.message:
        chat_id = update.message.chat_id
        user_text = update.message.text
        
        # вызов нашей логики (openai)
        reply_text = call_openai_api(chat_id, user_text)
        
        # отправляем ответ в Telegram
        context.bot.send_message(chat_id=chat_id, text=reply_text)

# Регистрируем handler
from telegram.ext import MessageHandler, Filters
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, process_telegram_update))


# =============== Flask route для webhook ===============
@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Точка входа для запросов от Telegram
    """
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, bot)
        dispatcher.process_update(update)
    except Exception as e:
        logging.error(f"webhook error: {e}")
    return jsonify({"status": "ok"})

# Маршрут для проверки (GET)
@app.route("/", methods=["GET"])
def index():
    return "Hello, this is your Zoo-bot on Render!"

