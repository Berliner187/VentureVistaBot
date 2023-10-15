import random
import time
from datetime import datetime, timedelta, timezone
import re

from sqlalchemy import create_engine, Column, Integer, String, Float, Sequence
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import update

import asyncio


# Инициализация и настройка базы данных
engine = create_engine('sqlite:///companies.db', echo=False)
Base = declarative_base()


class Company(Base):
    __tablename__ = 'companies'

    id = Column(Integer, Sequence('company_id_seq'), primary_key=True)
    ticker = Column(String(10), unique=True)
    name = Column(String(50))
    initial_price = Column(Float)
    description = Column(String(200))
    industry = Column(String(50))
    headquarters = Column(String(50))
    current_price = Column(Float)

    def __init__(self, ticker, name, initial_price, description=None, industry=None, headquarters=None):
        self.ticker = ticker
        self.name = name
        self.initial_price = initial_price
        self.description = description
        self.industry = industry
        self.headquarters = headquarters
        self.current_price = initial_price


Base.metadata.create_all(engine)


# Функция для обновления цены компании
def update_company_price(session, ticker, max_price_change):
    company = session.query(Company).filter_by(ticker=ticker).first()
    if company:
        price_change = random.uniform(-max_price_change, max_price_change)
        company.current_price += price_change
        # Ограничение цены, чтобы она не стала отрицательной
        company.current_price = max(company.current_price, 0)


price_update_interval = 3

# Создаем сессию для работы с базой данных
Session = sessionmaker(bind=engine)
session = Session()


START_COMPANY_PRICES = {}
COMPANY_PRICES = {}


# Определение временной зоны Москвы
moscow_tz = timezone(timedelta(hours=3))  # UTC+3 для Москвы

# Время начала моделирования (10 утра по московскому времени)
open_time = datetime.now(moscow_tz).replace(hour=10, minute=0, second=0, microsecond=0)
start_time = open_time + timedelta(seconds=price_update_interval)

# Время окончания моделирования (19 вечера по московскому времени)
end_time = datetime.now(moscow_tz).replace(hour=23, minute=0, second=0, microsecond=0)

# Максимальное изменение цены в одном шаге
max_price_change = 5.0


# Работа биржи. Тут формируются цены
async def work_of_the_stock_exchange():
    tickers = session.query(Company.ticker).all()
    ticker_list = [ticker[0] for ticker in tickers]

    all_companies = session.query(Company).all()

    for ticker in ticker_list:
        update_company_price(session, ticker, price_update_interval)
        session.commit()

    for company in all_companies:
        COMPANY_PRICES[company.name] = company.current_price

    print('\n/// STOCK EXCHANGE ///')
    for company in all_companies:
        print(f"Company: {company.name} ({company.current_price})")


def format_timedelta(td):
    days, seconds = td.days, td.seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if days == 0:
        return f"{hours}:{minutes}"
    else:
        return f"{days} день, {hours}:{minutes}"


# Ответ последних данных о компании
async def get_market_info():
    current_time = datetime.now(moscow_tz)
    print(current_time)

    if start_time <= current_time <= end_time:
        # Получаем информацию обо всех компаниях
        all_companies = session.query(Company).all()

        response = ''
        data_companies = []
        # Выводим информацию о каждой компании
        await work_of_the_stock_exchange()

        for company in all_companies:

            if company.name not in START_COMPANY_PRICES:
                START_COMPANY_PRICES[company.name] = company.current_price

            print(f"{company.name} -- ({company.current_price:.2f})")
            delta_price = round(company.current_price - START_COMPANY_PRICES[company.name], 2)
            if delta_price > 0:
                delta_price = f'⬆️+{delta_price} (+{round(delta_price / START_COMPANY_PRICES[company.name] * 100, 2)}%)'
            else:
                delta_price = f'⬇️{delta_price} ({round(delta_price / START_COMPANY_PRICES[company.name] * 100, 2)}%)'
            response += f"{company.name}: {company.current_price:.2f}\n{delta_price}\n\n"
            data_companies.append([company.name, company.current_price])

        response += f'\n[{current_time.strftime("%Y-%m-%d %H:%M:%S")}]'
        return {"text_info": response, "data_companies": data_companies}
    else:
        time_until_open = start_time - current_time
        close_message = f"\n<b>Биржа закрыта</b>\n\nОткроется через {format_timedelta(time_until_open)}"
        print(close_message)
        return {"text_info": close_message}


async def about_company(company_name):
    matching_companies = session.query(Company).filter(Company.name == company_name).all()
    # Проходим по выбранным компаниям и выводим информацию о них
    for company in matching_companies:
        print(f"Ticker: {company.ticker}\nFullname: {company.name}\n Price: {company.current_price}")
