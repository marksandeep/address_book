import falcon
import json

from sqlalchemy.orm import sessionmaker

from db_schema.models.auth_user import AuthUser, engine

Session = sessionmaker()
Session.configure(bind=engine)
session = Session()

class LoginInfo():

    def on_get(self, req, resp):
        list1=[]
        rows = session.query(AuthUser.id.label('id'), AuthUser.user_name.label('user_name'))
        for user in rows:
            list1.append({"user_name":user.user_name})
        if list1:
            resp.body = json.dumps(list1)
        resp.status = falcon.HTTP_200

    def on_post(self,req, resp):
        raw_json = req.stream.read()
        request_data = json.loads(raw_json)
        user_name = request_data.get('user_name')
        password = request_data.get('password')
        new_record = AuthUser(user_name=user_name, password=password)
        session.add(new_record)
        session.flush()
        session.commit()
        id = new_record.id
        if id:
            resp.body = json.dumps({'id': id})
        resp.status = falcon.HTTP_201
        pass
