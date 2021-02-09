#!/bin/bash
set -x

jupyter nbconvert --execute --inplace "notebooks/*.ipynb"

for nbfile in $(ls "notebooks"); do
    nbstripout --keep-count --keep-output --extra-keys 'metadata.celltoolbar metadata.language_info.codemirror_mode.version metadata.language_info.pygments_lexer metadata.language_info.version metadata.toc metadata.notify_time metadata.varInspector cell.metadata.heading_collapsed cell.metadata.hidden cell.metadata.code_folding cell.metadata.tags cell.metadata.init_cell' "notebooks/${nbfile}"
done

nb-strip-paths "notebooks"
echo "Done generating reference notebooks."
