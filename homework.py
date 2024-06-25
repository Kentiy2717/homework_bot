import logging
from http import HTTPStatus
import os
import requests
import sys
import time
from telebot import TeleBot
from dotenv import load_dotenv

from exceptions import (UnexpectedResponseError,
                        IncorrectResponseError,)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
ENV_VARIABLES = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]

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
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens():
    """Проверка токенов."""
    logger.debug('Загружаем токены')
    if not PRACTICUM_TOKEN or not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        message = 'Не найден токен. Программа остановлена.'
        logger.critical(message)
        sys.exit(message)
    # Евгений, подскажи, почему так тесты не проходят? Работает же!
    # for env in ENV_VARIABLES:
    #     if not env:
    #         logger.critical('Отсутствует переменная среды')
    #         # sys.exit('Работать не буду!')


def send_message(bot, message):
    """Отправка сообщений в телеграм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception:
        logger.error('Ошибка при отправке сообщения')
    else:
        logger.debug(
            f'Сообщение "{message}"'
            f' отправлено пользователю с id: {TELEGRAM_CHAT_ID}'
        )


def get_api_answer(timestamp):
    """Проверка доступности эндпойнта."""
    payload = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=payload
        )
        if homework_statuses.status_code != HTTPStatus.OK:
            message = (f'Эндпоинт недоступен.'
                       f'Статус ответа {homework_statuses.status_code}.')
            logger.error(message)
            raise requests.exceptions.HTTPError(message)
    except requests.exceptions.HTTPError as err:
        logger.error(err)
        raise UnexpectedResponseError(err) from err
    except requests.RequestException as err:
        logger.error(err)
        raise IncorrectResponseError(err) from err
    return homework_statuses.json()


def check_response(response):
    """Проверка наличия ключей в respons'е."""
    if not isinstance(response, dict):
        raise TypeError('Неверный формат данных, ожидаем словарь')
    if response.get('homeworks') is None:
        raise KeyError('Нет ключа homeworks!')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('Неверный формат homeworks, ожидаем список')
    if len(homeworks) == 0:
        message = 'Нет новых данных по домашней работе'
        logger.debug(message)
    return homeworks[0]


def parse_status(homework):
    """Проверка статуса."""
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if status is None or status not in HOMEWORK_VERDICTS:
        message = 'Ошибка ключа - {status}'
        logger.error(message)
        raise KeyError(message)
    elif not homework_name:
        message = 'Отсутствует ключ - "homework_name"'
        logger.error(message)
        raise KeyError(message)
    verdict = HOMEWORK_VERDICTS.get(status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            if response:
                homework = check_response(response)
                message = parse_status(homework)
                send_message(bot, message)
            else:
                logger.debug('Новых статусов нет.')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
        time.sleep(RETRY_PERIOD)
        timestamp = int(time.time())


if __name__ == '__main__':
    main()
