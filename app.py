from enum import Enum
from fastapi.security import APIKeyHeader
import jwt
import random
import string
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel, Field
from pathlib import Path
import tempfile

# Consts
EXPIRES_IN_MIN = 60
AUTH_ALGORITHM = 'HS256'
AUTH_SECRET_KEY = ''.join(
    random.choices(string.ascii_letters + string.ascii_uppercase, k=48)
)
FAKE_DB = {
    'users': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    'posts': [11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
}

# API Setup
app = FastAPI(title='Python Load Testing API [Simulation]', redoc_url=None)


@app.get('/', include_in_schema=False)
def redirect_to_docs():
    return RedirectResponse(url='/docs')


CredentialException = HTTPException(
    status_code=HTTPStatus.UNAUTHORIZED,
    detail='Not authenticated',
)

NotFoundException = HTTPException(
    status_code=HTTPStatus.NOT_FOUND, detail='Not found'
)

# Models


def generate_id() -> str:
    return ''.join(random.choices(string.ascii_uppercase, k=8))


class User(BaseModel):
    id_user: str = Field(default_factory=generate_id)


class DataResponse(BaseModel):
    id: str
    data: dict | list


class ToReplace(BaseModel):
    old: int
    new: int


class Kind(Enum):
    USERS = 'users'
    POSTS = 'posts'


# Security
oauth2_scheme = APIKeyHeader(name='Authorization')


def create_access_token(user: User):
    to_encode = {'sub': user.model_dump()}
    expire = datetime.now(tz=timezone.utc) + timedelta(minutes=EXPIRES_IN_MIN)
    to_encode.update({'exp': expire})
    return jwt.encode(to_encode, AUTH_SECRET_KEY, algorithm=AUTH_ALGORITHM)


def get_payload_from_token(token: str):
    if not token:
        raise CredentialException
    try:
        payload: dict = jwt.decode(
            token, AUTH_SECRET_KEY, algorithms=AUTH_ALGORITHM
        )
        p = payload.copy()
        p.pop('exp')
        if p.values():
            return payload
        raise CredentialException
    except jwt.ExpiredSignatureError as e:
        raise CredentialException from e
    except jwt.DecodeError as e:
        raise CredentialException from e


def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    payload = get_payload_from_token(token)
    if not payload or not payload.get('sub'):
        raise CredentialException
    return User(**payload.get('sub', {}))


## Auth Routes
@app.post('/auth')
def auth():
    access_token = create_access_token(User(id_user=generate_id()))
    return {'access_token': access_token}


@app.get('/me', response_model=User)
def me(user: User = Depends(get_current_user)):
    return user


## Crud Routes
### Login required


@app.get('/data', response_model=DataResponse)
def data(user: User = Depends(get_current_user)):
    return {
        'id': user.id_user,
        'data': FAKE_DB,
    }


@app.get('/data/{kind}', response_model=DataResponse)
def data_kind(kind: Kind, user: User = Depends(get_current_user)):
    return {
        'id': user.id_user,
        'data': FAKE_DB[kind.value],
    }


@app.post(
    '/data/{kind}', response_model=DataResponse, status_code=HTTPStatus.CREATED
)
def create_data_kind(
    kind: Kind, value: int, user: User = Depends(get_current_user)
):
    FAKE_DB[kind.value].append(value)
    return {
        'id': user.id_user,
        'data': FAKE_DB[kind.value],
    }


@app.put('/data/{kind}', response_model=DataResponse)
def update_data_kind(
    kind: Kind, to_replace: ToReplace, user: User = Depends(get_current_user)
):
    old_idx = (
        None
        if FAKE_DB[kind.value].count(to_replace.old) == 0
        else FAKE_DB[kind.value].index(to_replace.old)
    )
    if old_idx is None:
        raise NotFoundException
    FAKE_DB[kind.value][old_idx] = to_replace.new
    return {
        'id': user.id_user,
        'data': FAKE_DB[kind.value],
    }


@app.delete('/data/{kind}', response_model=DataResponse)
def delete_data_kind(
    kind: Kind, value: int, user: User = Depends(get_current_user)
):
    try:
        FAKE_DB[kind.value].remove(value)
        return {
            'id': user.id_user,
            'data': FAKE_DB[kind.value],
        }
    except ValueError as er:
        raise NotFoundException from er


## Static Routes
def create_sample_txt() -> Path:
    content = f"'Hello stranger. Your random code it's: {generate_id()}"
    path = Path(tempfile.mkdtemp('sample'), 'sample.txt')
    if path.exists():
        return path
    path.write_text(content)
    return path


@app.get('/sample')
def sample():
    path = create_sample_txt()
    return FileResponse(path, media_type='text/plain', filename=path.name)
