import subprocess


def compile_mjml(input_file: str, output_file: str):
    subprocess.run(["mjml", input_file, "-o", output_file], check=True)


compile_mjml("./src/waitlist_welcome.mjml", "./build/waitlist_welcome.html")
