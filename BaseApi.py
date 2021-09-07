class BaseApi:
    def get(self, *args, **kwargs):
        return self._session.get(*args, **kwargs)

    def post(self, *args, **kwargs):
        return self._session.post(*args, **kwargs)

    def patch(self, *args, **kwargs):
        return self._session.patch(*args, **kwargs)

    def delete(self, *args, **kwargs):
        return self._session.delete(*args, **kwargs)
        
    def put(self, *args, **kwargs):
        return self._session.put(*args, **kwargs)
