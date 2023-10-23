#!/usr/bin/env python3
import json
import os
import time

from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage

import stock_manager
import private.manage_users as manage_users


__version__ = '0.0.1.1'


os.system('clear')
print('=============== BOT aiogram START ===================')
print(f'---------------- {__version__} ---------------------')
print("""
     _  _  ____  _  _  ____  __  __  ____  ____    _  _  ____  ___  ____   __   
    ( \/ )( ___)( \( )(_  _)(  )(  )(  _ \( ___)  ( \/ )(_  _)/ __)(_  _) /__\  
     \  /  )__)  )  (   )(   )(__)(  )   / )__)    \  /  _)(_ \__ \  )(  /(__)\ 
      \/  (____)(_)\_) (__) (______)(_)\_)(____)    \/  (____)(___/ (__)(__)(__)
""")
print('==================== Venture Vista ==================')


### --- DEV PROGRAM INFO ---
DEBUG = True


## ВЗАИМОДЕЙСТВИЕ С API
try:
    with open('config.json') as config_file:
        _config = json.load(config_file)
    API_TOKEN = _config["telegram_token"]
    admin_user_id = _config["admin_id"]
except Exception as e:
    API_TOKEN = None
    print("ОШИБКА при ЧТЕНИИ токена ТЕЛЕГРАМ", e)


bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())


# Включение логгирования
# logging.basicConfig(level=logging.INFO)
# dp.middleware.setup(LoggingMiddleware())


# ============================================================================
# ------------------------- ПОЛЬЗОВАТЕЛЬСКИЕ КОМАНДЫ -------------------------
@dp.message_handler(commands=['start'])
async def start_message(message: types.Message):
    wait_message = await message.answer(
        "<b>/// ЗАПУСК...\n\n"
        "/// DESIGN by </b>KOZAK\n",
        parse_mode='HTML'
    )

    user_id = message.from_user.id
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    username = message.from_user.username

    print(user_id, first_name, last_name, username)
    manage_users.check_user_in_db(user_id=user_id, first_name=first_name, last_name=last_name, username=username)

    kb = [
        [
            types.KeyboardButton(text="Фондовый рынок"),
        ],
        [
            types.KeyboardButton(text="Мой портфель"),
            types.KeyboardButton(text="Мои финансы")
        ]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    # await bot.send_photo(
    #     message.from_user.id, photo=InputFile('img/menu.png', filename='start_message.png'), reply_markup=keyboard)
    await wait_message.delete()

    url_kb = InlineKeyboardMarkup(row_width=3)
    url_1 = InlineKeyboardButton(text='☎️Поддержка', url='https://t.me/schneller_los')
    url_2 = InlineKeyboardButton(text='🔛Промо', url='https://dribbble.com/kozak_developer')
    url_kb.add(url_1)
    url_kb.add(url_2)

    await message.answer(
        "<b>Venture</b> <i>Vista</i>.\n\n",
        reply_markup=url_kb, parse_mode='HTML')


@dp.message_handler(text='Главная')
@dp.message_handler(commands=['menu'])
async def main_func(message: types.Message):
    btn = [
        [
            types.KeyboardButton(text="Мои финансы"),
            types.KeyboardButton(text="Фондовый рынок")
        ],
        [
            types.KeyboardButton(text="Главная")
        ]
    ]

    keyboard = types.ReplyKeyboardMarkup(keyboard=btn, resize_keyboard=True, one_time_keyboard=True)
    await message.answer(
        "Вы на главной", reply_markup=keyboard, parse_mode='HTML')


# Состояния
class StockMarketState(StatesGroup):
    InStockMarket = State()  # Состояние, когда пользователь находится в разделе Фондовый рынок
    SentMessageId = State()  # Состояние для хранения ID отправленного сообщения
    WaitingForAmount = State()


class CompanyInfoState(StatesGroup):
    ChoosingCompany = State()   # Состояние, когда пользователь находится в разделе О компании


class StateWorkStockExchange(StatesGroup):
    pass


async def update_message(message: types.Message, new_text: str, keyboard):
    await message.edit_text(new_text, reply_markup=keyboard, parse_mode='HTML')


def template_stock_market_message(_market_status):
    return f"<b>ФОНДОВЫЙ РЫНОК</b>\n\n{_market_status}"


LAST_MESSAGE_STOCK_EX_BOT, LAST_MESSAGE_STOCK_EX_USER = {}, {}


# МЕХАНИЗМ УДАЛЕНИЯ СООБЩЕНИЯ (ИМИТАЦИЯ МЕНЮ)
async def delete_messages(message):
    try:
        if LAST_MESSAGE_STOCK_EX_USER.get(message.from_user.id):
            await bot.delete_message(message.chat.id, LAST_MESSAGE_STOCK_EX_USER[message.from_user.id])
        if LAST_MESSAGE_STOCK_EX_BOT.get(message.from_user.id):
            await bot.delete_message(message.chat.id, LAST_MESSAGE_STOCK_EX_BOT[message.from_user.id])
    except Exception:
        pass


async def drop_message(message: types.Message, sent_message):
    LAST_MESSAGE_STOCK_EX_USER[message.from_user.id] = sent_message.message_id
    LAST_MESSAGE_STOCK_EX_BOT[message.from_user.id] = message.message_id


# Декоратор для измерения времени выполнения
def timing_decorator(func):
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        print(f"{func.__name__} выполнилась за {end_time - start_time} секунд")
        return result
    return wrapper


@dp.message_handler(text='Фондовый рынок')
async def stock_market_start(message: types.Message):
    await delete_messages(message)

    # Отправка сообщения о рынке и кнопок
    market_status = await stock_manager.get_stock_exchange_info()
    keyboard = InlineKeyboardMarkup()
    print(market_status["data_companies"])

    # response_of_indicators = await stock_manager.get_stock_exchange_info()

    # Формирование кнопок
    for company in market_status["data_companies"]:
        company_info_button = InlineKeyboardButton(text=company, callback_data=f"company_{company}")
        keyboard.add(company_info_button)

    sent_message = await bot.send_message(
        message.from_user.id, template_stock_market_message(market_status['text_info']),
        reply_markup=keyboard, parse_mode='HTML')

    await drop_message(message, sent_message)


# Обработчик для кнопок с компаниями
def get_company_info_text(selected_company):
    return f"<b>{selected_company}</b>\n\n" \
           f""


# Обработка нажатия на кнопку
@dp.callback_query_handler(lambda callback: callback.data.startswith('company_'))
async def process_company_button(callback_query: types.CallbackQuery):
    selected_company = callback_query.data.split('_')[1]
    print(selected_company)

    new_message_text = get_company_info_text(selected_company)

    await bot.send_message(
        callback_query.from_user.id,
        new_message_text,
        parse_mode='HTML'
    )

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)


# Далее обработчики для кнопок "Купить" и "Продать"
@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith("buy_"), state=StockMarketState.InStockMarket)
async def handle_buy_button(callback_query: types.CallbackQuery, state: FSMContext):
    # Извлечение названия компании
    company_name = callback_query.data.split("_")[1]
    await bot.send_message(callback_query.from_user.id, f"Сколько хотите купить акций компании {company_name}?")
    await StockMarketState.WaitingForAmount.set()


@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith("sell_"), state=StockMarketState.InStockMarket)
async def handle_sell_button(callback_query: types.CallbackQuery, state: FSMContext):
    # Извлечение названия компании
    company_name = callback_query.data.split("_")[1]
    await bot.send_message(callback_query.from_user.id, f"Сколько хотите продать акций компании {company_name}?")


@dp.message_handler(lambda message: not message.text.isdigit(), state=StockMarketState.WaitingForAmount)
async def handle_invalid_input(message: types.Message):
    await message.reply("Пожалуйста, введите целое число.")
    print(message)
    return


@dp.message_handler(lambda message: message.text.isdigit(), state=StockMarketState.WaitingForAmount)
async def handle_amount_input(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        # Извлекаем название компании из состояния
        company_name = data['company_name']
        print(f'\n{company_name}\n')

    # Извлекаем введенное количество акций
    amount = int(message.text)
    print(amount)

    # Здесь вы можете добавить логику для записи информации о покупке в БД
    # Например, записать информацию о покупке акций компании `company_name` в количестве `amount`

    await message.reply(f"Вы успешно купили {amount} акций компании {company_name}.")

    # Завершаем состояние BuyStockState
    await state.finish()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
