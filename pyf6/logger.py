# -*- encoding: utf-8 -*-
"""
Copyright (c) 2025 - present by F6
"""
import os
import logging
import logging.config
from logging import StreamHandler
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import List, Union


class Logger(object):
    """
    Base class to catch logs from Python libraries.

    Start from example below.

    Example:

        >>>     Logger.init_root_logger(
        >>>         logs_dir='log',
        >>>         logging_format='%(asctime)s [%(threadName)s] [%(levelname)s] [APP_ID:APPID] [NOT:%(ncode)s] %(message)s',
        >>>         root_logging_level='DEBUG',
        >>>         session_filename='session_filename.log',
        >>>         info_filename='info_filename.log',
        >>>         warning_filename='warning_filename.log'
        >>>     )

        >>>     logger = Logger.init_logger(__name__)
    """

    @staticmethod
    def init_root_logger(
            logs_dir,
            logging_level,
            logging_format,
            session_filename=None,
            info_filename=None,
            warning_filename=None
    ):
        # type: (str, str, str, Union[str, None], Union[str, None], Union[str, None]) -> None

        """
        Initialize root logger with handlers.

        :param logs_dir: set the logs directory
        :param logging_level: set root logger level
        :param logging_format: apply logging format to root logger and handlers
        :param session_filename: tmp log with DEBUG level
        :param info_filename: lifetime log with INFO level
        :param warning_filename: lifetime log with WARNING level
        :return:
        """

        # Set up log files
        session_file = os.path.join(logs_dir, session_filename)
        info_file = os.path.join(logs_dir, info_filename)
        warning_file = os.path.join(logs_dir, warning_filename)

        if not os.path.exists(logs_dir):
            os.mkdir(logs_dir)

        # Remove session file before start
        if os.path.exists(session_file):
            os.remove(session_file)

        # Init root logger (Singleton object)
        logger = logging.getLogger()

        # Set up logger handlers
        session_handler = RotatingFileHandler(filename=session_file, mode='a', maxBytes=15*1024*1024, backupCount=5, encoding='utf-8')
        info_handler = RotatingFileHandler(filename=info_file, mode='a', maxBytes=15*1024*1024, backupCount=5, encoding='utf-8')
        warning_handler = RotatingFileHandler(filename=warning_file, mode='a', maxBytes=15*1024*1024, backupCount=5, encoding='utf-8')

        # Set root logger level
        logger.setLevel(logging_level)

        # Set logger handlers levels
        session_handler.setLevel(logging.DEBUG)
        info_handler.setLevel(logging.INFO)
        warning_handler.setLevel(logging.WARNING)

        # Set up logger filter
        # logger.addFilter(_NotificationCodeFilter())

        # Set up logger formats
        session_handler.setFormatter(logging.Formatter(logging_format))
        info_handler.setFormatter(logging.Formatter(logging_format))
        warning_handler.setFormatter(logging.Formatter(logging_format))

        # Register root logger handlers
        logger.addHandler(session_handler)
        logger.addHandler(info_handler)
        logger.addHandler(warning_handler)

    @staticmethod
    def create_TimedRotatingFileHandler(filename, log_format, handler_level):
        # type: (str, str, Union[int, str]) -> TimedRotatingFileHandler
        handler = TimedRotatingFileHandler(filename=filename, backupCount=5, when='midnight')
        handler.setLevel(handler_level)
        handler.setFormatter(logging.Formatter(log_format))
        return handler

    @staticmethod
    def create_RotatingFileHandler(filename, log_format, handler_level):
        # type: (str, str, Union[int, str]) -> RotatingFileHandler
        handler = RotatingFileHandler(filename=filename, mode='a', maxBytes=2*1024*1024, backupCount=5)
        handler.setLevel(handler_level)
        handler.setFormatter(logging.Formatter(log_format))
        return handler

    @staticmethod
    def create_StreamHandler(log_format, handler_level):
        # type: (str, Union[int, str]) -> StreamHandler
        handler = StreamHandler()
        handler.setLevel(handler_level)
        handler.setFormatter(logging.Formatter(log_format))
        return handler

    @staticmethod
    def disable_loggers(loggers):
        # type: (List[str]) -> None
        for _logger in loggers:
            catched_logger = logging.getLogger(_logger)
            catched_logger.disabled = True

    @staticmethod
    def init_logger(name=None):
        """To write your own logs. For better logs init with `name=__name__`"""

        # Join new logger to root
        logger = logging.getLogger(name)

        """
        CRITICAL 50
        ERROR    40
        WARNING  30
        INFO     20
        DEBUG    10
        NOTSET   0
        
        Logger Structure:                      Each logger stay in hierarchy, connects to root logger 
                                               and has it's own handlers with specific levels:
        ┌───────────┐                          ┌─────────────┐       ┌──────────────────┐
        │  Logger   │                          │ Root Logger ├───────┤  Handler (DEBUG) ├─ ...
        └─────┬─────┘                          └──────┬──────┘       └──────────────────┘
        ┌─────┴──────┐                         ┌──────┴───────┐        ┌─────────────────┐
        │  LogRecord │                         │ Child Logger ├────────┤  Handler (INFO) ├─ ...
        └─────┬──────┘                         └──────┬───────┘        └─────────────────┘
        ┌─────┴─────┐         ┌───────────┐    ┌──────┴─────────────┐     ┌─────────────────────┐
        │  Handler  ╞=========╡ Formatter │    │ Child.Child Logger ├─────┤  Handler (CRITICAL) ├─ ...
        └─────┬─────┘         └───────────┘    └────────────────────┘     └─────────────────────┘
         ┌────┴────┐
         │  output │
         └─────────┘
        """
        # Allow transfer messages to parent loggers.
        # If parent handlers has less or equal level then print message.
        logger.propagate = True

        # Allow capture warnings and redirect to logging
        logging.captureWarnings(True)

        return logger


class _NotificationCodeFilter(logging.Filter):
    """ Filter which adds a field named ncode to each log record.
        Allows notification code to be specified in log handler
        format strings.
    """
    # These are standard QRadar codes for identifying log levels.
    Q_INFO_CODE = '0000006000'
    Q_WARNING_CODE = '0000004000'
    Q_ERROR_CODE = '0000003000'

    def filter(self, record):
        record.ncode = self._log_level_to_notification_code.get(
            record.levelname.upper(), self.Q_INFO_CODE)
        return True

    _log_level_to_notification_code = {
        'DEBUG': Q_INFO_CODE,
        'INFO': Q_INFO_CODE,
        'WARNING': Q_WARNING_CODE,
        'ERROR': Q_ERROR_CODE,
        'CRITICAL': Q_ERROR_CODE
    }


class _FileHandler(logging.Handler):
    def __init__(self, filename):
        logging.Handler.__init__(self)
        self.filename = filename

    def emit(self, record):
        message = self.format(record)
        with open(self.filename, 'w') as file:
            file.write(message + '\n')
