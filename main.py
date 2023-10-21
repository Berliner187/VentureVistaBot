#!/usr/bin/env python3
import json
import os
from datetime import time
from csv import DictWriter, DictReader
import datetime
import re


import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import InputFile
from aiogram import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.types import ContentType
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import numpy as np
from aiogram.types import CallbackQuery

import schedule

import invest_engine
import private.manage_users as manage_users


__version__ = '0.0.1.0'


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


USER_STATE = {}
work_status = "work_status"


@dp.message_handler(text='Фондовый рынок')
async def stock_market_start(message: types.Message):
    state = dp.current_state(chat=message.chat.id, user=message.from_user.id)

    # Вход в рыночное меню: установка состояния StockMarketState.InStockMarket
    await StockMarketState.InStockMarket.set()

    # Отправка сообщения о рынке и кнопок
    market_status = await invest_engine.get_market_info()
    keyboard = InlineKeyboardMarkup()
    for company in market_status["data_companies"]:
        button_text = f"{company[0]}"
        company_info_button = InlineKeyboardButton(text=button_text, callback_data=f"company_{company[0]}")
        keyboard.add(company_info_button)

    sent_message = await bot.send_message(
        message.from_user.id, template_stock_market_message(market_status['text_info']),
        reply_markup=keyboard, parse_mode='HTML')


# Обработчик для кнопок с компаниями
@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith("company_"), state=StockMarketState.InStockMarket)
async def handle_company_info(callback_query: types.CallbackQuery, state: FSMContext):
    # Извлечение названия компании
    company_name = callback_query.data.split("_")[1]

    # Отправка информации о компании и клавиатуры
    company_keyboard = InlineKeyboardMarkup()
    buy_button = InlineKeyboardButton("Купить", callback_data=f"buy_{company_name}")
    sell_button = InlineKeyboardButton("Продать", callback_data=f"sell_{company_name}")
    company_keyboard.add(buy_button, sell_button)

    await bot.send_message(
        callback_query.from_user.id,
        f"Информация о компании {company_name}\n\n",
        reply_markup=company_keyboard,
    )


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


# Отслеживание выхода из рыночного меню
@dp.message_handler(lambda message: message.text not in {'Фондовый рынок'}, state=StockMarketState.InStockMarket)
async def exit_stock_market(message: types.Message, state: FSMContext):
    data = await state.get_data()
    sent_message_id = data.get('sent_message_id')

    if sent_message_id:
        await bot.delete_message(message.from_user.id, sent_message_id)

    await state.finish()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
