# -*- encoding: utf-8 -*-
"""
Copyright (c) 2025 - present by F6

This module contains the set of integration exceptions.

"""


class ConnectionException(Exception):
    """A connection exception occurred."""

    pass


class InputException(Exception):
    """An invalid input exception occurred."""

    pass


class ParserException(Exception):
    """Internal parser exception occurred."""

    pass


class FileTypeError(Exception):
    """A file type not supported exception occurred."""


class EmptyCredsError(Exception):
    """An empty credentials exception occurred."""

    pass


class EmptyDataError(Exception):
    """An empty data exception occurred."""


class MissingKeyError(Exception):
    """Missing important key exception occurred"""


class BadProtocolError(Exception):
    """An invalid protocol set"""


class EncryptionError(Exception):
    """All errors encountered by Encryption are reported via this class"""
