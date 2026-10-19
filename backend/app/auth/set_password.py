"""CLI de bootstrap/suporte — ``python -m app.auth.set_password`` (AUTH-25/26).

Email via ``input`` e senha via ``getpass`` (mesmo padrão do
``garmin/login.py``). Três caminhos: vincular o usuário seed (id 1 sem
email — display_name "Leonardo" preservado), resetar a senha de uma
conta existente (display_name intacto — reset de suporte) ou criar uma
conta nova quando o seed já tem email — display_name default é a parte
local do email, editável depois no perfil.

O seam ``run_set_password(email, password)`` recebe os valores prontos:
nenhum teste toca ``input``/``getpass`` (padrão do ``run_login``).
"""

from getpass import getpass

from app.auth.security import hash_password
from app.db.engine import SessionLocal
from app.db.models import DEFAULT_USER_ID, User


def run_set_password(email: str, password: str) -> User:
    """Define a senha do email dado e devolve o User afetado.

    Normaliza o email (trim + lowercase — mesma regra do service):
    conta existente → substitui o hash; inédito + seed sem email →
    vincula ao seed; inédito + seed já vinculado → cria conta nova.
    """
    normalized = email.strip().lower()
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == normalized).one_or_none()
        if user is not None:
            # AUTH-26: reset de suporte — só o hash muda
            user.password_hash = hash_password(password)
        else:
            seed = db.get(User, DEFAULT_USER_ID)
            if seed is not None and seed.email is None:
                # AUTH-25: bootstrap — vincula o seed preservando display_name
                user = seed
                user.email = normalized
                user.password_hash = hash_password(password)
            else:
                display_name = normalized.split("@", 1)[0] or normalized
                user = User(
                    display_name=display_name,
                    email=normalized,
                    password_hash=hash_password(password),
                )
                db.add(user)
        db.commit()
        db.refresh(user)
        return user


def main() -> None:
    email = input("Email: ")
    password = getpass("Senha: ")
    user = run_set_password(email, password)
    print(f"Senha definida para {user.email} ({user.display_name})")


if __name__ == "__main__":
    main()
