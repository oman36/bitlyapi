class APIException(Exception):
    pass


class HttpException(APIException):
    def __init__(self, code, text):
        self.code = code
        self.text = text

    def __str__(self):
        return f'[{self.code}] {self.text}'


class ApiStatusException(HttpException):
    pass


class SessionRequiredException(APIException):
    def __str__(self):
        return 'Session are required. Use "with" statement.'


class AuthException(APIException):
    pass
