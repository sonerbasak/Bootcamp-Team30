from fastapi import Request, status
from typing import Optional
from functions.database.queries import get_user_by_id

class CurrentUser(object):
    def __init__(self, id: int, username: str, email: str = None):
        self.id = id
        self.username = username
        self.email = email

async def require_auth(request: Request) -> Optional[CurrentUser]:
    user_id_str = request.cookies.get("user_id")

    if not user_id_str:
        return None

    try:
        user_id = int(user_id_str)
        user_data = get_user_by_id(user_id)
        if user_data:
            return CurrentUser(id=user_data['id'], username=user_data['username'], email=user_data.get('email'))
    except (ValueError, TypeError):
        pass

    return None