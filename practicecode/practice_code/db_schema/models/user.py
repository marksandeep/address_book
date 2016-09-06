from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String
from sqlalchemy import Sequence, create_engine
from sqlalchemy.orm import sessionmaker


Base = declarative_base()
engine = create_engine('mysql://root:rootroot@localhost/test_demo')
session = sessionmaker()


class User(Base):

    __tablename__ = 'users'

    id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    name = Column(String(50))
    address = Column(String(100))
    home_phone = Column(Integer)
    work_phone = Column(Integer)


    def __repr__(self):

       return "<User(name='%s', address='%s', home_phone='%d', work_phone='%d')>" % (
           self.name, self.fullname, self.password, self.work_phone)

session.configure(bind=engine)
Base.metadata.create_all(engine)

