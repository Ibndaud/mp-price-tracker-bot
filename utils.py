import re
from urllib.parse import urlparse


def get_steam_app_id(url: str) -> int | None:
    """
    Извлекает ID игры из ссылки Steam.

    Например:
    https://store.steampowered.com/app/413150/Stardew_Valley/

    Вернёт:
    413150
    """

    parsed_url = urlparse(url)

    if (
        parsed_url.scheme != "https"
        or parsed_url.hostname != "store.steampowered.com"
    ):
        return None

    match = re.fullmatch(
        r"/app/(\d+)(?:/[^/?#]*)?/?",
        parsed_url.path
    )

    if not match:
        return None

    return int(match.group(1))