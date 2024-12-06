import argparse
import threading
from typing import Callable, Dict, List
import pygame


from controller_companion.shortcut import Shortcut, ActionType
from controller_companion.controller import Controller
from controller_companion.controller_state import (
    ControllerState,
    button_mapper,
    d_pad_mapper,
)


valid_inputs = list(button_mapper.keys()) + list(d_pad_mapper.keys())
do_run = True


def check_combos(
    controller_states: Dict[int, ControllerState],
    defined_actions: List[Shortcut],
):
    for instance_id, state in controller_states.items():
        for action in defined_actions:
            if action.controller_state.describe() == state.describe():
                print(f"Combo detected: {action} on controller {instance_id}")
                action.execute()


def run(
    defined_actions: Dict[str, Shortcut] = {},
    debug: bool = False,
    controller_callback: Callable[[List[Controller]], None] = None,
):
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
        "--custom",
        help="Execute custom commands.",
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
        "-m",
        "--mapping",
        help="Mapping.",
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
    args = parser.parse_args()
    debug = args.debug or debug
    if args.valid_keys:
        return f"The following keys are valid inputs that can be used with the --shortcut argument:\n{Shortcut.get_valid_keyboard_keys()}"

    if args.mapping is not None:
        if len(args.mapping) != (
            len(args.task_kill) + len(args.custom) + len(args.shortcut)
        ):
            raise Exception(
                "Length of --mapping needs to match with combined sum of commands provided to --task_kill, --custom and --shortcut"
            )

        states = []
        defined_actions = []

        for m in args.mapping:
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
                        f"key {input} is not a valid input. Valid options are {valid_inputs}"
                    )
            states.append(ControllerState(buttons, d_pad))

        state_counter = 0
        for t in args.task_kill:
            defined_actions.append(
                Shortcut(
                    ActionType.TASK_KILL_BY_NAME,
                    target=t,
                    name=f'Kill "{t}"',
                    controller_state=states[state_counter],
                )
            )
            state_counter += 1

        for c in args.custom:
            defined_actions.append(
                Shortcut(
                    ActionType.CUSTOM_COMMAND,
                    target=c,
                    name=f'Run command "{c}"',
                    controller_state=states[state_counter],
                )
            )
            state_counter += 1

        for s in args.shortcut:
            defined_actions.append(
                Shortcut(
                    ActionType.KEYBOARD_SHORTCUT,
                    target=s,
                    name=f'Shortcut "{s}"',
                    controller_state=states[state_counter],
                )
            )
            state_counter += 1

    print("\n--------------------")
    print("Defined Mappings:")
    for action in defined_actions:
        print(str(action))
    print("--------------------\n")

    controllers: Dict[int, pygame.joystick.JoystickType] = {}
    controller_states: Dict[int, ControllerState] = {}

    pygame.init()
    pygame.joystick.init()

    t = threading.current_thread()

    # List the available joystick devices
    joysticks = [
        pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())
    ]

    # # Initialize all detected joysticks
    # for joystick in joysticks:
    #     joystick.init()
    #     print(f"Joystick {joystick.get_id()}: {joystick.get_name()}")

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
                    print("Controller added:", event)
                    c = pygame.joystick.Joystick(event.device_index)
                    c.init()
                    instance_id = c.get_instance_id()
                    controllers[instance_id] = Controller(
                        name=c.get_name(),
                        guid=c.get_guid(),
                        power_level=c.get_power_level(),
                        instance_id=c.get_instance_id(),
                        initialized=c.get_init(),
                    )
                    controller_states[instance_id] = ControllerState()
                else:
                    print("Controller removed:", event)
                    controllers.pop(instance_id)
                    controller_states.pop(instance_id)

                if controller_callback:
                    controller_callback(list(controllers.values()))
            else:
                # skip all other events. this way only relevant updates are processed below.
                # this is relevant as e.g. thumbstick updates spam lots of updates
                continue
            check_combos(controller_states, defined_actions)

            if debug:
                print(controller_states)

        pygame.time.wait(250)

    pygame.quit()


def get_connected_controllers() -> List[pygame.joystick.JoystickType]:
    pygame.init()
    pygame.joystick.init()

    controllers = [
        pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())
    ]
    return [f"{c.get_name()} ({(c.get_guid())})" for c in controllers]


if __name__ == "__main__":
    defined_actions = [
        Shortcut(
            name="close acrobat",
            action_type=ActionType.TASK_KILL_BY_NAME,
            target="Acrobat.exe",
            controller_state=ControllerState([6], (-1, 0)),
        )
    ]

    run(defined_actions)
