import datetime
import requests
import tomllib
import re
import traceback

import shutil
import os

import json
import yaml
import toml

CONFIG_ADDRESS = "config.toml"

class WeatherData:
    def __init__(self, config_address):
        with open(config_address, 'rb') as f:
            self.config = tomllib.load(f)
            f.close()
        if 'longitude' not in self.config['location'] or 'latitude' not in self.config['location']:
            self.request_location()
        if 'api_key' not in self.config['weather'] or self.config['weather']['api_key'] == "":
            self.find_api_key()
        self.data = { "dt": datetime.datetime.now() }
        self.request_weather_data()

    def find_config_param(self, param: str):
        params = param.split('.')
        out = self.config[params[0]]
        for param in params[1:]:
            out = out[param]
        return str(out)

    def replace_config_params(self, string: str):
        return re.sub(r'{.*?}', lambda s: self.find_config_param(s.group(0)[1:-1]), string)

    def request_api(self, api_config: dict):
        params = api_config['params']
        for key, param in params.items():
            params[key] = self.replace_config_params(param)
        response = requests.get(api_config['url'], params=params)
        if response.status_code != 200:
            traceback.print_stack()
            raise Exception("ERROR: API request failed")
        return response.json()

    def request_location(self):
        location_api_config = self.config['location']['api']
        location = self.request_api(location_api_config)
        self.config['location']['longitude'] = location[location_api_config['longitude_loc']]
        self.config['location']['latitude'] = location[location_api_config['latitude_loc']]

    def find_api_key(self):
        path = self.config['weather']['api_key_path']
        with open(path, 'rb') as f:
            self.config['weather']['api_key'] = str(f.read())[2:-1]
            f.close()

    def request_weather_data(self):
        for key, api_config in self.config['weather']['apis'].items():
            self.data[key] = self.request_api(api_config)
        self.data['dt'] = datetime.datetime.now()

    def get_data(self):
        new_data = {'dt': self.data['dt'].strftime("%Y-%m-%dT%H:%M:%S%z") }
        for key, value in self.data.items():
            if key != 'dt':
                new_data[key] = value
        return new_data

    def to_json(self):
        return json.dumps(self.get_data(), indent=4)

    def to_yaml(self):
        return yaml.dump(self.get_data(), indent=4)

    def to_toml(self):
        return toml.dumps(self.get_data())

    def save(self):
        file_type = self.config['output']['file_type']
        output_dir = self.config['output']['output_dir']
        output_path = os.path.join(output_dir, self.data['dt'].strftime(self.config['output']['file_name']) + '.' + file_type)
        output_string = ""
        if file_type == 'json':
            output_string = self.to_json()
        elif file_type == 'yaml':
            output_string = self.to_yaml()
        elif file_type == 'toml':
            output_string = self.to_toml()
        if os.path.exists(output_dir):
            if self.config['output']['clear_old_data']:
                shutil.rmtree(output_dir)
                os.makedirs(output_dir)
        else:
            os.makedirs(output_dir)

        with open(output_path, 'w') as f:
            f.write(output_string)
            f.close()

if __name__ == "__main__":
    weather_data = WeatherData(CONFIG_ADDRESS)
    weather_data.save()