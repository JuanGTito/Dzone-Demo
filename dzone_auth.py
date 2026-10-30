"""Cuentas de demostración y sesiones locales con permisos por rol."""
from dataclasses import dataclass
import hashlib
import hmac
import secrets
import dzone_core as core


@dataclass(frozen=True)
class Session:
    username: str
    role: str
    token: str


_sessions={}
ROUNDS=260_000


def init_users():
    with core.conn() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
            username TEXT PRIMARY KEY, rol TEXT NOT NULL, salt TEXT NOT NULL,
            password_hash TEXT NOT NULL, iteraciones INTEGER NOT NULL, activo INTEGER NOT NULL DEFAULT 1)''')
        for username,role in [('demo0','Supervisor')]+[(name,'Tecnico') for name,_ in core.TECHS]:
            if c.execute('SELECT 1 FROM usuarios WHERE username=?',(username,)).fetchone():continue
            salt=secrets.token_hex(16)
            digest=hashlib.pbkdf2_hmac('sha256',username.encode(),bytes.fromhex(salt),ROUNDS).hex()
            c.execute('INSERT INTO usuarios(username,rol,salt,password_hash,iteraciones) VALUES(?,?,?,?,?)',(username,role,salt,digest,ROUNDS))


def authenticate(username,password):
    username=username.strip().lower()
    with core.conn() as c:row=c.execute('SELECT * FROM usuarios WHERE username=? AND activo=1',(username,)).fetchone()
    salt=bytes.fromhex(row['salt']) if row else b'\0'*16
    digest=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,row['iteraciones'] if row else ROUNDS).hex()
    if not row or not hmac.compare_digest(digest,row['password_hash']):raise ValueError('Usuario o contraseña incorrectos.')
    session=Session(row['username'],row['rol'],secrets.token_urlsafe(32))
    _sessions[session.token]=(session,core.DB.resolve())
    return session


def require(session,role=None):
    if not isinstance(session,Session) or _sessions.get(session.token)!=(session,core.DB.resolve()):
        raise ValueError('Inicia sesión para continuar.')
    with core.conn() as c:row=c.execute('SELECT rol,activo FROM usuarios WHERE username=?',(session.username,)).fetchone()
    if not row or not row['activo'] or row['rol']!=session.role:raise ValueError('La sesión ya no es válida.')
    if role and session.role!=role:raise ValueError('Esta acción no está permitida para tu rol.')
    return session


def revoke(session):
    if isinstance(session,Session):_sessions.pop(session.token,None)


def invalidate_all():
    _sessions.clear()


def authorize_ticket(session,row,technician_only=False):
    require(session,'Tecnico' if technician_only else None)
    if session.role=='Tecnico' and row['tecnico']!=session.username:
        raise ValueError('Este ticket no está asignado a tu usuario.')
    return row
