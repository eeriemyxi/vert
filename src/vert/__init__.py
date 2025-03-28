import argparse
import logging
import pathlib
import io
import enum

log = logging.getLogger(__file__)


class SupportedType(enum.StrEnum):
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


def _split_filename(supported_formats: list[str], file: pathlib.Path):
    raw_split = file.name.split(".")
    name = io.StringIO()
    suffix = io.StringIO()
    found_suffix = False

    for i, s in enumerate(reversed(raw_split)):
        if len(raw_split) - 1 > i:
            s = "." + s

        if not found_suffix:
            suffix.seek(0)
            suffix.write(s + suffix.getvalue())

        if not found_suffix and suffix.getvalue() in supported_formats:
            found_suffix = True
        elif found_suffix:
            name.seek(0)
            name.write(s + name.getvalue())
    
    if not found_suffix:
        raise ValueError(f"Archive format not supported: {suffix.getvalue()}")
        
    return name.getvalue(), suffix.getvalue()


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


def _extract_compression(suffix: str):
    splits = suffix.split(".")

    if not len(splits) >= 2:
        raise ValueError(f"There is no compression to extract for {splits=} from {suffix=}.")

    return splits[-1]


def _zip_list_contents(zip_):
    zip_.printdir()


def _tar_list_contents(tar):
    tar.list()


def list_contents(file) -> None:
    log.info("Listing contents for '%s'", file)

    file = file.resolve()

    try:
        filename, file_type = _split_filename(list(SupportedType), file)
    except ValueError:
        log.critical("Unsupported file format: '%s'", _joined_suffix(file))
        exit(1)
    else:
        file_type = SupportedType.from_str(file_type)

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
    import zipfile

    rc_count = 0
    for x in zipfile.Path(zip_).iterdir():
        if "/" not in x.name:
            rc_count += 1
        if rc_count > 1:
            return False
    return True


def _tar_is_nested(tar):
    log.info("Checking if the contents are nested. This can take some time...")

    rc_count = 0
    for x in tar:
        if "/" not in x.name:
            rc_count += 1
        if rc_count > 1:
            return False
    return True


def _print_extraction_info(dest):
    log.info("Contents will be extracted to '%s'", dest.relative_to(pathlib.Path.cwd()))


def _zip_extract_file(zip_, file, dest):
    log.debug("Called _zip_extract_file")
    dest.mkdir(exist_ok=True)

    _print_extraction_info(dest)
    if _should_use_external_tools():
        import subprocess

        subprocess.run(["unzip", file, "-d", dest])
        return
    zip_.extractall(path=dest)


def _tar_extract_file(tar, file, dest):
    log.debug("Called _tar_extract_file")
    dest.mkdir(exist_ok=True)

    _print_extraction_info(dest)
    if _should_use_external_tools():
        import subprocess

        subprocess.run(["tar", "-xf", file, "--directory", dest])
        return
    log.debug(f"Extracting contents of {file=} to {dest=}")
    tar.extractall(path=dest, filter="data")


def extract_archive(file):
    log.info("Extracting contents of '%s'", file)

    file = file.resolve()
    cwd = pathlib.Path.cwd()

    try:
        filename, file_type = _split_filename(list(SupportedType), file)
    except ValueError:
        log.critical("Unsupported file format: '%s'", _joined_suffix(file))
        exit(1)
    else:
        file_type = SupportedType.from_str(file_type)

    module = _import_backend(file, file_type)

    log.debug(f"{module=}")
    log.debug(f"{file_type=}")

    if file_type is SupportedType.ZIP:
        assert module.is_zipfile(file), f"improper zip file: {file}"
        with module.ZipFile(file, "r") as zip_:
            _zip_extract_file(
                zip_,
                file,
                cwd if _zip_is_nested(zip_) else cwd / filename,
            )
    elif file_type in (SupportedType.TARGZ, SupportedType.TARXZ):
        assert module.is_tarfile(file), f"improper tar file: {file}"
        log.debug(f"Opening file {file=}")
        with module.open(file, f"r:{_extract_compression(file_type)}") as tar:
            log.debug(f"Opened file {file=}")
            _tar_extract_file(
                tar,
                file,
                cwd if _tar_is_nested(tar) else cwd / filename,
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



def main():
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


if __name__ == "__main__":
    main()
