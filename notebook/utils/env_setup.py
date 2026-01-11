import os
import sys


def find_project_root(start_path=None, marker_file="pyproject.toml"):
    """
    Traverse upward from start_path to find the directory containing marker_file.
    """
    if start_path is None:
        start_path = os.getcwd()

    current = os.path.abspath(start_path)
    while True:
        if os.path.exists(os.path.join(current, marker_file)):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            raise FileNotFoundError(
                f"Could not find '{marker_file}' in any parent directory."
            )
        current = parent


def setup_src_path():
    """
    Adds <project_root>/src to sys.path so modules can be imported from notebooks.
    """
    project_root = find_project_root()
    src_path = os.path.join(project_root, "src")

    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    return src_path  # optional: for confirmation/logging


# Optional CLI use for debugging
if __name__ == "__main__":
    print("Added to sys.path:", setup_src_path())
