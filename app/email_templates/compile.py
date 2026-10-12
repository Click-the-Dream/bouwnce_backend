# Controlled local build helper for MJML; not user-facing code.
import subprocess  # nosec
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def compile_mjml(input_file: str, output_file: str) -> None:
    input_file = str(BASE_DIR / input_file)
    output_file = str(BASE_DIR / output_file)

    # Build-helper only: argv is a compile-time constant list scoped to this
    # repo's MJML sources, never user input.
    subprocess.run(  # nosec
        ["npx", "--yes", "mjml", input_file, "-o", output_file], check=True
    )


if __name__ == "__main__":
    compile_mjml("./src/newsletter.mjml", "./build/newsletter.html")
