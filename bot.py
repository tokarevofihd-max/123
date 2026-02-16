import asyncio
import aiosqlite

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, CallbackQuery
)
from aiogram.enums import ContentType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage

TOKEN = "8537270994:AAEq_RGSLwc2lxgALZqPNuAyhoA4Q_jIsnQ"
ADMIN_ID = 123456789

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ---------- МЕНЮ ----------
menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔥 Смотреть анкеты")],
        [KeyboardButton(text="👤 Моя анкета")],
        [KeyboardButton(text="❤️ Кто лайкнул"), KeyboardButton(text="🏆 Топ")],
        [KeyboardButton(text="⚙️ Фильтр")],
        [KeyboardButton(text="📝 Создать анкету"), KeyboardButton(text="✏️ Изменить анкету")]
    ],
    resize_keyboard=True
)

swipe_kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="❤️", callback_data="like"),
        InlineKeyboardButton(text="❌", callback_data="skip")
    ]
])

# ---------- СОСТОЯНИЯ ----------
class Form(StatesGroup):
    name = State()
    age = State()
    city = State()
    drink = State()
    description = State()
    photo = State()
    filter_age = State()
    filter_city = State()

# ---------- БД ----------
async def init_db():
    async with aiosqlite.connect("database.db") as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS profiles(
        user_id INTEGER PRIMARY KEY,
        name TEXT,
        age INTEGER,
        city TEXT,
        drink TEXT,
        description TEXT,
        photo TEXT
        )""")

        await db.execute("""
        CREATE TABLE IF NOT EXISTS likes(
        user_id INTEGER,
        liked_user_id INTEGER
        )""")

        await db.execute("""
        CREATE TABLE IF NOT EXISTS filters(
        user_id INTEGER PRIMARY KEY,
        age INTEGER,
        city TEXT
        )""")

        await db.commit()

# ---------- СТАРТ ----------
@dp.message(F.text == "/start")
async def start(message: Message):
    await message.answer("🍻 Добро пожаловать!", reply_markup=menu)

# ---------- СОЗДАНИЕ ----------
@dp.message(F.text == "📝 Создать анкету")
async def create_profile(message: Message, state: FSMContext):
    await message.answer("Имя?")
    await state.set_state(Form.name)

@dp.message(F.text == "✏️ Изменить анкету")
async def edit_profile(message: Message, state: FSMContext):

    async with aiosqlite.connect("database.db") as db:
        cursor = await db.execute("SELECT 1 FROM profiles WHERE user_id=?", (message.from_user.id,))
        if not await cursor.fetchone():
            await message.answer("❌ У тебя нет анкеты")
            return

    await message.answer("Как тебя зовут?")
    await state.set_state(Form.name)

@dp.message(Form.name)
async def name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Возраст?")
    await state.set_state(Form.age)

@dp.message(Form.age)
async def age(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введите число")
        return
    await state.update_data(age=int(message.text))
    await message.answer("📍Город?")
    await state.set_state(Form.city)

@dp.message(Form.city)
async def city(message: Message, state: FSMContext):
    await state.update_data(city=message.text)
    await message.answer("Что пьёшь?")
    await state.set_state(Form.drink)

@dp.message(Form.drink)
async def drink(message: Message, state: FSMContext):
    await state.update_data(drink=message.text)
    await message.answer("О себе?")
    await state.set_state(Form.description)

@dp.message(Form.description)
async def desc(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("📸 Отправь фото")
    await state.set_state(Form.photo)

# ---------- ФОТО ----------
@dp.message(Form.photo)
async def photo_handler(message: Message, state: FSMContext):

    if message.content_type != ContentType.PHOTO:
        await message.answer("❌ Отправь фото")
        return

    data = await state.get_data()
    photo_id = message.photo[-1].file_id

    async with aiosqlite.connect("database.db") as db:
        await db.execute(
            "INSERT OR REPLACE INTO profiles VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                message.from_user.id,
                data.get("name"),
                data.get("age"),
                data.get("city"),
                data.get("drink"),
                data.get("description"),
                photo_id
            )
        )
        await db.commit()

    await message.answer("✅ Анкета сохранена!", reply_markup=menu)
    await state.clear()

# ---------- МОЯ АНКЕТА ----------
@dp.message(F.text == "👤 Моя анкета")
async def my_profile(message: Message):
    async with aiosqlite.connect("database.db") as db:
        cursor = await db.execute("SELECT * FROM profiles WHERE user_id=?", (message.from_user.id,))
        p = await cursor.fetchone()

    if not p:
        await message.answer("❌ У тебя нет анкеты")
        return

    text = f"{p[1]}, {p[2]}\n{p[3]}\n🍹 {p[4]}\n{p[5]}"
    await message.answer_photo(p[6], caption=text)

# ---------- ФИЛЬТР ----------
@dp.message(F.text == "⚙️ Фильтр")
async def filter_start(message: Message, state: FSMContext):
    await message.answer("Мин возраст:")
    await state.set_state(Form.filter_age)

@dp.message(Form.filter_age)
async def filter_age(message: Message, state: FSMContext):
    await state.update_data(age=int(message.text))
    await message.answer("Город:")
    await state.set_state(Form.filter_city)

@dp.message(Form.filter_city)
async def filter_city(message: Message, state: FSMContext):
    data = await state.get_data()

    async with aiosqlite.connect("database.db") as db:
        await db.execute("INSERT OR REPLACE INTO filters VALUES (?, ?, ?)",
                         (message.from_user.id, data["age"], message.text))
        await db.commit()

    await message.answer("✅ Фильтр сохранён", reply_markup=menu)
    await state.clear()

# ---------- ПРОСМОТР ----------
queues = {}
current = {}

@dp.message(F.text == "🔥 Смотреть анкеты")
async def view(message: Message):
    async with aiosqlite.connect("database.db") as db:
        cursor = await db.execute("SELECT age, city FROM filters WHERE user_id=?", (message.from_user.id,))
        f = await cursor.fetchone()

        if f:
            cursor = await db.execute(
                "SELECT * FROM profiles WHERE age>=? AND city=? AND user_id!=?",
                (f[0], f[1], message.from_user.id)
            )
        else:
            cursor = await db.execute("SELECT * FROM profiles WHERE user_id!=?", (message.from_user.id,))

        queues[message.from_user.id] = await cursor.fetchall()

    await send_next(message.from_user.id)

async def send_next(user_id):
    q = queues.get(user_id)

    if not q:
        await bot.send_message(user_id, "😢 Анкеты закончились")
        return

    profile = q.pop(0)
    current[user_id] = profile[0]

    text = f"{profile[1]}, {profile[2]}\n{profile[3]}\n🍹 {profile[4]}\n{profile[5]}"
    await bot.send_photo(user_id, profile[6], caption=text, reply_markup=swipe_kb)

# ---------- LIKE ----------
@dp.callback_query(F.data == "like")
async def like(call: CallbackQuery):
    user = call.from_user.id
    liked = current.get(user)

    async with aiosqlite.connect("database.db") as db:
        await db.execute("INSERT INTO likes VALUES (?, ?)", (user, liked))
        cursor = await db.execute("SELECT 1 FROM likes WHERE user_id=? AND liked_user_id=?", (liked, user))
        if await cursor.fetchone():
            await bot.send_message(user, "❤️ У вас МЭТЧ!")
            await bot.send_message(liked, "❤️ У вас МЭТЧ!")
        await db.commit()

    await send_next(user)
    await call.answer()

@dp.callback_query(F.data == "skip")
async def skip(call: CallbackQuery):
    await send_next(call.from_user.id)
    await call.answer()

# ---------- КТО ЛАЙКНУЛ ----------
@dp.message(F.text == "❤️ Кто лайкнул")
async def who_liked(message: Message):
    async with aiosqlite.connect("database.db") as db:
        cursor = await db.execute("""
        SELECT profiles.name FROM likes
        JOIN profiles ON profiles.user_id=likes.user_id
        WHERE likes.liked_user_id=?
        """, (message.from_user.id,))
        rows = await cursor.fetchall()

    if not rows:
        await message.answer("😢 Пока никто")
        return

    await message.answer("\n".join([r[0] for r in rows]))

# ---------- ТОП ----------
@dp.message(F.text == "🏆 Топ")
async def top(message: Message):
    async with aiosqlite.connect("database.db") as db:
        cursor = await db.execute("""
        SELECT profiles.name, COUNT(*) FROM likes
        JOIN profiles ON profiles.user_id=likes.liked_user_id
        GROUP BY liked_user_id ORDER BY COUNT(*) DESC LIMIT 10
        """)
        rows = await cursor.fetchall()

    if not rows:
        await message.answer("Нет данных")
        return

    text = "\n".join([f"{r[0]} — {r[1]} ❤️" for r in rows])
    await message.answer(text)

# ---------- АДМИН ----------
@dp.message(F.text == "/admin")
async def admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("👑 Админ панель\n/users")

@dp.message(F.text == "/users")
async def users(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    async with aiosqlite.connect("database.db") as db:
        cursor = await db.execute("SELECT COUNT(*) FROM profiles")
        count = await cursor.fetchone()

    await message.answer(f"👥 Пользователей: {count[0]}")

# ---------- ЗАПУСК ----------
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
