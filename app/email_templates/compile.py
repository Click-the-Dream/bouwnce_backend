import subprocess  # nosec B404
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def compile_mjml(input_file: str, output_file: str) -> None:
    input_file = str(BASE_DIR / input_file)
    output_file = str(BASE_DIR / output_file)

    subprocess.run(  # nosec B603, B607
        ["npx", "--yes", "mjml", input_file, "-o", output_file], check=True
    )


if __name__ == "__main__":
    compile_mjml("./src/event_reminder.mjml", "./build/event_reminder.html")
