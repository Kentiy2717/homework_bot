import logging
import os
import requests
import sys
import time
from datetime import datetime

from telebot import TeleBot, types
from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
ENV_VARIABLES = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]

RETRY_PERIOD = 20  # надо 600
VERIFICATION_INTERVAL = 270 * 60 * 60 * 24  # 7 дней в Unix
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """check_tokens."""
    for env in ENV_VARIABLES:
        if not env:
            print(f'Отсутствует необходимая переменные среды - {env}')
            sys.exit('Работать не буду!')


def send_message(bot, message):
    """send_message."""
    bot.send_message(TELEGRAM_CHAT_ID, message)


def get_api_answer(timestamp):
    """get_api_answer."""
    payload = {'from_date': timestamp}
    homework_statuses = requests.get(
        ENDPOINT,
        headers=HEADERS,
        params=payload
    )
    return homework_statuses.json()


def check_response(response):
    """check_response."""
    homework = response['homeworks']
    return homework


def parse_status(homework):
    """parse_status."""
    homework_name = homework['lesson_name']
    for status in HOMEWORK_VERDICTS:
        if status == homework['status']:
            verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    # Создаем объект класса бота
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time()) - VERIFICATION_INTERVAL
    bot.send_message(
        TELEGRAM_CHAT_ID,
        'За все время Вашей учебы были сданы на проверку следующие работы:'
    )
    while True:
        try:
            response = get_api_answer(timestamp)
            if len(response['homeworks']):
                homeworks = check_response(response)
                for homework in homeworks:
                    message = parse_status(homework)
                    send_message(bot, message)
            time.sleep(RETRY_PERIOD)
            timestamp = int(time.time())

        except Exception as error:
            message = f'Сбой в работе программы: {error}'


if __name__ == '__main__':
    main()
