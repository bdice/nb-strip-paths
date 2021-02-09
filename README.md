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

This project's code is copied from *nbqa* under the MIT license. [nbqa](https://github.com/nbQA-dev/nbQA/tree/master/nbqa) is a wonderful tool for using Python linters/formatters with Jupyter notebooks, and I strongly recommend trying it!

## Tests

The tests require [nbconvert](https://github.com/jupyter/nbconvert) and [nbstripout](https://github.com/kynan/nbstripout).

For now, there is only a regression test. The output must be verified manually for correctness if committing changes to the test file.

To run the tests, execute:

```bash
cd tests
./run_tests.sh
```

If the test notebook is updated, execute:

```bash
cd tests
./generate_reference_notebooks.sh
```

and verify the notebook looks correct before committing.
