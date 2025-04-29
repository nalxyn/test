from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram import Bot, Update, InputFile
import pandas as pd
import os, sqlite3

TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
DB_NAME = "sites.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            xpath TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Привет! Отправь мне Excel-файл с сайтами для парсинга.\n"
        "Формат файла:\n"
        "- title: Название сайта\n"
        "- url: Ссылка на сайт\n"
        "- xpath: XPath для цены"
    )

def handle_file(update: Update, context: CallbackContext):
    file = update.message.document.get_file()
    filename = file.download()
    try:
        df = pd.read_excel(filename)
        required_columns = ["title", "url", "xpath"]
        if not all(col in df.columns for col in required_columns):
            update.message.reply_text("Ошибка: в файле должны быть колонки 'title', 'url', 'xpath'.")
            return

        update.message.reply_text(f"Получены данные:\n{df.to_string(index=False)}")

        conn = sqlite3.connect(DB_NAME)
        df.to_sql("sites", conn, if_exists="append", index=False)
        conn.close()
        
        update.message.reply_text("✅ Данные успешно сохранены в базу!")
        
    except Exception as e:
        update.message.reply_text(f"Ошибка: {str(e)}")
    finally:
        os.remove(filename)

def main():
    init_db()
    updater = Updater(TOKEN)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.document, handle_file))
    
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
