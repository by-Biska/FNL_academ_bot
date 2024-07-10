import asyncio
import os
from typing import Final

import aiosqlite
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Use environment variables for sensitive information
TOKEN = '7475622289:AAGdIJIjUMEl2xaqYWhRsw-gfSXxFJd7-eY'

# Initialize bot and dispatcher
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

SUBJECTS_DATA = {
1: {  # Кафедра 1
        'all': {  # Предметы для всех групп и семестров этой кафедры
            'Общая физика': 'https://example.com/physics',
        },
        1: {  # Группа 1
            1: {  # Семестр 1
                'Термех': 'https://example.com/termeh1',
                'Математика': 'https://example.com/math1',
            },
            2: {  # Семестр 2
                'Термех': 'https://example.com/termeh2',
                'Сопромат': 'https://example.com/sopromat',
            },
        },
        2: {  # Группа 2
            1: {
                'Информатика': 'https://example.com/informatics1',
            },
            2: {
                'Программирование': 'https://example.com/programming',
            },
        },
    },
    2: {  # Кафедра 2
        'all': {
            'Английский язык': 'https://example.com/english',
        },
        1: {
            1: {
                'Экономика': 'https://example.com/economics1',
            },
            2: {
                'Менеджмент': 'https://example.com/management',
            },
        },
    },
}


async def user_exists(user_id: int) -> bool:
    async with aiosqlite.connect('users.db') as db:
        cursor = await db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return await cursor.fetchone() is not None


async def get_user_data(user_id):
    async with aiosqlite.connect('users.db') as db:
        cursor = await db.execute('''
            SELECT semestr, group_number, kafedra, user_fullname
            FROM users
            WHERE user_id = ?
        ''', (user_id,))
        user_data = await cursor.fetchone()
    return user_data


def generate_menu_buttons(semester, group, kafedra):
    buttons = []

    # Добавляем предметы для всех групп и семестров кафедры
    if kafedra in SUBJECTS_DATA and 'all' in SUBJECTS_DATA[kafedra]:
        for subject, url in SUBJECTS_DATA[kafedra]['all'].items():
            buttons.append([types.InlineKeyboardButton(text=subject, callback_data=f"subject:{subject}")])

    # Добавляем предметы для конкретной группы и семестра
    if kafedra in SUBJECTS_DATA and group in SUBJECTS_DATA[kafedra] and semester in SUBJECTS_DATA[kafedra][group]:
        for subject, url in SUBJECTS_DATA[kafedra][group][semester].items():
            buttons.append([types.InlineKeyboardButton(text=subject, callback_data=f"subject:{subject}")])

    # Общая кнопка для всех
    buttons.append([types.InlineKeyboardButton(text='Помощь', callback_data='help')])

    buttons.append([types.InlineKeyboardButton(text='Профиль', callback_data='profile')])
    buttons.append([types.InlineKeyboardButton(text='Изменить профиль', callback_data='edit_profile')])

    return buttons


# Constants
KAFEDRA_OPTIONS: Final = {
    "ФН1": 1, "ФН2": 2, "ФН3": 3,
    "ФН4": 4, "ФН7": 7, "ФН11": 11,
    "ФН12": 12, "ФН14": 14
}

# Define states for the registration process
class RegistrationStates(StatesGroup):
    choosing_kafedra = State()
    choosing_group = State()
    choosing_semester = State()
    entering_name = State()
    editing_profile = State()

async def add_user(user_id: int, full_name: str, username: str, tg_name: str, semester: int, group: int, kafedra: str):
    async with aiosqlite.connect('users.db') as db:
        # Check if the user already exists
        cursor = await db.execute('SELECT 1 FROM users WHERE user_id = ?', (user_id,))
        user_exists = await cursor.fetchone()

        if user_exists:
            # Update existing user
            await db.execute('''
                UPDATE users 
                SET user_fullname = ?, username = ?, telegram_name = ?, semestr = ?, group_number = ?, kafedra = ?
                WHERE user_id = ?
            ''', (full_name, username, tg_name, semester, group, kafedra, user_id))
        else:
            # Insert new user
            await db.execute('''
                INSERT INTO users (user_id, user_fullname, username, telegram_name, semestr, group_number, kafedra)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, full_name, username, tg_name, semester, group, kafedra))

        await db.commit()

@dp.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext) -> None:
    if await user_exists(message.from_user.id):
        await message.answer('Вы уже зарегистрированы. Используйте /menu для доступа к функциям.')
    else:
        kb = [
            [types.InlineKeyboardButton(text="ФН1", callback_data="1"),
             types.InlineKeyboardButton(text="ФН2", callback_data="2"),
             types.InlineKeyboardButton(text="ФН3", callback_data="3")],
            [types.InlineKeyboardButton(text="ФН4", callback_data="4"),
             types.InlineKeyboardButton(text="ФН7", callback_data="7"),
             types.InlineKeyboardButton(text="ФН11", callback_data="11")],
            [types.InlineKeyboardButton(text="ФН12", callback_data="12"),
             types.InlineKeyboardButton(text="ФН14", callback_data="14")]
        ]
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)
        await message.answer('Привет! Выбери свою кафедру', reply_markup=keyboard)
        await state.set_state(RegistrationStates.choosing_kafedra)

@dp.callback_query(RegistrationStates.choosing_kafedra)
async def kafedra_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(kafedra=callback.data)
    kb = [
        [types.InlineKeyboardButton(text=str(i), callback_data=f'group{i}') for i in range(1, 5)]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)
    await callback.message.edit_text('Выбери номер своей группы', reply_markup=keyboard)
    await state.set_state(RegistrationStates.choosing_group)

@dp.callback_query(RegistrationStates.choosing_group)
async def group_callback(callback: types.CallbackQuery, state: FSMContext):
    group = int(callback.data.replace('group', ''))
    await state.update_data(group=group)
    kb = [
        [types.InlineKeyboardButton(text=str(i), callback_data=f'semester{i}') for i in range(1, 3)]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)
    await callback.message.edit_text('Выбери номер своего семестра', reply_markup=keyboard)
    await state.set_state(RegistrationStates.choosing_semester)

@dp.callback_query(RegistrationStates.choosing_semester)
async def semester_callback(callback: types.CallbackQuery, state: FSMContext):
    semester = int(callback.data.replace('semester', ''))
    await state.update_data(semester=semester)
    await callback.message.edit_text('Напиши своё ФИО (пример: Иванов Иван Иванович)')
    await state.set_state(RegistrationStates.entering_name)

@dp.message(RegistrationStates.entering_name)
async def final(message: types.Message, state: FSMContext):
    full_name = message.text.strip()
    if len(full_name.split()) != 3:
        await message.answer('Пожалуйста, введите ФИО в правильном формате (Фамилия Имя Отчество).')
        return

    user_data = await state.get_data()
    await add_user(
        message.from_user.id,
        full_name,
        message.from_user.username,
        message.from_user.full_name,
        user_data['semester'],
        user_data['group'],
        user_data['kafedra']
    )
    await state.clear()
    await message.answer('Регистрация завершена! Напишите /menu для дальнейшей работы.')

@dp.message(Command("menu"))
async def menu_handler(message: types.Message):
    user_data = await get_user_data(message.from_user.id)
    print(user_data)
    if user_data:
        semester, group, kafedra, full_name = user_data
        kb = generate_menu_buttons(semester, group, kafedra)
        if kb:
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)
            await message.answer('Выберите предмет:', reply_markup=keyboard)
        else:
            await message.answer('Извините, для вас нет доступных предметов.')
    else:
        await message.answer('Пожалуйста, сначала зарегистрируйтесь.')

@dp.callback_query(F.data == "menu")
async def menu1_handler(callback: types.CallbackQuery):
    user_data = await get_user_data(callback.from_user.id)
    print(user_data)
    if user_data:
        semester, group, kafedra, full_name = user_data
        kb = generate_menu_buttons(semester, group, kafedra)
        if kb:
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)
            await callback.message.edit_text('Выберите предмет:', reply_markup=keyboard)
        else:
            await callback.message.answer('Извините, для вас нет доступных предметов.')
    else:
        await callback.message.answer('Пожалуйста, сначала зарегистрируйтесь.')


@dp.callback_query(F.data.startswith("subject:"))
async def subject_handler(callback: types.CallbackQuery):
    subject = callback.data.split(":")[1]
    user_data = await get_user_data(callback.from_user.id)
    if user_data:
        semester, group, kafedra, full_name = user_data
        url = None

        # Проверяем, есть ли предмет в общем списке для кафедры
        if kafedra in SUBJECTS_DATA and 'all' in SUBJECTS_DATA[kafedra]:
            url = SUBJECTS_DATA[kafedra]['all'].get(subject)

        # Если не нашли в общем списке, ищем для конкретной группы и семестра
        if not url and kafedra in SUBJECTS_DATA and group in SUBJECTS_DATA[kafedra] and semester in \
                SUBJECTS_DATA[kafedra][group]:
            url = SUBJECTS_DATA[kafedra][group][semester].get(subject)

        if url:
            kb = [[types.InlineKeyboardButton(text=f"Ссылка на {subject}", url=url)]]
            kb.append([types.InlineKeyboardButton(text='Меню', callback_data='menu')])
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)
            await callback.message.edit_text(f"Ресурсы по предмету {subject}:", reply_markup=keyboard)
        else:
            await callback.message.edit_text(f"Извините, ссылка на предмет {subject} не найдена.")
    else:
        await callback.message.edit_text("Пожалуйста, сначала зарегистрируйтесь.")


# @dp.message(Command("menu"))
# async def menu_handler(message: types.Message):
#     kb = [
#         [types.InlineKeyboardButton(text='термех', callback_data='tr'),
#          types.InlineKeyboardButton(text='предмет 2', callback_data='pr2')],
#         [types.InlineKeyboardButton(text='Помощь', callback_data='help')]
#     ]
#     keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)
#     await message.answer('Выберай!', reply_markup=keyboard)


@dp.callback_query(F.data == 'help')
async def help_handler(callback: types.CallbackQuery):
    await callback.message.edit_text('Это раздел помощи. Ориши свой вопрос!.')

@dp.callback_query(F.data == "profile")
async def profile_handler(callback: types.CallbackQuery):
    user_data = await get_user_data(callback.from_user.id)
    if user_data:
        semester, group, kafedra, full_name = user_data
        profile_text = f"Ваш профиль:\n\nИмя: {full_name}\nКафедра: ФН{kafedra}\nГруппа: {group}\nСеместр: {semester}"
        kb = [[types.InlineKeyboardButton(text='Назад в меню', callback_data='menu')]]
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)
        await callback.message.edit_text(profile_text, reply_markup=keyboard)
    else:
        await callback.message.edit_text("Профиль не найден. Пожалуйста, зарегистрируйтесь.")


@dp.callback_query(F.data == "edit_profile")
async def edit_profile_handler(callback: types.CallbackQuery, state: FSMContext):
    kb = [
        [types.InlineKeyboardButton(text="ФН1", callback_data="edit:1"),
         types.InlineKeyboardButton(text="ФН2", callback_data="edit:2"),
         types.InlineKeyboardButton(text="ФН3", callback_data="edit:3")],
        [types.InlineKeyboardButton(text="ФН4", callback_data="edit:4"),
         types.InlineKeyboardButton(text="ФН7", callback_data="edit:7"),
         types.InlineKeyboardButton(text="ФН11", callback_data="edit:11")],
        [types.InlineKeyboardButton(text="ФН12", callback_data="edit:12"),
         types.InlineKeyboardButton(text="ФН14", callback_data="edit:14")]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)
    await callback.message.edit_text('Выберите новую кафедру:', reply_markup=keyboard)
    await state.set_state(RegistrationStates.editing_profile)


@dp.callback_query(RegistrationStates.editing_profile, F.data.startswith("edit:"))
async def edit_kafedra_callback(callback: types.CallbackQuery, state: FSMContext):
    kafedra = callback.data.split(":")[1]
    await state.update_data(kafedra=kafedra)
    kb = [
        [types.InlineKeyboardButton(text=str(i), callback_data=f'edit_group:{i}') for i in range(1, 5)]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)
    await callback.message.edit_text('Выберите новый номер группы:', reply_markup=keyboard)


@dp.callback_query(RegistrationStates.editing_profile, F.data.startswith("edit_group:"))
async def edit_group_callback(callback: types.CallbackQuery, state: FSMContext):
    group = int(callback.data.split(":")[1])
    await state.update_data(group=group)
    kb = [
        [types.InlineKeyboardButton(text=str(i), callback_data=f'edit_semester:{i}') for i in range(1, 3)]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)
    await callback.message.edit_text('Выберите новый номер семестра:', reply_markup=keyboard)


@dp.callback_query(RegistrationStates.editing_profile, F.data.startswith("edit_semester:"))
async def edit_semester_callback(callback: types.CallbackQuery, state: FSMContext):
    semester = int(callback.data.split(":")[1])
    await state.update_data(semester=semester)
    await callback.message.edit_text('Введите ваше новое ФИО (Фамилия Имя Отчество):')
    await state.set_state(RegistrationStates.entering_name)


@dp.message(RegistrationStates.entering_name)
async def edit_name_handler(message: types.Message, state: FSMContext):
    full_name = message.text.strip()
    if len(full_name.split()) != 3:
        await message.answer('Пожалуйста, введите ФИО в правильном формате (Фамилия Имя Отчество).')
        return

    user_data = await state.get_data()
    await add_user(
        message.from_user.id,
        full_name,
        message.from_user.username,
        message.from_user.full_name,
        user_data['semester'],
        user_data['group'],
        user_data['kafedra']
    )

    await state.clear()
    await message.answer('Профиль успешно обновлен! Используйте /menu для доступа к функциям.')
async def main() -> None:
    # Initialize database
    async with aiosqlite.connect('users.db') as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                user_fullname TEXT,
                username TEXT,
                telegram_name TEXT,
                semestr INTEGER,
                group_number INTEGER,
                kafedra INTEGER
            )
        ''')
        await db.commit()

    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())



# import asyncio, aiosqlite
# from aiogram import Bot, Dispatcher, types, F
# from aiogram.filters import Command
#
# dp = Dispatcher()
#
# kafedra = semestr = group = 0
#
#
# async def add_user(user_id, full_name, username, tg_name, sm, group, kf):
#     connect = await aiosqlite.connect('users.db')
#     cursor = await connect.cursor()
#     print(user_id, full_name, username, tg_name, type(sm), group, kf)
#     # check_user = await cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
#     # check_user = await check_user.fetchone()
#     # if check_user is None:
#     await cursor.execute(
#         'INSERT INTO users (user_id, user_fullname, username, telegram_name, semestr, group_number, kafedra) VALUES (?, ?, ?, ?, ?, ?, ?)',
#         (user_id, full_name, username, tg_name, sm, group, kf))
#     await connect.commit()
#     await cursor.close()
#     await connect.close()
#
#
# @dp.message(Command('start'))
# async def start_command(message: types.Message) -> None:
#     kb = [
#         [types.InlineKeyboardButton(text="ФН1", callback_data='fn1'),
#          types.InlineKeyboardButton(text="ФН2", callback_data='fn2'),
#          types.InlineKeyboardButton(text="ФН3", callback_data='fn3')
#          ],
#         [types.InlineKeyboardButton(text="ФН4", callback_data='fn4'),
#          types.InlineKeyboardButton(text="ФН5", callback_data='fn5'),
#          types.InlineKeyboardButton(text="ФН11", callback_data='fn11')
#          ],
#         [types.InlineKeyboardButton(text="ФН12", callback_data='fn12'),
#          types.InlineKeyboardButton(text="ФН14", callback_data='fn14')
#          ],
#     ]
#     keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)
#     await message.answer('Привет бла-бла-бла! Выбери свой свою кафедру', reply_markup=keyboard)
#
#
# @dp.callback_query(F.data == 'fn1')
# @dp.callback_query(F.data == 'fn2')
# @dp.callback_query(F.data == 'fn3')
# @dp.callback_query(F.data == 'fn4')
# @dp.callback_query(F.data == 'fn5')
# @dp.callback_query(F.data == 'fn11')
# @dp.callback_query(F.data == 'fn12')
# async def kafedra_callback(callback: types.CallbackQuery):
#     kb = [
#         [types.InlineKeyboardButton(text='1', callback_data='group1'),
#          types.InlineKeyboardButton(text='2', callback_data='group2'),
#          types.InlineKeyboardButton(text='3', callback_data='group3'),
#          types.InlineKeyboardButton(text='4', callback_data='group4'), ]
#     ]
#     keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)
#     global kafedra
#     kafedra = callback.data
#     await callback.message.edit_text('Выбери номер своей группы', reply_markup=keyboard)
#
#
# @dp.callback_query(F.data == 'group1')
# @dp.callback_query(F.data == 'group2')
# @dp.callback_query(F.data == 'group3')
# @dp.callback_query(F.data == 'group4')
# async def semestr_callback(callback: types.CallbackQuery):
#     kb = [
#         [types.InlineKeyboardButton(text='1', callback_data='semestr1')],
#         [types.InlineKeyboardButton(text='2', callback_data='semestr2')]
#     ]
#     keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)
#     global group
#     group = callback.data
#     await callback.message.edit_text('Выбери номер своего семестра', reply_markup=keyboard)
#
#
# @dp.callback_query(F.data == 'semestr1')
# @dp.callback_query(F.data == 'semestr2')
# async def your_name_handler(callback: types.CallbackQuery):
#     global semestr
#     semestr = callback.data
#     await callback.message.edit_text('Напиши своё ФИО НАЧИНАЯ СО СЛОВА ФИО(пример: ФИО Иванов Иван Иванович)')
#
#
# @dp.message(F.text.startswith('ФИО'))
# async def final(message: types.Message):
#     fio = message.text
#     await add_user(message.from_user.id, fio[3:], message.from_user.username, message.from_user.full_name,
#                    int(semestr[-1]), int(group[-1]), kafedra)
#     await message.answer('Молодец, это всё!\nНапиши меню если для дальнейшей работы')
#
#
# @dp.message(F.text == 'меню')
# async def menu_handler(message: types.Message):
#     kb = [
#         [types.InlineKeyboardButton(text='термех', callback_data='tr'),
#          types.InlineKeyboardButton(text='предмет 2', callback_data='pr2')],
#         [types.InlineKeyboardButton(text='Помощь', callback_data='help')]
#     ]
#     keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)
#     await message.answer('Выберай!', reply_markup=keyboard)
#
#
# @dp.message(F.data == 'tr')
# async def tr_handler(callback: types.CallbackQuery):
#     kb = [
#         [types.InlineKeyboardButton(text='ссылочка', url='google.com')],
#     ]
#     keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)
#     await callback.message.edit_text('Получай!', reply_markup=keyboard)
#
#
# async def main() -> None:
#     token = "7475622289:AAGdIJIjUMEl2xaqYWhRsw-gfSXxFJd7-eY"
#     bot = Bot(token)
#     await dp.start_polling(bot)
#
#
# if __name__ == "__main__":
#     asyncio.run(main())
