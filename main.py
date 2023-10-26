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
from sqlalchemy import create_engine, Column, Integer, String, Float, Sequence
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import stock_manager
import private.manage_users as manage_users
import public.manage_companies as manage_companies


__version__ = '0.0.2.0'


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
# ======================== БАЗЫ ДАННЫХ =====================
# ------------------------- КОМПАНИИ -----------------------
engine = create_engine(f'sqlite:///companies.db', echo=False)
Base = declarative_base()

Session = sessionmaker(bind=engine)
session_companies = Session()

# ------------------ ПОЛЬЗОВАТЕЛИ -----------------
# Инициализация и настройка базы данных
engine_users = create_engine(f'sqlite:///private/users.db', echo=False)
DataBaseUsers = declarative_base()

SessionUsers = sessionmaker(bind=engine_users)
session_users = SessionUsers()


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

    # manage_users.check_user_in_db(user_id=user_id, first_name=first_name, last_name=last_name, username=username)

    kb = [
        [
            types.KeyboardButton(text="📈Фондовый рынок"),
        ],
        [
            types.KeyboardButton(text="👛Бумажник"),
            types.KeyboardButton(text="💼Портфель")
        ]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await wait_message.delete()

    url_kb = InlineKeyboardMarkup(row_width=3)
    url_1 = InlineKeyboardButton(text='☎️Поддержка', url='https://t.me/schneller_los')
    url_2 = InlineKeyboardButton(text='🔛Промо', url='https://dribbble.com/kozak_developer')
    url_kb.add(url_1)
    url_kb.add(url_2)

    await message.answer(
        "<b>Venture</b> <i>Vista</i>.\n\n",
        reply_markup=keyboard, parse_mode='HTML')

    existing_user = session_users.query(manage_users.User).filter_by(user_id=user_id).first()

    if existing_user is not None:
        pass
    else:
        print(f"/// NEW USER: {user_id} ///")
        new_user = manage_users.User(user_id=user_id, first_name=first_name, last_name=last_name, username=username)
        personal_account = manage_users.PersonalAccount(user_id, 1000, 'RST', 'Bonus')
        session_users.add(new_user)
        session_users.add(personal_account)
        session_users.commit()

        await message.answer(
            f"<b>Ваш счёт пополнен на {AVAILABLE_CURRENCY['RST']}1,000 ✅</b>.\n\n"
            f"Начните торговать прямо сейчас!",
            reply_markup=keyboard, parse_mode='HTML')


@dp.message_handler(text='🏠Главная')
@dp.message_handler(commands=['menu'])
async def main_func(message: types.Message):
    btn = [
        [
            types.KeyboardButton(text="📈Фондовый рынок")
        ],
        [
            types.KeyboardButton(text="🏠Главная"),
            types.KeyboardButton(text="👛Бумажник"),
            types.KeyboardButton(text="💼Портфель"),
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
    ConfirmPurchase = State()


class CompanyInfoState(StatesGroup):
    ChoosingCompany = State()   # Состояние, когда пользователь находится в разделе О компании


async def update_message(message: types.Message, new_text: str, keyboard):
    await message.edit_text(new_text, reply_markup=keyboard, parse_mode='HTML')


def template_stock_market_message(_market_status):
    return f"<b>📈 ФОНДОВЫЙ РЫНОК 📈</b>\n\n{_market_status}"


# ------- КОНСТАНТЫ -----------
AVAILABLE_CURRENCY = {
    "RST": "Σ"
}


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


@dp.message_handler(text='📈Фондовый рынок')
async def stock_market_main(message: types.Message):
    await delete_messages(message)

    # Отправка сообщения о рынке и кнопок
    market_status = await stock_manager.get_stock_exchange_info()
    keyboard = InlineKeyboardMarkup()

    # Формирование кнопок с компаниями
    for company in market_status["data_companies"]:
        company_info_button = InlineKeyboardButton(text=company, callback_data=f"company_{company}")
        keyboard.add(company_info_button)

    sent_message = await bot.send_message(
        message.from_user.id, template_stock_market_message(market_status['text_info']),
        reply_markup=keyboard, parse_mode='HTML')

    await drop_message(message, sent_message)


# Обработка нажатия на кнопку
@dp.callback_query_handler(lambda callback: callback.data.startswith('company_'))
async def process_company_button(callback_query: types.CallbackQuery):
    market_prices = await stock_manager.get_actual_prices()

    selected_company = callback_query.data.split('_')[1]

    company = session_companies.query(manage_companies.Company).filter_by(name=selected_company).first()
    description = company.description
    current_price = company.current_price

    keyboard = InlineKeyboardMarkup(row_width=2)
    buy_button = InlineKeyboardButton(text="Купить", callback_data=f"buy_{selected_company}")
    sell_button = InlineKeyboardButton(text="Продать", callback_data=f"sell_{selected_company}")
    # back_btn = InlineKeyboardButton(text='⬅️ Назад', callback_data='Фондовый рынок')
    keyboard.add(buy_button, sell_button)

    current_price = round(current_price, 2)
    day_max = round(market_prices[selected_company]['day_max'], 2)
    day_min = round(market_prices[selected_company]['day_min'], 2)

    day_start_price = market_prices[selected_company]['day_start_price']
    delta_day_start_price = round(current_price - day_start_price, 2)
    delta_day_start_price_percent = round(100 - day_start_price * 100 / current_price, 2)

    indicators = ''
    if delta_day_start_price > 0:
        indicators += f'+{delta_day_start_price}🟩  (+{delta_day_start_price_percent}%)'
    elif delta_day_start_price == 0:
        indicators += f'{delta_day_start_price}🟨  ({delta_day_start_price_percent}%)'
    else:
        indicators += f'{delta_day_start_price}🟥  ({delta_day_start_price_percent}%)'

    await bot.send_message(
            callback_query.from_user.id,
            f"<b>О компании {selected_company}</b>\n\n"
            f"{description}\n\n"
            f"<b>{current_price}</b>  {indicators}\n"
            f"{day_max}⬆️  {day_min}⬇️",
            reply_markup=keyboard,
            parse_mode='HTML'
        )

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)


SELECTED_COMPANY = {}


# Обработчик кнопки "Купить"
@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith("buy_"))
async def process_buy_button(callback_query: types.CallbackQuery):
    btn = [
        [
            types.KeyboardButton(text="📈Фондовый рынок")
        ],
        [
            types.KeyboardButton(text="🏠Главная"),
            types.KeyboardButton(text="💼Портфель"),
            types.KeyboardButton(text="👛Бумажник"),
        ]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=btn, resize_keyboard=True, one_time_keyboard=True)

    selected_company = callback_query.data.split("_")[1]
    # Выбранная пользователем компания временно хранится здесь
    SELECTED_COMPANY[callback_query.from_user.id] = selected_company

    await bot.send_message(
        callback_query.from_user.id,
        f"Сколько акций {selected_company} вы хотите купить?",
        reply_markup=keyboard, parse_mode='HTML'
    )
    await StockMarketState.WaitingForAmount.set()


@dp.message_handler(state=StockMarketState.WaitingForAmount)
async def process_amount_input(message: types.Message, state: FSMContext):
    try:
        # count - он же quantity - означает количество
        company = session_companies.query(manage_companies.Company).filter_by(name=SELECTED_COMPANY[message.from_user.id]).first()
        current_price = company.current_price
        ticker = company.ticker

        quantity = int(message.text)
        message_user_id = message.from_user.id

        personal_account = session_users.query(manage_users.PersonalAccount).filter_by(user_id=message_user_id).first()
        currency = personal_account.currency

        if personal_account.balance >= current_price * quantity:
            personal_account.balance -= current_price * quantity

            exist_company = session_users.query(manage_users.Portfolio).filter_by(ticker=ticker).first()

            if exist_company:
                print('///// ПОПАЛ ////////')
                # TODO: Обновить существующие данные
                average_price = round(exist_company.purchase_amount * exist_company.count) + (current_price * quantity)
                exist_company.count += quantity
                exist_company.purchase_amount = average_price
            else:
                new_transaction = manage_users.Portfolio(message_user_id, 'buy', ticker, current_price, quantity, 'RST')
                session_users.add(new_transaction)

            session_users.commit()

            await message.answer(
                f"<b>Успешно ✅</b>\n\nВы приобрели акции компании {company.name}\n\n"
                f"<i>Количество: {quantity}</i>\n"
                f"<i>Сумма: {round(current_price * quantity, 2)} {AVAILABLE_CURRENCY[currency]}</i>\n\n"
                f"Доступно: {round(personal_account.balance, 2)} {AVAILABLE_CURRENCY[currency]}",
                parse_mode='HTML'
            )
        else:
            await message.answer(
                f"<b>Недостаточно средств 🚫</b>\n\nВыполнить операцию невозможно.\n\n"
                f"Доступно: {round(personal_account.balance, 2)} {AVAILABLE_CURRENCY[currency]}",
                parse_mode='HTML'
            )

        await state.finish()
        SELECTED_COMPANY[message.from_user.id] = None
    except ValueError:
        await message.answer("Введите корректное количество акций.")


@dp.message_handler(text='💼Портфель')
async def process_buy_button(message: types.Message):
    personal_account = session_users.query(manage_users.Portfolio).filter_by(user_id=message.from_user.id)
    print(personal_account)
    # personal_account


@dp.message_handler(text='👛Бумажник')
async def process_buy_button(message: types.Message):
    pass


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
