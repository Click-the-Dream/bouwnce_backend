import subprocess


def compile_mjml(input_file: str, output_file: str):
    subprocess.run(["mjml", input_file, "-o", output_file], check=True)


# compile_mjml("./src/vendor_alert_order.mjml", "./build/vendor_alert_order.html")
