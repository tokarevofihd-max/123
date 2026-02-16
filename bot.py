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

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ---------- МЕНЮ ----------
menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔥 Смотреть анкеты")],
        [KeyboardButton(text="👤 Моя анкета")],
        [KeyboardButton(text="📝 Создать анкету")]
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
        liked_user_id INTEGER,
        UNIQUE(user_id, liked_user_id)
        )""")

        await db.commit()

# ---------- СТАРТ ----------
@dp.message(F.text == "/start")
async def start(message: Message):
    await message.answer("🍻 Бот для поиска компании выпить", reply_markup=menu)

# ---------- СОЗДАНИЕ ----------
@dp.message(F.text == "📝 Создать анкету")
async def create_profile(message: Message, state: FSMContext):
    await message.answer("Имя?")
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
    await message.answer("Город?")
    await state.set_state(Form.city)

@dp.message(Form.city)
async def city(message: Message, state: FSMContext):
    await state.update_data(city=message.text.lower())
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
    await message.answer("Отправь фото")
    await state.set_state(Form.photo)

@dp.message(Form.photo)
async def photo_handler(message: Message, state: FSMContext):

    if message.content_type != ContentType.PHOTO:
        await message.answer("Отправь фото")
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
        await message.answer("❌ Нет анкеты")
        return

    text = f"{p[1]}, {p[2]}\n📍 {p[3]}\n🍹 {p[4]}\n{p[5]}"
    await message.answer_photo(p[6], caption=text)

# ---------- ПРОСМОТР ----------
queues = {}
current = {}

@dp.message(F.text == "🔥 Смотреть анкеты")
async def view(message: Message):

    async with aiosqlite.connect("database.db") as db:
        cursor = await db.execute(
            "SELECT * FROM profiles WHERE user_id!=? AND city=(SELECT city FROM profiles WHERE user_id=?)",
            (message.from_user.id, message.from_user.id)
        )
        queues[message.from_user.id] = await cursor.fetchall()

    await send_next(message.from_user.id)

async def send_next(user_id):
    q = queues.get(user_id)

    if not q:
        await bot.send_message(user_id, "😢 Анкеты закончились")
        return

    profile = q.pop(0)
    current[user_id] = profile[0]

    text = f"{profile[1]}, {profile[2]}\n📍 {profile[3]}\n🍹 {profile[4]}\n{profile[5]}"
    await bot.send_photo(user_id, profile[6], caption=text, reply_markup=swipe_kb)

# ---------- LIKE ----------
@dp.callback_query(F.data == "like")
async def like(call: CallbackQuery):

    user = call.from_user.id
    liked = current.get(user)

    async with aiosqlite.connect("database.db") as db:
        await db.execute("INSERT OR IGNORE INTO likes VALUES (?, ?)", (user, liked))

        cursor = await db.execute(
            "SELECT 1 FROM likes WHERE user_id=? AND liked_user_id=?",
            (liked, user)
        )
        match = await cursor.fetchone()

        if match:
            user_chat = await bot.get_chat(user)
            liked_chat = await bot.get_chat(liked)

            user_link = f'<a href="tg://user?id={user}">{user_chat.first_name}</a>'
            liked_link = f'<a href="tg://user?id={liked}">{liked_chat.first_name}</a>'

            await bot.send_message(user, f"💖 МЭТЧ!\nНапиши 👉 {liked_link}", parse_mode="HTML")
            await bot.send_message(liked, f"💖 МЭТЧ!\nНапиши 👉 {user_link}", parse_mode="HTML")

        await db.commit()

    await send_next(user)
    await call.answer()

# ---------- SKIP ----------
@dp.callback_query(F.data == "skip")
async def skip(call: CallbackQuery):
    await send_next(call.from_user.id)
    await call.answer()

# ---------- ЗАПУСК ----------
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
