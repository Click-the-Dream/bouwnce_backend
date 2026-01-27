import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def compile_mjml(input_file: str, output_file: str):
    input_file = str(BASE_DIR / input_file)
    output_file = str(BASE_DIR / output_file)

    subprocess.run(
    ["npx", "--yes", "mjml", input_file, "-o", output_file],
    check=True,
)



# compile_mjml("./src/buyer_order_cancelled.mjml", "./build/buyer_order_cancelled.html")
