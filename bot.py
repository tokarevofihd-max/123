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
viewed_profiles = {}

likes_sent = {}
likes_received = {}
likes_view_index = {}

# ---------- МЕНЮ ----------
menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔥 Найти людей рядом")],
        [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="💌 Лайки")],
        [KeyboardButton(text="⚙️ Кого искать")],
        [KeyboardButton(text="✏️ создать / Изменить анкету")]
    ],
    resize_keyboard=True
)

gender_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👨 Мужской"), KeyboardButton(text="👩 Женский")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

search_gender_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👨 Искать парней"), KeyboardButton(text="👩 Искать девушек")],
        [KeyboardButton(text="🌍 Искать всех")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

swipe_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="❤️ Нравится", callback_data="like")],
        [InlineKeyboardButton(text="👎 Дальше", callback_data="skip")]
    ]
)

# ---------- СОСТОЯНИЯ ----------
class CreateProfile(StatesGroup):
    name = State()
    age = State()
    gender = State()
    city = State()
    about = State()
    photo = State()

class SearchSettings(StatesGroup):
    gender = State()

# ---------- START ----------
@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer("💜 Добро пожаловать", reply_markup=menu)

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
    await message.answer("Выбери пол:", reply_markup=gender_kb)
    await state.set_state(CreateProfile.gender)

@dp.message(CreateProfile.gender)
async def set_gender(message: types.Message, state: FSMContext):
    gender = "male" if "Муж" in message.text else "female"
    await state.update_data(gender=gender)
    await message.answer("Город:", reply_markup=menu)
    await state.set_state(CreateProfile.city)

@dp.message(CreateProfile.city)
async def set_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await message.answer("О себе:")
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
        "gender": data["gender"],
        "search_gender": "any",
        "city": data["city"],
        "about": data["about"],
        "photo": message.photo[-1].file_id,
        "username": message.from_user.username
    }

    viewed_profiles[message.from_user.id] = set()

    await state.clear()
    await message.answer("✅ Анкета сохранена", reply_markup=menu)

# ---------- НАСТРОЙКА ПОИСКА ----------
@dp.message(F.text == "⚙️ Кого искать")
async def search_settings(message: types.Message, state: FSMContext):
    await message.answer("Выбери кого искать:", reply_markup=search_gender_kb)
    await state.set_state(SearchSettings.gender)

@dp.message(SearchSettings.gender)
async def set_search_gender(message: types.Message, state: FSMContext):
    uid = message.from_user.id

    if uid not in users:
        await message.answer("Создай анкету сначала")
        return

    if "парней" in message.text:
        users[uid]["search_gender"] = "male"
    elif "девушек" in message.text:
        users[uid]["search_gender"] = "female"
    else:
        users[uid]["search_gender"] = "any"

    await state.clear()
    await message.answer("✅ Настройки сохранены", reply_markup=menu)

# ---------- ФУНКЦИЯ ПОИСКА ----------
def get_profiles_same_city(uid):
    if uid not in users:
        return []

    my_city = users[uid]["city"].strip().lower()
    search_gender = users[uid]["search_gender"]
    viewed = viewed_profiles.get(uid, set())

    return [
        u for u, data in users.items()
        if u != uid
        and data["city"].strip().lower() == my_city
        and (search_gender == "any" or data["gender"] == search_gender)
        and u not in viewed
    ]

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
    profiles = get_profiles_same_city(uid)

    if not profiles:
        await message.answer("Нет подходящих анкет 😔")
        return

    i = view_index.get(uid, 0)

    if i >= len(profiles):
        await message.answer("Анкеты закончились")
        return

    target = profiles[i]
    viewed_profiles.setdefault(uid, set()).add(target)

    user = users[target]

    text = f"💘 <b>{user['name']}, {user['age']}</b>\n📍 {user['city']}\n\n✨ {user['about']}"

    await message.answer_photo(user["photo"], caption=text, reply_markup=swipe_kb, parse_mode="HTML")

# ---------- LIKE ----------
@dp.callback_query(F.data == "like")
async def like(callback: types.CallbackQuery):

    uid = callback.from_user.id
    profiles = get_profiles_same_city(uid)

    if uid not in view_index or view_index[uid] >= len(profiles):
        await callback.answer()
        return

    target = profiles[view_index[uid]]

    likes_sent.setdefault(uid, set()).add(target)
    likes_received.setdefault(target, set()).add(uid)

    liker = users[uid]
    await bot.send_message(target, f"❤️ Тебя лайкнул(а) {liker['name']}")

    if uid in likes_sent.get(target, set()):
        link1 = f"https://t.me/{users[uid]['username']}"
        link2 = f"https://t.me/{users[target]['username']}"

        await callback.message.answer(f"💘 MATCH!\n👉 {link2}")
        await bot.send_message(target, f"💘 MATCH!\n👉 {link1}")

    view_index[uid] += 1
    await callback.message.delete()
    await send_next(uid, callback.message)
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
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
