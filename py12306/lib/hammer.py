import asyncio
import datetime
from abc import abstractmethod, ABC
from typing import Any, Optional, Dict

from aioredis import Channel

from lib.helper import json_friendly_loads, json_friendly_dumps


class EventItem:

    def __init__(self, name: str, data: Any) -> None:
        super().__init__()
        self.name = name
        self.data = data

    def dumps(self) -> str:
        return json_friendly_dumps({'name': self.name, 'data': self.data})


class EventAbstract(ABC):

    @abstractmethod
    async def publish(self, item: EventItem):
        pass

    @abstractmethod
    async def subscribe(self) -> EventItem:
        pass


class RedisEventEngine(EventAbstract):

    def __init__(self):
        super().__init__()
        from app.app import Redis, Config
        self.redis = Redis
        self._channel_name = Config.APP_NAME
        self._msg_queue = asyncio.Queue()
        self._subscribed = False

    async def publish(self, item: EventItem):
        await self.redis.publish(self._channel_name, item.dumps())

    async def subscribe(self) -> EventItem:
        if not self._subscribed:
            self._subscribed = True
            ret = await self.redis.subscribe(self._channel_name)
            asyncio.ensure_future(self._handle_msg(ret[0]))
        return await self._msg_queue.get()

    async def _handle_msg(self, channel: Channel):
        while await channel.wait_message():
            msg = await channel.get()
            await self._msg_queue.put(EventItem(**json_friendly_loads(msg)))


class AsyncioEventEngine(EventAbstract):

    def __init__(self):
        super().__init__()
        self._queue_lists = []

    async def publish(self, item: EventItem):
        for queue in self._queue_lists:
            await queue.put(item)

    async def subscribe(self) -> EventItem:
        queue = asyncio.Queue()
        self._queue_lists.append(queue)
        return await queue.get()


class EventHammer:
    EVENT_ORDER_TICKET = 'order_ticket'
    EVENT_VERIFY_QUERY_JOB = 'verify_query_job'

    def __init__(self, engine: EventAbstract) -> None:
        super().__init__()
        self.engine: Optional[EventAbstract] = engine

    async def publish(self, item: EventItem):
        await self.engine.publish(item)

    async def subscribe(self) -> EventItem:
        return await self.engine.subscribe()


# // 缓存
class CacheAbstract(ABC):

    @abstractmethod
    async def set(self, key: str, val: str):
        pass

    @abstractmethod
    async def get(self, key: str, default: Any = None):
        pass

    @abstractmethod
    async def lpush(self, key: str, val):
        pass

    @abstractmethod
    async def lget(self, key: str, default: Any = None) -> list:
        pass

    @abstractmethod
    async def sadd(self, key: str, val):
        pass

    @abstractmethod
    async def sget(self, key: str, default: Any = None) -> set:
        pass

    @abstractmethod
    async def hset(self, key: str, field: str, val: str):
        pass

    @abstractmethod
    async def hget(self, key: str, field: str, default: Any = None):
        pass

    @abstractmethod
    async def hdel(self, key: str, field: str):
        pass


class RedisCacheEngine(CacheAbstract):

    def __init__(self):
        super().__init__()
        from app.app import Redis
        self.redis = Redis

    async def set(self, key: str, val: str):
        return await self.redis.set(key, val)

    async def get(self, key: str, default: Any = None):
        ret = await self.redis.get(key)
        if not ret:
            return default
        return ret.decode()

    async def lpush(self, key: str, val):
        pass

    async def lget(self, key: str, default: Any = None) -> list:
        pass

    async def sadd(self, key: str, val):
        pass

    async def sget(self, key: str, default: Any = None) -> set:
        pass

    async def hset(self, key: str, field: str, val: str):
        return await self.redis.hset(key, field, val)

    async def hget(self, key: str, field: str, default: Any = None):
        ret = await self.redis.hget(key, field) or default
        if not ret:
            return default
        return ret.decode()

    async def hdel(self, key: str, field: str):
        return await self.redis.hdel(key, field)


class AsyncioCacheEngine(CacheAbstract):

    def __init__(self):
        super().__init__()
        self._queue = asyncio.Queue()
        self.string_dict = {}
        self.list_items: Dict[str, list] = {}
        self.set_items: Dict[str, set] = {}
        self.hash_items: Dict[str, dict] = {}

    async def set(self, key: str, val: str):
        self.string_dict[key] = val

    async def get(self, key: str, default: Any = None):
        self.string_dict.get(key, default)

    async def lpush(self, key: str, val):
        if key not in self.list_items:
            self.list_items[key] = []
        self.list_items[key].append(key)

    async def lget(self, key: str, default: Any = None) -> list:
        if key not in self.list_items:
            return default
        return self.list_items[key]

    async def sadd(self, key: str, val):
        if key not in self.set_items:
            self.set_items[key] = set()
        self.set_items[key].add(key)

    async def sget(self, key: str, default: Any = None) -> set:
        if key not in self.set_items:
            return default
        return self.set_items[key]

    async def hset(self, key: str, field: str, val: str):
        if key not in self.hash_items:
            self.hash_items[key] = {}
        self.hash_items[key][field] = val

    async def hget(self, key: str, field: str, default: Any = None):
        if key not in self.hash_items:
            return default
        return self.hash_items[key].get(field, default)

    async def hdel(self, key: str, field: str):
        if key not in self.hash_items:
            return
        if field in self.hash_items[key]:
            del self.hash_items[key][field]


class CacheHammer:
    KEY_DARK_ROOM = 'dark_room'

    def __init__(self, engine: CacheAbstract) -> None:
        super().__init__()
        self.engine: Optional[CacheAbstract] = engine

    async def set(self, key: str, val: str):
        return await self.engine.set(key, val)

    async def get(self, key: str, default: Any = None):
        return await self.engine.get(key, default)

    async def hset(self, key: str, field: str, val: str):
        return await self.engine.hset(key, field, val)

    async def hget(self, key: str, field: str, default: Any = None):
        return await self.engine.hget(key, field, default)

    async def hdel(self, key: str, field: str):
        return await self.engine.hdel(key, field)

    async def add_dark_room(self, baby: str):
        return await self.hset(self.KEY_DARK_ROOM, baby, json_friendly_dumps({
            'id': baby,
            'created_at': datetime.datetime.now()
        }))

    async def in_dark_room(self, baby: str) -> bool:
        _baby = await self.hget(self.KEY_DARK_ROOM, baby)
        if not _baby:
            return False
        _baby = json_friendly_loads(_baby)
        # 超过限制时长
        if not isinstance(_baby.get('created_at'), datetime.datetime) or \
                (datetime.datetime.now() - _baby['created_at']).seconds > 60:
            await self.hdel(self.KEY_DARK_ROOM, baby)
            return False
        return True
