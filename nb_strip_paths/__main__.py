"""Strip user paths from Jupyter notebook."""

import json
import os
import re
import sys
from pathlib import Path
from typing import Iterator, Mapping, Optional, Sequence

from nb_strip_paths.cmdline import CLIArgs
from nb_strip_paths.find_root import find_project_root

EXCLUDES = (
    r"/("
    r"\.direnv|\.eggs|\.git|\.hg|\.ipynb_checkpoints|\.mypy_cache|\.nox|\.svn|\.tox|\.venv|"
    r"_build|buck-out|build|dist|venv"
    r")/"
)


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
