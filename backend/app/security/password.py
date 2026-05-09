"""Hash / verify mật khẩu — dùng thư viện bcrypt trực tiếp (tránh passlib + bcrypt 4.x lỗi)."""

import bcrypt

_ROUNDS = 12


def hash_password(plain: str) -> str:
    if len(plain.encode("utf-8")) > 72:
        plain = plain[:72]
    digest = bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=_ROUNDS))
    return digest.decode("ascii")


def verify_password(plain: str, password_hash: str) -> bool:
    if len(plain.encode("utf-8")) > 72:
        plain = plain[:72]
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), password_hash.encode("ascii"))
    except ValueError:
        return False
