#!/usr/bin/env bash
# Usage: bash scripts/download_public_datasets.sh [pole|ctu13|iot23|govdocs]
set -e
cd "$(dirname "$0")/../datasets"
case "$1" in
  pole)
    git clone --depth 1 https://github.com/neo4j-graph-examples/pole.git pole/pole_repo
    cp pole/pole_repo/data/pole-data-importer.zip pole/pole_repo/data/pole-50.dump pole/
    echo "POLE files copied to datasets/pole/ (git-ignored)";;
  ctu13)
    echo "CTU-13 (about 1.9 GB). Open the page, pick ONE scenario, and download only that:"
    echo "  https://www.stratosphereips.org/datasets-ctu13"
    echo "  https://mcfp.felk.cvut.cz/publicDatasets/CTU-13-Dataset/"
    echo "Save into datasets/ctu13/ and record date and size in datasets/README.md";;
  iot23)
    echo "IoT-23: open https://www.stratosphereips.org/datasets-iot23 (Zenodo 10.5281/zenodo.4743746)"
    echo "Download one labelled capture, not the full 8.8 GB / 21 GB sets. Save into datasets/iot23/";;
  govdocs)
    echo "Govdocs1: open https://digitalcorpora.org/corpora/files/ and download ONE subset."
    echo "Save into datasets/govdocs1/";;
  *) echo "Usage: $0 [pole|ctu13|iot23|govdocs]"; exit 1;;
esac
