import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Enum
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import enum

# Загружаем переменные из .env
load_dotenv()

# os.getenv автоматически возьмет DSN из файла .env
DSN = os.getenv('DSN', 'postgresql://user:1234@localhost:5432/vkinder_db')


engine = create_engine(DSN)
Session = sessionmaker(bind=engine)
Base = declarative_base()

class InteractionStatus(enum.Enum):
    VIEWED = 'viewed'
    FAVORITE = 'favorite'
    BLACKLISTED = 'blacklisted'

class User(Base):
    """Таблица пользователей бота."""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    vk_id = Column(Integer, unique=True, nullable=False)
    
    # Связь с таблицей взаимодействий
    interactions = relationship('Interaction', back_populates='user')

class Candidate(Base):
    """Таблица найденных людей для знакомства."""
    __tablename__ = 'candidates'

    id = Column(Integer, primary_key=True)
    vk_id = Column(Integer, unique=True, nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    profile_link = Column(String(150), nullable=False)

    interactions = relationship('Interaction', back_populates='candidate')

class Interaction(Base):
    """Связующая таблица (история действий: лайк, дизлайк, пропуск)."""
    __tablename__ = 'interactions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    candidate_id = Column(Integer, ForeignKey('candidates.id'), nullable=False)
    status = Column(Enum(InteractionStatus), nullable=False, default=InteractionStatus.VIEWED)

    user = relationship('User', back_populates='interactions')
    candidate = relationship('Candidate', back_populates='interactions')

def create_tables():
    """Скрипт для создания таблиц в БД (требование диплома)."""
    Base.metadata.create_all(engine)

if __name__ == '__main__':
    create_tables()
    print("Таблицы успешно созданы!")