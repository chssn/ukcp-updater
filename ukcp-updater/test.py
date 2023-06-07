import re
from loguru import logger

def menu_option(title:str, data_type:str, options:list) -> str:
    while True:
        print(title)
        print("-"*30)
        output = {}
        for number, item in enumerate(options, start=1):
            print(f"{number}.\t{item}")
            output[int(number)] = item

        print(f"n.\tEnter new {data_type}")
        logger.debug(f"{data_type} menu options are {output}")
        
        choice = input(f"Please select which {data_type} you wish to use in all profiles: ")
        if re.match(r"[nN0-9]{1,}", choice):
            if choice.upper() == "N":
                return input(f"Enter the new {data_type}: ")
            elif int(choice) >= 1 and int(choice) <= int(number):
                return output[int(choice)]
        else:
            logger.error(f"No number detected. Please enter the number corresponding to the option you wish to use")

lst = ["A", "B", "C"]

menu_option("Test", "CID", lst)