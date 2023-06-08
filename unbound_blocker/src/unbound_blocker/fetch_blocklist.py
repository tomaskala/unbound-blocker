import ipaddress
import logging
import re
import sys
from collections.abc import Iterator
from pathlib import Path
from subprocess import run

import click
import requests
from requests.exceptions import Timeout

LOGGER = logging.getLogger(__name__)
COMMENT = re.compile(r"\s*#.*$")
TRAILING_DOTS = re.compile(r"\.+$")
REQUEST_TIMEOUT = 10


def all_lines(source: Path) -> Iterator[str]:
    with source.open(encoding="utf-8") as f:
        yield from map(str.strip, f)


def is_ip_address(string: str) -> bool:
    try:
        ipaddress.ip_address(string)
    except ValueError:
        return False
    else:
        return True


def parse_blocklist(text: str) -> list[str]:
    blocklist = []
    lines = text.lower().splitlines()

    for line in filter(None, (COMMENT.sub(repl="", string=line) for line in lines)):
        parts = line.split()

        if is_ip_address(parts[0]):
            blocklist.extend([TRAILING_DOTS.sub("", part) for part in parts[1:]])
        elif len(parts) == 1:
            blocklist.append(TRAILING_DOTS.sub("", parts[0]))
        else:
            LOGGER.warning("Unexpected format of line '%s'", line)

    return blocklist


def retrieve_blocklist(sources: Path) -> set[str]:
    LOGGER.info("Retrieving blocklist")
    blocklist = []

    for source in all_lines(sources):
        try:
            response = requests.get(source, timeout=REQUEST_TIMEOUT)
        except Timeout:
            LOGGER.error("Timeout when retrieving source '%s'", source)
            continue

        if not response:
            LOGGER.error(
                "Got status code %d from source '%s'",
                response.status_code,
                source,
            )
            continue

        LOGGER.info("Parsing source '%s'", source)
        blocklist.extend(parse_blocklist(response.text))

    return set(blocklist)


def clear_blocklist(unbound_control: Path) -> None:
    LOGGER.info("Clearing blocklist")
    LOGGER.info("Obtaining current local zones")

    p = run(
        [unbound_control, "list_local_zones"],
        bufsize=1,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    print(p.stderr, file=sys.stderr)

    if p.returncode != 0:
        LOGGER.critical("%s exitted with code %d", unbound_control, p.returncode)
        sys.exit(1)

    blocklist = []

    for local_zone in p.stdout.splitlines():
        parts = local_zone.split(" ")

        if len(parts) != 2:
            LOGGER.error("Unexpected format of local zone '%s'", local_zone)
            continue

        if parts[1] == "always_null":
            blocklist.append(parts[0])

    LOGGER.info("Removing current blocklist (%d domains)", len(blocklist))

    if blocklist:
        p = run(
            [unbound_control, "local_zones_remove"],
            input="\n".join(blocklist) + "\n",
            bufsize=1,
            capture_output=False,
            text=True,
            encoding="utf-8",
        )

        if p.returncode != 0:
            LOGGER.critical("%s exitted with code %d", unbound_control, p.returncode)
            sys.exit(1)


def load_blocklist(blocklist: list[str], unbound_control: Path) -> None:
    LOGGER.info("Filling blocklist (%d domains)", len(blocklist))
    local_zones = [f"{domain}. always_null" for domain in blocklist]

    if local_zones:
        p = run(
            [unbound_control, "local_zones"],
            input="\n".join(local_zones) + "\n",
            bufsize=1,
            capture_output=False,
            text=True,
            encoding="utf-8",
        )

        if p.returncode != 0:
            LOGGER.critical("%s exitted with code %d", unbound_control, p.returncode)
            sys.exit(1)

    LOGGER.info("Success")


@click.command
@click.argument(
    "sources",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
)
@click.option(
    "-u",
    "--unbound-control",
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
        executable=True,
        path_type=Path,
    ),
    default=Path("/usr/sbin/unbound-control"),
    show_default=True,
    help="Path to unbound-control(8)",
)
@click.option(
    "-w",
    "--whitelist",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    help="Whitelist file with one domain per line",
)
def main(sources: Path, unbound_control: Path, whitelist: Path) -> None:
    """
    Use unbound(8) as a DNS blocker.

    Read one blocklist URL per line from SOURCES, retrieve its contents and parse
    it as a blocklist in the hosts(5) format. The obtained domains are passed to
    unbound-control(8) to always resolve them to the null address.
    """
    logging.basicConfig(
        format="%(asctime)-15s %(levelname)s [%(filename)s:%(lineno)d]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )

    blocklist = retrieve_blocklist(sources)

    if whitelist is not None:
        blocklist -= set(all_lines(whitelist))

    clear_blocklist(unbound_control)
    load_blocklist(list(blocklist), unbound_control)


if __name__ == "__main__":
    main()
