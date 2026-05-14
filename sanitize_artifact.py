from pathlib import Path
import json

ROOT = Path(".")

SKIP_DIRS = {".git", "__pycache__", ".ipynb_checkpoints"}

REPLACEMENTS = {
    # Personal/local Linux paths
    "data/imdb/sf_025": "data/imdb/sf_025",
    "data/imdb/sf_050": "data/imdb/sf_050",
    "data/imdb/sf_1": "data/imdb/sf_1",
    "/path/to/local-home": "/path/to/local-home",

    "/path/to/schemalens/imdb": "/path/to/schemalens/imdb",
    "/path/to/schemalens/fiben": "/path/to/schemalens/fiben",
    "/path/to/schemalens/ldbc_snb": "/path/to/schemalens/ldbc_snb",
    "/path/to/fiben": "/path/to/fiben",
    "/path/to/imdb": "/path/to/imdb",
    "/path/to/local-data": "/path/to/local-data",
    "/path/to/jupyter-home": "/path/to/jupyter-home",

    # Windows/local paths
    "C:\\Users\\Hudso": "C:\\path\\to\\user",
    "local-drive": "local-drive",

    # GitHub/user identifiers
    "Anonymous Author": "Anonymous Author",
    "anonymous@example.com": "anonymous@example.com",
    "anonymous-user": "anonymous-user",
    "anonymous-user": "anonymous-user",

    # Remote access examples
    "user@remote-host": "user@remote-host",
    "remote-host": "remote-host",
}


TEXT_EXTENSIONS = {
    ".py", ".md", ".txt", ".csv", ".json", ".yml", ".yaml", ".sh", ".bat"
}


def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def replace_text(text: str) -> str:
    for old, new in REPLACEMENTS.items():
        text = text.replace(old, new)
    return text


def clean_notebook(path: Path) -> None:
    with path.open("r", encoding="utf-8") as f:
        nb = json.load(f)

    def clean_obj(obj):
        if isinstance(obj, str):
            return replace_text(obj)
        if isinstance(obj, list):
            return [clean_obj(x) for x in obj]
        if isinstance(obj, dict):
            return {k: clean_obj(v) for k, v in obj.items()}
        return obj

    nb = clean_obj(nb)

    # Clear outputs and execution counts to remove local paths printed by previous runs.
    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "code":
            cell["outputs"] = []
            cell["execution_count"] = None

    # Remove local execution metadata when present.
    nb.get("metadata", {}).pop("widgets", None)

    with path.open("w", encoding="utf-8") as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)

    print(f"Cleaned notebook: {path}")


def clean_text_file(path: Path) -> None:
    try:
        original = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return

    cleaned = replace_text(original)

    if cleaned != original:
        path.write_text(cleaned, encoding="utf-8")
        print(f"Cleaned text file: {path}")


def main():
    for path in ROOT.rglob("*"):
        if not path.is_file() or should_skip(path):
            continue

        if path.suffix == ".ipynb":
            clean_notebook(path)
        elif path.suffix.lower() in TEXT_EXTENSIONS:
            clean_text_file(path)


if __name__ == "__main__":
    main()