from urllib.parse import urlparse

def simple_traverse(obj, path, default=None):
    """
    Traverse a nested dictionary or list using the given path.

    :param obj: The object to traverse (dict or list).
    :param path: A tuple representing the path to traverse.
    :param default: The value to return if the path does not exist.
    :return: The value at the end of the path, or the default if the path does not exist.
    """
    for key in path:
        if isinstance(obj, dict):
            obj = obj.get(key, default)
        elif isinstance(obj, list) and isinstance(key, int) and 0 <= key < len(obj):
            obj = obj[key]
        else:
            return default
    return obj


def validate_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False
