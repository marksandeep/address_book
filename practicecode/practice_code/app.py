import falcon

from api_resource.auth.login import LoginInfo
from api_resource.address.sample import UserInfo

api = falcon.API()
api.add_route('/user', UserInfo())
api.add_route('/auth', LoginInfo())