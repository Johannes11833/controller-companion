import platform
import shutil
import PyInstaller.__main__
from pathlib import Path

from controller_companion import VERSION
from controller_companion.app import resources

HERE = Path(__file__).parent.absolute()
path_to_main = str(HERE / "app/app.py")


def install():

    PyInstaller.__main__.run(
        [
            path_to_main,
            "--name",
            "controller-companion",
            "--windowed",
            "--add-data",
            "controller_companion/res:controller_companion/res",
            "--icon",
            str(resources.APP_ICON_ICO),
            # remove question to override an existing output folder
            "--noconfirm",
        ]
    )

    # zip the pyinstaller output as an artifact
    os_name = platform.system().replace("Darwin", "Mac").lower()
    output_path = f"dist/controller-companion-{VERSION}-{os_name}"
    shutil.make_archive(output_path, "zip", "dist/controller-companion")
