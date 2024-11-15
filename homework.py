import logging
from logging.handlers import RotatingFileHandler
from http import HTTPStatus
import os
import sys
import time

from dotenv import load_dotenv
import requests
from telebot import TeleBot

from exceptions import (IncorrectResponseCodeError,
                        NotTokenError)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s, %(funcName)s, %(message)s, %(name)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(funcName)s - %(levelname)s - %(message)s'
)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)
file_handler = RotatingFileHandler(
    'my_logger.log',
    maxBytes=50000000,
    backupCount=5,
    encoding='utf-8'
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


def check_tokens():
    """Проверка токенов."""
    logger.debug('Загружаем токены')
    ENV_VARIABLES = (
        ('PRACTICUM_TOKEN', PRACTICUM_TOKEN),
        ('TELEGRAM_TOKEN', TELEGRAM_TOKEN),
        ('TELEGRAM_CHAT_ID', TELEGRAM_CHAT_ID)
    )
    not_all_tokens = []
    for name, value in ENV_VARIABLES:
        if not value:
            not_all_tokens.append(name)
    if not_all_tokens:
        message = f'Отсутствуют переменные среды: {not_all_tokens}'
        logger.critical(message)
        raise NotTokenError(message)


def send_message(bot, message):
    """Отправка сообщений в телеграм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as err:
        logger.error(f'Ошибка при отправке сообщения {err}')
        return False
    else:
        logger.debug(
            f'Сообщение "{message}"'
            f' отправлено пользователю с id: {TELEGRAM_CHAT_ID}'
        )
        return True


def get_api_answer(timestamp):
    """Проверка доступности эндпойнта."""
    payload = {'from_date': timestamp}
    params = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': payload
    }
    logger.debug('Начат запрос к API на эндпоинт {url}'
                 ' с параметрами {headers}'
                 ' и временем {params}'.format(**params))
    try:
        homework_statuses = requests.get(**params)
    except Exception as error:
        message = ('Ошибка подключения {error} '
                   'к эндпоинту {ENDPOINT}.'
                   'с параметрами {headers}.'
                   'и временем {params}.').format(error=error, **params)
        raise ConnectionError(message)
    if homework_statuses.status_code != HTTPStatus.OK:
        message = (f'Эндпоинт недоступен.'
                   f'Статус ответа {homework_statuses.status_code}.'
                   f'Причина ответа {homework_statuses.reason}.'
                   f'Текст ответа {homework_statuses.text}.')
        raise IncorrectResponseCodeError(message)
    return homework_statuses.json()


def check_response(response):
    """Проверка наличия ключей в respons'е."""
    if not isinstance(response, dict):
        raise TypeError('Неверный формат данных, ожидаем словарь')
    if not response.get('homeworks'):
        raise KeyError('Нет ключа homeworks!')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('Неверный формат homeworks, ожидаем список')
    return homeworks


def parse_status(homework):
    """Проверка статуса."""
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if not homework_name:
        raise KeyError('Отсутствует ключ - "homework_name"')
    elif not status:
        raise KeyError('Отсутствует ключ - "status"')
    elif status not in HOMEWORK_VERDICTS:
        raise ValueError('Неопознанный ключ. '
                         'Ключа "status" нет в "HOMEWORK_VERDICTS"')
    verdict = HOMEWORK_VERDICTS.get(status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = 0
    last_message = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            if not response:
                logger.debug('Новых статусов нет.')
                continue
            homework = check_response(response)[0]
            message = parse_status(homework)
            if last_message != message and send_message(bot, message):
                last_message = message
                timestamp = response.get('current_date', timestamp)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if message != last_message and send_message(bot, message):
                last_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
