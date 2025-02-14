from pathlib import Path


def yield_model_paths(dirpath: Path = None):
    """
    Returns a generator over all curated model filepaths.
    Uses dirpath as the curated model directory if provided;
    otherwise, assumes the following project structure:

        BioModelsDAG
        |
        └───BioModelsDAG
            |
            └───curated
                |   BIOMD0000000001.xml   # curated model
                |   ...
            |   ...
        |   ...

    :param dirpath: Path to directory containing curated models.
    :raises FileExistsError if dirpath is invalid (if provided) or the "curated"
                            directory is not present at "~/BioModelsDAG/BioModelsDAG/curated".
    :rtype: generator
    """
    if dirpath is None:
        from . import PROJECT_ROOT
        dirpath = PROJECT_ROOT / "BioModelsDAG" / "curated"
    if not dirpath.exists():
        raise FileExistsError("'{}' is not a valid directory path.".format(dirpath))

    for model_path in dirpath.iterdir():
        yield str(model_path.resolve())
