import base64
import re
from datetime import datetime

from valorai.errors import ApiError
from valorai.records import ProfileUpdate, Registration

STATES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}
MAX_AVATAR_BYTES = 2 * 1024 * 1024
AVATAR_PREFIX = re.compile(r"^data:image/(?:jpeg|jpg|png);base64,([A-Za-z0-9+/=\s]+)$")


def digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def valid_cpf(value: str) -> bool:
    cpf = digits(value)
    if len(cpf) != 11 or re.fullmatch(r"(\d)\1+", cpf):
        return False
    for size in (9, 10):
        total = sum(int(cpf[index]) * (size + 1 - index) for index in range(size))
        if ((total * 10) % 11) % 10 != int(cpf[size]):
            return False
    return True


def old_enough(value: object, today: datetime) -> bool:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False
    year, month, day = (int(part) for part in value.split("-"))
    try:
        born = datetime(year, month, day, 12, 0, tzinfo=today.tzinfo)
        cutoff = datetime(today.year - 16, today.month, today.day, 23, 59, tzinfo=today.tzinfo)
    except ValueError:
        return False
    return born.date().isoformat() == value and born <= cutoff and born.year >= 1900


def password_message(value: object) -> str | None:
    if not isinstance(value, str):
        return "Use pelo menos 8 caracteres."
    message = None
    if len(value) < 8:
        message = "Use pelo menos 8 caracteres."
    if len(value) > 32:
        message = "Use no máximo 32 caracteres."
    if not re.search(r"[A-Z]", value):
        message = "Inclua uma letra maiúscula."
    if not re.search(r"[0-9]", value):
        message = "Inclua um número."
    if len(value.encode()) > 72:
        message = "A senha excede o limite de 72 bytes."
    return message


def registration_from(body: dict, today: datetime) -> Registration:
    errors: dict[str, str] = {}
    name = body.get("name")
    if not isinstance(name, str) or not (3 <= len(name.strip()) <= 120):
        errors["name"] = "Informe seu nome completo."
    cpf = body.get("cpf")
    if not isinstance(cpf, str) or not valid_cpf(cpf):
        errors["cpf"] = "Confira os dígitos do CPF."
    if not old_enough(body.get("birthDate"), today):
        errors["birthDate"] = "É necessário ter pelo menos 16 anos."
    phone = body.get("phone")
    phone_digits = digits(phone) if isinstance(phone, str) else ""
    if not re.fullmatch(r"[1-9]{2}9\d{8}", phone_digits):
        errors["phone"] = "Informe DDD e celular com 9 dígitos."
    postal = body.get("postalCode")
    postal_digits = digits(postal) if isinstance(postal, str) else ""
    if len(postal_digits) != 8:
        errors["postalCode"] = "Informe os 8 dígitos do CEP."
    state = body.get("state")
    if state not in STATES:
        errors["state"] = "Selecione seu estado."
    city = body.get("city")
    if not isinstance(city, str) or not (2 <= len(city.strip()) <= 100):
        errors["city"] = "Informe sua cidade."
    email = body.get("email")
    if not isinstance(email, str) or len(email.strip()) > 200 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email.strip()):
        errors["email"] = "Informe um e-mail válido."
    password_error = password_message(body.get("password"))
    if password_error:
        errors["password"] = password_error
    if body.get("password") != body.get("confirmPassword"):
        errors["confirmPassword"] = "As senhas precisam ser iguais."
    if body.get("demoConsent") is not True:
        errors["demoConsent"] = "Confirme que está testando o protótipo."
    if errors:
        raise ApiError(422, "Confira os campos destacados.", errors)
    assert isinstance(name, str) and isinstance(cpf, str) and isinstance(phone, str)
    assert isinstance(postal, str) and isinstance(state, str) and isinstance(city, str)
    assert isinstance(email, str) and isinstance(body.get("password"), str)
    birth = body.get("birthDate")
    assert isinstance(birth, str)
    return Registration(
        name.strip(), digits(cpf), birth, phone_digits, postal_digits, state, city.strip(),
        email.strip().lower(), body["password"],
    )


def profile_update_from(body: dict, today: datetime, current_cpf: str) -> ProfileUpdate:
    errors: dict[str, str] = {}
    if "cpf" in body and body.get("cpf") is not None:
        raw_cpf = body.get("cpf")
        if not isinstance(raw_cpf, str) or digits(raw_cpf) != current_cpf:
            errors["cpf"] = "O CPF permanece inalterável."
    name = body.get("name")
    if not isinstance(name, str) or not (3 <= len(name.strip()) <= 120):
        errors["name"] = "Informe seu nome completo."
    if not old_enough(body.get("birthDate"), today):
        errors["birthDate"] = "É necessário ter pelo menos 16 anos."
    phone = body.get("phone")
    phone_digits = digits(phone) if isinstance(phone, str) else ""
    if not re.fullmatch(r"[1-9]{2}9\d{8}", phone_digits):
        errors["phone"] = "Informe DDD e celular com 9 dígitos."
    postal = body.get("postalCode")
    postal_digits = digits(postal) if isinstance(postal, str) else ""
    if len(postal_digits) != 8:
        errors["postalCode"] = "Informe os 8 dígitos do CEP."
    state = body.get("state")
    if state not in STATES:
        errors["state"] = "Selecione seu estado."
    city = body.get("city")
    if not isinstance(city, str) or not (2 <= len(city.strip()) <= 100):
        errors["city"] = "Informe sua cidade."

    keep_avatar = True
    avatar_data: str | None = None
    if "avatar" in body:
        raw_avatar = body.get("avatar")
        if raw_avatar is None or raw_avatar == "":
            keep_avatar = False
            avatar_data = None
        elif isinstance(raw_avatar, str):
            match = AVATAR_PREFIX.match(raw_avatar.strip())
            if not match:
                errors["avatar"] = "Envie uma imagem em JPG ou PNG."
            else:
                try:
                    decoded = base64.b64decode(match.group(1), validate=True)
                    if len(decoded) > MAX_AVATAR_BYTES:
                        errors["avatar"] = "O avatar deve ter no máximo 2 MB."
                    else:
                        keep_avatar = False
                        avatar_data = raw_avatar.strip()
                except Exception:
                    errors["avatar"] = "Não foi possível ler a imagem do avatar."
        else:
            errors["avatar"] = "Envie uma imagem em JPG ou PNG."

    if errors:
        raise ApiError(422, "Confira os campos destacados.", errors)
    assert isinstance(name, str) and isinstance(state, str) and isinstance(city, str)
    birth = body.get("birthDate")
    assert isinstance(birth, str)
    return ProfileUpdate(
        name=name.strip(),
        birth_date=birth,
        phone=phone_digits,
        postal_code=postal_digits,
        state=state,
        city=city.strip(),
        avatar_data=avatar_data,
        keep_avatar=keep_avatar,
    )
