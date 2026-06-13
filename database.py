from datetime import date, datetime  # работа с датами
from sqlalchemy import Integer, String, Date, DateTime, Boolean, select  # типы данных и инструмент для запросов
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker  # подключение и работа с базой
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column  # описание таблиц через Python-классы
from sqlalchemy.testing.suite.test_reflection import users
from aiogram.types import Message

# Подключение к файлу базы данных tasks.db.
# В этом файле будут храниться все задачи.
engine = create_async_engine("sqlite+aiosqlite:///tasks.db")

# Session помогает открывать короткое "общение" с базой:
# записать задачу, получить список, изменить или удалить запись.
Session = async_sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    # Служебный класс. Он нужен, чтобы Python-классы можно было связать с таблицами.
    pass


class DayTask(Base):
    # Описание одной задачи: какие поля будут храниться в таблице day_tasks.
    __tablename__ = "day_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # уникальный id
    title: Mapped[str] = mapped_column(String, nullable=False)  # название задачи обязательно
    description: Mapped[str | None] = mapped_column(String)  # описание может быть пустым
    task_date: Mapped[date] = mapped_column(Date, nullable=False)  # дата задачи
    is_done: Mapped[bool] = mapped_column(Boolean, default=False)  # выполнена или нет
    user_id: Mapped[str] = mapped_column(String, default=False)
    remind_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_reminded: Mapped[bool] = mapped_column(Boolean, default=False)


async def create_tables() -> None:
    # При старте программы проверяем, создана ли таблица для задач.
    # Если таблицы еще нет, создаем ее автоматически.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Добавляет новую задачу в базу данных и возвращает ее номер.
async def add_task(
    title: str,
    user_id: int,
    description: str | None = None,
    task_date: date | None = None,
    remind_at: datetime | None = None
) -> int:
    async with Session() as session:
        # Создаем новую задачу в памяти программы.
        task = DayTask(
            title=title,
            user_id=user_id,
            description=description,
            task_date=task_date or date.today(),
            remind_at=remind_at
        )

        # Добавляем задачу в базу и сохраняем изменения.
        session.add(task)
        await session.commit()

        return task.id


# Получает список задач из базы.
# Если указана дата, возвращает задачи только за этот день.
async def get_tasks(task_date: date | None = None) -> list[DayTask]:
    async with Session() as session:
        # Готовим запрос: "выбрать задачи".
        query = select(DayTask)

        if task_date is not None:
            # Если нужна конкретная дата, добавляем фильтр по дате.
            query = query.where(DayTask.task_date == task_date)

        # Сортируем задачи по их номеру, чтобы они шли в понятном порядке.
        query = query.order_by(DayTask.id)

        result = await session.execute(query)

        return list(result.scalars().all())


# Изменяет задачу по ее номеру.
# Можно поменять название, описание, дату или статус выполнения.
async def update_task(
    task_id: int,
    title: str | None = None,
    description: str | None = None,
    task_date: date | None = None,
    is_done: bool | None = None
) -> bool:
    async with Session() as session:
        # Ищем задачу по номеру.
        task = await session.get(DayTask, task_id)

        if task is None:
            # Если задачи с таким номером нет, сообщаем об этом вызывающему коду.
            return False

        # Ниже меняем только те поля, для которых пришло новое значение.
        if title is not None:
            task.title = title

        if description is not None:
            task.description = description

        if task_date is not None:
            task.task_date = task_date

        if is_done is not None:
            task.is_done = is_done

        await session.commit()

        return True


# Удаляет задачу по ее номеру.
# Возвращает True, если задача нашлась и была удалена.
async def delete_task(task_id: int) -> bool:
    async with Session() as session:
        # Сначала ищем задачу, которую нужно удалить.
        task = await session.get(DayTask, task_id)

        if task is None:
            # Если такой задачи нет, удалять нечего.
            return False

        # Удаляем найденную задачу и сохраняем изменения.
        await session.delete(task)
        await session.commit()

        return True

#
# async def main() -> None:
#     await create_tables()  # создаем таблицы
#     #пример добавления задачи
#     task_id = await add_task(
#         title="Купить продукты",
#         description="Молоко, яйца, хлеб",
#         task_date=date.today(),
#         user_id=message.from_user.id,
#     )
#     #пример обновления задачи
#     await update_task(
#         task_id=task_id,
#         is_done=True
#     )
#     #пример получения задачи
#     tasks = await get_tasks(date.today())
#
#     for task in tasks:
#         print(task.id, task.title, task.description, task.task_date, task.is_done)
#
#     await delete_task(task_id)
# # k = 1 * (4.6 - 2) / 0.4 =
# if __name__ == "__main__":
#     import asyncio  # запуск асинхронного кода
#
#     asyncio.run(main())  # стартуем event loop