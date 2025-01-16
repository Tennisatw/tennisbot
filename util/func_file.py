import os
import pathlib

from util.config import MESSAGES, ROOT_PATH
from util.set import sets


def _get_absolute_path(address):
    if os.path.isabs(address):
        return address
    return os.path.join(ROOT_PATH, address)


def file_check(param):
    address = _get_absolute_path(param[0])
    try:
        file_list = []

        def walk(f_address):
            if os.path.isfile(f_address):
                file_list.append(f_address)
                return
            else:
                f_entries = pathlib.Path(f_address)
                for f_entry in f_entries.iterdir():
                    if f_entry.is_file():
                        file_list.append(str(f_entry))
                    else:
                        file_list.append(str(f_entry) + "/")

        walk(address)

        if len(file_list) == 1:
            return MESSAGES.get(sets.lang, {}).get("file_check_success", '').format(file=file_list[0])
        else:
            file_text = "\n".join(file_list)
            return MESSAGES.get(sets.lang, {}).get("file_check_folder", '').format(file_text=file_text)

    except FileNotFoundError:
        return MESSAGES.get(sets.lang, {}).get("file_check_failed", '')


def file_read(param):
    address = _get_absolute_path(param[0])
    try:
        file = open(address, "r", encoding="utf-8")
        text = file.read()
        file.close()
        return text
    except FileNotFoundError:
        return MESSAGES.get(sets.lang, {}).get("file_read_failed", '')


def file_send(param):
    address = _get_absolute_path(param[0])
    try:
        file_list = []

        def walk(f_address):
            if os.path.isfile(f_address):
                file_list.append(f_address)
                return
            else:
                f_entries = pathlib.Path(f_address)
                for f_entry in f_entries.iterdir():
                    walk(str(f_entry))

        walk(address)

        if len(file_list) == 1:
            return file_list[0]
        else:
            return "\n".join(file_list)
    except FileNotFoundError:
        return MESSAGES.get(sets.lang, {}).get("file_check_failed", '')
    
    