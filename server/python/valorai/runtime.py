from contextvars import ContextVar

from valorai.http import RegistrationApi

api_context: ContextVar[RegistrationApi] = ContextVar("valorai_api")


def current_api() -> RegistrationApi:
    return api_context.get()
