import subprocess


def compile_mjml(input_file: str, output_file: str):
    subprocess.run(["mjml", input_file, "-o", output_file], check=True)


compile_mjml("/home/pcnerd/projects/bouwnce/bouwnce_backend/app/email_templates/src/newsletter.mjml", "/home/pcnerd/projects/bouwnce/bouwnce_backend/app/email_templates/build/newsletter.html")
