class RetryException(Exception):

    def __init__(self, msg='', default=None, wait_s: int = 0, *args: object) -> None:
        self.msg = msg
        self.default = default
        self.wait_s = wait_s
        super().__init__(msg, *args)


class MaxRetryException(Exception):
    pass


class NeedToImplementException(Exception):
    pass


class PassengerNotFoundException(Exception):
    pass


class InstanceAlreadyInitedException(Exception):
    pass


class LoadConfigFailException(Exception):

    def __init__(self, msg: str, *args: object) -> None:
        super().__init__(*args)
        self.msg = msg
