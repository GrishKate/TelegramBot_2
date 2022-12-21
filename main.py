import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters import Text
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from db import database, show_all, delete_old, delete_name, make_string, set_group, make_notifications, set_flag, \
    get_flag, from_user_to_date, from_date_to_user
from variables import API_TOKEN

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
scheduler = AsyncIOScheduler()

HELP = '''
Чтобы увидеть кнопки, введите /menu.

Вы можете написать:

номер группы xxxx

покажи дедлайны

удали истекшие дедлайны

добавь дедлайн
название1 гггг-мм-дд чч::мм
название2 гггг-мм-дд чч::мм
...

измени дедлайны
название1 гггг-мм-дд чч::мм
название2 гггг-мм-дд чч::мм
...

удали дедлайны
название1
название2
...

Или нажать на соответствующие кнопки.
'''

START = '''
Привет! Я твой бот-календарь. Умею напоминать о дедлайнах в твоей учебной группе за день и за час до них.
Для знакомства с методами напиши /help. 
Чтобы увидеть кнопки, напиши /menu.

А сейчас введи номер твоей учебной группы, чтобы я смог напоминать тебе о дедлайнax! 
'''

GOOD_FORMAT_REPLY = '''
Введи название предмета и дату дедлайна в формате:
название1 дд.мм чч:мм
название2 дд.мм чч:мм
...'''

BAD_FORMAT_REPLY = '''Вводи название предмета и дату дедлайна в формате: название дд.мм чч:мм'''

BAD_DELETE_REPLY = "Введи название предмета"


@dp.message_handler(commands="menu")
async def get_keyboard(message: types.Message):
    kb = [
        [types.KeyboardButton(text="Добавить")],
        [types.KeyboardButton(text="Показать")],
        [types.KeyboardButton(text="Изменить")],
        [types.KeyboardButton(text="Удалить")],
        [types.KeyboardButton(text="Удалить истекшие")],
        [types.KeyboardButton(text="Ввести номер группы")],
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb)
    await message.answer("Что сделать с дедлайнами?", reply_markup=keyboard)


@dp.message_handler(Text("Ввести номер группы"))
async def change_group_number(message: types.Message):
    await set_flag(message.from_user.id, "set_group")
    await message.answer("Введи номер твоей группы")


@dp.message_handler(Text("Показать"))
async def show_deadlines(message: types.Message):
    show = await show_all(message.from_user.id)
    if show is None:
        await message.reply("Не знаю номер твоей группы. Напиши /help")
    else:
        await message.answer(make_string(show))


@dp.message_handler(Text("Удалить истекшие"))
async def delete_old_deadlines(message: types.Message):
    ok = await delete_old(message.from_user.id)
    if ok == "bad_group":
        await message.reply("Не знаю номер твоей группы. Напиши /help")
    else:
        await message.reply("Удалил")


@dp.message_handler(Text("Удалить"))
async def delete_by_names(message: types.Message):
    await set_flag(message.from_user.id, "delete_deadlines")
    await message.reply('''Введи названия предметов, по которым хочешь удалить дедлайны, в формате:
    название1
    название2
    ...''')


@dp.message_handler(Text("Изменить"))
async def change_deadlines(message: types.Message):
    await set_flag(message.from_user.id, "change_deadlines")
    await message.reply(GOOD_FORMAT_REPLY)


@dp.message_handler(Text("Добавить"))
async def add_deadlines(message: types.Message):
    await set_flag(message.from_user.id, "add_deadlines")
    await message.reply(GOOD_FORMAT_REPLY)


@dp.message_handler()
async def handle_message(message: types.Message):
    flag = await get_flag(message.from_user.id)
    lines = message.text.split("\n")
    first = lines[0].lower().strip()
    if flag == "set_group":
        await set_flag(message.from_user.id, "no_flag")
        await set_group(message.from_user.id, message.text.strip())
        await message.answer("Спасибо! Теперь я знаю номер твоей группы {}.".format(message.text.strip()))
    elif flag == "add_deadlines":
        ok_reply = "Добавил"
        not_ok_reply = BAD_FORMAT_REPLY
        start_num = 0
        await apply_func(add, start_num, lines, message, ok_reply, not_ok_reply)
    elif flag == "change_deadlines":
        ok_reply = "Изменил"
        not_ok_reply = BAD_FORMAT_REPLY
        start_num = 0
        await apply_func(change, start_num, lines, message, ok_reply, not_ok_reply)
    elif flag == "delete_deadlines":
        ok_reply = "Удалил"
        not_ok_reply = BAD_DELETE_REPLY
        start_num = 0
        await apply_delete(delete_name, start_num, lines, message, ok_reply, not_ok_reply)
    else:
        if first == "/start":
            await set_flag(message.from_user.id, "set_group")
            await message.answer(START)
        elif first == "добавь дедлайн":
            ok_reply = "Добавил"
            not_ok_reply = BAD_FORMAT_REPLY
            start_num = 1
            await apply_func(add, start_num, lines, message, ok_reply, not_ok_reply)
        elif first == "покажи дедлайны":
            show = await show_all(message.from_user.id)
            if show is None:
                await message.reply("Не знаю номер твоей группы. Напиши /help")
            else:
                await message.answer(make_string(show))
        elif first == "удали истекшие дедлайны":
            ok = await delete_old(message.from_user.id)
            if ok == "bad_group":
                await message.reply("Не знаю номер твоей группы. Напиши /help")
            else:
                await message.reply("Удалил")
        elif first == "измени дедлайны":
            ok_reply = "Изменил"
            not_ok_reply = 'Введи название предмета и дату дедлайна в формате "название гггг-мм-дд чч:мм"'
            start_num = 1
            await apply_func(change, start_num, lines, message, ok_reply, not_ok_reply)
        elif first == "удали дедлайны":
            ok_reply = "Удалил"
            not_ok_reply = BAD_DELETE_REPLY
            start_num = 1
            await apply_delete(delete_name, start_num, lines, message, ok_reply, not_ok_reply)
        elif first == "/help":
            await message.answer(HELP)
        elif first[:12] == "номер группы":
            await set_group(message.from_user.id, first[13:].strip())
        else:
            await message.answer("Я не понимаю. Напиши /help")


async def apply_func(func, start_num, lines, message, ok_reply, not_ok_reply):
    f = True
    for i in range(start_num, len(lines)):
        try:
            name, user_date, user_time = lines[i].split(" ")
            date, time = from_user_to_date(user_date, user_time)
            if date is None:
                f = False
                await message.reply("Вводите дату в формате дд.мм чч:мм")
                break
        except Exception:
            f = False
            await message.reply(not_ok_reply)
            break
        if f:
            ok = await func(name, date, time, message.from_user.id)
            if ok == "bad_group":
                await message.reply("Не знаю номер твоей группы. Напиши /help")
                f = False
                break
            elif ok != "OK":
                f = False
                await message.reply(not_ok_reply)
                break
    if f:
        await set_flag(message.from_user.id, "no_flag")
        await message.reply(ok_reply)


async def apply_delete(func, start_num, lines, message, ok_reply, not_ok_reply):
    f = True
    for i in range(start_num, len(lines)):
        ok = await func(lines[i].strip(), message.from_user.id)
        if ok == "bad_group":
            await message.answer("Не знаю номер твоей группы. Напиши /help")
            f = False
            break
        elif ok != "OK":
            f = False
            await message.reply(not_ok_reply)
            break
    if f:
        await set_flag(message.from_user.id, "no_flag")
        await message.reply(ok_reply)


async def on_startup(dp):
    await schedule_jobs()


async def send_notification(telegram_id, message, name, date, time):
    group = await database.fetch_all('SELECT student_group '
                                     'FROM users '
                                     'WHERE telegram_id = :telegram_id',
                                     values={'telegram_id': telegram_id})
    date_time = await database.fetch_all('SELECT date, time '
                                         'FROM database '
                                         'WHERE student_group = :student_group AND name = :name',
                                         values={'student_group': group[0][0], 'name': name})
    if date_time and date_time[0][0] == date and date_time[0][1] == time:
        await dp.bot.send_message(telegram_id, message)


async def schedule_jobs():
    notifications = await make_notifications()
    for notification in notifications:
        scheduler.add_job(send_notification, "date", run_date=notification['notification_date'],
                          args=(notification['telegram_id'], notification['message'], notification['name'],
                                notification['date'], notification['time']))


async def add(name, date, time, telegram_id):
    try:
        group = await database.fetch_all('SELECT student_group '
                                         'FROM users '
                                         'WHERE telegram_id = :telegram_id',
                                         values={'telegram_id': telegram_id})
        if not group:
            return "bad_group"
        group = group[0][0]
        await database.execute(f"INSERT INTO database(name, date, time, student_group)"
                               " VALUES (:name, :date, :time, :student_group)",
                               values={'name': name, 'date': date, 'time': time, 'student_group': group})
        telegram_ids = await database.fetch_all('SELECT telegram_id '
                                                'FROM users '
                                                'WHERE student_group = :student_group',
                                                values={'student_group': group})
        for t_id in telegram_ids:
            user_date, user_time = from_date_to_user(date, time)
            scheduler.add_job(send_notification, "date",
                              run_date=datetime.strptime(date + " " + time, "%Y-%m-%d %H:%M:%S") - timedelta(days=1),
                              args=(t_id[0], "Завтра дедлайн " + name + " : " + user_date + " " + user_time, name, date,
                                    time))
            scheduler.add_job(send_notification, "date",
                              run_date=datetime.strptime(date + " " + time, "%Y-%m-%d %H:%M:%S") - timedelta(hours=1),
                              args=(t_id[0], "Через час дедлайн " + name + " : " + user_date + " " + user_time, name,
                                    date,
                                    time))
        return "OK"
    except Exception:
        return "NO"


async def change(name, date, time, telegram_id):
    try:
        group = await database.fetch_all('SELECT student_group '
                                         'FROM users '
                                         'WHERE telegram_id = :telegram_id',
                                         values={'telegram_id': telegram_id})
        if not group:
            return "bad_group"
        group = group[0][0]
        await database.execute(
            'UPDATE database SET date = "{}", time="{}" WHERE name = "{}" AND student_group="{}"'.format(date, time,
                                                                                                         name,
                                                                                                         group))
        telegram_ids = await database.fetch_all('SELECT telegram_id '
                                                'FROM users '
                                                'WHERE student_group = :student_group',
                                                values={'student_group': group})
        for t_id in telegram_ids:
            user_date, user_time = from_date_to_user(date, time)
            scheduler.add_job(send_notification, "date",
                              run_date=datetime.strptime(date + " " + time, "%Y-%m-%d %H:%M:%S") - timedelta(days=1),
                              args=(t_id[0], "Завтра дедлайн " + name + " : " + user_date + " " + user_time, name,
                                    date, time))
            scheduler.add_job(send_notification, "date",
                              run_date=datetime.strptime(date + " " + time, "%Y-%m-%d %H:%M:%S") - timedelta(hours=1),
                              args=(t_id[0], "Через час дедлайн " + name + " : " + user_date + " " + user_time, name,
                                    date, time))
        return "OK"
    except Exception:
        return "NO"


if __name__ == '__main__':
    scheduler.start()
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)
