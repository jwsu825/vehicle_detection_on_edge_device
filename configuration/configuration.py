import configparser
import re

import constants


class __ConfigurationInfo:
    # this class will be used to store all the configuration
    # info regarding any runtime values that need to be set

    def __init__(self, ini_file=constants.DEFAULT_CONFIG_FILE):
        self.__configuration = {}
        self.ini_file = ini_file
        self.__read_file()
        return

    def __read_file(self):
        config_parser = configparser.ConfigParser()
        config_parser.read(self.ini_file)
        for section in config_parser.sections():
            items = config_parser.items(section)
            for key, value in items:
                self.__add_new_value(section, key, value)

        print(self.__configuration)

    def save(self):
        updated_config = configparser.ConfigParser()
        for section in self.__configuration:
            updated_config.add_section(section)
            for key in self.__configuration[section]:
                updated_config.set(section, key, str(self.__configuration[section][key]))

        with open(self.ini_file, 'w') as updated_ini:
            updated_config.write(updated_ini)

    def __add_new_value(self, section, key, value):
        # this function takes in a section, key, and value
        # it will determine whether the value is a string, int, bool,
        # or float, and add it to the configuration dictionary
        # under the appropriate section and key
        if section not in self.__configuration:
            self.__configuration[section] = {}

        if re.match('\d*\.\d+', value) or value.lower() == 'nan':
            try:
                self.__configuration[section][key] = float(value)
            except:
                raise
        elif re.match('\d+', value):
            try:
                self.__configuration[section][key] = int(value)
            except:
                raise
        elif re.match('\[*\]', value):
            try:
                tmp_value = value.replace('[', '').replace(']', '')
                self.__configuration[section][key] = tmp_value.split(',')
            except:
                raise
        elif value.lower() == 'true':
            self.__configuration[section][key] = True
        elif value.lower() == 'false':
            self.__configuration[section][key] = False
        else:
            self.__configuration[section][key] = value

    def get_value(self, section, key):
        # this function will return None if section of key is not
        # found or the key is not found in the section

        if section not in self.__configuration or \
                        key not in self.__configuration[section]:
            return None
        return self.__configuration[section][key]

    def set_value(self, section, key, updated_value):
        # this will set the value of config[section][key] to updated_value
        if section not in self.__configuration or key not in self.__configuration[section]:
            return False
        self.__configuration[section][key] = updated_value
        return True

    def update_configuration(self, new_config):
        if new_config is None:
            return
        for section in new_config:
            for key in new_config[section]:
                self.set_value(section, key, new_config[section][key])

        self.save()
        print(self.__configuration)

    def get_configuration(self):
        return self.__configuration

configuration = __ConfigurationInfo()
