"""
    Управление компаниями в БД
"""
from sqlalchemy import DateTime, inspect
from sqlalchemy import create_engine, Column, Integer, String, Float, Sequence
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import update

import os


COMPANIES_DB = 'companies'


# Инициализация и настройка базы данных
engine = create_engine(f'sqlite:///{COMPANIES_DB}.db', echo=False)
Base = declarative_base()

# Создаем сессию для работы с базой данных
Session = sessionmaker(bind=engine)
session = Session()


class Company(Base):
    __tablename__ = 'companies'

    id = Column(Integer, Sequence('company_id_seq'), primary_key=True)
    ticker = Column(String(10), unique=True)
    name = Column(String(50), unique=True)
    initial_price = Column(Float)
    currency = Column(String(10))
    description = Column(String(200))
    industry = Column(String(50))
    headquarters = Column(String(50))
    current_price = Column(Float)

    def __init__(self, ticker, name, initial_price, currency, description=None, industry=None, headquarters=None):
        self.ticker = ticker
        self.name = name
        self.initial_price = initial_price
        self.currency = currency
        self.description = description
        self.industry = industry
        self.headquarters = headquarters
        self.current_price = initial_price


def add_new_company(ticker, name, initial_price, currency, description=None, industry=None, headquarters=None):
    company = session.query(Company).filter_by(ticker=ticker).first()
    if not company:
        new_record = Company(
            ticker=ticker,
            name=name,
            initial_price=initial_price,
            currency=currency,
            description=description,
            industry=industry,
            headquarters=headquarters
        )
        session.add(new_record)
        session.commit()


if not os.path.exists(COMPANIES_DB):
    Base.metadata.create_all(engine)
