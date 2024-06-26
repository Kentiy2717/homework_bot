class MyExceptionError(Exception):
    """
    Родительский класс моих исключений.
    От него будут наследоваться все остальные исключения.
    """

    pass


class UnexpectedResponseError(MyExceptionError):
    """Cбой при запросе к эндпоинту. Неожиданный ответ."""

    pass


class IncorrectResponseError(MyExceptionError):
    """Cбой при запросе к эндпоинту. Некорректный ответ."""

    pass


class NotTokenError(MyExceptionError):
    """Cбой при запросе к эндпоинту. Некорректный ответ."""

    pass


class SendingMessageError(MyExceptionError):
    """Cбой при запросе к эндпоинту. Некорректный ответ."""

    pass

