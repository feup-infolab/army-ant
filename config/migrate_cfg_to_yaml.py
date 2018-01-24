#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# migrate_cfg_to_yaml.py
# José Devezas <joseluisdevezas@gmail.com>
# 2018-01-24

import configparser, sys, os
from ruamel.yaml import YAML

def typed_value(v):
    if v == 'True': return True
    if v == 'False': return False

    try:
        return int(v)
    except ValueError:
        try:
            return float(v)
        except ValueError:
            return v

if len(sys.argv) < 3:
    print("Usage: %s <server.cfg> <config.yaml>" % sys.argv[0])
    sys.exit(1)

cfg_path = sys.argv[1]
yaml_path = sys.argv[2]

if os.path.exists(yaml_path):
    ans = input("%s already exists, overwrite? [yN] " % yaml_path)
    if ans.lower() != 'y': sys.exit(1)

config = configparser.ConfigParser(default_section=None)
config.read(cfg_path)

yaml_data = {
    'defaults': {},
    'engines': {}
}

for k in config['DEFAULT']:
    current = yaml_data['defaults']
    parts = k.split('_')
    for i in range(len(parts)):
        if i+1 < len(parts):
            if not parts[i] in current:
                current[parts[i]] = {}
            current = current[parts[i]]
        else:
            current[parts[i]] = typed_value(config['DEFAULT'][k])

for section in config.sections():
    if section == 'DEFAULT': continue

    if config.has_option(section, 'preload'):
        preload = config[section]['preload']
        config.remove_option(section, 'preload')
        config[section]['index_preload'] = preload

    start = yaml_data['engines'][section] = {}
    for k in config[section]:
        current = start
        parts = k.split('_')
        for i in range(len(parts)):
            if i+1 < len(parts):
                if not parts[i] in current:
                    current[parts[i]] = {}
                current = current[parts[i]]
            else:
                current[parts[i]] = typed_value(config[section][k])

if 'db' in yaml_data['defaults'] and not 'name' in yaml_data['defaults']['db']:
    yaml_data['defaults']['db']['name'] = 'army_ant'

yaml = YAML()
with open(yaml_path, 'w') as f:
    yaml.dump(yaml_data, f)
