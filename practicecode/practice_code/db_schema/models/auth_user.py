from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String
from sqlalchemy import Sequence, create_engine
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
engine = create_engine('mysql://root:rootroot@localhost/test_demo')
session = sessionmaker()


class AuthUser(Base):

    __tablename__ = 'auth_users'

    id = Column(Integer, Sequence('auth_id_seq'), primary_key=True)
    user_name = Column(String(50), unique=True)
    password = Column(String(20))

    def  __repr__(self):
        pass


session.configure(bind=engine)
Base.metadata.create_all(engine)