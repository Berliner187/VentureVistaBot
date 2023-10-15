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
from aiogram.types import InputFile
from aiogram import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import aiogram.utils.markdown as fmt

import numpy as np

import schedule

import invest_engine
# import aiosqlite


__version__ = '0.0.0.1'


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
dp = Dispatcher(bot)


# Включение логгирования
logging.basicConfig(level=logging.INFO)
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
    await asyncio.sleep(1)
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


stock_market_message = {}


async def update_message(message: types.Message, new_text: str):
    await message.edit_text(new_text, parse_mode='HTML')


def template_stock_market_message(_market_status):
    return f"<b>ФОНДОВЫЙ РЫНОК</b>\n\n{_market_status}"


@dp.message_handler(text='Фондовый рынок')
async def stock_market(message: types.Message):
    market_status = await invest_engine.get_market_info()

    sent_message = await bot.send_message(
        message.from_user.id, template_stock_market_message(market_status), parse_mode='HTML')

    while True:
        await asyncio.sleep(invest_engine.price_update_interval)

        market_info = await invest_engine.get_market_info()
        print('// market_info:', market_info)
        print(template_stock_market_message(market_info))
        await update_message(sent_message, template_stock_market_message(market_info))


if __name__ == '__main__':
    # Создание и запуск цикла для работы бота и обновления цен
    loop = asyncio.get_event_loop()

    # Запускаем функцию работы биржи в фоновом режиме
    stock_exchange_task = loop.create_task(invest_engine.work_of_the_stock_exchange())
    # Запускаем бота
    bot_task = loop.create_task(executor.start_polling(dp, skip_updates=True))

    # Запуск event loop для выполнения обеих задач
    loop.run_until_complete(asyncio.gather(stock_exchange_task, bot_task))

    while True:
        loop.run_until_complete(invest_engine.work_of_the_stock_exchange())
