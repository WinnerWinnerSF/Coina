import logging
import sqlite3
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler
import os

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Функция для создания базы данных и таблицы
def initialize_db():
    db_path = os.path.join(os.path.dirname(__file__), 'coins.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            coins REAL
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("База данных инициализирована.")

# Функция для добавления пользователя в базу данных
def add_user_to_db(user_id, username):
    db_path = os.path.join(os.path.dirname(__file__), 'coins.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    
    if result is None:
        cursor.execute("INSERT INTO users (user_id, username, coins) VALUES (?, ?, ?)", 
                       (user_id, username, 0))
        logger.info(f"Пользователь {username} добавлен в базу данных.")
    
    conn.commit()
    conn.close()

# Функция для обновления коинов
def update_coins(user_id, coins=0.0004):
    db_path = os.path.join(os.path.dirname(__file__), 'coins.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("UPDATE users SET coins = coins + ? WHERE user_id=?", (coins, user_id))
    
    conn.commit()
    conn.close()
    logger.info(f"Коины обновлены для пользователя ID {user_id}.")

# Команда /start
def start(update, context):
    update.message.reply_text("Привет! Я бот, который начисляет коины за сообщения.")

# Обработка сообщений
def handle_message(update, context):
    try:
        user = update.message.from_user
        if not user:
            raise ValueError("Нет данных пользователя.")
        user_id = user.id
        username = user.username if user.username else "Неизвестный пользователь"
        add_user_to_db(user_id, username)
        update_coins(user_id)
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}")
        update.message.reply_text("Произошла ошибка при обработке вашего сообщения.")

# Команда /coinlist
def coinlist(update, context):
    db_path = os.path.join(os.path.dirname(__file__), 'coins.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT username, coins FROM users ORDER BY coins DESC LIMIT 10")
    top_users = cursor.fetchall()
    
    message = "Топ 10 участников:\n"
    for i, (username, coins) in enumerate(top_users, start=1):
        message += f"{i}. {username}: {coins:.4f} коинов\n"
    
    update.message.reply_text(message)
    conn.close()

def main():
    initialize_db()
    
    TOKEN = '7391304816:AAE7PpQaJXwW7foZa4ycMfwqkobmZ6HA-kk'
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("coinlist", coinlist))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
    
