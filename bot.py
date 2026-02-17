import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

TOKEN = "8537270994:AAE6KUI6-hjh8xsaoGg-GX036Ue7HRXMYG0"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

users = {}
view_index = {}

likes_sent = {}
likes_received = {}

likes_view_index = {}

# ---------- МЕНЮ ----------
menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔥 Найти людей рядом")],
        [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="💌 Лайки")],
        [KeyboardButton(text="✏️ создать / Изменить анкету")]
    ],
    resize_keyboard=True
)

swipe_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="❤️ Нравится", callback_data="like")],
        [InlineKeyboardButton(text="👎 Дальше", callback_data="skip")]
    ]
)

likes_swipe_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="❤️ Лайк в ответ", callback_data="like_back")],
        [InlineKeyboardButton(text="👎 Пропустить", callback_data="skip_like")]
    ]
)

# ---------- СОСТОЯНИЯ ----------
class CreateProfile(StatesGroup):
    name = State()
    age = State()
    city = State()
    about = State()
    photo = State()

# ---------- START ----------
@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer("💜 Добро пожаловать в POBOKALY Bot. пиши /start чтобы начать", reply_markup=menu)

# ---------- СОЗДАНИЕ ----------
@dp.message(F.text == "✏️ создать / Изменить анкету")
async def create(message: types.Message, state: FSMContext):
    await message.answer("Введите имя:")
    await state.set_state(CreateProfile.name)

@dp.message(CreateProfile.name)
async def set_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Возраст:")
    await state.set_state(CreateProfile.age)

@dp.message(CreateProfile.age)
async def set_age(message: types.Message, state: FSMContext):
    await state.update_data(age=message.text)
    await message.answer("Город:")
    await state.set_state(CreateProfile.city)

@dp.message(CreateProfile.city)
async def set_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await message.answer("что любишь выпить? Расскижи больше о себе):")
    await state.set_state(CreateProfile.about)

@dp.message(CreateProfile.about)
async def set_about(message: types.Message, state: FSMContext):
    await state.update_data(about=message.text)
    await message.answer("Отправь фото 📸")
    await state.set_state(CreateProfile.photo)

@dp.message(CreateProfile.photo, F.photo)
async def set_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()

    users[message.from_user.id] = {
        "name": data["name"],
        "age": data["age"],
        "city": data["city"],
        "about": data["about"],
        "photo": message.photo[-1].file_id,
        "username": message.from_user.username
    }

    await state.clear()
    await message.answer("✅ Анкета сохранена", reply_markup=menu)

# ---------- ПРОФИЛЬ ----------
@dp.message(F.text == "👤 Профиль")
async def profile(message: types.Message):
    user = users.get(message.from_user.id)
    if not user:
        await message.answer("❌ Нет анкеты")
        return

    text = f"💘 <b>{user['name']}, {user['age']}</b>\n📍 {user['city']}\n\n✨ {user['about']}"
    await message.answer_photo(user["photo"], caption=text, parse_mode="HTML")

# ---------- СМОТРЕТЬ ----------
@dp.message(F.text == "🔥 Найти людей рядом")
async def view(message: types.Message):
    uid = message.from_user.id

    if uid not in users:
        await message.answer("Сначала создай анкету")
        return

    view_index[uid] = 0
    await send_next(uid, message)

async def send_next(uid, message):
    profiles = [u for u in users if u != uid]

    if not profiles:
        await message.answer("Нет анкет")
        return

    i = view_index.get(uid, 0)

    if i >= len(profiles):
        await message.answer("Анкеты закончились")
        return

    target = profiles[i]
    user = users[target]

    text = f"💘 <b>{user['name']}, {user['age']}</b>\n📍 {user['city']}\n\n✨ {user['about']}"

    await message.answer_photo(user["photo"], caption=text, reply_markup=swipe_kb, parse_mode="HTML")

# ---------- LIKE ----------
@dp.callback_query(F.data == "like")
async def like(callback: types.CallbackQuery):

    uid = callback.from_user.id
    profiles = [u for u in users if u != uid]

    if uid not in view_index or view_index[uid] >= len(profiles):
        await callback.answer()
        return

    target = profiles[view_index[uid]]

    likes_sent.setdefault(uid, set()).add(target)
    likes_received.setdefault(target, set()).add(uid)

    liker = users[uid]
    await bot.send_message(target, f"❤️ Тебя лайкнул(а) {liker['name']}")

    # MATCH
    if uid in likes_sent.get(target, set()):

        link1 = f"https://t.me/{users[uid]['username']}"
        link2 = f"https://t.me/{users[target]['username']}"

        await callback.message.answer(f"💘 MATCH!\n👉 {link2}")
        await bot.send_message(target, f"💘 MATCH!\n👉 {link1}")

    view_index[uid] += 1
    await callback.message.delete()
    await send_next(uid, callback.message)
    await callback.answer()

# ---------- ЛАЙКИ КАК В ДАЙВИНЧИКЕ ----------
@dp.message(F.text == "💌 Лайки")
async def view_likes(message: types.Message):

    uid = message.from_user.id
    liked = list(likes_received.get(uid, set()))

    if not liked:
        await message.answer("😔 Пока лайков нет")
        return

    likes_view_index[uid] = 0
    await send_like_profile(uid, message)

async def send_like_profile(uid, message):

    liked = list(likes_received.get(uid, set()))
    i = likes_view_index.get(uid, 0)

    if i >= len(liked):
        await message.answer("👍 Ты посмотрел всех")
        return

    target = liked[i]
    user = users[target]

    text = f"❤️ Тебя лайкнул(а)\n\n💘 <b>{user['name']}, {user['age']}</b>\n📍 {user['city']}\n\n✨ {user['about']}"

    await message.answer_photo(user["photo"], caption=text, reply_markup=likes_swipe_kb, parse_mode="HTML")

# ---------- ЛАЙК В ОТВЕТ ----------
@dp.callback_query(F.data == "like_back")
async def like_back(callback: types.CallbackQuery):

    uid = callback.from_user.id
    liked = list(likes_received.get(uid, set()))

    if uid not in likes_view_index:
        return

    target = liked[likes_view_index[uid]]

    likes_sent.setdefault(uid, set()).add(target)

    link1 = f"https://t.me/{users[uid]['username']}"
    link2 = f"https://t.me/{users[target]['username']}"

    await callback.message.answer(f"💘 MATCH!\n👉 {link2}")
    await bot.send_message(target, f"💘 MATCH!\n👉 {link1}")

    likes_view_index[uid] += 1
    await callback.message.delete()
    await send_like_profile(uid, callback.message)
    await callback.answer()

# ---------- ПРОПУСТИТЬ ----------
@dp.callback_query(F.data == "skip_like")
async def skip_like(callback: types.CallbackQuery):

    uid = callback.from_user.id
    likes_view_index[uid] += 1

    await callback.message.delete()
    await send_like_profile(uid, callback.message)
    await callback.answer()

# ---------- SKIP ----------
@dp.callback_query(F.data == "skip")
async def skip(callback: types.CallbackQuery):
    uid = callback.from_user.id
    view_index[uid] += 1
    await callback.message.delete()
    await send_next(uid, callback.message)
    await callback.answer()

# ---------- ЗАПУСК ----------
async def main():
    print("BOT STARTED")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
