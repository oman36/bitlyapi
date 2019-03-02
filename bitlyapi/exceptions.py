class APIException(Exception):
    pass


class HttpException(APIException):
    def __init__(self, code, text):
        self.code = code
        self.text = text

    def __str__(self):
        return '[%d] %s' % (self.code, self.text)


class ApiStatusException(HttpException):
    pass


class HttpMethodNotAllowedException(APIException):
    def __init__(self, method):
        self.method = method

    def __str__(self):
        return 'Method "%s" not allowed' % self.method


class SessionRequiredException(APIException):
    def __str__(self):
        return 'Session are required. Use "with" statement.'


class AuthException(APIException):
    pass
