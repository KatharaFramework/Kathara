from ....exceptions import SettingsError
from ....setting.Setting import Setting
from ....trdparty.consolemenu import *
from ....trdparty.consolemenu import UserQuit

SAVED_STRING = "Saved successfully!\n"
PRESS_ENTER_STRING = "Press [Enter] to continue."


def format_bool(value):
    return "Yes" if value else "No"


def current_bool(attribute_name, text=None):
    return lambda: "%sCurrent: %s%s" % (text + " (" if text else "",
                                        (format_bool(getattr(Setting.get_instance(), attribute_name))),
                                        ")" if text else ""
                                        )


def current_string(attribute_name, text=None):
    return lambda: "%sCurrent: %s%s" % (text + " (" if text else "",
                                        getattr(Setting.get_instance(), attribute_name),
                                        ")" if text else ""
                                        )


def update_setting_value(attribute_name, value):
    reload = False

    if attribute_name == "manager_type" and Setting.get_instance().manager_type != value:
        reload = True

    setattr(Setting.get_instance(), attribute_name, value)

    try:
        if reload:
            Setting.get_instance().load_settings_addon()

        Setting.get_instance().check()

        Setting.get_instance().save()

        print(SAVED_STRING)
    except SettingsError as e:
        print(str(e))

    Screen().input(PRESS_ENTER_STRING)


def read_and_validate_value(prompt_msg, validator):
    prompt_utils = PromptUtils(Screen())
    answer = prompt_utils.input(prompt=prompt_msg,
                                validators=validator,
                                enable_quit=True
                                )

    return answer


def read_value(attribute_name, validator, prompt_msg, error_msg):
    try:
        answer = read_and_validate_value(prompt_msg=prompt_msg,
                                         validator=validator
                                         )

        while not answer.validation_result:
            answer = read_and_validate_value(prompt_msg=prompt_msg,
                                             validator=validator
                                             )
    except UserQuit:
        return

    setattr(Setting.get_instance(), attribute_name, answer.input_string)
    Setting.get_instance().save()

    print(SAVED_STRING)

    Screen().input(PRESS_ENTER_STRING)
