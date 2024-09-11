import sqlite3
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler

# Функция для создания базы данных и таблицы
def initialize_db():
    conn = sqlite3.connect('coins.db')
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

# Функция для добавления пользователя в базу данных
def add_user_to_db(user_id, username):
    conn = sqlite3.connect('coins.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    
    if result is None:
        cursor.execute("INSERT INTO users (user_id, username, coins) VALUES (?, ?, ?)", 
                       (user_id, username, 0))
    
    conn.commit()
    conn.close()

# Функция для обновления коинов
def update_coins(user_id, coins=0.0004):
    conn = sqlite3.connect('coins.db')
    cursor = conn.cursor()

    cursor.execute("UPDATE users SET coins = coins + ? WHERE user_id=?", (coins, user_id))
    
    conn.commit()
    conn.close()

# Команда /start
def start(update, context):
    update.message.reply_text("Привет! Я бот, который начисляет коины за сообщения.")

# Обработка сообщений
def handle_message(update, context):
    user = update.message.from_user
    add_user_to_db(user.id, user.username)  # Регистрируем пользователя
    update_coins(user.id)  # Начисляем коины
    update.message.reply_text(f"{user.username}, вам начислено 0.0004 коина!")

# Команда /coinlist
def coinlist(update, context):
    conn = sqlite3.connect('coins.db')
    cursor = conn.cursor()

    cursor.execute("SELECT username, coins FROM users ORDER BY coins DESC LIMIT 10")
    top_users = cursor.fetchall()
    
    message = "Топ 10 участников:\n"
    for i, (username, coins) in enumerate(top_users, start=1):
        message += f"{i}. {username}: {coins:.4f} коинов\n"
    
    update.message.reply_text(message)
    conn.close()

def main():
    initialize_db()  # Инициализируем базу данных
    
    TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    
    # Обработчики команд
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("coinlist", coinlist))
    
    # Обработчик сообщений
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
