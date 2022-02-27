import logging
import os
from enum import Enum
from pathlib import Path

import redis
import vk_api as vk
from dotenv import load_dotenv
from vk_api.keyboard import VkKeyboard
from vk_api.longpoll import VkEventType, VkLongPoll
from vk_api.utils import get_random_id

from import_quiz import import_quiz_files

logger = logging.getLogger(__name__)


class Choices(Enum):
    NEW_QUESTION = 'Новый вопрос'
    ANSWER = 'Ответ'
    GIVEUP = 'Сдаться'
    SCORE = 'Мой счёт'


def handle_new_question_request(event, vk_api, keyboard, redis_conn):
    logger.debug('question-handler\n')
    question_answer = redis_conn.hrandfield('quiz', 1, withvalues=True)
    redis_conn.set(event.user_id, question_answer[1])
    vk_api.messages.send(
        user_id=event.user_id,
        message=question_answer[0],
        random_id=get_random_id(),
        keyboard=keyboard.get_keyboard()
    )


def handle_solution_attempt(event, vk_api, keyboard, redis_conn):
    logger.debug(f'answer-handler: {event.text}\n')
    answer = redis_conn.get(event.user_id).decode()
    if answer.rstrip(' .') == event.text:
        vk_api.messages.send(
            user_id=event.user_id,
            message=(
                'Правильно! Поздравляю! Для следующего вопроса нажми '
                '«Новый вопрос»'
            ),
            random_id=get_random_id(),
            keyboard=keyboard.get_keyboard()
        )
    else:
        vk_api.messages.send(
            user_id=event.user_id,
            message='Неправильно… Попробуешь ещё раз?',
            random_id=get_random_id(),
            keyboard=keyboard.get_keyboard()
        )


def handle_giveup(event, vk_api, keyboard, redis_conn):
    logger.debug('giving up\n')
    answer = redis_conn.getdel(event.user_id)
    vk_api.messages.send(
        user_id=event.user_id,
        message=answer,
        random_id=get_random_id(),
        keyboard=keyboard.get_keyboard()
    )
    question_answer = redis_conn.hrandfield('quiz', 1, withvalues=True)
    redis_conn.set(event.user_id, question_answer[1])
    vk_api.messages.send(
        user_id=event.user_id,
        message=question_answer[0],
        random_id=get_random_id(),
        keyboard=keyboard.get_keyboard()
    )


def main():
    load_dotenv()
    quiz_vk_token = os.environ['QUIZ_VK_TOKEN']
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
    # vk bot part
    vk_session = vk.VkApi(token=quiz_vk_token)
    vk_api = vk_session.get_api()
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button(Choices.NEW_QUESTION.value)
    keyboard.add_button(Choices.GIVEUP.value)
    keyboard.add_line()
    keyboard.add_button(Choices.SCORE.value)
    longpoll = VkLongPoll(vk_session)
    try:
        for event in longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                if event.text == Choices.NEW_QUESTION.value:
                    handle_new_question_request(
                        event, vk_api, keyboard, redis_conn
                    )
                elif event.text == Choices.GIVEUP.value:
                    handle_giveup(
                        event, vk_api, keyboard, redis_conn
                    )
                else:
                    handle_solution_attempt(
                        event, vk_api, keyboard, redis_conn
                    )
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
