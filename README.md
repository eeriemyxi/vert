# Vert
Sane way to extract/view archived contents.

Vert will detect whether or not an archive file is nested inside a directory and
create a directory before extracting if there isn't.

# How To Install
```bash
git clone --depth 1 --branch main https://github.com/eeriemyxi/vert
pip install ./vert
```
Or,
```
pip install git+https://github.com//eeriemyxi/vert@main
```

# Usage
```bash
vert l myzip.{zip,tar.gz,tar.xz}
```
View the contents of the archive.

```bash
vert x myzip.{zip,tar.gz,tar.xz}
```
Extract the contents of the archive. If the contents are not nested then it will extract
them into a directory `myzip`.

# Command-line Arguments
```
usage: vert [-h] [--log-level LOG_LEVEL] {x,l} ...

Vert - Sane way to extract/view archived contents.

positional arguments:
  {x,l}
    x                   Extract contents of the archive (in a sane way).
    l                   List contents of the archive.

options:
  -h, --help            show this help message and exit
  --log-level LOG_LEVEL
                        Set log level. Options: DEBUG, INFO (default), CRITICAL, ERROR
```
