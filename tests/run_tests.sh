#!/bin/bash

set -x

# Copy all the notebooks to a temp directory that we will use for comparison later
mkdir -p .comparison-notebooks
cp -r notebooks/*.ipynb .comparison-notebooks

# Re-generate the reference notebooks
./generate_reference_notebooks.sh

# Diff all the notebooks
for nbfile in $(ls notebooks); do
    test_nbfile="notebooks/${nbfile}"
    comparison_nbfile=".comparison-notebooks/${nbfile}"
    DIFF=$(diff "${comparison_nbfile}" "${test_nbfile}")
    if [ "$DIFF" != "" ]; then
        echo "Notebook ${test_nbfile} has a non-empty diff!"
        diff "${comparison_nbfile}" "${test_nbfile}"
        mv .comparison-notebooks/*.ipynb notebooks
        exit 1
    fi
done

# Move back all the notebooks
mv .comparison-notebooks/*.ipynb notebooks
echo "All notebooks passed tests."
