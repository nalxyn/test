from datetime import datetime
from openai import OpenAI
import os, telebot, psycopg2

# Конфигурация
DB_NAME = 'postgres' # Название базы данных
DB_USER = 'postgres' # Имя пользователя базы данных
DB_PASSWORD = '' # Пароль для пользователя базы данных
HOST = 'localhost' # Хост для базы данных
PORT = '5432' # Порт базы данных
TELEGRAM_TOKEN = 'TELEGRAM_TOKEN' # TOKEN для TELEGRAM
OPENAI_API_KEY = 'OPENAI_API_KEY' # API ключ для OPENAI
DB_URL = f'postgresql://{DB_USER}:{DB_PASSWORD}@{HOST}:{PORT}/{DB_NAME}' # URL для подключения к базе данных(например: postgresql://user:password@localhost:5432/dbname)
gpt_v = 'gpt-3.5-turbo' # Выбор версии модели для взаимоедействия с  OpenAI(например: "gpt-3.5-turbo" или "gpt-4")
gpt_token = 1000 # Максимальное количество токенов для AI модели(для модели "gpt-3.5-turbo" максимальное значение 4096)
gpt_temperature = 0.7 # баланса между креативностью и точностью для AI модели(оптимальные настройки для модели "gpt-3.5-turbo" = 0.7)

# Подключение к PostgreSQL
def db_connection():
    try:
        return psycopg2.connect(DB_URL)
    except Exception as e:
        print(f'[DB ERROR]: {e}')

# Создание таблицы для хранения данных, если нет таблицы
def init_db():
    conn = db_connection()
    with conn.cursor() as cur:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS chat_context (
                user_id BIGINT PRIMARY KEY,
                context TEXT,
                updated_at TIMESTAMP
            )
        ''')
    conn.commit()
    conn.close()

# Инициализация Telegram бота, OpenAI и DB
bot = telebot.TeleBot(TELEGRAM_TOKEN)
ai = OpenAI(api_key=OPENAI_API_KEY)
init_db()

# Функции для работы с контекстом
def get_user_context(user_id):
    conn = db_connection()
    with conn.cursor() as cur:
        cur.execute(f'SELECT context FROM chat_context WHERE user_id = {user_id}')
        result = cur.fetchone()
    conn.close()
    return result[0] if result else None

def update_user_context(user_id, context):
    conn = db_connection()
    with conn.cursor() as cur:
        cur.execute('''
            INSERT INTO chat_context (user_id, context, updated_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id) 
            DO UPDATE SET context = EXCLUDED.context, updated_at = EXCLUDED.updated_at
        ''', (user_id, context, datetime.now()))
    conn.commit()
    conn.close()

def clear_user_context(user_id):
    conn = db_connection()
    with conn.cursor() as cur:
        cur.execute(f'DELETE FROM chat_context WHERE user_id = {user_id}')
    conn.commit()
    conn.close()

# Обработка команд
@bot.message_handler(commands=['start'])
def tg_start(message):
    bot.reply_to(message, 'Привет! Я ИИ-бот, я почти живой. Спроси меня что-нибудь и я постараюсь тебе помочь!')

@bot.message_handler(commands=['help'])
def tg_help(message):
    help_text = '''
    Доступные команды:
    /start - начать общение
    /help  - показать справку
    /reset - очистить переписку
    /about - информация о боте
    '''
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['reset'])
def tg_reset_context(message):
    clear_user_context(message.from_user.id)
    bot.reply_to(message, 'Контекст разговора сброшен. Я всё забыл, что было до этого.')

@bot.message_handler(commands=['about'])
def tg_about(message):
    about_text = '''
    Я бот с искуственным интелектом и использую OpenAI GPT для генерации ответов.
    Спроси меня что-нибудь и я постараюсь тебе помочь!
    '''
    bot.reply_to(message, about_text)

# Обработка текстовых сообщений
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    user_message = message.text

    # Формируем сообщения для OpenAI
    messages = []
    messages.append({'role': 'user', 'content': user_message})

    try:
        # Оптимизация: очищаем контекст, если он слишком длинный
        if len(str(messages)) > 3000:
            print('Разговор слишком длинный, нужно очистить часть истории.')
            messages = messages[-4:]  # Оставляем последние 4 сообщения
            bot.send_message(message.chat.id, 'Разговор слишком длинный, очищю часть истории.')

        # Запрос к OpenAI
        response = ai.chat.completions.create(model=gpt_v, messages=messages, max_tokens=gpt_token, temperature=gpt_temperature)
        ai_resp = response.choices[0].message
        ai_response = ai_resp.model_dump().get('content')
        # Обновляем контекст
        messages.append({'role': 'assistant', 'content': ai_response})
        update_user_context(chat_id, str(messages))
        # Отправляем ответ
        bot.reply_to(message, ai_response)
    except Exception as e:
        print(f'[ERROR]: {e}')
        bot.reply_to(message, 'Извините, произошла ошибка. Пожалуйста, попробуйте еще раз.')

if __name__ == '__main__':
    print('[INFO]: Бот запущен...')
    bot.infinity_polling()
