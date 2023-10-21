import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import DateTime, inspect
from sqlalchemy import create_engine, Column, Integer, String, Float, Sequence
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import update

from apscheduler.schedulers.background import BackgroundScheduler

# Создаем планировщик задач
from flask import Flask, jsonify

import threading
import time


__version__ = '0.0.1.0'


app = Flask(__name__)
scheduler = BackgroundScheduler()

# Инициализация и настройка базы данных
engine = create_engine('sqlite:///companies.db', echo=False)
Base = declarative_base()

# Создаем сессию для работы с базой данных
Session = sessionmaker(bind=engine)
session = Session()


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


price_update_interval = 3


START_COMPANY_PRICES = {}
COMPANY_PRICES = {}


# Определение временной зоны Москвы
moscow_tz = timezone(timedelta(hours=3))
# Время начала моделирования (10 утра по московскому времени)
open_time = datetime.now(moscow_tz).replace(hour=10, minute=0, second=0, microsecond=0)
start_time = open_time + timedelta(seconds=price_update_interval)
# Время окончания моделирования (19 вечера по московскому времени)
end_time = datetime.now(moscow_tz).replace(hour=20, minute=31, second=0, microsecond=0)

# Максимальное изменение цены в одном шаге
max_price_change = 2.0


def format_time(time_not_formatted):
    return time_not_formatted.strftime("%H:%M:%S %Y-%d-%m")


# Функция для обновления цены компании
def update_company_price(session, ticker, max_price_change):
    company = session.query(Company).filter_by(ticker=ticker).first()
    if company:
        price_change = random.uniform(-max_price_change, max_price_change)
        company.current_price += price_change
        # Ограничение цены, чтобы она не стала отрицательной
        company.current_price = max(company.current_price, 0)

        # Создаем новую запись в companies_history с уникальным ID на основе времени
        new_record = CompanyHistory(
            ticker=ticker,
            name=company.name,
            current_price=company.current_price,
            time_update=format_time(datetime.now(moscow_tz))
        )

        session.add(new_record)
        session.commit()


Base.metadata.create_all(engine)


# Работа биржи. Тут формируются цены
def work_of_the_stock_exchange():
    time_now = datetime.now(moscow_tz)
    formatted_time = format_time(time_now)

    global COMPANY_PRICES
    code = 101

    while True:
        if start_time <= time_now <= end_time:
            tickers = session.query(Company.ticker).all()
            companies_from_db = session.query(Company).all()

            ticker_list = [ticker[0] for ticker in tickers]

            for ticker in ticker_list:
                update_company_price(session, ticker, max_price_change)
                session.commit()

            for company in companies_from_db:
                COMPANY_PRICES[company.name] = company.current_price

            print(f'\n/+/ STOCK EXCHANGE: WORK {formatted_time} ///')
            COMPANY_PRICES["options"] = {'last_update': formatted_time, 'status': code}
            return code
        else:
            print(f'\n/-/ STOCK EXCHANGE: NOT WORK {formatted_time} ///')
            code = 102
            COMPANY_PRICES["options"] = {'status': code}
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


# Ответ последних данных о компании
async def get_market_info():
    current_time = datetime.now(moscow_tz)

    if start_time <= current_time <= end_time:
        # Получаем информацию обо всех компаниях
        all_companies = session.query(Company).all()

        response = ''
        # Выводим информацию о каждой компании
        # await work_of_the_stock_exchange()

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

        response += f'[{current_time.strftime("%Y-%m-%d %H:%M:%S")}]'
        return {
            "text_info": response,
            "data_companies": COMPANY_PRICES
        }
    else:
        time_until_open = start_time - current_time
        close_message = f"<b>Биржа закрыта</b>\n\nОткроется через {format_timedelta(time_until_open)}"
        print(close_message)
        return {
            "text_info": close_message,
            "data_companies": COMPANY_PRICES
        }


if __name__ == '__main__':
    scheduler.add_job(work_of_the_stock_exchange, 'interval', seconds=price_update_interval)
    scheduler.start()

    @app.route('/', methods=['GET'])
    def get_data():
        return jsonify(COMPANY_PRICES)

    app.run()
