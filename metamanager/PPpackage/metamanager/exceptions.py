class SubmanagerCommandFailure(Exception):
    def __init__(self, message: str):
        super().__init__()

        self.message = message


class EpochException(Exception):
    pass
