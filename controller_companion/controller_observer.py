import argparse
import os
import threading
import traceback
from typing import Callable, Dict, List


import controller_companion
from controller_companion.app.controller_layouts import XboxControllerLayout
from controller_companion.logs import logger
from controller_companion import logs

# import pygame, hide welcome message
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "yes"
import pygame
from rich.table import Table
from rich.console import Console


from controller_companion.mapping import Mapping, ActionType
from controller_companion.controller import Controller, ControllerType


class ControllerObserver:

    def __init__(self):
        self.thread = None
        self.do_run = False

    def start_detached(
        self,
        defined_actions: List[Mapping],
        debug: bool = False,
        controller_callback: Callable[[List[Controller]], None] = None,
        restart_delay_ms: int = 1000,
        disabled_controllers: List[str] = None,
    ):
        self.thread = threading.Thread(
            target=self.start,
            daemon=True,
            args=[
                defined_actions,
            ],
            kwargs={
                "debug": debug,
                "controller_callback": controller_callback,
                "restart_delay_ms": restart_delay_ms,
                "disabled_controllers": disabled_controllers,
            },
        )
        self.thread.start()

    def start(
        self,
        defined_actions: List[Mapping],
        debug: bool = False,
        controller_callback: Callable[[List[Controller]], None] = None,
        restart_delay_ms: int = 1000,
        disabled_controllers: List[str] = None,
    ):
        self.do_run = True

        if debug:
            logs.set_log_level(logs.DEBUG)
        else:
            logs.set_log_level(logs.INFO)

        # ------------------- print the defined mappings in a table ------------------ #
        if len(defined_actions) > 0:
            table = Table(title="Defined Mappings")
            table.add_column("Name", justify="left", style="blue", header_style="blue")
            table.add_column(
                "Shortcut", justify="left", style="magenta", header_style="magenta"
            )
            table.add_column(
                "Action", justify="left", style="green", header_style="green"
            )
            table.add_column(
                "Type",
                justify="left",
                style="bright_black",
                header_style="bright_black",
            )

            for mapping in defined_actions:
                table.add_row(
                    mapping.name,
                    mapping.get_shortcut_string(),
                    mapping.target,
                    mapping.controller_type.value,
                )
            Console().log(table)
        else:
            logger.info("No mappings have been defined.")
        # ---------------------------------------------------------------------------- #

        logger.debug(f"Disabled controllers: {disabled_controllers}")
        logger.info("Listening to controller inputs.")

        pygame.init()

        try:
            self.__subscribe_to_pygame_events(
                defined_actions=defined_actions,
                controller_callback=controller_callback,
                disabled_controllers=disabled_controllers,
            )
        except Exception:
            logger.error(
                f"An exception occurred inside __process_pygame_events:\n{traceback.format_exc()}"
            )
            logger.info(f"restarting controller observation in {restart_delay_ms}s")
            pygame.time.wait(restart_delay_ms)
            return self.start(
                defined_actions=defined_actions,
                debug=debug,
                controller_callback=controller_callback,
                restart_delay_ms=restart_delay_ms,
            )

        pygame.quit()

    def stop(self):
        """Stops the controller observer thread if it was launches detached."""
        if self.thread and self.thread.is_alive:
            self.do_run = False
            self.thread.join()
            logger.debug("ControllerObserver thread stopped.")

    def __subscribe_to_pygame_events(
        self,
        defined_actions: Dict[str, Mapping] = {},
        controller_callback: Callable[[List[Controller]], None] = None,
        disabled_controllers: List[str] = None,
    ):
        controllers: Dict[int, Controller] = {}
        # we do not really need access the joysticks, but apparently we need to
        # keep a reference to all connected joysticks for them to function.
        pygame_joysticks: Dict[int, pygame.joystick.JoystickType] = {}

        while self.do_run:
            for event in pygame.event.get():
                instance_id = event.dict.get("instance_id", None)

                if event.type in [pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP]:
                    button = event.dict["button"]

                    controllers[instance_id].update_controller_state(
                        button=button, add_button=event.type == pygame.JOYBUTTONDOWN
                    )
                elif event.type == pygame.JOYHATMOTION:
                    d_pad_state = event.dict["value"]
                    controllers[instance_id].update_controller_state(
                        d_pad_state=d_pad_state
                    )
                elif event.type in [pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED]:
                    if event.type == pygame.JOYDEVICEADDED:
                        joy = pygame.joystick.Joystick(event.device_index)
                        instance_id = joy.get_instance_id()
                        pygame_joysticks[instance_id] = joy

                        controllers[instance_id] = Controller.from_pygame(joystick=joy)
                        logger.info(f"Controller connected: {controllers[instance_id]}")
                    else:
                        c = controllers.pop(instance_id)
                        logger.info(f"Controller removed: {c}")
                        del pygame_joysticks[event.instance_id]

                    if controller_callback:
                        # call the callback through a thread so it does not keep the observer waiting (e.g. app in background)
                        threading.Thread(
                            target=controller_callback,
                            args=[list(controllers.values())],
                        ).start()
                else:
                    # skip all other events. this way only relevant updates are processed below.
                    # this is relevant as e.g. thumbstick updates spam lots of updates
                    continue
                self.__check_for_mappings(
                    controllers, defined_actions, disabled_controllers
                )

                if event.type in [
                    pygame.JOYBUTTONDOWN,
                    pygame.JOYBUTTONUP,
                    pygame.JOYHATMOTION,
                ]:
                    logger.debug(f"Controller state changed: {controllers}")
            pygame.time.wait(250)

    def __check_for_mappings(
        self,
        controller_states: Dict[int, Controller],
        defined_actions: List[Mapping],
        disabled_controllers: List[str] = None,
    ):
        """Checks if one of the current controller states matches a defined mapping.

        Args:
            controller_states (Dict[int, ControllerState]): Dict of all current controller states where the key is the instance-id.
            defined_actions (List[Mapping]): List of defined mappings.
            disabled_controllers (List[str]): List of guids of the disabled controllers.
        """
        if disabled_controllers is None:
            disabled_controllers = []

        for instance_id, controller in controller_states.items():
            if (
                not isinstance(controller.layout, XboxControllerLayout)
                and len(controller.active_controller_inputs) > 0
            ):
                logger.debug(
                    f"{controller.name} emulated Xbox buttons: {controller.get_active_xbox_button_names()}"
                )

            for action in defined_actions:
                if controller.matches(
                    active_controller_inputs=action.active_controller_buttons,
                    controller_type=action.controller_type,
                ):
                    if controller.guid not in disabled_controllers:
                        logger.info(
                            f"Mapping detected: {action} on controller {instance_id}"
                        )
                        action.execute()


def cli():
    parser = argparse.ArgumentParser(description="Controller Companion.")
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

    ControllerObserver().start(
        defined_actions=defined_actions, debug=debug, disabled_controllers=args.disable
    )


if __name__ == "__main__":
    cli()
