import argparse
import os
import threading
import traceback
from typing import Callable, Dict, List


import controller_companion
from controller_companion.logs import logger
from controller_companion import logs

# import pygame, hide welcome message
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "yes"
import pygame
from rich.table import Table
from rich.console import Console


from controller_companion.mapping import Mapping, ActionType
from controller_companion.controller import Controller
from controller_companion.controller_state import (
    ControllerState,
    button_mapper,
    d_pad_mapper,
)


VALID_KEYBOARD_KEYS = list(button_mapper.keys()) + list(d_pad_mapper.keys())
do_run = True


def start_observer(
    defined_actions: List[Mapping],
    debug: bool = False,
    controller_callback: Callable[[List[Controller]], None] = None,
    restart_delay_ms: int = 1000,
):

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
        table.add_column("Action", justify="left", style="green", header_style="green")

        for mapping in defined_actions:
            table.add_row(
                mapping.name,
                mapping.controller_state.describe(),
                mapping.target,
            )
        Console().log(table)
    else:
        logger.info("No mappings have been defined.")
    # ---------------------------------------------------------------------------- #

    logger.info("Listening to controller inputs.")

    try:
        __process_pygame_events(
            defined_actions=defined_actions,
            controller_callback=controller_callback,
        )
    except Exception:
        logger.error(
            f"An exception occurred inside __process_pygame_events:\n{traceback.format_exc()}"
        )
        logger.info(f"restarting controller observation in {restart_delay_ms}s")
        pygame.time.wait(restart_delay_ms)
        return start_observer(
            defined_actions=defined_actions,
            debug=debug,
            controller_callback=controller_callback,
            restart_delay_ms=restart_delay_ms,
        )

    pygame.quit()


def __process_pygame_events(
    defined_actions: Dict[str, Mapping] = {},
    controller_callback: Callable[[List[Controller]], None] = None,
):
    pygame.init()
    pygame.joystick.init()

    t = threading.current_thread()

    # Initialize all detected joysticks
    # Apparently with more than one controller connected this is required for all controllers to raise button/ d-pad events
    # even though they will also raise an pygame.JOYDEVICEADDED event right from the start.
    for i in range(pygame.joystick.get_count()):
        pygame.joystick.Joystick(i).init()

    controllers: Dict[int, pygame.joystick.JoystickType] = {}
    controller_states: Dict[int, ControllerState] = {}

    while getattr(t, "do_run", True):
        for event in pygame.event.get():
            instance_id = event.dict.get("instance_id", None)

            if event.type in [pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP]:
                button = event.dict["button"]

                active_buttons = controller_states[instance_id].active_buttons
                if event.type == pygame.JOYBUTTONDOWN:
                    active_buttons.append(button)
                else:
                    active_buttons.remove(button)
            elif event.type == pygame.JOYHATMOTION:
                controller_states[instance_id].d_pad_state = event.dict["value"]
            elif event.type in [pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED]:
                if event.type == pygame.JOYDEVICEADDED:
                    logger.info(f"Controller connected: {event}")
                    c = pygame.joystick.Joystick(event.device_index)
                    c.init()
                    instance_id = c.get_instance_id()
                    name = c.get_name()

                    controllers[instance_id] = Controller(
                        # on windows the controller name is wrapped inside "Controller()" when connected via USB
                        name=name.removeprefix("Controller (").removesuffix(")"),
                        guid=c.get_guid(),
                        power_level=c.get_power_level(),
                        instance_id=c.get_instance_id(),
                        initialized=c.get_init(),
                    )
                    controller_states[instance_id] = ControllerState()
                else:
                    logger.info(f"Controller removed: {event}")
                    controllers.pop(instance_id)
                    controller_states.pop(instance_id)

                if controller_callback:
                    # call the callback through a thread so it does not keep the observer waiting (e.g. app in background)
                    threading.Thread(
                        target=controller_callback, args=[list(controllers.values())]
                    ).start()
            else:
                # skip all other events. this way only relevant updates are processed below.
                # this is relevant as e.g. thumbstick updates spam lots of updates
                continue
            __check_for_mappings(controller_states, defined_actions)

            logger.debug(f"Controller state changed: {controller_states}")
        pygame.time.wait(250)


def __check_for_mappings(
    controller_states: Dict[int, ControllerState],
    defined_actions: List[Mapping],
):
    """Checks if one of the current controller states matches a defined mapping.

    Args:
        controller_states (Dict[int, ControllerState]): Dict of all current controller states where the key is the instance-id.
        defined_actions (List[Mapping]): List of defined mappings.
    """
    for instance_id, state in controller_states.items():
        for action in defined_actions:
            if action.controller_state.describe() == state.describe():
                logger.info(f"Mapping detected: {action} on controller {instance_id}")
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

        states = []
        for m in args.input:
            keys = m.split(",")
            buttons = []
            d_pad = (0, 0)
            for input in keys:
                if input in button_mapper:
                    buttons.append(button_mapper[input])
                elif input in d_pad_mapper:
                    d_pad = d_pad_mapper[input]
                else:
                    raise Exception(
                        f"key {input} is not a valid input. Valid options are {VALID_KEYBOARD_KEYS}"
                    )
            states.append(ControllerState(buttons, d_pad))

        state_counter = 0
        for t in args.task_kill:
            defined_actions.append(
                Mapping(
                    ActionType.TASK_KILL_BY_NAME,
                    target=t,
                    name=f'Kill "{t}"',
                    controller_state=states[state_counter],
                )
            )
            state_counter += 1

        for c in args.console:
            defined_actions.append(
                Mapping(
                    ActionType.CONSOLE_COMMAND,
                    target=c,
                    name=f'Run command "{c}"',
                    controller_state=states[state_counter],
                )
            )
            state_counter += 1

        for s in args.shortcut:
            defined_actions.append(
                Mapping(
                    ActionType.KEYBOARD_SHORTCUT,
                    target=s,
                    name=f'Shortcut "{s}"',
                    controller_state=states[state_counter],
                )
            )
            state_counter += 1

    start_observer(defined_actions=defined_actions, debug=debug)


if __name__ == "__main__":
    cli()
