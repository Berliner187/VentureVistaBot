import random
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import DateTime, inspect
from sqlalchemy import create_engine, Column, Integer, String, Float, Sequence
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import update

from apscheduler.schedulers.background import BackgroundScheduler

from flask import Flask, jsonify

from public.manage_companies import Company


__version__ = '0.0.2.0'


# Инициализация и настройка базы данных
engine = create_engine('sqlite:///companies.db', echo=False)
Base = declarative_base()

# Создаем сессию для работы с базой данных
Session = sessionmaker(bind=engine)
session = Session()


class CompanyHistory(Base):
    __tablename__ = 'companies_history'

    id = Column(Integer, primary_key=True)
    ticker = Column(String(10))
    name = Column(String(50))
    current_price = Column(Float)
    time_update = Column(String(20))

    def __init__(self, ticker, name, current_price, time_update):
        self.ticker = ticker
        self.name = name
        self.current_price = current_price
        self.time_update = time_update


price_update_interval = 5


START_COMPANY_PRICES = {}
COMPANY_PRICES = {}


# Определение временной зоны Москвы
moscow_tz = timezone(timedelta(hours=3))
# Время начала моделирования
open_time = datetime.now(moscow_tz).replace(hour=10, minute=0, second=0, microsecond=0)
start_time = open_time + timedelta(seconds=price_update_interval)
# Время окончания моделирования
end_time = datetime.now(moscow_tz).replace(hour=23, minute=31, second=0, microsecond=0)

# Максимальное изменение цены в одном шаге
max_price_change = 10.0


def format_time(time_not_formatted):
    return time_not_formatted.strftime("%H:%M:%S %Y-%d-%m")


# Расчет показателей, которые видит пользователь
def indicators_of_stocks():
    pass


# Функция для обновления цены компании
def update_company_price(session, ticker, max_price_change):
    company = session.query(Company).filter_by(ticker=ticker).first()
    if company:
        price_change = random.uniform(-max_price_change, max_price_change)
        company.current_price += price_change
        # Ограничение цены, чтобы она не стала отрицательной
        company.current_price = max(company.current_price, 0.01)

        # Создаем новую запись в companies_history с уникальным ID на основе времени
        new_record = CompanyHistory(
            ticker=ticker,
            name=company.name,
            current_price=company.current_price,
            time_update=format_time(datetime.now(moscow_tz))
        )

        session.add(new_record)
        session.commit()


# Создание БД
Base.metadata.create_all(engine)

# manage_companies.add_new_company(session, 'TSLA', 'Tesla', 700, 'An innovative company specializing in electric cars and energy solutions', 'Automotive and Energy', 'Palo Alto, California, USA')


# Работа биржи. Тут формируются цены
def work_of_the_stock_exchange():
    time_now = datetime.now(moscow_tz)
    formatted_time = format_time(time_now)
    last_update_price = ''

    global COMPANY_PRICES
    code = 200

    while True:
        if start_time <= time_now <= end_time:
            tickers = session.query(Company.ticker).all()
            companies_from_db = session.query(Company).all()

            ticker_list = [ticker[0] for ticker in tickers]

            for ticker in ticker_list:
                update_company_price(session, ticker, max_price_change)
                session.commit()

            for company in companies_from_db:
                company_name = company.name

                if company_name not in COMPANY_PRICES:
                    COMPANY_PRICES[company_name] = {}  # Создать пустой словарь для компании
                    COMPANY_PRICES[company_name]["day_min"] = company.current_price
                    COMPANY_PRICES[company_name]["day_max"] = company.current_price

                COMPANY_PRICES[company_name]["price"] = company.current_price

                if company.current_price > COMPANY_PRICES[company_name]["day_max"]:
                    COMPANY_PRICES[company_name]["day_max"] = company.current_price
                if company.current_price < COMPANY_PRICES[company_name]["day_min"]:
                    COMPANY_PRICES[company_name]["day_min"] = company.current_price

            last_update_price += formatted_time
            print(f'\n/+/ STOCK EXCHANGE {formatted_time} /WORK/')
            COMPANY_PRICES["options"] = {'last_update': formatted_time, 'status': code}
            return code
        else:
            print(f'\n/-/ STOCK EXCHANGE {formatted_time} /NOT WORK/')
            code = 404
            COMPANY_PRICES["options"] = {'last_update': last_update_price, 'status': code}
            return code


def format_timedelta(td):
    days, seconds = td.days, td.seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if days == 0:
        return f"{hours} ч, {minutes} мин"
    elif days < 0:
        return f"{hours} ч, {minutes} мин"
    else:
        return f"{days} день, {hours}:{minutes}"


async def get_actual_prices():
    async with httpx.AsyncClient() as client:
        response = await client.get('http://localhost:5000/data')
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Произошла ошибка при получении данных: {response.status_code}")
            return {}


# Ответ последних данных о компании
async def get_stock_exchange_info():
    current_time = datetime.now(moscow_tz)
    global COMPANY_PRICES

    if start_time <= current_time <= end_time:
        # Получаем информацию обо всех компаниях
        # all_companies = session.query(Company).all()

        response = ''
        # Выводим информацию о каждой компании
        companies_indicators = await get_actual_prices()

        companies = []

        for company_name, company_data in companies_indicators.items():
            if company_name != 'options':
                print(company_name, company_data)

                price = company_data.get("price")
                day_max = company_data.get("day_max")
                day_min = company_data.get("day_min")

                for key, value in company_data.items():
                    print(f"  {key}: {value}")

                delta_price = round(price - day_min, 2)
                percent_price = round(100 - day_min * 100 / price, 2)
                day_min, day_max = round(day_min, 2), round(day_max, 2)
                if delta_price > 0:
                    delta_price = f'🟩 +{delta_price} (+{percent_price}%)'
                elif delta_price == 0:
                    delta_price = f'🟨 {delta_price} ({percent_price}%)'
                else:
                    delta_price = f'🟥 {delta_price} ({percent_price}%)'

                response += f"{company_name}: {price:.2f}\n{delta_price}\n\n"
                companies.append(company_name)

        response += f'[{current_time.strftime("%Y-%m-%d %H:%M:%S")}]'
        return {
            "text_info": response,
            "data_companies": companies
        }
    else:
        time_until_open = start_time - current_time
        close_message = f"<b>Биржа закрыта</b>\n\nОткроется через {format_timedelta(time_until_open)}"
        print(close_message)
        return {
            "text_info": close_message,
            "data_companies": COMPANY_PRICES
        }
