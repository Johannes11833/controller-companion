import argparse
import json
from pathlib import Path


import controller_companion
from controller_companion.app.app import launch_app
from controller_companion.app.controller_layouts import XboxControllerLayout
from controller_companion.controller_observer import ControllerObserver
from controller_companion.mapping import Mapping, ActionType
from controller_companion.controller import ControllerType


def cli():
    parser = argparse.ArgumentParser(
        description=controller_companion.APP_NAME,
    )
    parser.add_argument(
        "-t",
        "--task_kill",
        help="Kill tasks by their name.",
        nargs="+",
        type=str,
        default=[],
    )
    parser.add_argument(
        "-c",
        "--console",
        help="Execute console commands.",
        nargs="+",
        type=str,
        default=[],
    )
    parser.add_argument(
        "-s",
        "--shortcut",
        help='Keyboard shortcut, where each shortcut is defined by a number of keys separated by "+" (e.g. "alt+f4").',
        nargs="+",
        type=str,
        default=[],
    )
    parser.add_argument(
        "-i",
        "--input",
        help="Input controller button combination.",
        nargs="+",
        type=str,
    )
    parser.add_argument(
        "--disable",
        help="GUIDs of the controllers to ignore.",
        nargs="+",
        type=str,
    )
    parser.add_argument(
        "--valid-keys",
        help="List all valid keys.",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-d",
        "--debug",
        help="Enable debug messages.",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-v",
        "--version",
        help="Print the installed version of this library.",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--config",
        help="Use the config file of the app to setup the mappings.",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--custom-config",
        help="Use a custom config file to setup the mappings (using the same format as the App config).",
        type=str,
        default=None,
    )
    parser.add_argument(
        "--ui",
        help="Launch the app version of controller companion. Setting this flag will ignore all other arguments (except --minimized).",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-m",
        "--minimized",
        help="Launch the app minimized.",
        action="store_true",
        default=False,
    )

    args = parser.parse_args()
    debug = args.debug
    defined_actions = []

    if args.version:
        print("Installed version:", controller_companion.VERSION)
        return
    elif args.valid_keys:
        print(
            f"The following keys are valid inputs that can be used with the --shortcut argument:\n{Mapping.get_valid_keyboard_keys()}"
        )
        return

    if args.ui:
        launch_app(minimized=args.minimized)
    else:
        if args.input is not None:
            if len(args.input) != (
                len(args.task_kill) + len(args.console) + len(args.shortcut)
            ):
                raise Exception(
                    "Length of --mapping needs to match with combined sum of commands provided to --task_kill, --console and --shortcut"
                )

            active_buttons_list = []
            controller_type = ControllerType.XBOX
            layout = XboxControllerLayout()
            button_mapper = layout.get_button_layout()
            d_pad_mapper = layout.get_d_pad_layout()
            for button_combination in args.input:
                button_names = button_combination.split(",")
                for name in button_names:
                    if name not in button_mapper and name not in d_pad_mapper:
                        raise Exception(
                            f"key {name} is not a valid input. Valid options are {Mapping.get_valid_controller_inputs()}"
                        )
                active_buttons_list.append(button_names)

            state_counter = 0
            for t in args.task_kill:
                defined_actions.append(
                    Mapping(
                        ActionType.TASK_KILL_BY_NAME,
                        target=t,
                        name=f'Kill "{t}"',
                        active_controller_buttons=active_buttons_list[state_counter],
                        controller_type=controller_type,
                    )
                )
                state_counter += 1

            for c in args.console:
                defined_actions.append(
                    Mapping(
                        ActionType.CONSOLE_COMMAND,
                        target=c,
                        name=f'Run command "{c}"',
                        active_controller_buttons=active_buttons_list[state_counter],
                        controller_type=controller_type,
                    )
                )
                state_counter += 1

            for s in args.shortcut:
                defined_actions.append(
                    Mapping(
                        ActionType.KEYBOARD_SHORTCUT,
                        target=s,
                        name=f'Shortcut "{s}"',
                        active_controller_buttons=active_buttons_list[state_counter],
                        controller_type=controller_type,
                    )
                )
                state_counter += 1

        # ------------------------------ config support ------------------------------ #
        custom_config = args.custom_config
        use_config = args.config
        if custom_config is not None or use_config:
            path = custom_config if custom_config else controller_companion.CONFIG_PATH
            settings = json.loads(Path(path).read_text())
            defined_actions = [
                Mapping.from_dict(d) for d in settings.get("actions", [])
            ]
        # ---------------------------------------------------------------------------- #

        ControllerObserver().start(
            defined_actions=defined_actions,
            debug=debug,
            disabled_controllers=args.disable,
        )


if __name__ == "__main__":
    cli()
