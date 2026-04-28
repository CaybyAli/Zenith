class ZenithError(Exception):
    pass


class ValidationError(ZenithError):
    pass


class StorageError(ZenithError):
    pass


class RoutingError(ZenithError):
    pass


class ModeError(ZenithError):
    pass


class NotFoundError(ZenithError):
    pass