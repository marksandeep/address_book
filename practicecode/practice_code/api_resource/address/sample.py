import falcon
import json

from sqlalchemy.orm import sessionmaker

from db_schema.models.user import User, engine

Session = sessionmaker()
Session.configure(bind=engine)
session = Session()


class UserInfo():

    def on_get(self, req, resp):
        list1 = []
        rows = session.query(User.id.label('id'), User.name.label('name'), User.home_phone.label('home_phone'))
        for i in rows:
            list1.append({'id': i.id, 'name': i.name, 'home_phone': i.home_phone})
        if list1:
            resp.body = json.dumps(list1)
        resp.status = falcon.HTTP_200

    def on_post(self, req, resp):

        raw_json = req.stream.read()
        request_data = json.loads(raw_json)
        name = request_data.get('name')
        address = request_data.get('address')
        home_phone = request_data.get('home_phone')
        work_phone = request_data.get('work_phone')
        new_record = User(name=name, address=address, home_phone=home_phone, work_phone=work_phone)
        session.add(new_record)
        session.flush()
        session.commit()
        id = new_record.id
        if id:
            resp.body = json.dumps({'id':id})
        resp.status = falcon.HTTP_201

