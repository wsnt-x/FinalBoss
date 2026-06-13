from aiogram.fsm.context import FSMContext
from datetime import date, datetime
from keyboards.inline import delete_task_keyboard, toggle_task_keyboard
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State,StatesGroup
from database import add_task, get_tasks, delete_task, update_task
from lexicons.lexicons_ru import START_BTN_1, START_BTN_2, START_BTN_3, START_BTN_4


# Состояние "бот ждет название задачи".
# Оно нужно, чтобы бот понимал: следующее сообщение пользователя надо сохранить как задачу.
class AddTask(StatesGroup):
    waiting_title = State()
    waiting_remind_time = State()

# Здесь собираются все реакции бота, которые относятся к задачам.
router=Router()

# Эти тексты являются кнопками меню. Если пользователь нажал такую кнопку,
# бот не должен считать ее названием новой задачи.
MAIN_MENU_BUTTONS = {START_BTN_1, START_BTN_2, START_BTN_3, START_BTN_4}


async def show_add_task_prompt(message: Message, state: FSMContext):
    # Просим пользователя написать название задачи.
    # После этого бот будет ждать именно текст задачи.
    await message.answer(
        "➕ <b>Новая задача</b>\n\nВведите название задачи:",
        parse_mode="HTML"
    )
    await state.set_state(AddTask.waiting_title)


async def show_tasks_list(message: Message):
    # Берем из базы все задачи на сегодняшний день.
    tasks = await get_tasks(task_date=date.today())

    if not tasks:
        await message.answer("📭 На сегодня задач пока нет.")
        return

    # Собираем один общий текст со всеми задачами, чтобы отправить его одним сообщением.
    text = "📋 <b>Задачи на сегодня</b>\n\n"
    for number, task in enumerate(tasks, start=1):
        status = "✅" if task.is_done else "⬜"
        text += f"{number}. {status} {task.title}\n"

    await message.answer(text, parse_mode="HTML")


async def show_delete_task_menu(message: Message):
    # Получаем задачи и показываем кнопки удаления.
    # Каждая кнопка относится к одной конкретной задаче.
    tasks = await get_tasks(task_date=date.today())

    if not tasks:
        await message.answer("📭 На сегодня задач пока нет.")
        return

    await message.answer(
        "🗑 <b>Удаление задачи</b>\n\nВыберите задачу, которую нужно удалить:",
        reply_markup=delete_task_keyboard(tasks),
        parse_mode="HTML"
    )


async def show_toggle_task_menu(message: Message):
    # Получаем задачи и показываем кнопки для смены статуса:
    # выполнена задача или еще нет.
    tasks = await get_tasks(task_date=date.today())

    if not tasks:
        await message.answer("📭 На сегодня задач пока нет.")
        return

    await message.answer(
        "✅ <b>Статус задачи</b>\n\nВыберите задачу, чтобы изменить статус:",
        reply_markup=toggle_task_keyboard(tasks),
        parse_mode="HTML"
    )


@router.message(F.text == START_BTN_1)
async def add_task_message_handler(message: Message, state: FSMContext):
    # Пользователь нажал обычную кнопку "Добавить задачу" в меню.
    await show_add_task_prompt(message, state)


@router.callback_query(F.data == "add_task")
async def add_task_handler(callback: CallbackQuery,state: FSMContext):
    # Пользователь нажал кнопку добавления внутри сообщения.
    await show_add_task_prompt(callback.message, state)
    await callback.answer()


@router.message(AddTask.waiting_title)
async def waiting_title_handler(message: Message, state: FSMContext):
    # Здесь бот получает текст, который пользователь ввел как название новой задачи.
    title = message.text.strip()

    if title in MAIN_MENU_BUTTONS:
        # Если вместо названия пользователь нажал кнопку меню,
        # прекращаем добавление задачи и возвращаем его к обычному выбору действий.
        await state.clear()
        await message.answer("Добавление задачи отменено. Выберите действие на клавиатуре.")
        return

    if not title:
        # Пустую строку нельзя сохранить как задачу.
        await message.answer("⚠️ Название задачи не может быть пустым.")
        return

    # Пока не сохраняем задачу в базу.
    # Сначала запоминаем название и просим пользователя ввести время напоминания.
    await state.update_data(title=title)
    await state.set_state(AddTask.waiting_remind_time)

    await message.answer(
        "⏰ Введите время напоминания в формате ЧЧ:ММ\n\nНапример: 18:30"
    )

    # Сбрасываем режим ожидания названия: бот снова работает в обычном режиме.
    await state.clear()
    await message.answer(
        f"✅ <b>Задача добавлена</b>\n\n{title}",
        parse_mode="HTML"
    )

@router.message(AddTask.waiting_remind_time)
async def waiting_remind_time_handler(message: Message, state: FSMContext):
    remind_time_text = message.text.strip()

    try:
        remind_time = datetime.strptime(remind_time_text, "%H:%M").time()
    except ValueError:
        await message.answer("Введите время в формате ЧЧ:ММ, например 18:30.")
        return

    remind_at = datetime.combine(date.today(), remind_time)

    data = await state.get_data()
    title = data["title"]

    task_id = await add_task(
        title=title,
        user_id=message.from_user.id,
        remind_at=remind_at
    )

    await state.clear()

    await message.answer(
        f"✅ <b>Задача добавлена</b>\n\n"
        f"{title}\n\n"
        f"⏰ Напомню в {remind_time_text}",
        parse_mode="HTML"
    )

@router.message(F.text == START_BTN_2)
async def list_tasks_message_handler(message: Message):
    # Пользователь нажал обычную кнопку "Список задач" в меню.
    await show_tasks_list(message)


@router.callback_query(F.data=="list_tasks")
async def list_tasks_handler(callback: CallbackQuery):
    # Пользователь нажал кнопку списка задач внутри сообщения.
    await show_tasks_list(callback.message)
    await callback.answer()


@router.message(F.text == START_BTN_3)
async def delete_task_message_handler(message: Message):
    # Пользователь нажал обычную кнопку "Удалить задачу" в меню.
    await show_delete_task_menu(message)


@router.callback_query(F.data=="delete_task")
async def delete_task_handler(callback: CallbackQuery):
    # Пользователь нажал кнопку открытия удаления внутри сообщения.
    await show_delete_task_menu(callback.message)
    await callback.answer()


@router.callback_query(F.data.startswith("delete_task:"))
async def confirm_delete_task_handler(callback: CallbackQuery):
    # В кнопке спрятан номер задачи. Достаем его, чтобы понять, что именно удалить.
    task_id = int(callback.data.split(":")[1])

    is_deleted = await delete_task(task_id)

    if not is_deleted:
        # Если задача не найдена, показываем пользователю всплывающее уведомление.
        await callback.answer("Задача не найдена.", show_alert=True)
        return

    # После удаления снова получаем список задач и обновляем сообщение с кнопками.
    tasks = await get_tasks(task_date=date.today())

    if tasks:
        await callback.message.edit_text(
            "🗑 <b>Удаление задачи</b>\n\nВыберите задачу, которую нужно удалить:",
            reply_markup=delete_task_keyboard(tasks),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text("📭 Задач больше нет.")

    await callback.answer("Задача удалена.")


@router.message(F.text == START_BTN_4)
async def toggle_task_message_handler(message: Message):
    # Пользователь нажал обычную кнопку "Изменить статус" в меню.
    await show_toggle_task_menu(message)


@router.callback_query(F.data == "toggle_task")
async def toggle_task_handler(callback: CallbackQuery):
    # Пользователь нажал кнопку открытия смены статуса внутри сообщения.
    await show_toggle_task_menu(callback.message)
    await callback.answer()


@router.callback_query(F.data.startswith("toggle_task:"))
async def confirm_toggle_task_handler(callback: CallbackQuery):
    # В кнопке спрятаны номер задачи и ее текущий статус.
    # Достаем эти данные, чтобы переключить статус на противоположный.
    _, task_id, current_status = callback.data.split(":")

    task_id = int(task_id)
    current_status = bool(int(current_status))

    new_status = not current_status

    is_updated = await update_task(task_id=task_id, is_done=new_status)

    if not is_updated:
        # Если задача не найдена, показываем пользователю всплывающее уведомление.
        await callback.answer("Задача не найдена.", show_alert=True)
        return

    # После изменения статуса заново строим кнопки,
    # чтобы галочка или пустой квадрат стали актуальными.
    tasks = await get_tasks(task_date=date.today())

    await callback.message.edit_text(
        "✅ <b>Статус задачи</b>\n\nВыберите задачу, чтобы изменить статус:",
        reply_markup=toggle_task_keyboard(tasks),
        parse_mode="HTML"
    )

    text = "Задача выполнена." if new_status else "Задача снова не выполнена."
    await callback.answer(text)
