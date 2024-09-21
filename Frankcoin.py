import mysql.connector
import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

# Конфигурация логирования и подключения к базе данных
logging.basicConfig(level=logging.INFO)
DB_CONFIG = {
    'user': 'u4599_p5zq1X6TiT',
    'password': '9b!zh74Q5ZkDxg=hNjXwSd!g',
    'host': '157.90.239.85',
    'port': '3306',
    'database': 's4599_Infoplayers'
}

game_active = None

def connect_db():
    return mysql.connector.connect(**DB_CONFIG)

def initialize_db():
    with connect_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS coins (
                    user_id BIGINT PRIMARY KEY,
                    username VARCHAR(255),
                    coins DECIMAL(10, 4)
                )
            """)
            conn.commit()

def execute_query(query, params=None):
    with connect_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall() if 'SELECT' in query else None

def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    if not username:
        logging.info("Пользователь без юзернейма. Coins не начислены.")
        return  # Не начисляем коины, если юзернейма нет

    coins_earned = 0.0004
    existing_user = execute_query("SELECT coins FROM coins WHERE user_id = %s", (user_id,))
    if existing_user:
        execute_query("UPDATE coins SET coins = coins + %s WHERE user_id = %s", (coins_earned, user_id))
    else:
        execute_query("INSERT INTO coins (user_id, username, coins) VALUES (%s, %s, %s)", 
                       (user_id, username, coins_earned))

    logging.info(f"Пользователю {username} ({user_id}) начислено {coins_earned} коинов.")

def start_game(update: Update, context: CallbackContext):
    global game_active
    if game_active:
        context.bot.send_message(chat_id=update.message.chat_id, text="Игра уже активна.")
        return

    username = update.message.from_user.username
    if not username:
        context.bot.send_message(chat_id=update.message.chat_id, text="Для участия в игре необходим юзернейм.")
        return  # Не позволяем игроку начать игру без юзернейма

    bet_side = 'heads' if update.message.text.startswith('/o') else 'tails' if update.message.text.startswith('/r') else None
    bet_amount = float(context.args[0]) if context.args else None
    if not bet_side or bet_amount is None:
        context.bot.send_message(chat_id=update.message.chat_id, text="Ошибка: неверная ставка.")
        return

    challenged_id = update.message.reply_to_message.from_user.id if update.message.reply_to_message else None
    if challenged_id:
        challenged_username = context.bot.get_chat_member(chat_id=update.message.chat_id, user_id=challenged_id).user.username
        if not challenged_username:
            context.bot.send_message(chat_id=update.message.chat_id, text="Приглашенный игрок должен иметь юзернейм.")
            return  # Не позволяем участвовать без юзернейма

        bettor_coins = execute_query("SELECT coins FROM coins WHERE user_id = %s", (update.message.from_user.id,))
        challenged_coins = execute_query("SELECT coins FROM coins WHERE user_id = %s", (challenged_id,))

        if bettor_coins and challenged_coins and bettor_coins[0][0] >= bet_amount and challenged_coins[0][0] >= bet_amount:
            game_active = {'bettor': update.message.from_user.id, 'challenged': challenged_id, 'bet_amount': bet_amount, 'bet_side': bet_side}
            keyboard = [[InlineKeyboardButton("Принять ставку", callback_data='accept'), InlineKeyboardButton("Отмена", callback_data='cancel')]]
            context.bot.send_message(chat_id=update.message.chat_id, text=f"@{username} вызывает @{challenged_username} на игру в орел-решка с ставкой {bet_amount} на {bet_side}.", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            context.bot.send_message(chat_id=update.message.chat_id, text="Недостаточно франккоинов для ставки.")

def show_coins(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    coins = execute_query("SELECT coins FROM coins WHERE user_id = %s", (user_id,))
    message = f"@{update.message.from_user.username}, у вас {coins[0][0] if coins else 0} франккоинов."
    context.bot.send_message(chat_id=update.message.chat_id, text=message)

def show_top(update: Update, context: CallbackContext):
    results = execute_query("SELECT username, coins FROM coins ORDER BY coins DESC LIMIT 20")
    top_message = "ТОП-20 пользователей:\n\n" + "\n".join(f"{rank + 1}. @{username} — {coins} 🪙FCoin" 
                                for rank, (username, coins) in enumerate(results)) if results else "В базе данных пока нет пользователей."
    context.bot.send_message(chat_id=update.message.chat_id, text=top_message)

def end_game(update: Update, context: CallbackContext, accepted: bool):
    global game_active
    if not game_active:
        context.bot.send_message(chat_id=update.message.chat_id, text="Нет активной игры.")
        return

    winner_id = game_active['bettor'] if random.choice([True, False]) else game_active['challenged']
    bet_amount = game_active['bet_amount']
    execute_query("UPDATE coins SET coins = coins + %s WHERE user_id = %s", (bet_amount, winner_id))
    execute_query("UPDATE coins SET coins = coins - %s WHERE user_id = %s", (bet_amount, game_active['challenged'] if winner_id == game_active['bettor'] else game_active['bettor']))
    
    context.bot.send_message(chat_id=update.message.chat_id, text=f"🪙 Игра завершена! Победитель: @{update.message.from_user.username}. Заработал: {bet_amount} франккоинов.")
    game_active = None

def button(update: Update, context: CallbackContext):
    query = update.callback_query
    if query.data == 'accept':
        if query.from_user.id == game_active['challenged']:
            end_game(update, context, True)
    elif query.data == 'cancel':
        end_game(update, context, False)

def error_handler(update: Update, context: CallbackContext):
    logging.error(f"Ошибка: {context.error}")

def onegram(update: Update, context: CallbackContext):
    user_id = update.message.reply_to_message.from_user.id
    if update.message.from_user.id not in [admin.user.id for admin in context.bot.get_chat_administrators(update.message.chat_id)]:
        context.bot.send_message(chat_id=update.message.chat_id, text="Команда доступна только администраторам.")
        return

    coins = execute_query("SELECT coins FROM coins WHERE user_id = %s", (user_id,))
    if coins and coins[0][0] >= 1:
        execute_query("UPDATE coins SET coins = coins - 1 WHERE user_id = %s", (user_id,))
        context.bot.send_message(chat_id=update.message.chat_id, text=f"Пользователь @{update.message.reply_to_message.from_user.username} обменял 1 коин на ваучер.")
    else:
        context.bot.send_message(chat_id=update.message.chat_id, text="Недостаточно коинов для обмена.")

def cancel_game(update: Update, context: CallbackContext):
    global game_active
    if not game_active:
        context.bot.send_message(chat_id=update.message.chat_id, text="Нет активной игры для сброса.")
        return
    game_active = None
    context.bot.send_message(chat_id=update.message.chat_id, text="Игра сброшена.")

def update_usernames(update: Update, context: CallbackContext):
    """Команда для обновления юзернеймов в базе данных."""
    users = execute_query("SELECT user_id FROM coins")
    for user_id in users:
        new_username = context.bot.get_chat_member(chat_id=update.effective_chat.id, user_id=user_id[0]).user.username
        execute_query("UPDATE coins SET username = %s WHERE user_id = %s", (new_username, user_id[0]))
    context.bot.send_message(chat_id=update.message.chat_id, text="Юзернеймы обновлены.")

def main():
    initialize_db()
    updater = Updater(token='7391304816:AAElyYZf991bag-UVEo8lxZsi2GYWOi8t4w', use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dispatcher.add_handler(CommandHandler('mycoins', show_coins))
    dispatcher.add_handler(CommandHandler('top', show_top))
    dispatcher.add_handler(CommandHandler(['o', 'r'], start_game))
    dispatcher.add_handler(CommandHandler('onegram', onegram))
    dispatcher.add_handler(CommandHandler('cg', cancel_game))
    dispatcher.add_handler(CommandHandler('update_usernames', update_usernames))
    dispatcher.add_handler(CallbackQueryHandler(button))
    dispatcher.add_error_handler(error_handler)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
            
