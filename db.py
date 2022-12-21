from databases import Database
from datetime import datetime, timedelta

database = Database('sqlite:///database.db')


async def get_flag(telegram_id):
    flag = await database.fetch_all('SELECT flag '
                                    'FROM users '
                                    'WHERE telegram_id = :telegram_id',
                                    values={'telegram_id': telegram_id})
    if not flag:
        return None
    return flag[0][0]


async def set_flag(telegram_id, flag):
    previous = await get_flag(telegram_id)
    if previous is None:
        await database.execute(f"INSERT INTO users(telegram_id, flag)"
                               " VALUES (:telegram_id, :flag)",
                               values={'telegram_id': telegram_id, 'flag': flag})
    else:
        await database.execute(
            'UPDATE users SET flag="{}" WHERE telegram_id="{}"'.format(flag, telegram_id))


async def set_group(telegram_id, group):
    old_group = await database.fetch_all('SELECT student_group '
                                         'FROM users '
                                         'WHERE telegram_id = :telegram_id',
                                         values={'telegram_id': telegram_id})
    if not old_group:
        await database.execute(
            "INSERT INTO users (telegram_id, student_group) VALUES ('{}', '{}')".format(telegram_id, group))
    else:
        await database.execute(
            'UPDATE users SET student_group="{}" WHERE telegram_id="{}"'.format(group, telegram_id))


async def show_all(telegram_id):
    group = await database.fetch_all('SELECT student_group '
                                     'FROM users '
                                     'WHERE telegram_id = :telegram_id',
                                     values={'telegram_id': telegram_id})
    if not group:
        return None
    messages = await database.fetch_all('SELECT * FROM database WHERE student_group="{}"'.format(group[0][0]))
    return messages


async def delete_old(telegram_id):
    group = await database.fetch_all('SELECT student_group '
                                     'FROM users '
                                     'WHERE telegram_id = :telegram_id',
                                     values={'telegram_id': telegram_id})
    if not group:
        return "bad_group"
    date = str(datetime.date(datetime.now()))
    time = str(datetime.time(datetime.now()))
    await database.execute('DELETE'
                           ' FROM database '
                           ' WHERE student_group = "{}" AND (date < "{}" OR ( date ="{}" AND time < "{}" ))'.format(
        group[0][0], date, date, time))
    return "OK"


async def delete_name(name, telegram_id):
    try:
        group = await database.fetch_all('SELECT student_group '
                                         'FROM users '
                                         'WHERE telegram_id = :telegram_id',
                                         values={'telegram_id': telegram_id})
        if not group:
            return "bad_group"
        await database.execute('DELETE'
                               ' FROM database '
                               ' WHERE name = "{}" AND student_group = "{}"'.format(name, group[0][0]))
        return "OK"
    except Exception:
        return "NO"


async def make_notifications():
    table = await database.fetch_all('SELECT * '
                                     'FROM database ')
    result = []
    for row in table:
        group = row[3]
        telegram_id = await database.fetch_all('SELECT telegram_id '
                                               'FROM users '
                                               'WHERE student_group = :student_group',
                                               values={'student_group': group})
        for t_id in telegram_id:
            user_date, user_time = from_date_to_user(row[1], row[2])
            result.append(
                {'notification_date': datetime.strptime(row[1] + " " + row[2], "%Y-%m-%d %H:%M:%S") - timedelta(days=1),
                 'message': "Завтра дедлайн " + row[0] + " : " + user_date + " " + user_time,
                 'telegram_id': t_id[0],
                 'name': row[0],
                 'date': row[1],
                 'time': row[2]})
            result.append(
                {'notification_date': datetime.strptime(row[1] + " " + row[2], "%Y-%m-%d %H:%M:%S") - timedelta(
                    hours=1),
                 'message': "Через час дедлайн " + row[0] + " : " + user_date + " " + user_time,
                 'telegram_id': t_id[0],
                 'name': row[0],
                 'date': row[1],
                 'time': row[2]})
    return result


def make_string(lst):
    lst.sort(key=lambda x: x[1] + " " + x[2])
    result = "Дедлайны:\n"
    for line in lst:
        user_date, user_time = from_date_to_user(line[1], line[2])
        result += str(line[0]) + " : " + user_date + " " + user_time + "\n"
    return result


def from_user_to_date(user_date, user_time):
    year = datetime.now().year
    now_month = datetime.now().month
    try:
        deadline_month = user_date.split(".")[1]
    except Exception:
        return None
    if str(deadline_month) < str(now_month):
        year = int(year)
        year += 1
    try:
        dt = datetime.strptime(user_date.strip() + "." + str(year) + " " + user_time.strip(), "%d.%m.%Y %H:%M")
        date = dt.strftime("%Y-%m-%d")
        time = dt.strftime("%H:%M:%S")
    except Exception:
        return [None, None]
    return [date, time]


def from_date_to_user(date_, time_):
    dt = datetime.strptime(str(date_) + " " + str(time_), "%Y-%m-%d %H:%M:%S")
    return [dt.strftime("%d.%m"),
            dt.strftime("%H:%M")]
