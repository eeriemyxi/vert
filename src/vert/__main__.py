import argparse
import logging
import pathlib
from enum import Enum

log = logging.getLogger(__file__)


class SupportedType(Enum):
    ZIP = ".zip"
    TARXZ = ".tar.xz"
    TARGZ = ".tar.gz"

    @classmethod
    def from_str(cls, type_s: str):
        if type_s == ".zip":
            return cls.ZIP
        elif type_s == ".tar.xz":
            return cls.TARXZ
        elif type_s == ".tar.gz":
            return cls.TARGZ


def _joined_suffix(path: pathlib.Path) -> str:
    return "".join(path.suffixes[-2:])


def _check_suffix(path: pathlib.Path, suffix: str | list[str] | tuple[str]):
    suffixes = _joined_suffix(path)
    if isinstance(suffix, str):
        return suffix == suffixes
    if isinstance(suffix, list | tuple):
        return any(_check_suffix(path, s) for s in suffix)


def _name_without_suffix(name: str):
    return name.rsplit(".", maxsplit=2)[0]


def _should_use_external_tools() -> bool:
    # INFO: Python doesn't reload the module if you do this, so there is no
    # overhead involved on repeating calls.
    # See: https://docs.python.org/3/library/sys.html#sys.modules
    import os

    return (
        os.environ.get("VERT_USE_EXTERNAL_TOOLS", "false").strip().casefold() == "true"
    )


def _import_backend(file: pathlib.Path, file_type: SupportedType):
    log.debug(f"{file.suffix=}")

    if file_type in (SupportedType.TARGZ, SupportedType.TARXZ):
        log.debug("Importing tarfile module")
        import tarfile as module
    elif file_type is SupportedType.ZIP:
        log.debug("Importing zipfile module")
        import zipfile as module

    return module


def _extract_compression(suffix: str | SupportedType):
    if isinstance(suffix, SupportedType):
        suffix = suffix.value
    return suffix.split(".")[-1]


def _zip_list_contents(zip_):
    zip_.printdir()


def _tar_list_contents(tar):
    tar.list()


def list_contents(file) -> None:
    log.info("Listing contents for '%s'", file)

    file = file.resolve()
    file_type = SupportedType.from_str(_joined_suffix(file))
    if not file_type:
        log.critical("Unsupported file format: '%s'", _joined_suffix(file))
        exit(1)

    module = _import_backend(file, file_type)

    log.debug(f"{module=}")
    log.debug(f"{file_type=}")

    if file_type is SupportedType.ZIP:
        with module.ZipFile(file, "r") as zip_:
            _zip_list_contents(zip_)
    elif file_type in (SupportedType.TARGZ, SupportedType.TARXZ):
        with module.open(file, f"r:{_extract_compression(file_type)}") as tar:
            _tar_list_contents(tar)


def _zip_is_nested(zip_):
    log.info("Checking if the contents are nested. This can take some time...")
    rc_count = 0
    for x in zip_.namelist():
        if "/" not in x:
            rc_count += 1
        if rc_count > 1:
            return False
    return True


def _tar_is_nested(tar):
    log.info("Checking if the contents are nested. This can take some time...")
    rc_count = 0
    for x in tar.getnames():
        if "/" not in x:
            rc_count += 1
        if rc_count > 1:
            return False
    return True


def _print_extraction_info(dest):
    log.info("Contents will be extracted to '%s'", dest.relative_to(pathlib.Path.cwd()))


def _zip_extract_file(zip_, file, dest):
    dest.mkdir(exist_ok=True)

    _print_extraction_info(dest)
    if _should_use_external_tools():
        import subprocess

        subprocess.run(["unzip", file, "-d", dest])
        return
    zip_.extractall(path=dest)


def _tar_extract_file(tar, file, dest):
    dest.mkdir(exist_ok=True)

    _print_extraction_info(dest)
    if _should_use_external_tools():
        import subprocess

        subprocess.run(["tar", "-xf", file, "--directory", dest])
        return
    tar.extractall(path=dest, filter="data")


def extract_archive(file):
    log.info("Extracting contents of '%s'", file)

    file = file.resolve()
    cwd = pathlib.Path.cwd()

    file_type = SupportedType.from_str(_joined_suffix(file))
    if not file_type:
        log.critical("Unsupported file format: '%s'", _joined_suffix(file))
        exit(1)

    module = _import_backend(file, file_type)

    log.debug(f"{module=}")
    log.debug(f"{file_type=}")

    if file_type is SupportedType.ZIP:
        assert module.is_zipfile(file), f"improper zip file: {file}"
        with module.ZipFile(file, "r") as zip_:
            _zip_extract_file(
                zip_,
                file,
                cwd if _zip_is_nested(zip_) else cwd / _name_without_suffix(file.name),
            )
    elif file_type in (SupportedType.TARGZ, SupportedType.TARXZ):
        assert module.is_tarfile(file), f"improper tar file: {file}"
        with module.open(file, f"r:{_extract_compression(file_type)}") as tar:
            _tar_extract_file(
                tar,
                file,
                cwd if _tar_is_nested(tar) else cwd / _name_without_suffix(file.name),
            )
    log.info(f"Finished extracting '%s'", file.relative_to(cwd))


def cmd_list_contents(args):
    for file in args.files:
        if not file.exists():
            log.critical(f"File '{file}' doesn't exist. Skipping...")
            continue
        list_contents(file)


def cmd_extract_archives(args):
    if _should_use_external_tools():
        log.info("Using external tools `tar` or `unzip` for extraction...")
    for file in args.files:
        if not file.exists():
            log.critical(f"File '{file}' doesn't exist. Skipping...")
            continue
        extract_archive(file)


def _show_version():
    import importlib.metadata

    print(importlib.metadata.version("vert"))


LOG_LEVEL = "INFO"

parser = argparse.ArgumentParser(
    description="Vert - Sane way to extract/view archived contents."
)

parser.add_argument(
    "-L",
    "--log-level",
    help="Set log level. Options: DEBUG, INFO (default), CRITICAL, ERROR",
    type=str,
    default="INFO",
)

parser.add_argument(
    "-v",
    "--version",
    help="See current version.",
    action="store_true",
)
subparsers = parser.add_subparsers()

parser_extract = subparsers.add_parser(
    "x",
    help=f"Extract contents of the archive (in a sane way).",
)
parser_extract.add_argument("files", type=pathlib.Path, nargs="+")
parser_extract.set_defaults(func=cmd_extract_archives)

parser_list = subparsers.add_parser(
    "l",
    help=f"List contents of the archive.",
)
parser_list.add_argument("files", type=pathlib.Path, nargs="+")
parser_list.set_defaults(func=cmd_list_contents)

args = parser.parse_args()
LOG_LEVEL = args.log_level

logging.basicConfig(
    level=LOG_LEVEL,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

if args.version:
    _show_version()
    exit()

if not hasattr(args, "func"):
    parser.print_help()
    exit(1)

args.func(args)


def main():
    pass
