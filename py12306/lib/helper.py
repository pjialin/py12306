class ShareInstance():
    __session = None

    @classmethod
    def share(cls):
        if not cls.__session:
            cls.__session = cls()
        return cls.__session


