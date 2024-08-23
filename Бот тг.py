import logging
import os
import time
from datetime import datetime
from io import BytesIO
from ssl import webdriver
from ssl.webdriver.chrome.service import Service
from ssl.webdriver.chrome.options import Options
from telegram import Update, InputMediaPhoto
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from webdriver_manager.chrome import ChromeDriverManager
# Конфигурация логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


# Константы
GROUP_URLS = {
    '5030301/40001': 'https://ruz.spbstu.ru/faculty/124/groups/40299',
    '5030301/40002': 'https://ruz.spbstu.ru/faculty/124/groups/40300',
}
CHROME_DRIVER_PATH = ChromeDriverManager().install()

# Кэш скриншотов
schedule_cache = {}


# Время хранения кеша в секундах (1 день)
cache_ttl = 86400


# Функция для получения скриншота
def get_schedule_screenshot(group_id: str) -> BytesIO:
    global schedule_cache

    today = datetime.now()
    week_number = today.strftime('%W')  # Номер недели в году
    url = GROUP_URLS.get(group_id)

    cache_key = f"{group_id}_{week_number}"
    if cache_key in schedule_cache:
        # Проверяем, не истекло ли время хранения кеша
        cache_timestamp = schedule_cache[cache_key]['timestamp']
        if time.time() - cache_timestamp < cache_ttl:
            logger.info(f"Returning cached screenshot for {cache_key}")
            return BytesIO(schedule_cache[cache_key]['screenshot'])
        else:
            # Если время хранения истекло, удаляем элемент из кеша
            del schedule_cache[cache_key]
            logger.info(f"Cache expired for {cache_key}")

    logger.info(f"Capturing screenshot for {cache_key}")

    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Запуск в фоновом режиме
    chrome_options.add_argument('--disable-gpu')

    service = Service(CHROME_DRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get(url)
        driver.implicitly_wait(10)

        # Прокрутка вниз для загрузки динамического контента
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        screenshot = driver.get_screenshot_as_png()
        # Добавляем элемент в кеш с текущим временем
        schedule_cache[cache_key] = {
            'screenshot': screenshot,
            'timestamp': time.time()
        }
    except Exception as e:
        logger.error(f"Error during screenshot capture: {e}")
        raise
    finally:
        driver.quit()

    return BytesIO(screenshot)


    if not url:
        raise ValueError('Unknown group ID')

    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Запуск в фоновом режиме
    chrome_options.add_argument('--disable-gpu')

    service = Service(CHROME_DRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get(url)
        driver.implicitly_wait(10)  # Подождем, пока страница загрузится

        # Прокрутка вниз для загрузки динамического контента (если нужно)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # Сделаем скриншот
        screenshot = driver.get_screenshot_as_png()
    except Exception as e:
        logger.error(f"Error during screenshot capture: {e}")
        raise
    finally:
        driver.quit()

    return BytesIO(screenshot)


# Обработчик команды /start
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        'Привет! Выбери свою группу:\n'
        '1. 5030301/40001\n'
        '2. 5030301/40002'
    )


# Обработчик сообщений
def handle_message(update: Update, context: CallbackContext) -> None:
    group_id = update.message.text.strip()
    if group_id in GROUP_URLS:
        try:
            screenshot = get_schedule_screenshot(group_id)
            update.message.reply_photo(photo=screenshot)
        except Exception as e:
            logger.error(f"Error fetching schedule: {e}")
            update.message.reply_text('Произошла ошибка при получении расписания. Попробуйте позже.')
    else:
        update.message.reply_text('Некорректный выбор. Пожалуйста, выберите 5030301/40001 или 5030301/40002.')


def main() -> None:
    token = os.getenv('TELEGRAM_BOT_TOKEN')  # Использование переменной окружения

    if not token:
        logger.error("Telegram bot token is not set in environment variables.")
        return

    updater = Updater(token)
    dispatcher = updater.dispatcher

    # Обработчики команд
    dispatcher.add_handler(CommandHandler("start", start))

    # Обработчик текстовых сообщений
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    # Запуск бота
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
