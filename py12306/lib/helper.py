class ShareInstance():
    __session = None

    @classmethod
    def share(cls):
        if not cls.__session:
            cls.__session = cls()
        return cls.__session


# Expand dict
class Dict(dict):
    def get(self, key, default=None, sep='.'):
        keys = key.split(sep)
        for i, key in enumerate(keys):
            try:
                value = self[key]
                if len(keys[i + 1:]) and isinstance(value, Dict):
                    return value.get(sep.join(keys[i + 1:]), default=default, sep=sep)
                return value
            except KeyError:
                return self.dict_to_dict(default)
