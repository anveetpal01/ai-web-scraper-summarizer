class AppError(Exception):
    """An error whose message is safe to show to the user, with the HTTP status to respond with."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
