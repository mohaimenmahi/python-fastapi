from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class FakeUser:
    id: int
    email: str
    hashed_password: str
    is_active: bool = True
    roles: list = field(default_factory=list)


@dataclass
class FakeRole:
    id: int
    name: str


@dataclass
class FakeRefreshToken:
    id: int
    user_id: int
    token_hash: str
    expires_at: datetime
    revoked_at: datetime | None = None
    replaced_by_id: int | None = None


class FakeUserRepository:
    def __init__(self):
        self._users: dict[int, FakeUser] = {}
        self._next_id = 1

    async def get_by_email(self, email: str) -> FakeUser | None:
        return next((u for u in self._users.values() if u.email == email), None)

    async def create(self, **kwargs) -> FakeUser:
        user = FakeUser(id=self._next_id, **kwargs)
        self._users[user.id] = user
        self._next_id += 1
        return user


class FakeRoleRepository:
    def __init__(self, default_role: FakeRole | None = None):
        self.default_role = default_role
        self.assigned: list[tuple[FakeUser, FakeRole]] = []

    async def get_role_by_name(self, name: str) -> FakeRole | None:
        if self.default_role and self.default_role.name == name:
            return self.default_role
        return None

    async def assign_role(self, user: FakeUser, role: FakeRole) -> None:
        user.roles.append(role)
        self.assigned.append((user, role))


class FakeRefreshTokenRepository:
    def __init__(self):
        self._tokens: dict[str, FakeRefreshToken] = {}
        self._next_id = 1

    async def create(self, user_id: int, token_hash: str, expires_at: datetime) -> FakeRefreshToken:
        token = FakeRefreshToken(
            id=self._next_id, user_id=user_id, token_hash=token_hash, expires_at=expires_at
        )
        self._tokens[token_hash] = token
        self._next_id += 1
        return token

    async def get_by_hash(self, token_hash: str) -> FakeRefreshToken | None:
        return self._tokens.get(token_hash)

    async def revoke(self, token: FakeRefreshToken, replaced_by_id: int | None = None) -> None:
        token.revoked_at = datetime.now()
        token.replaced_by_id = replaced_by_id

    async def revoke_all_for_user(self, user_id: int) -> None:
        for token in self._tokens.values():
            if token.user_id == user_id and token.revoked_at is None:
                token.revoked_at = datetime.now()
