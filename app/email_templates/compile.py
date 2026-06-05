import subprocess  # nosec B404 - controlled local build helper
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def compile_mjml(input_file: str, output_file: str) -> None:
    input_file = str(BASE_DIR / input_file)
    output_file = str(BASE_DIR / output_file)

    subprocess.run(
        ["npx", "--yes", "mjml", input_file, "-o", output_file], check=True
    )  # nosec B603,B607 - controlled local build helper for MJML


if __name__ == "__main__":
    compile_mjml("./src/newsletter.mjml", "./build/newsletter.html")
