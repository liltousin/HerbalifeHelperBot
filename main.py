from config import TOKEN
import data_worker as db
import pic_worker as pic
from aiogram import Dispatcher, Bot, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())


class UserRegistration(StatesGroup):
    waiting_for_firstname = State()
    waiting_for_lastname = State()
    waiting_for_profile_picture = State()
    waiting_for_confirmation = State()


@dp.message_handler(state=UserRegistration.waiting_for_firstname)
async def entered_firstname(message: types.Message, state: FSMContext):
    await state.update_data(firstname=message.text.capitalize())
    await message.answer('Введите вашу фамилию', reply_markup=types.ReplyKeyboardRemove())
    await UserRegistration.next()


@dp.message_handler(state=UserRegistration.waiting_for_lastname)
async def entered_lastname(message: types.Message, state: FSMContext):
    await state.update_data(lastname=message.text.capitalize())
    await message.answer(f"Пришлите ваше фото", reply_markup=types.ReplyKeyboardRemove())
    await UserRegistration.next()


@dp.message_handler(content_types=types.ContentType.PHOTO, state=UserRegistration.waiting_for_profile_picture)
async def sending_photo(message: types.Message, state: FSMContext):
    await message.photo[-1].download(destination_file=f'pic/{message.from_user.id}.jpg')
    pic.resize_image(f'pic/{message.from_user.id}.jpg')
    user_data = await state.get_data()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add('Да')
    keyboard.add('Нет')
    await message.answer_photo(
        photo=open(f'pic/{message.from_user.id}.jpg', 'rb'),
        caption=f"{user_data['firstname']} {user_data['lastname']}, все верно?",
        reply_markup=keyboard)
    await UserRegistration.next()


@dp.message_handler(state=UserRegistration.waiting_for_confirmation)
async def user_data_validation(message: types.Message, state: FSMContext):
    if message.text == 'Нет':
        await UserRegistration.first()
        await message.answer('Введите ваше имя', reply_markup=types.ReplyKeyboardRemove())
        await state.reset_data()
    elif message.text == 'Да':
        user_data = await state.get_data()
        db.add_user_data(message.from_user.id, user_data)
        await message.answer(
            f"{user_data['firstname']} {user_data['lastname']}, вы успешно зарегистрировались",
            reply_markup=types.ReplyKeyboardRemove())
        await state.finish()
        firstname, lastname = db.get_user_name(message.from_user.id)
        await message.answer(f'Здравствуйте {firstname} {lastname}', reply_markup=types.ReplyKeyboardRemove())
    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add('Да')
        keyboard.add('Нет')
        await message.answer('Используйте клавиатуру!', reply_markup=keyboard)


@dp.message_handler(commands='start')
async def start(message: types.Message):
    if db.user_check(message.from_user.id):
        firstname, lastname = db.get_user_name(message.from_user.id)
        await message.answer(f'Здравствуйте {firstname} {lastname}', reply_markup=types.ReplyKeyboardRemove())
    else:
        await message.answer('Кажется вы не пользовались до этого ботом.')
        await message.answer('Введите ваше имя', reply_markup=types.ReplyKeyboardRemove())
        await UserRegistration.first()


if __name__ == '__main__':
    db.create_db()
    executor.start_polling(dp)
