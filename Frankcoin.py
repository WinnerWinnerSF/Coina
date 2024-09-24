import mysql.connector
import logging
import random
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

bot_start_time = time.time()
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

# Определяем глобальные переменные
winner_identified = None
betsizewinner = 0.0000
game_active = None

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
    
    # Проверка времени
    if update.message.date.timestamp() < bot_start_time:
        return  # Игнорировать сообщения до запуска бота

    user_id = update.message.from_user.id
    username = update.message.from_user.username
    
    # Если юзернейм отсутствует, просто выходим из функции
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
    
    logger.info(f"Пользователю {username} ({user_id}) начислено {coins_earned} коинов.")

def show_coins(update: Update, context: CallbackContext):
    """Команда /mycoins для показа количества франккоинов."""
    if update.message is None or update.message.from_user is None:
        logger.warning("Получено обновление без сообщения или информации о пользователе.")
        return

    user_id = update.message.from_user.id
    username = update.message.from_user.username or "Неизвестный пользователь"
    
    try:
        connection = connect_db()
        cursor = connection.cursor()
        
        # Получаем количество коинов, побед и проигрышей
        cursor.execute("SELECT username, coins, successful_game, unsuccessful_game FROM coins WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        
        chat_id = update.message.chat_id
        
        if result:
            db_username, coins, successful_game, unsuccessful_game = result
            if db_username != username:
                # Обновление юзернейма в базе данных
                cursor.execute("UPDATE coins SET username = %s WHERE user_id = %s", (username, user_id))
                connection.commit()
                context.bot.send_message(chat_id=chat_id, text=f"Ваш юзернейм обновлен на @{username}.")
                
            message = (f"@{username}, у вас {coins} франккоинов.\n"
                       f"Победы: {successful_game}, Проигрыши: {unsuccessful_game}")
        else:
            message = f"@{username}, вы еще не получили франккоины."
        
        context.bot.send_message(chat_id=chat_id, text=message)
    except mysql.connector.Error as err:
        logger.error(f"Ошибка при работе с базой данных: {err}")
        context.bot.send_message(chat_id=update.message.chat_id, text="Произошла ошибка при получении данных.")
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение: {e}")
    finally:
        cursor.close()
        connection.close()

def show_top(update: Update, context: CallbackContext):
    """Команда /top для показа ТОП-20 пользователей по количеству коинов."""
    if update.message is None:
        logger.warning("Получено обновление без сообщения.")
        return

    try:
        connection = connect_db()
        cursor = connection.cursor()
        
        # Получаем данные о пользователях, включая количество побед и проигрышей
        cursor.execute("""
            SELECT username, coins, successful_game, unsuccessful_game FROM coins
            WHERE username IS NOT NULL
            ORDER BY coins DESC
            LIMIT 20
        """)
        
        results = cursor.fetchall()
        
        chat_id = update.message.chat_id
        
        if results:
            top_message = "ТОП-20 пользователей по количеству франккоинов:\n\n"
            for rank, (username, coins, successful_game, unsuccessful_game) in enumerate(results, start=1):
                top_message += (f"{rank}. @{username} — {coins} 🪙FCoin | "
                                f"Победы: {successful_game}, Проигрыши: {unsuccessful_game}\n")
            context.bot.send_message(chat_id=chat_id, text=top_message)
        else:
            context.bot.send_message(chat_id=chat_id, text="В базе данных пока нет пользователей.")
    except mysql.connector.Error as err:
        logger.error(f"Ошибка при работе с базой данных: {err}")
        context.bot.send_message(chat_id=update.message.chat_id, text="Произошла ошибка при получении данных.")
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение: {e}")
    finally:
        cursor.close()
        connection.close() 
                
def start_game(update: Update, context: CallbackContext):
    """Запуск игры."""
    global game_active
    
    if game_active:
        context.bot.send_message(chat_id=update.message.chat_id, text="Игра уже активна.")
        return

    bettor_id = update.message.from_user.id
    bettor_username = update.message.from_user.username

    if bettor_username is None:
        context.bot.send_message(chat_id=update.message.chat_id, text="Ошибка: У вас скрыт юзернейм. Вы не можете играть.")
        return

    bet_side = None
    bet_amount = None
    
    if update.message.text.startswith('/o'):
        bet_side = 'heads'
    elif update.message.text.startswith('/r'):
        bet_side = 'tails'
    
    if bet_side:
        if len(context.args) > 0:
            try:
                bet_amount = float(context.args[0])
            except ValueError:
                bet_amount = None
        else:
            bet_amount = None
        
        if bet_amount is None:
            context.bot.send_message(chat_id=update.message.chat_id, text="Ошибка: Ставка не указана или указана неверно.")
            return

        if update.message.reply_to_message and update.message.reply_to_message.from_user:
            challenged_id = update.message.reply_to_message.from_user.id
            challenged_username = update.message.reply_to_message.from_user.username

            if challenged_username is None:
                context.bot.send_message(chat_id=update.message.chat_id, text="Ошибка: У пользователя, которого вы вызываете, скрыт юзернейм. Игра не может быть начата.")
                return

            chat_id = update.message.chat_id

            game_active = {
                'bettor': bettor_id,
                'challenged': challenged_id,
                'bet_amount': bet_amount,
                'bet_side': bet_side,
                'chat_id': chat_id,
                'started': False  # Игра ещё не началась
            }

            side_translation = {
                'heads': 'орел',
                'tails': 'решка'
            }
            
            try:
                connection = connect_db()
                cursor = connection.cursor()
                
                cursor.execute("SELECT coins FROM coins WHERE user_id = %s", (bettor_id,))
                bettor_coins = cursor.fetchone()
                cursor.execute("SELECT coins FROM coins WHERE user_id = %s", (challenged_id,))
                challenged_coins = cursor.fetchone()
                
                if bettor_coins and challenged_coins:
                    bettor_coins = bettor_coins[0]
                    challenged_coins = challenged_coins[0]
                    
                    if bettor_coins < bet_amount or challenged_coins < bet_amount:
                        context.bot.send_message(chat_id=update.message.chat_id, text="Недостаточно франккоинов для ставки.")
                        game_active = None
                        return
                    
                    keyboard = [
                        [InlineKeyboardButton("Принять ставку", callback_data='accept')],
                        [InlineKeyboardButton("Отмена", callback_data='cancel')]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    bet_side_russian = side_translation.get(bet_side, 'неизвестно')
                    
                    message = context.bot.send_message(
                        chat_id=update.message.chat_id,
                        text=f"@{bettor_username} ({bettor_id}) вызывает @{challenged_username} ({challenged_id}) на игру в орел-решка и ставит {bet_amount} франккоинов на {bet_side_russian}.",
                        reply_markup=reply_markup
                    )
                    game_active['message_id'] = message.message_id  # Сохраняем ID сообщения
                else:
                    context.bot.send_message(chat_id=update.message.chat_id, text="Ошибка при получении данных о франккоинах.")
            except mysql.connector.Error as err:
                logger.error(f"Ошибка при работе с базой данных: {err}")
                context.bot.send_message(chat_id=update.message.chat_id, text="Произошла ошибка при проверке данных о франккоинах.")
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение: {e}")
            finally:
                cursor.close()
                connection.close()
        else:
            context.bot.send_message(chat_id=update.message.chat_id, text="Ответьте на сообщение пользователя, чтобы его вызвать на игру.")
    else:
        context.bot.send_message(chat_id=update.message.chat_id, text="Ошибка в команде.")
def end_game(update: Update, context: CallbackContext, accepted: bool):
    """Закончить игру."""
    global game_active, winner_identified, betsizewinner
    
    if not game_active:
        context.bot.send_message(chat_id=update.message.chat_id, text="Нет активной игры.")
        return

    chat_id = game_active['chat_id']
    
    if accepted:
        bettor_id = game_active['bettor']
        challenged_id = game_active['challenged']
        bet_amount = game_active['bet_amount']
        bet_side = game_active['bet_side']
        
        try:
            connection = connect_db()
            cursor = connection.cursor()
            
            # Получение данных игроков
            bettor_data = cursor.execute("SELECT username, coins FROM coins WHERE user_id = %s", (bettor_id,))
            challenged_data = cursor.execute("SELECT username, coins FROM coins WHERE user_id = %s", (challenged_id,))
            
            if bettor_data and challenged_data:
                bettor_username, bettor_coins = bettor_data
                challenged_username, challenged_coins = challenged_data
                
                if bettor_coins < bet_amount or challenged_coins < bet_amount:
                    context.bot.send_message(chat_id=chat_id, text="Ошибка при проверке количества франккоинов.")
                    return
                
                result = 'heads' if random.choice([True, False]) else 'tails'
                winner_id = bettor_id if (result == bet_side) else challenged_id
                loser_id = challenged_id if winner_id == bettor_id else bettor_id
                
                winner_identified = winner_id
                betsizewinner = round(bet_amount, 4) * 2

                # Обновление монет
                cursor.execute("UPDATE coins SET coins = coins - %s WHERE user_id = %s", (bet_amount, loser_id))
                cursor.execute("UPDATE coins SET coins = coins + %s WHERE user_id = %s", (betsizewinner, winner_id))
                
                # Запись неудачной игры для проигравшего
                cursor.execute("UPDATE coins SET unsuccessful_game = unsuccessful_game + 1 WHERE user_id = %s", (loser_id,))
                
                connection.commit()
                
                victory_message = context.bot.send_message(chat_id=chat_id, 
                    text=f"🪙 Игра завершена! Выпал {'орел' if result == 'heads' else 'решка'}. Победитель: @{winner_username}. Ваш банк: {betsizewinner}")
                
                # Удаление сообщения с кнопками
                if 'message_id' in game_active:
                    context.bot.delete_message(chat_id=chat_id, message_id=game_active['message_id'])
                
            else:
                context.bot.send_message(chat_id=chat_id, text="Ошибка при получении данных о франккоинах.")
        except mysql.connector.Error as err:
            logger.error(f"Ошибка при работе с базой данных: {err}")
            context.bot.send_message(chat_id=update.message.chat_id, text="Произошла ошибка при обработке данных о франккоинах.")
        finally:
            cursor.close()
            connection.close()
    else:
        context.bot.send_message(chat_id=chat_id, text="Ставка была отменена.")                    

def button(update: Update, context: CallbackContext):
    """Обработка нажатий на кнопки."""
    global game_active, winner_identified, betsizewinner
    query = update.callback_query
    
    if query is None or query.message is None:
        logger.warning("Получено обновление без информации о запросе или сообщении.")
        return
    
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    
    if query.data == 'collect_prize':
        if user_id == winner_identified:
            try:
                connection = connect_db()
                cursor = connection.cursor()
                cursor.execute("UPDATE coins SET coins = coins + %s WHERE user_id = %s", (betsizewinner, user_id))
                connection.commit()
                
                # Запись удачной игры для победителя
                cursor.execute("UPDATE coins SET successful_game = successful_game + 1 WHERE user_id = %s", (user_id,))
                connection.commit()
                
                context.bot.send_message(chat_id=chat_id, text=f"Вы забрали приз! Сумма выигрыша: {betsizewinner}.")
                
                # Удаляем сообщение о победе
                context.bot.delete_message(chat_id=chat_id, message_id=query.message.message_id)
                
            finally:
                cursor.close()
                connection.close()
                
            winner_identified = None
            betsizewinner = 0.0000
            game_active = None
        else:
            context.bot.send_message(chat_id=chat_id, text="Вы не можете забрать приз, так как не являетесь победителем.")

    elif query.data == 'double':
        if user_id == winner_identified:
            win_amount = betsizewinner * 2 if random.choice([True, False]) else 0
            
            try:
                connection = connect_db()
                cursor = connection.cursor()
                
                if win_amount > 0:
                    cursor.execute("UPDATE coins SET coins = coins + %s WHERE user_id = %s", (win_amount, user_id))
                    cursor.execute("UPDATE coins SET successful_game = successful_game + 1 WHERE user_id = %s", (user_id,))
                    result_text = "Умножение на 2 успешно!"
                else:
                    cursor.execute("UPDATE coins SET unsuccessful_game = unsuccessful_game + 1 WHERE user_id = %s", (user_id,))
                    result_text = "Не удалось удвоить ставку."
                
                connection.commit()
            finally:
                cursor.close()
                connection.close()

            context.bot.send_message(chat_id=chat_id, text=f"{result_text} Новый банк победителя составляет: {win_amount}.")
            context.bot.delete_message(chat_id=chat_id, message_id=query.message.message_id)

            winner_identified = None
            betsizewinner = 0.0000
            game_active = None
        else:
            context.bot.send_message(chat_id=chat_id, text="Вы не можете выполнить это действие, так как не являетесь победителем.")
    
    elif query.data == 'accept':
        if user_id == game_active['challenged']:
            if game_active['started']:
                query.answer("Игра уже началась, вы не можете отменить ставку.")
                return
            
            # Удаляем сообщение с кнопками
            context.bot.delete_message(chat_id=chat_id, message_id=game_active['message_id'])
            game_active['started'] = True
            end_game(update, context, True)
        else:
            query.answer("Вы не можете принять эту ставку.")
  
    elif query.data == 'cancel':
        if user_id in [game_active['challenged'], game_active['bettor']]:
            if game_active['started']:
                query.answer("Игра уже началась, вы не можете отменить ставку.")
                return
            
            # Удаляем сообщение с кнопками
            context.bot.delete_message(chat_id=chat_id, message_id=game_active['message_id'])
            end_game(update, context, False)
            winner_identified = None
            betsizewinner = 0.00
            game_active = None
        else:
            query.answer("Вы не можете отменить эту ставку.")
    else:
        query.answer("Нет активной игры.")
    

def error_handler(update: Update, context: CallbackContext):
    """Обработчик ошибок."""
    logger.error(f"Ошибка при обработке обновления: {context.error}")

def onegram(update: Update, context: CallbackContext):
    """Команда /onegram для обмена 1 франккоина на ваучер."""
    if update.message.reply_to_message is None or update.message.reply_to_message.from_user is None:
        context.bot.send_message(chat_id=update.message.chat_id, text="Пожалуйста, ответьте на сообщение пользователя, чтобы провести обмен.")
        return

    user_id = update.message.reply_to_message.from_user.id
    chat_id = update.message.chat_id

    # Проверка, является ли пользователь администратором
    try:
        chat_administrators = context.bot.get_chat_administrators(chat_id)
        admin_ids = [admin.user.id for admin in chat_administrators]
        
        if update.message.from_user.id not in admin_ids:
            context.bot.send_message(chat_id=chat_id, text="Эта команда доступна только администраторам чата.")
            return

        with connect_db() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT coins FROM coins WHERE user_id = %s", (user_id,))
                result = cursor.fetchone()

                if result:
                    user_coins = result[0]

                    if user_coins >= 1:
                        cursor.execute("UPDATE coins SET coins = coins - 1 WHERE user_id = %s", (user_id,))
                        connection.commit()
                        message = f"Пользователь @{update.message.reply_to_message.from_user.username} обменял 1 коин на ваучер бесплатной покупки. Осталось {user_coins - 1} коинов."
                    else:
                        message = "У пользователя недостаточно коинов для обмена."
                else:
                    message = "Пользователь не найден в базе данных."

        context.bot.send_message(chat_id=chat_id, text=message)
    except mysql.connector.Error as err:
        logger.error(f"Ошибка при работе с базой данных: {err}")
        context.bot.send_message(chat_id=chat_id, text="Произошла ошибка при обработке данных.")
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение: {e}")

def cancel_game(update: Update, context: CallbackContext):
    """Команда /cg для сброса текущей игры."""
    global game_active
    
    if not game_active:
        context.bot.send_message(chat_id=update.message.chat_id, text="Нет активной игры для сброса.")
        return
    
    game_active = None

    context.bot.send_message(chat_id=update.message.chat_id, text="Игра была сброшена.")

def give_coins(update: Update, context: CallbackContext):
    """Команда /give для передачи коинов."""
    if update.message.reply_to_message is None:
        context.bot.send_message(chat_id=update.message.chat_id, text="Пожалуйста, ответьте на сообщение пользователя, чтобы подарить коины.")
        return

    user_id = update.message.from_user.id
    recipient_id = update.message.reply_to_message.from_user.id
    amount = context.args[0] if context.args else None

    try:
        amount = float(amount)
    except (ValueError, IndexError):
        context.bot.send_message(chat_id=update.message.chat_id, text="Ошибка: укажите корректное количество коинов для передачи.")
        return

    if amount <= 0:
        context.bot.send_message(chat_id=update.message.chat_id, text="Количество коинов должно быть больше нуля.")
        return

    try:
        connection = connect_db()
        cursor = connection.cursor()
        
        # Проверяем, есть ли у отправителя достаточное количество коинов
        cursor.execute("SELECT coins FROM coins WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        
        if result and result[0] >= amount:
            # Уменьшаем коинов у отправителя и увеличиваем у получателя
            cursor.execute("UPDATE coins SET coins = coins - %s WHERE user_id = %s", (amount, user_id))
            cursor.execute("UPDATE coins SET coins = coins + %s WHERE user_id = %s", (amount, recipient_id))
            connection.commit()
            
            context.bot.send_message(chat_id=update.message.chat_id, text=f"@{update.message.from_user.username} подарил {amount} коинов @{update.message.reply_to_message.from_user.username}.")
        else:
            context.bot.send_message(chat_id=update.message.chat_id, text="Недостаточно коинов для передачи.")
    except mysql.connector.Error as err:
        logger.error(f"Ошибка при работе с базой данных: {err}")
        context.bot.send_message(chat_id=update.message.chat_id, text="Произошла ошибка при передаче коинов.")
    finally:
        cursor.close()
        connection.close()

def main():
    """Запуск бота."""
    global job_queue
    
    initialize_db()
    
    TOKEN = '7391304816:AAElyYZf991bag-UVEo8lxZsi2GYWOi8t4w'
    
    updater = Updater(token=TOKEN, use_context=True)
    job_queue = updater.job_queue
    
    dispatcher = updater.dispatcher
    
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dispatcher.add_handler(CommandHandler('mycoins', show_coins))
    dispatcher.add_handler(CommandHandler('top', show_top))
    dispatcher.add_handler(CommandHandler('o', start_game))
    dispatcher.add_handler(CommandHandler('r', start_game))
    dispatcher.add_handler(CommandHandler('onegram', onegram))
    dispatcher.add_handler(CommandHandler('cg', cancel_game))
    dispatcher.add_handler(CommandHandler('give', give_coins))
    dispatcher.add_handler(CallbackQueryHandler(button))
    
    # Добавление обработчика ошибок
    dispatcher.add_error_handler(error_handler)
    
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
