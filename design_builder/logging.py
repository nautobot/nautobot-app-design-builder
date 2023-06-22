"""Defines logging capability for design builder."""
import logging

from nautobot.extras.choices import LogLevelChoices
from nautobot.extras.models import JobResult

from .util import nautobot_version

if nautobot_version < "2.0.0":
    # MIN_VERSION: 2.0.0
    _logger_to_level_choices = {
        logging.DEBUG: LogLevelChoices.LOG_INFO,
        logging.INFO: LogLevelChoices.LOG_INFO,
        logging.WARNING: LogLevelChoices.LOG_WARNING,
        logging.ERROR: LogLevelChoices.LOG_FAILURE,  # pylint: disable=no-member
        logging.CRITICAL: LogLevelChoices.LOG_FAILURE,  # pylint: disable=no-member
    }
    LOG_INFO = LogLevelChoices.LOG_INFO
    LOG_DEBUG = LogLevelChoices.LOG_INFO
    LOG_SUCCESS = LogLevelChoices.LOG_SUCCESS  # pylint: disable=no-member
    LOG_WARNING = LogLevelChoices.LOG_WARNING
    LOG_FAILURE = LogLevelChoices.LOG_FAILURE  # pylint: disable=no-member
    # /MIN_VERSION: 2.0.0
else:
    _logger_to_level_choices = {
        logging.DEBUG: LogLevelChoices.LOG_DEBUG,  # pylint: disable=no-member
        logging.INFO: LogLevelChoices.LOG_INFO,
        logging.WARNING: LogLevelChoices.LOG_WARNING,
        logging.ERROR: LogLevelChoices.LOG_ERROR,  # pylint: disable=no-member
        logging.CRITICAL: LogLevelChoices.LOG_CRITICAL,  # pylint: disable=no-member
    }
    LOG_INFO = LogLevelChoices.LOG_INFO
    LOG_DEBUG = LogLevelChoices.LOG_DEBUG  # pylint: disable=no-member
    LOG_SUCCESS = LogLevelChoices.LOG_INFO
    LOG_WARNING = LogLevelChoices.LOG_WARNING
    LOG_FAILURE = LogLevelChoices.LOG_ERROR  # pylint: disable=no-member


class JobResultHandler(logging.Handler):
    """JobResultHandler is a logging handler that will copy logged messages to a JobResult."""

    def __init__(self, job_result: JobResult):
        """Initialize the JobResultHandler.

        Args:
            job_result (JobResult): The JobResult that logs should be copied to.
        """
        super().__init__()
        self.job_result = job_result

    def emit(self, record: logging.LogRecord) -> None:
        """Copy the log record to the JobResult.

        Args:
            record (logging.LogRecord): Information to be logged
        """
        level = _logger_to_level_choices[record.levelno]
        msg = self.format(record)
        self.job_result.log(level_choice=level, message=msg)


def get_logger(name, job_result: JobResult):
    """Retrieve the named logger and add a JobResultHandler to it.

    Args:
        name (_type_): _description_
        job_result (JobResult): _description_

    Returns:
        _type_: _description_
    """
    logger = logging.getLogger(name)
    logger.addHandler(JobResultHandler(job_result))
    return logger


class LoggingMixin:
    """Use this class anywhere a job result needs to log to a job result."""

    def _log(self, obj, message, level_choice=LOG_INFO):
        """Log a message. Do not call this method directly; use one of the log_* wrappers below."""
        if hasattr(self, "job_result") and self.job_result:
            self.job_result.log(
                message,
                obj=obj,
                level_choice=level_choice,
            )

    def log(self, message):
        """Log a generic message which is not associated with a particular object."""
        self._log(None, message, level_choice=LOG_INFO)

    def log_debug(self, message):
        """Log a debug message which is not associated with a particular object."""
        self._log(None, message, level_choice=LOG_DEBUG)

    def log_success(self, obj=None, message=None):
        """Record a successful test against an object. Logging a message is optional."""
        self._log(obj, message, level_choice=LOG_SUCCESS)

    def log_info(self, obj=None, message=None):
        """Log an informational message."""
        self._log(obj, message, level_choice=LOG_INFO)

    def log_warning(self, obj=None, message=None):
        """Log a warning."""
        self._log(obj, message, level_choice=LOG_WARNING)

    def log_failure(self, obj=None, message=None):
        """Log a failure. Calling this method will automatically mark the overall job as failed."""
        self._log(obj, message, level_choice=LOG_FAILURE)
        self.failed = True
