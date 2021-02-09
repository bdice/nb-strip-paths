"""Strip user paths from Jupyter notebook."""

import json
import os
import re
import shutil
import sys
from pathlib import Path
from textwrap import dedent
from typing import Iterator, Mapping, Optional, Sequence, Set, Tuple

from nb_strip_paths.cmdline import CLIArgs
from nb_strip_paths.find_root import find_project_root
from nb_strip_paths.text import BOLD, RESET

BASE_ERROR_MESSAGE = dedent(
    f"""\
    {BOLD}{{}}
    Please report a bug at https://github.com/bdice/nb-strip-paths/nbQA/issues {RESET}
    """
)
MIN_VERSIONS = {"isort": "5.3.0"}
VIRTUAL_ENVIRONMENTS_URL = (
    "https://realpython.com/python-virtual-environments-a-primer/"
)
EXCLUDES = (
    r"/("
    r"\.direnv|\.eggs|\.git|\.hg|\.ipynb_checkpoints|\.mypy_cache|\.nox|\.svn|\.tox|\.venv|"
    r"_build|buck-out|build|dist|venv"
    r")/"
)


class UnsupportedPackageVersionError(Exception):
    """Raise if installed module is older than minimum required version."""

    def __init__(self, command: str, current_version: str, min_version: str) -> None:
        """Initialise with command, current version, and minimum version."""
        self.msg = (
            f"{BOLD}nbqa only works with {command} >= {min_version}, "
            f"while you have {current_version} installed.{RESET}"
        )
        super().__init__(self.msg)


def _get_notebooks(root_dir: str) -> Iterator[Path]:
    """
    Get generator with all notebooks in directory.

    Parameters
    ----------
    root_dir
        Notebook or directory to run third-party tool on.

    Returns
    -------
    notebooks
        All Jupyter Notebooks found in directory.
    """
    if not Path(root_dir).is_dir():
        return iter((Path(root_dir),))
    return (
        i
        for i in Path(root_dir).rglob("*.ipynb")
        if not re.search(EXCLUDES, str(i.resolve().as_posix()))
    )


def _filter_by_include_exclude(
    notebooks: Iterator[Path],
    include: Optional[str],
    exclude: Optional[str],
) -> Iterator[Path]:
    """
    Include files which match include, exclude those matching exclude.

    notebooks
        Notebooks (not directories) to run code quality tool on.
    include:
        Global file include pattern.
    exclude:
        Global file exclude pattern.

    Returns
    -------
    Iterator
        Notebooks matching include and not matching exclude.
    """
    include = include or ""
    exclude = exclude or "^$"
    include_re, exclude_re = re.compile(include), re.compile(exclude)
    return (
        notebook
        for notebook in notebooks
        if include_re.search(str(notebook.as_posix()))
        if not exclude_re.search(str(notebook.as_posix()))
    )


def _get_all_notebooks(
    root_dirs: Sequence[str], include: Optional[str], exclude: Optional[str]
) -> Iterator[Path]:
    """
    Get generator with all notebooks passed in via the command-line, applying exclusions.

    Parameters
    ----------
    root_dirs
        All the notebooks/directories passed in via the command-line.

    Returns
    -------
    Iterator
        All Jupyter Notebooks found in all passed directories/notebooks.
    """
    return _filter_by_include_exclude(
        (j for i in root_dirs for j in _get_notebooks(i)), include, exclude
    )


def _temp_python_file_for_notebook(
    notebook: Path, tmpdir: str, project_root: Path
) -> Path:
    """
    Get temporary file to save converted notebook into.

    Parameters
    ----------
    notebook
        Notebook that third-party tool will be run on.
    tmpdir
        Temporary directory where converted notebooks will be saved.
    project_root
        Root of repository, where .git / .hg / .nbqa.ini file is.

    Returns
    -------
    Path
        Temporary Python file whose location mirrors that of the notebook, but
        inside the temporary directory.

    Raises
    ------
    FileNotFoundError
        If notebook doesn't exist.
    """
    if not notebook.exists():
        raise FileNotFoundError(
            f"{BOLD}No such file or directory: {str(notebook)}{RESET}"
        )
    relative_notebook_path = (
        notebook.resolve().relative_to(project_root).with_suffix(".py")
    )
    temp_python_file = Path(tmpdir) / relative_notebook_path
    temp_python_file.parent.mkdir(parents=True, exist_ok=True)
    return temp_python_file


def _replace_temp_python_file_references_in_out_err(
    tmpdirname: str,
    temp_python_file: Path,
    notebook: Path,
    out: str,
    err: str,
) -> Tuple[str, str]:
    """
    Replace references to temporary Python file with references to notebook.

    Parameters
    ----------
    tmpdirname
        Temporary directory used for converting notebooks to python files
    temp_python_file
        Temporary Python file where notebook was converted to.
    notebook
        Original Jupyter notebook.
    out
        Captured stdout from third-party tool.
    err
        Captured stderr from third-party tool.

    Returns
    -------
    out
        Stdout with temporary directory replaced by current working directory.
    err
        Stderr with temporary directory replaced by current working directory.
    """
    # 1. Relative path is used because some tools like pylint always report only
    # the relative path of the file(relative to project root),
    # though absolute path was passed as the input.
    # 2. This `resolve()` part is necessary to handle cases when the path used
    # is a symlink as well as no normalize the path.
    # I couldn't reproduce this locally, but during CI, on the Windows job, I found
    # that VSSADM~1 was changing into VssAdministrator.
    paths = (
        str(path)
        for path in [
            temp_python_file,
            temp_python_file.resolve(),
            temp_python_file.relative_to(tmpdirname),
        ]
    )

    notebook_path = str(notebook)
    for path in paths:
        out = out.replace(path, notebook_path)
        err = err.replace(path, notebook_path)

    return out, err


def _create_blank_init_files(
    notebook: Path, tmpdirname: str, project_root: Path
) -> None:
    """
    Replicate local (possibly blank) __init__ files to temporary directory.

    Parameters
    ----------
    notebook
        Notebook third-party tool is being run against.
    tmpdirname
        Temporary directory to store converted notebooks in.
    project_root
        Root of repository, where .git / .hg / .nbqa.ini file is.
    """
    parts = notebook.resolve().relative_to(project_root).parts

    for idx in range(1, len(parts)):
        init_files = Path(os.path.join(*parts[:idx])).glob("__init__.py")
        for init_file in init_files:
            Path(tmpdirname).joinpath(init_file).parent.mkdir(
                parents=True, exist_ok=True
            )
            Path(tmpdirname).joinpath(init_file).touch()
            break  # Only need to copy one __init__ file.


def _preserve_config_files(
    config_files: Sequence[str], tmpdirname: str, project_root: Path
) -> None:
    """
    Copy local config file to temporary directory.

    Parameters
    ----------
    config_files
        Config files for third-party tool (e.g. mypy).
    tmpdirname
        Temporary directory to store converted notebooks in.
    project_root
        Root of repository, where .git / .hg / .nbqa.ini file is.
    """
    for config_file in config_files:
        config_file_path = project_root / config_file
        if config_file_path.exists():
            target_location = Path(tmpdirname) / config_file_path.resolve().relative_to(
                project_root
            )
            target_location.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(
                str(config_file_path),
                str(target_location),
            )


def _get_mtimes(arg: Path) -> Set[float]:
    """
    Get the modification times of any converted notebooks.

    Parameters
    ----------
    arg
        Notebook or directory to run 3rd party tool on.

    Returns
    -------
    Set
        Modification times of any converted notebooks.
    """
    if not arg.is_dir():
        return {os.path.getmtime(str(arg))}
    return {os.path.getmtime(str(i)) for i in arg.rglob("*.py")}


def _strip_paths(notebook_json: Mapping, project_root: Path):
    """Strip user paths from given notebook."""

    project_root_string = str(project_root) + os.sep

    mutated = False
    for cell in notebook_json["cells"]:
        if cell["cell_type"] == "code":
            for output in cell["outputs"]:
                for line_number, line in enumerate(output["text"]):
                    if project_root_string in line:
                        output["text"][line_number] = line.replace(
                            project_root_string, ""
                        )
                        mutated = True
    return notebook_json, mutated


def _run_on_one_root_dir(cli_args: CLIArgs, project_root: Path) -> int:
    """
    Run third-party tool on a single notebook or directory.

    Parameters
    ----------
    cli_args
        Command line arguments passed to nb-strip-paths.
    project_root
        Root of repository, where .git / .hg / .nbqa.ini file is.

    Returns
    -------
    int
        Output code from third-party tool.

    Raises
    ------
    RuntimeError
        If unable to parse or reconstruct notebook.
    """
    all_notebooks = list(
        _get_all_notebooks(cli_args.root_dirs, cli_args.include, cli_args.exclude)
    )

    for notebook in all_notebooks:
        print("Replacing user paths in", notebook)
        notebook_json = json.loads(notebook.read_text(encoding="utf-8"))
        notebook_json, mutated = _strip_paths(notebook_json, project_root)
        if mutated:
            notebook.write_text(
                f"{json.dumps(notebook_json, indent=1, ensure_ascii=False)}\n",
                encoding="utf-8",
            )

    if not all_notebooks:
        sys.stderr.write(
            "No .ipynb notebooks found in given directories: "
            f"{' '.join(i for i in cli_args.root_dirs if Path(i).is_dir())}\n"
        )
        return 0

    output_code = 0

    return output_code


def main(argv: Optional[Sequence[str]] = None) -> None:
    """
    Strip user paths from notebook or directory.

    Parameters
    ----------
    argv
        Command-line arguments (if calling this function directly), defaults to
        :code:`None` if calling via command-line.
    """
    cli_args: CLIArgs = CLIArgs.parse_args(argv)
    project_root: Path = find_project_root(tuple(cli_args.root_dirs))

    output_code = _run_on_one_root_dir(cli_args, project_root)

    sys.exit(output_code)


if __name__ == "__main__":
    main()
