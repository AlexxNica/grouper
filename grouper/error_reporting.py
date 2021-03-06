import logging
import signal
import sys
import traceback
from types import FrameType  # noqa

try:
    from raven.contrib.tornado import AsyncSentryClient
    raven_installed = True
except ImportError:
    raven_installed = False


signame_by_signum = {v: k for k, v in signal.__dict__.items() if k.startswith('SIG') and not
        k.startswith('SIG_')}


class SentryProxy(object):
    """Simple proxy for sentry client that logs to stderr even if no sentry client exists."""
    def __init__(self, sentry_client):
        self.sentry_client = sentry_client

    def captureException(self, exc_info=None, **kwargs):
        if self.sentry_client:
            self.sentry_client.captureException(exc_info=exc_info, **kwargs)

        logging.exception("exception occurred")


def get_sentry_client(sentry_dsn):
    # type: (str) -> SentryProxy
    if sentry_dsn and raven_installed:
        logging.info("sentry client setup dsn={}".format(sentry_dsn))
        sentry_client = SentryProxy(sentry_client=AsyncSentryClient(sentry_dsn))
    else:
        if not sentry_dsn:
            logging.info("no sentry_dsn specified")

        if not raven_installed:
            logging.info("raven not installed")

        sentry_client = SentryProxy(sentry_client=None)

    return sentry_client


def log_and_exit_handler(signum, frame):
    # type: (int, FrameType) -> None
    logging.warning("caught signal {}, exiting".format(signame_by_signum[signum]))
    sys.exit(1)


def dump_thread_handler(signum, frame):
    # type: (int, FrameType) -> None
    for thread_id, thread_frame in sys._current_frames().items():
        print("-- thread id {}:".format(thread_id))
        print("".join(traceback.format_stack(thread_frame)))


def setup_signal_handlers():
    # type: () -> None
    """Setup the handlers for API and FE servers. Specifically we message on
    any signal and we dump thread tracebacks on SIGUSR1."""
    for signum in [signal.SIGINT, signal.SIGTERM]:
        signal.signal(signum, log_and_exit_handler)

    signal.signal(signal.SIGUSR1, dump_thread_handler)
