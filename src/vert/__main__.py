import argparse
import enum
import importlib
import logging
import pathlib

log = logging.getLogger(__file__)


class SupportedType(enum.Enum):
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
    return "".join(path.suffixes)


def _check_suffix(path: pathlib.Path, suffix: str | list[str] | tuple[str]):
    suffixes = _joined_suffix(path)
    if isinstance(suffix, str):
        return suffix == suffixes
    if isinstance(suffix, list | tuple):
        return any(_check_suffix(path, s) for s in suffix)


def _name_without_suffix(name: str):
    return name.rsplit(".", maxsplit=2)[0]


def _import_correct_mod(file: pathlib.Path):
    log.debug(f"{file.suffix=}")

    if _check_suffix(file, (".tar.gz", ".tar.xz")):
        log.debug("Importing tarfile module")
        module = importlib.import_module("tarfile")
    elif _check_suffix(file, ".zip"):
        log.debug("Importing zipfile module")
        module = importlib.import_module("zipfile")
    else:
        log.critical("Unsupported file format: %s", _joined_suffix(file))
        exit(1)

    return module, SupportedType.from_str(_joined_suffix(file))


def _extract_compression(suffix: str | SupportedType):
    if isinstance(suffix, SupportedType):
        suffix = suffix.value
    return suffix.split(".")[-1]


def _zip_list_contents(zip_):
    zip_.printdir()


def _tar_list_contents(tar):
    tar.list()


def list_contents(args) -> None:
    file = args.file.resolve()
    module, file_suffix = _import_correct_mod(file)
    log.debug(f"{module=}")
    log.debug(f"{file_suffix=}")

    if file_suffix is SupportedType.ZIP:
        with module.ZipFile(file, "r") as zip_:
            _zip_list_contents(zip_)
    elif file_suffix in (SupportedType.TARGZ, SupportedType.TARXZ):
        with module.open(file, f"r:{_extract_compression(file_suffix)}") as tar:
            _tar_list_contents(tar)


def _zip_is_nested(zip_):
    return len(zip_.namelist()) == 1


def _tar_is_nested(tar):
    return len(tar.getnames()) == 1


def _zip_extract_file(zip_, dest):
    zip_.extractall(path=dest)


def _tar_extract_file(tar, dest):
    tar.extractall(path=dest, filter="data")


def extract_archive(args):
    file = args.file.resolve()
    cwd = pathlib.Path.cwd()
    module, file_suffix = _import_correct_mod(file)
    log.debug(f"{module=}")
    log.debug(f"{file_suffix=}")

    if file_suffix is SupportedType.ZIP:
        assert module.is_zipfile(file), f"improper zip file: {file}"
        with module.ZipFile(file, "r") as zip_:
            _zip_extract_file(
                zip_,
                cwd if _zip_is_nested(zip_) else cwd / _name_without_suffix(file.name),
            )
    elif file_suffix in (SupportedType.TARGZ, SupportedType.TARXZ):
        assert module.is_tarfile(file), f"improper tar file: {file}"
        with module.open(file, f"r:{_extract_compression(file_suffix)}") as tar:
            _tar_extract_file(
                tar,
                cwd if _tar_is_nested(tar) else cwd / _name_without_suffix(file.name),
            )


LOG_LEVEL = "INFO"

parser = argparse.ArgumentParser(
    description="Vert - Sane way to extract/view archived contents."
)

parser.add_argument(
    "--log-level",
    help="Set log level. Options: DEBUG, INFO (default), CRITICAL, ERROR",
    type=str,
    default="INFO",
)

subparsers = parser.add_subparsers()

parser_extract = subparsers.add_parser(
    "x",
    help=f"Extract contents of the archive (in a sane way).",
)
parser_extract.add_argument("file", type=pathlib.Path)
parser_extract.set_defaults(func=extract_archive)

parser_list = subparsers.add_parser(
    "l",
    help=f"List contents of the archive.",
)
parser_list.add_argument("file", type=pathlib.Path)
parser_list.set_defaults(func=list_contents)

args = parser.parse_args()
LOG_LEVEL = args.log_level

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(levelname)s: [%(asctime)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

if not hasattr(args, "func"):
    parser.print_help()
    exit(1)

args.func(args)


def main():
    pass
