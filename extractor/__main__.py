import argparse
import sys
from pathlib import Path

from .pipeline import extract


def main() -> None:
    parser = argparse.ArgumentParser(prog="extractor", description="Текст документа -> JSON по схеме")
    parser.add_argument("path", type=Path, help="текстовый файл документа (UTF-8)")
    args = parser.parse_args()

    try:
        text = args.path.read_text(encoding="utf-8")
    except OSError as error:
        sys.exit(f"Не удалось прочитать файл: {error}")
    except UnicodeDecodeError:
        sys.exit(f"Файл не в кодировке UTF-8: {args.path}")

    sys.stdout.reconfigure(encoding="utf-8")  # иначе Windows-консоль падает на казахских буквах
    print(extract(text).model_dump_json(indent=2))


if __name__ == "__main__":
    main()
