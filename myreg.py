#!/usr/bin/env python3
import os
import json
import tempfile

REG_PATH = r"SOFTWARE\Scheduler\Settings"


file_name = tempfile.gettempdir()+ '\\registry.json'
winreg = None

class Processor:
    def set_reg(self, name, value, type='json'):
        return self._get_instance(type).set_reg(name, value)
    def get_reg(self, name, type='json'):
        return self._get_instance(type).get_reg(name)
    def get_reg_all(self, type='json'):
        return self._get_instance(type).get_reg_all()
    def _get_instance(self, type='json'):
        global winreg
        if os.name is 'nt' and type != 'json':   
            import winreg

            return WinRegProcessor()
        else:
            return JsonProcessor()


class WinRegProcessor:
    def set_reg(self, name, value):
        try:            
            registry_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH)
            if isinstance(value, str):
                winreg.SetValueEx(registry_key, name, 0, winreg.REG_SZ, value)
            else:
                winreg.SetValueEx(registry_key, name, 0, winreg.REG_DWORD, value)
            winreg.CloseKey(registry_key)
            return True
        except OSError:
            return False

    def get_reg(self, name):
        try:
            registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ)
            value, regtype = winreg.QueryValueEx(registry_key, name)
            winreg.CloseKey(registry_key)
            return value
        except OSError:
            return None

    def get_reg_all(self):
        try:
            #TODO: Should be implemented
            return None
        except OSError:
            return None


class JsonProcessor:
    def set_reg(self, name, value):
        data = self._read_file(file_name)
        if not data:
            details = {}
            details[name] = value
            with open(file_name, 'w+') as json_file:
                json.dump(details, json_file)
        else:
            data[name] = value
            with open(file_name, 'w+') as json_file:
                json.dump(data, json_file)

    def get_reg(self, name):
        data = self._read_file(file_name)
        if data and name in data:
            return data[name]
        return None

    def get_reg_all(self):
        data = self._read_file(file_name)
        if data:
            return data
        return None

    def _read_file(self, file_name):
        try:
            with open(file_name) as json_file:
                data = json.load(json_file)
                if data:
                    return data
        except Exception as e:
            pass

        return None


##############################################
#
#   Private Methods
#
##############################################

def _set_reg(name, value):
    p = Processor()
    return p.set_reg(name, value)

def _get_reg(name):
    p = Processor()
    return p.get_reg(name)

def _get_reg_all():
    p = Processor()
    return p.get_reg_all()


##############################################
#
#   Public Methods
#
##############################################

def get_value(key):
    return _get_reg(key)

def set_value(key, value):
    return _set_reg(key, value)    