import time

import redis
from fastapi import HTTPException, status

from app.core.config import get_settings


settings = get_settings()
redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)


def enforce_chat_rate_limit(user_id: int) -> None:
    window = settings.chat_rate_limit_window_sec
    limit = settings.chat_rate_limit_max_requests
    now = int(time.time())
    bucket = now // window
    key = f'kb:rate:{user_id}:{bucket}'
    count = redis_client.incr(key)
    if count == 1:
        redis_client.expire(key, window)
    if count > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f'Rate limit exceeded ({limit}/{window}s)',
        )
