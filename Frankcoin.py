import json
import os
import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Конфигурация логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Путь к файлу данных
DATA_FILE = 'coins.json'

def initialize_data():
    """Инициализация файла данных."""
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w') as file:
            json.dump({}, file)

def load_data():
    """Загрузка данных из JSON-файла."""
    with open(DATA_FILE, 'r') as file:
        return json.load(file)

def save_data(data):
    """Сохранение данных в JSON-файл."""
    with open(DATA_FILE, 'w') as file:
        json.dump(data, file, indent=4)

def handle_message(update: Update, context: CallbackContext):
    """Обработка сообщений и начисление коинов."""
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "Неизвестный пользователь"
    
    # Определяем количество коинов за сообщение
    coins_earned = 0.0004

    data = load_data()
    
    if str(user_id) not in data:
        data[str(user_id)] = {"username": username, "coins": 0}
    
    data[str(user_id)]["coins"] += coins_earned
    save_data(data)
    
    logger.info(f"Пользователю {username} ({user_id}) начислено {coins_earned} коинов. Всего: {data[str(user_id)]['coins']}")

def show_coins(update: Update, context: CallbackContext):
    """Команда /coins для показа количества коинов."""
    user_id = update.message.from_user.id
    data = load_data()
    
    if str(user_id) in data:
        coins = data[str(user_id)]['coins']
        update.message.reply_text(f"У вас {coins} коинов.")
    else:
        update.message.reply_text("Вы еще не получили коины.")

def main():
    """Запуск бота."""
    # Инициализация данных
    initialize_data()
    
    # Вставьте ваш токен здесь
    TOKEN = '7391304816:AAE7PpQaJXwW7foZa4ycMfwqkobmZ6HA-kk'
    
    # Создание объекта Updater
    updater = Updater(token=TOKEN, use_context=True)
    
    # Получение диспетчера для регистрации обработчиков
    dispatcher = updater.dispatcher
    
    # Регистрация обработчиков команд и сообщений
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dispatcher.add_handler(CommandHandler('coins', show_coins))
    
    # Запуск бота
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
    
