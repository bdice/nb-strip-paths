# nb-strip-paths

This is a pre-commit hook that strips user paths from Jupyter notebooks. For example:

```
# When executing from a repository "my_awesome_code"
/home/bdice/my_awesome_code/some_directory/file.txt
# becomes...
some_directory/file.txt
```

This makes cleaner (and safer) examples for projects with tutorials that deal with filesystems and must print absolute paths.
Created for use with [signac-examples](https://github.com/glotzerlab/signac-examples).
