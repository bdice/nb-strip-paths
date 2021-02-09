"""Parses the command line arguments provided."""
import argparse
from textwrap import dedent
from typing import List, Optional, Sequence

from nb_strip_paths import __version__
from nb_strip_paths.text import BOLD, RESET

USAGE_MSG = dedent(
    f"""\
    nb-strip-paths <notebook or directory>
    {BOLD}Please specify:{RESET}
    - 1) some notebooks (or, if supported by the tool, directories)
    {BOLD}Examples:{RESET}
        nb-strip-paths notebook.ipynb
    """
)


class CLIArgs:  # pylint: disable=R0902
    """
    Stores the command line arguments passed.

    Attributes
    ----------
    root_dirs
        The notebooks or directories to run third-party tool on.
    nb_strip_paths_files
        Global file include pattern.
    nb_strip_paths_exclude
        Global file exclude pattern.
    """

    root_dirs: Sequence[str]
    nb_strip_paths_files: Optional[str]
    nb_strip_paths_exclude: Optional[str]

    def __init__(self, args: argparse.Namespace, cmd_args: Sequence[str]) -> None:
        """
        Initialize this instance with the parsed command line arguments.

        Parameters
        ----------
        args
            Command line arguments passed to nb-strip-paths
        cmd_args
            Additional options to pass to the tool
        """
        self.root_dirs = args.root_dirs
        self.include = args.include or None
        self.exclude = args.exclude or None

    def __str__(self) -> str:
        """Return the command from the parsed command line arguments."""
        args: List[str] = ["nb-strip-paths", self.command]
        args.extend(self.root_dirs)
        if self.include:
            args.append(f"--include={self.include}")
        if self.exclude:
            args.append(f"--exclude={self.exclude}")

        return " ".join(args)

    @staticmethod
    def parse_args(argv: Optional[Sequence[str]]) -> "CLIArgs":
        """
        Parse command-line arguments.

        Parameters
        ----------
        argv
            Passed via command-line.

        Returns
        -------
        CLIArgs
            Object that holds all the parsed command line arguments.
        """
        parser = argparse.ArgumentParser(
            description="Strip user paths from a Jupyter notebook's output cells.",
            usage=USAGE_MSG,
        )
        parser.add_argument(
            "root_dirs", nargs="+", help="Notebooks or directories to run command on."
        )
        parser.add_argument(
            "--include",
            help="Global file include pattern.",
        )
        parser.add_argument(
            "--exclude",
            help="Global file exclude pattern.",
        )
        parser.add_argument(
            "--version", action="version", version=f"nb-strip-paths {__version__}"
        )
        args, cmd_args = parser.parse_known_args(argv)
        return CLIArgs(args, cmd_args)
