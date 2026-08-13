"""Entidade User — dados e regras de domínio.

Duas mudanças de segurança em relação à versão anterior:
- a senha passa a usar hash com salt (era MD5 puro);
- não existe mais `to_dict()` aqui. A serialização mora em `routes/dto/user_dto.py`, com
  allowlist — era o `to_dict()` do model que devolvia o campo `password` na resposta HTTP.
"""
from werkzeug.security import check_password_hash, generate_password_hash

from database import db
from utils.datetime_utils import utc_now

PAPEIS_VALIDOS = ("user", "admin", "manager")


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default="user")
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    def set_password(self, senha: str) -> None:
        self.password = generate_password_hash(senha)

    def check_password(self, senha: str) -> bool:
        """Verifica a senha, com re-hash das credenciais legadas em MD5.

        A base existente foi gravada com `hashlib.md5(pwd).hexdigest()` — 32 caracteres hex, sem
        salt. Como MD5 não é reversível, a migração acontece no login: se o valor armazenado tem
        o formato antigo e confere, é regravado no formato novo.
        """
        armazenado = self.password or ""

        if check_password_hash(armazenado, senha):
            return True

        if self._e_hash_md5_legado(armazenado) and self._confere_md5_legado(armazenado, senha):
            self.set_password(senha)
            db.session.commit()
            return True

        return False

    @staticmethod
    def _e_hash_md5_legado(valor: str) -> bool:
        return len(valor) == 32 and all(c in "0123456789abcdef" for c in valor.lower())

    @staticmethod
    def _confere_md5_legado(armazenado: str, senha: str) -> bool:
        import hashlib  # import local: só existe para migrar a base antiga
        return armazenado == hashlib.md5(senha.encode()).hexdigest()  # noqa: S324

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def __repr__(self) -> str:
        return f"<User {self.id} {self.email!r}>"
