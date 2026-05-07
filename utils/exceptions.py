class DownloadError(Exception):
    """Base downloader exception with a user-safe message."""


class UnsupportedUrlError(DownloadError):
    pass


class DownloadLimitError(DownloadError):
    pass


class NoResultsError(DownloadError):
    pass
