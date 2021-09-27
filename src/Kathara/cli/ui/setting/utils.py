from typing import Optional, Callable, Any, Tuple, List

from ....exceptions import SettingsError
from ....setting.Setting import Setting
from ....trdparty.consolemenu import *
from ....trdparty.consolemenu import UserQuit
from ....trdparty.consolemenu.prompt_utils import InputResult
from ....trdparty.consolemenu.validators.base import BaseValidator

SAVED_STRING = "Saved successfully!\n"
PRESS_ENTER_STRING = "Press [Enter] to continue."

URL_REGEX = r'^(?:http)s?://'  # http:// or https://
URL_REGEX += r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
URL_REGEX += r'localhost|'  # localhost...
URL_REGEX += r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
URL_REGEX += r'(?::\d+)?$'  # optional port


def format_bool(value: bool) -> str:
    return "Yes" if value else "No"


def current_bool(attribute_name: str, text: Optional[str] = None) -> Callable[[], str]:
    return lambda: "%sCurrent: %s%s" % (text + " (" if text else "",
                                        (format_bool(getattr(Setting.get_instance(), attribute_name))),
                                        ")" if text else ""
                                        )


def current_string(attribute_name: str, text: Optional[str] = None) -> Callable[[], str]:
    return lambda: "%sCurrent: %s%s" % (text + " (" if text else "",
                                        getattr(Setting.get_instance(), attribute_name),
                                        ")" if text else ""
                                        )


def update_setting_value(attribute_name: str, value: Any, stdout: bool = True) -> None:
    reload = False

    if attribute_name == "manager_type" and Setting.get_instance().manager_type != value:
        reload = True

    setattr(Setting.get_instance(), attribute_name, value)

    try:
        if reload:
            Setting.get_instance().load_settings_addon()

        Setting.get_instance().check()

        Setting.get_instance().save()

        if stdout:
            print(SAVED_STRING)
    except SettingsError as e:
        print(str(e))

    if stdout:
        Screen().input(PRESS_ENTER_STRING)


def update_setting_values(attribute_values: List[Tuple[str, Any]]) -> None:
    for attribute_name, value in attribute_values:
        update_setting_value(attribute_name, value, stdout=False)

    print(SAVED_STRING)
    Screen().input(PRESS_ENTER_STRING)


def read_and_validate_value(prompt_msg: str, validator: BaseValidator, error_msg: str) -> InputResult:
    prompt_utils = PromptUtils(Screen())
    answer = prompt_utils.input(prompt=prompt_msg,
                                validators=validator,
                                enable_quit=True
                                )

    if not answer.validation_result:
        print(error_msg)

    return answer


def read_value(attribute_name: str, validator: BaseValidator, prompt_msg: str, error_msg: str) -> None:
    try:
        answer = read_and_validate_value(prompt_msg=prompt_msg,
                                         validator=validator,
                                         error_msg=error_msg
                                         )

        while not answer.validation_result:
            answer = read_and_validate_value(prompt_msg=prompt_msg,
                                             validator=validator,
                                             error_msg=error_msg
                                             )
    except UserQuit:
        return

    setattr(Setting.get_instance(), attribute_name, answer.input_string)
    Setting.get_instance().save()

    print(SAVED_STRING)

    Screen().input(PRESS_ENTER_STRING)
