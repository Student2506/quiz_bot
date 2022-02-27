import logging
import os
from enum import Enum
from functools import partial
from pathlib import Path

import redis
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup
from telegram.ext import (CommandHandler, ConversationHandler, Filters,
                          MessageHandler, RegexHandler, Updater)

from import_quiz import import_quiz_files

logger = logging.getLogger(__name__)


class Choices(Enum):
    NEW_QUESTION = 'Новый вопрос'
    ANSWER = 'Ответ'
    GIVEUP = 'Сдаться'
    SCORE = 'Мой счёт'


def start(bot, update):
    """Send a message when the command /start is issued."""
    custom_keyboard = [
        [Choices.NEW_QUESTION.value, Choices.GIVEUP.value],
        [Choices.SCORE.value]
    ]
    reply_markup = ReplyKeyboardMarkup(custom_keyboard)
    update.message.reply_text(
        'Привет! Я бот для викторин!',
        reply_markup=reply_markup
    )
    return Choices.NEW_QUESTION.value


def handle_new_question_request(bot, update, redis_conn):
    logger.debug('question-handler\n')
    question_answer = redis_conn.hrandfield('quiz', 1, withvalues=True)
    redis_conn.set(update.message.from_user['id'], question_answer[1])
    update.message.reply_text(question_answer[0].decode())
    return Choices.ANSWER.value


def handle_solution_attempt(bot, update, redis_conn):
    logger.debug(f'answer-handler: {update.message.text}\n')
    answer = redis_conn.get(update.message.from_user['id']).decode()
    if answer.rstrip(' .') == update.message.text.rstrip(' .'):
        update.message.reply_text(
            'Правильно! Поздравляю! '
            'Для следующего вопроса нажми «Новый вопрос»'
        )
        return Choices.NEW_QUESTION.value
    else:
        update.message.reply_text('Неправильно… Попробуешь ещё раз?')
        return Choices.ANSWER.value


def handle_giveup(bot, update, redis_conn):
    logger.debug('giving up\n')
    answer = redis_conn.getdel(update.message.from_user['id'])
    update.message.reply_text(answer.decode())
    question_answer = redis_conn.hrandfield('quiz', 1, withvalues=True)
    redis_conn.set(update.message.from_user['id'], question_answer[1])
    update.message.reply_text(question_answer[0].decode())
    return Choices.ANSWER.value


def error(bot, update, error):
    """Log errors caused by Updates."""
    logger.warning(f'Update {update} caused error {error}')


def main():
    load_dotenv()
    quiz_bot_token = os.environ['QUIZ_BOT_TOKEN']
    quiz_redis_user = os.environ['QUIZ_REDIS_USER']
    quiz_redis_pass = os.environ['QUIZ_REDIS_PASS']
    quiz_redis_url = os.environ['QUIZ_REDIS_URL']
    quiz_redis_port = os.environ['QUIZ_REDIS_PORT']
    FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(format=FORMAT, level=logging.DEBUG)
    redis_conn = redis.Redis(
        host=quiz_redis_url,
        port=quiz_redis_port,
        db=0,
        username=quiz_redis_user,
        password=quiz_redis_pass
    )

    import_quiz_files(Path('quiz_files'), redis_conn)
    # telegram bot part
    updater = Updater(quiz_bot_token)
    dp = updater.dispatcher
    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            Choices.NEW_QUESTION.value: [
                MessageHandler(
                    Filters.text,
                    partial(
                        handle_new_question_request,
                        redis_conn=redis_conn,
                    )
                ),
            ],
            Choices.ANSWER.value: [
                RegexHandler(
                    f'^{Choices.GIVEUP.value}$',
                    partial(
                        handle_giveup,
                        redis_conn=redis_conn,
                    )
                ),
                MessageHandler(
                    Filters.text,
                    partial(
                        handle_solution_attempt,
                        redis_conn=redis_conn,
                    )
                ),

            ],
        },
        fallbacks=[]
    )
    dp.add_handler(conversation_handler)
    dp.add_error_handler(error)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
