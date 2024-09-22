import mysql.connector
import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

# Конфигурация логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Параметры подключения к базе данных
DB_CONFIG = {
    'user': 'u4599_p5zq1X6TiT',
    'password': '9b!zh74Q5ZkDxg=hNjXwSd!g',
    'host': '157.90.239.85',
    'port': '3306',
    'database': 's4599_Infoplayers'
}

# Глобальные переменные
game_active = None
current_prize = 0

def connect_db():
    """Установка соединения с базой данных."""
    return mysql.connector.connect(**DB_CONFIG)

def initialize_db():
    """Инициализация базы данных и таблицы."""
    try:
        connection = connect_db()
        cursor = connection.cursor()
        create_table_query = """
        CREATE TABLE IF NOT EXISTS coins (
            user_id BIGINT PRIMARY KEY,
            username VARCHAR(255),
            coins DECIMAL(10, 4)
        )
        """
        cursor.execute(create_table_query)
        connection.commit()
    except mysql.connector.Error as err:
        logger.error(f"Ошибка при подключении к базе данных: {err}")
    finally:
        cursor.close()
        connection.close()

def handle_message(update: Update, context: CallbackContext):
    """Обработка сообщений и начисление коинов."""
    if update.message is None or update.message.from_user is None:
        return
    
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    
    if username is None:
        return

    coins_earned = 0.0004

    try:
        connection = connect_db()
        cursor = connection.cursor()
        cursor.execute("SELECT coins FROM coins WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        
        if result:
            cursor.execute("UPDATE coins SET coins = coins + %s WHERE user_id = %s", (coins_earned, user_id))
        else:
            cursor.execute("INSERT INTO coins (user_id, username, coins) VALUES (%s, %s, %s)", 
                           (user_id, username, coins_earned))
        
        connection.commit()
    except mysql.connector.Error as err:
        logger.error(f"Ошибка при работе с базой данных: {err}")
    finally:
        cursor.close()
        connection.close()
    
    logger.info(f"Пользователю {username} начислено {coins_earned} коинов.")

def show_coins(update: Update, context: CallbackContext):
    """Команда /mycoins для показа количества франккоинов."""
    if update.message is None or update.message.from_user is None:
        return

    user_id = update.message.from_user.id
    username = update.message.from_user.username or "Неизвестный пользователь"
    
    try:
        connection = connect_db()
        cursor = connection.cursor()
        cursor.execute("SELECT username, coins FROM coins WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        
        chat_id = update.message.chat_id
        
        if result:
            db_username, coins = result
            if db_username != username:
                cursor.execute("UPDATE coins SET username = %s WHERE user_id = %s", (username, user_id))
                connection.commit()
                context.bot.send_message(chat_id=chat_id, text=f"Ваш юзернейм обновлен на @{username}.")
            message = f"@{username}, у вас {coins} франккоинов."
        else:
            message = f"@{username}, вы еще не получили франккоины."
        
        context.bot.send_message(chat_id=chat_id, text=message)
    except mysql.connector.Error as err:
        logger.error(f"Ошибка при работе с базой данных: {err}")
        context.bot.send_message(chat_id=update.message.chat_id, text="Произошла ошибка при получении данных.")
    finally:
        cursor.close()
        connection.close()

def show_top(update: Update, context: CallbackContext):
    """Команда /top для показа ТОП-20 пользователей по количеству коинов."""
    if update.message is None:
        return

    try:
        connection = connect_db()
        cursor = connection.cursor()
        cursor.execute("SELECT user_id, username, coins FROM coins")
        results = cursor.fetchall()
        
        for user in results:
            user_id, username, coins = user
            if username is None:
                cursor.execute("DELETE FROM coins WHERE user_id = %s", (user_id,))
        
        connection.commit()
        cursor.execute("SELECT username, coins FROM coins WHERE username IS NOT NULL ORDER BY coins DESC LIMIT 20")
        results = cursor.fetchall()
        
        chat_id = update.message.chat_id
        
        if results:
            top_message = "ТОП-20 пользователей по количеству франккоинов:\n\n"
            for rank, (username, coins) in enumerate(results, start=1):
                top_message += f"{rank}. @{username} — {coins} 🪙FCoin\n"
            context.bot.send_message(chat_id=chat_id, text=top_message)
        else:
            context.bot.send_message(chat_id=chat_id, text="В базе данных пока нет пользователей.")
    except mysql.connector.Error as err:
        logger.error(f"Ошибка при работе с базой данных: {err}")
        context.bot.send_message(chat_id=update.message.chat_id, text="Произошла ошибка при получении данных.")
    finally:
        cursor.close()
        connection.close()

def start_game(update: Update, context: CallbackContext, bet_side):
    """Запуск игры."""
    global game_active
    
    if game_active:
        context.bot.send_message(chat_id=update.message.chat_id, text="Игра уже активна.")
        return

    bettor_id = update.message.from_user.id
    bettor_username = update.message.from_user.username or "Неизвестный пользователь"

    if len(context.args) > 0:
        try:
            bet_amount = float(context.args[0])
        except ValueError:
            bet_amount = None
        
        if bet_amount is None or bet_amount <= 0:
            context.bot.send_message(chat_id=update.message.chat_id, text="Ошибка: Ставка должна быть положительным числом.")
            return

        if update.message.reply_to_message and update.message.reply_to_message.from_user:
            challenged_id = update.message.reply_to_message.from_user.id
            challenged_username = update.message.reply_to_message.from_user.username or "Неизвестный пользователь"

            game_active = {
                'bettor': bettor_id,
                'bettor_username': bettor_username,
                'challenged': challenged_id,
                'challenged_username': challenged_username,
                'bet_amount': bet_amount,
                'bet_side': bet_side,
                'chat_id': update.message.chat_id
            }

            send_bet_invitation(context, bettor_username, challenged_username, bet_amount, bet_side)
        else:
            context.bot.send_message(chat_id=update.message.chat_id, text="Ответьте на сообщение пользователя, чтобы его вызвать на игру.")
    else:
        context.bot.send_message(chat_id=update.message.chat_id, text="Ошибка: Ставка не указана.")

def send_bet_invitation(context, bettor_username, challenged_username, bet_amount, bet_side):
    """Отправка приглашения на игру."""
    side_translation = {'heads': 'орел', 'tails': 'решка'}
    bet_side_russian = side_translation.get(bet_side, 'неизвестно')

    keyboard = [
        [InlineKeyboardButton("Принять ставку", callback_data='accept')],
        [InlineKeyboardButton("Отмена", callback_data='cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_message(
        chat_id=game_active['chat_id'],
        text=f"@{bettor_username} вызывает @{challenged_username} на игру в орел-решка и ставит {bet_amount:.4f} франккоинов на {bet_side_russian}.",
        reply_markup=reply_markup
    )

def end_game(update: Update, context: CallbackContext, accepted: bool):
    """Закончить игру и предложить варианты умножения."""
    global game_active, current_prize
    
    if not game_active:
        context.bot.send_message(chat_id=update.message.chat_id, text="Нет активной игры.")
        return

    chat_id = game_active['chat_id']
    
    if accepted:
        bettor_id = game_active['bettor']
        bettor_username = game_active['bettor_username']
        challenged_id = game_active['challenged']
        challenged_username = game_active['challenged_username']
        bet_amount = game_active['bet_amount']
        bet_side = game_active['bet_side']
        
        result = random.choice(['heads', 'tails'])
        winner_id = bettor_id if (result == bet_side) else challenged_id
        
        if winner_id == bettor_id:
            current_prize = bet_amount
            context.bot.send_message(chat_id=chat_id, text=f"Поздравляем, @{bettor_username}! Вы выиграли {current_prize:.4f} франккоинов.")
        else:
            current_prize = 0
            # Проигравшему ничего не говорим

        # Умножение
        context.bot.send_message(chat_id=chat_id, text="Вы можете попробовать удвоить вашу победу. Нажмите кнопку ниже:")
        keyboard = [
            [InlineKeyboardButton("Удвоить", callback_data='double')],
            [InlineKeyboardButton("Не удваивать", callback_data='no_double')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(chat_id=chat_id, text="Выберите действие:", reply_markup=reply_markup)

    else:
        context.bot.send_message(chat_id=chat_id, text="Игра отменена.")
    
    game_active = None

def button(update: Update, context: CallbackContext):
    """Обработка нажатий на кнопки."""
    query = update.callback_query
    query.answer()

    if query.data == 'accept':
        end_game(update, context, accepted=True)
    elif query.data == 'cancel':
        end_game(update, context, accepted=False)
    elif query.data == 'double':
        if current_prize > 0:
            double_prize = current_prize * 2
            context.bot.send_message(chat_id=query.message.chat_id, text=f"Вы удвоили приз! Теперь у вас {double_prize:.4f} франккоинов.")
            current_prize = 0  # Сброс текущего приза
        else:
            context.bot.send_message(chat_id=query.message.chat_id, text="У вас нет приза для удвоения.")
    elif query.data == 'no_double':
        context.bot.send_message(chat_id=query.message.chat_id, text="Вы отказались от удвоения.")
    
def main():
    """Основная функция бота."""
    initialize_db()
    updater = Updater("7391304816:AAElyYZf991bag-UVEo8lxZsi2GYWOi8t4w", use_context=True)

    dp = updater.dispatcher
    dp.add_handler(CommandHandler("mycoins", show_coins))
    dp.add_handler(CommandHandler("top", show_top))
    dp.add_handler(CommandHandler("o", lambda update, context: start_game(update, context, 'heads')))  # Обработчик для орла
    dp.add_handler(CommandHandler("r", lambda update, context: start_game(update, context, 'tails')))  # Обработчик для решки
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dp.add_handler(CallbackQueryHandler(button))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
    
