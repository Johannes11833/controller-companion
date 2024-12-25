import platform
import shutil
import subprocess

from controller_companion import VERSION


def install():

    subprocess.run(args=["pyinstaller", "./controller-companion.spec", "--noconfirm"])

    # zip the pyinstaller output as an artifact
    os_name = platform.system().replace("Darwin", "Mac").lower()
    output_path = f"dist/controller-companion-{VERSION}-{os_name}"
    shutil.make_archive(output_path, "zip", "dist/controller-companion")
