#!/usr/bin/env python3
import argparse
import logging
import os
import select
from systemd import journal


class Exporter:
    def __init__(
        self,
        target_systemd_unit: str,
        logger: logging.Logger = None,
        log_level: str = "INFO",
        systemd_log_level: str = "INFO",
    ):
        # set up our logger
        if not logger:
            logger_level = getattr(logging, log_level.upper())
            self.logger = logging.getLogger(__name__)
            logging.basicConfig(level=logger_level)
        else:
            self.logger = logger

        # set up our journal
        journal_log_level = getattr(journal, f"LOG_{systemd_log_level.upper()}")
        self.reader = journal.Reader()
        self.reader.log_level(journal_log_level)

        # if there's a specific systemd unit to filter on, like the kubelet, set that filter
        if target_systemd_unit:
            self._target_systemd_unit = target_systemd_unit  # we're saving this for a useful log output on startup/debugging
            logging.debug(
                "Target systemd service provided, targeting _SYSTEMD_UNIT [%s]",
                target_systemd_unit,
            )
            self.reader.add_match(_SYSTEMD_UNIT=target_systemd_unit)

    def log(self):
        self.logger.info("Starting log collection")
        if self._target_systemd_unit:
            self.logger.info(
                "Logging events to systemd service [%s]", self._target_systemd_unit
            )
        else:
            self.logger.info("Logging all systemd events - this will be noisy!")
        # start at the head of the journal
        self.logger.debug("Seeking head of systemd logs")
        self.reader.seek_head()

        # poll the stream for logs
        p = select.poll()
        p.register(self.reader, self.reader.get_events())

        self.logger.debug("Polling for events...")
        while p.poll():
            # if the process is not a new line of log output
            if self.process() != journal.APPEND:
                self.logger.debug("Found non-append event, continuing...")
                continue

            for entry in j:
                self.logger.debug("Received entry [%s]", entry)
                if entry["MESSAGE"]:
                    print(f"{entry['__REALTIME_TIMESTAMP']} {entry['MESSAGE']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-l",
        "--exported-log-level",
        dest="systemd_log_level",
        default=os.environ.get("EXPORTER_SYSTEMD_LOG_LEVEL", "INFO"),
        help="The log level to read systemd logs at; one of ALERT, CRIT, DEBUG, EMERG, ERR, INFO, LOG, WARNING",
    )
    parser.add_argument(
        "-t",
        "--target",
        "-t",
        dest="target_systemd_unit",
        default=os.environ.get("EXPORTER_SYSTEMD_TARGET"),
        help="The systemd unit to target",
    )
    parser.add_argument(
        "--log-level",
        dest="log_level",
        default=os.environ.get("EXPORTER_PYTHON_LOG_LEVEL", "INFO"),
        help="The **Python** log level to output application debug logs at",
    )
    args = parser.parse_args()

    exporter = Exporter(
        target_systemd_unit=args.target_systemd_unit,
        log_level=args.log_level,
        systemd_log_level=args.systemd_log_level,
    )
    exporter.log()
