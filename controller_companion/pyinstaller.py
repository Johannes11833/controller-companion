import PyInstaller.__main__
from pathlib import Path

from controller_companion.app import resources

HERE = Path(__file__).parent.absolute()
path_to_main = str(HERE / "app/app.py")


def install():
    print(
        str(resources.APP_ICON_ICO.absolute()),
    )
    PyInstaller.__main__.run(
        [
            path_to_main,
            "--onefile",
            "--windowed",
            "--add-data",
            "controller_companion/res:controller_companion/res",
            "--icon",
            str(resources.APP_ICON_ICO),
        ]
    )
