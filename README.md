# Vert
Sane way to extract/view archived contents.

Vert will detect whether or not an archive file is nested inside a directory and
create a directory before extracting if there isn't.

> [!WARNING] 
> By default Vert uses Python's in-built libraries for extraction. If
> you'd like you may use external tools like `tar` and `unzip` instead. Please
> see [Configuration](#configuration) section. While I have made efforts to
> safely use these libraries, they are still always more likely to have
> vulnerabilities than mature tools like `tar` and `unzip`.

## Technical Details
Vert simply checks whether or not the root of the archive's source tree is a
single file/directory to judge if it should create a directory to nest the
contents into.

# How To Install
```bash
git clone --depth 1 --branch main https://github.com/eeriemyxi/vert
pip install ./vert
```
Or,
```
pip install git+https://github.com/eeriemyxi/vert@main
```
# Configuration
By default it uses `tarfile` and `zipfile` modules from Python's standard
library to extract content. If you'd like to use `tar` and `unzip` utilities
instead, then you can set `VERT_USE_EXTERNAL_TOOLS` environment variable to
`"true"`; setting it to anything else will mean `"false"`, but that may change
later so your safest bet is to set it to `"false"` if you want to turn it off.

# Usage
```bash
vert l myzip.zip myzip2.tar.xz myzip3.tar.gz
```
View the contents of the archives.

```bash
vert x myzip.zip myzip2.tar.xz myzip3.tar.gz
```
Extract the contents of the archives. If the contents are not nested then it will extract
them into directories `myzip`, `myzip2`, and `myzip3`.

# Command-line Arguments
```
usage: vert [-h] [--log-level LOG_LEVEL] [-v] {x,l} ...

Vert - Sane way to extract/view archived contents.

positional arguments:
  {x,l}
    x                   Extract contents of the archive (in a sane way).
    l                   List contents of the archive.

options:
  -h, --help            show this help message and exit
  --log-level LOG_LEVEL
                        Set log level. Options: DEBUG, INFO (default), CRITICAL, ERROR
  -v, --version         See current version.
```
