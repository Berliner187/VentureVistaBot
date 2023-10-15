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
# import aiosqlite


__version__ = '0.0.0.2'


os.system('clear')
print('=============== BOT aiogram START ===================')
print(f'---------------- {__version__} ---------------------')
print("""
    Venture Vista
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


async def check_user_in_db(message):
    user_id = message.from_user.id
    first_name = message.chat.first_name
    last_name = message.chat.last_name
    user_name = message.chat.username


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
    first_name = message.chat.first_name
    last_name = message.chat.last_name
    user_name = message.chat.username
    await manage_users.check_user_in_db(user_id, first_name, last_name, user_name)

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
    url_more = InlineKeyboardButton(text='✱Больше', callback_data='more_info_callback')
    url_2 = InlineKeyboardButton(text='🔛Промо', url='https://dribbble.com/shots/22302443-Taxi-Watcher-Y-Logo-Design-Yandex-Taxi')
    url_3 = InlineKeyboardButton(text='❓Часто задаваемые вопросы', url='https://telegra.ph/FAQ-08-27-5')
    url_main = InlineKeyboardButton(text='📰Инструкция', callback_data='send_instruction_callback')
    url_start = InlineKeyboardButton(text='🚀Начать', callback_data='set_address_callback')
    url_kb.add(url_1, url_more)
    url_kb.add(url_3)
    url_kb.add(url_main, url_start)

    await message.answer(
        "<b>Venture</b> <i>Vista</i>.\n\n",
        reply_markup=keyboard, parse_mode='HTML')


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


class CompanyInfoState(StatesGroup):
    ChoosingCompany = State()   # Состояние, когда пользователь находится в разделе О компании


async def update_message(message: types.Message, new_text: str, keyboard):
    await message.edit_text(new_text, reply_markup=keyboard, parse_mode='HTML')


def template_stock_market_message(_market_status):
    return f"<b>ФОНДОВЫЙ РЫНОК</b>\n\n{_market_status}"


USER_STATE = {}
work_status = "work_status"


@dp.message_handler(text='Фондовый рынок')
async def stock_market(message: types.Message, state: FSMContext):
    await StockMarketState.InStockMarket.set()  # Установка состояния

    market_status = await invest_engine.get_market_info()

    keyboard = InlineKeyboardMarkup()
    for company in market_status["data_companies"]:
        # Создайте кнопку, внутри которой будет информация о компании
        button_text = f"{company[0]}"
        company_info_button = InlineKeyboardButton(text=button_text, callback_data=f"{company[0]}")

        # Добавьте кнопку в объект InlineKeyboardMarkup
        keyboard.add(company_info_button)

    sent_message = await bot.send_message(
        message.from_user.id, template_stock_market_message(market_status['text_info']),
        reply_markup=keyboard, parse_mode='HTML')

    if work_status is not True:
        USER_STATE[work_status] = True
        await asyncio.sleep(invest_engine.price_update_interval)

        while True:
            await asyncio.sleep(invest_engine.price_update_interval)

            market_inform = await invest_engine.get_market_info()
            print('//// market_info:', market_inform)

            try:
                await update_message(sent_message, template_stock_market_message(market_inform['text_info']), keyboard)
            except Exception:
                pass

            await state.update_data(sent_message_id=sent_message.message_id)


@dp.message_handler(text='Мои финансы')
async def stock_market(message: types.Message):
    pass


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

    # while True:
    #     asyncio.sleep(invest_engine.price_update_interval)
    #     market_info = invest_engine.get_market_info()
    #     print('// market_info:', market_info)
    #
    #     asyncio.run(stock_exchange_task)
