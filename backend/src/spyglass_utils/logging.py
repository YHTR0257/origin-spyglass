import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """名前付きロガーを返す。

    呼び出し側は `get_logger(__name__)` のように使う。
    初回呼び出し時にルートロガーのハンドラが未設定であれば
    stderr への StreamHandler を追加する。

    Args:
        name: ロガー名。通常は呼び出しモジュールの `__name__`。

    Returns:
        設定済みの Logger インスタンス。
    """
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
        root.addHandler(handler)
        root.setLevel(logging.INFO)

    return logging.getLogger(name)
