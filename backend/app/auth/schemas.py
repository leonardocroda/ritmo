"""Schemas Pydantic dos endpoints de auth (mesmo padrão dos domínios).

Validação de formato é AQUI (422 por campo, mensagem específica em
PT-BR — tom do app); regras de negócio (convite, unicidade) são do
service. Email sem ``email-validator`` (design: argon2-cffi é a única
dependência nova) — regex própria para pegar o malformado óbvio.
"""

import re

from pydantic import BaseModel, field_validator

# malformado óbvio (a@b.tld) — validação de entregabilidade não é escopo
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegisterIn(BaseModel):
    """POST /api/auth/register — cadastro por convite (AUTH-01..05)."""

    display_name: str
    email: str
    password: str
    invite_code: str = ""

    @field_validator("display_name")
    @classmethod
    def nome_valido(cls, v: str) -> str:
        nome = v.strip()
        if not nome:
            raise ValueError("nome é obrigatório")
        if len(nome) > 120:
            raise ValueError("nome deve ter até 120 caracteres")
        return nome

    @field_validator("email")
    @classmethod
    def email_valido(cls, v: str) -> str:
        if not _EMAIL_RE.fullmatch(v.strip()):
            raise ValueError("email inválido")
        return v

    @field_validator("password")
    @classmethod
    def senha_valida(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("senha deve ter pelo menos 8 caracteres")
        return v


class LoginIn(BaseModel):
    """POST /api/auth/login — sem validação de formato: qualquer erro de
    credencial vira a 401 genérica única (AUTH-07)."""

    email: str
    password: str


class MeOut(BaseModel):
    """Corpo de register/login/me — nunca expõe password_hash."""

    id: int
    email: str | None
    display_name: str
