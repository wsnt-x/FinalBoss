import logging
from aiogram import Bot, Dispatcher
from asyncio import create_task, run
from configs.config import BOT_TOKEN
from handlers.start import router as start_router
from handlers.tasks import router as tasks_router
from database import create_tables
from app_logging import setup_logging
from cron import cron

# Объект для записей в журнал: сюда бот будет писать, что он запустился и что база готова.
logger = logging.getLogger(__name__)


async def main():
    # Включаем понятный формат сообщений в консоли: время, уровень важности и текст.
    setup_logging()

    # Проверяем, есть ли нужные таблицы в базе. Если их нет, программа создаст их сама.
    await create_tables()
    logger.info("Database tables are ready")

    # Создаем самого Telegram-бота и помощника, который будет разбирать сообщения пользователей.
    bot=Bot(token=BOT_TOKEN)
    dp=Dispatcher()

    # Подключаем файлы с реакциями бота: отдельно стартовое меню и отдельно работу с задачами.
    dp.include_router(start_router)
    dp.include_router(tasks_router)

    logger.info("Bot started")

    # Запускаем отдельный цикл напоминаний, который будет работать рядом с ботом.
    create_task(cron(bot))
    logger.info("Cron started")

    # Бот начинает постоянно ждать новые сообщения и нажатия кнопок от пользователей.
    await dp.start_polling(bot)

# Запуск бота
run(main())
