import logging
import os
import random
from dotenv import load_dotenv
from enum import Enum
from pathlib import Path

import redis
import vk_api as vk
from vk_api.keyboard import VkKeyboard
from vk_api.longpoll import VkEventType, VkLongPoll
from vk_api.utils import get_random_id

logger = logging.getLogger(__name__)


class Choices(Enum):
    NEW_QUESTION = 'Новый вопрос'
    ANSWER = 'Ответ'
    GIVEUP = 'Сдаться'
    SCORE = 'Мой счёт'


def handle_new_question_request(event, vk_api, keyboard, redis_conn, quiz):
    logger.debug('question-handler\n')
    pair = random.randint(0, len(quiz))
    redis_conn.set(event.user_id, pair)
    vk_api.messages.send(
        user_id=event.user_id,
        message=quiz[pair]['question'],
        random_id=get_random_id(),
        keyboard=keyboard.get_keyboard()
    )


def handle_solution_attempt(event, vk_api, keyboard, redis_conn, quiz):
    logger.debug(f'answer-handler: {event.text}\n')
    pair = int(redis_conn.get(event.user_id))
    if quiz[pair]['answer'].rstrip(' .') == event.text:
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


def handle_giveup(event, vk_api, keyboard, redis_conn, quiz):
    logger.debug('giving up\n')
    pair = int(redis_conn.getdel(event.user_id))
    vk_api.messages.send(
        user_id=event.user_id,
        message=quiz[pair]['answer'],
        random_id=get_random_id(),
        keyboard=keyboard.get_keyboard()
    )
    pair = random.randint(0, len(quiz))
    redis_conn.set(event.user_id, pair)
    vk_api.messages.send(
        user_id=event.user_id,
        message=quiz[pair]['question'],
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
    quiz_folder = Path('quiz_files')
    counter = 0
    question_flag = False
    answer_flag = False
    quiz = {}
    for file in quiz_folder.iterdir():
        with open(file, encoding='koi8-r') as fh:
            question = ''
            answer = ''
            for line in fh:
                if 'Вопрос' in line:
                    question_flag = True
                    continue
                if question_flag:
                    question += line.lstrip(' ')
                if question.endswith('\n\n'):
                    question_flag = False
                if 'Ответ' in line:
                    answer_flag = True
                    continue
                if answer_flag:
                    answer += line.lstrip(' ')
                if answer.endswith('\n\n'):
                    quiz[counter] = {
                        'question': question.replace('\n', ' ').rstrip(),
                        'answer': answer.replace('\n', ' ').rstrip()
                    }
                    counter += 1
                    question = ''
                    answer = ''
                    answer_flag = False
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
                        event, vk_api, keyboard, redis_conn, quiz
                    )
                elif event.text == Choices.GIVEUP.value:
                    handle_giveup(
                        event, vk_api, keyboard, redis_conn, quiz
                    )
                else:
                    handle_solution_attempt(
                        event, vk_api, keyboard, redis_conn, quiz
                    )
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
