#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# logging
# José Devezas (joseluisdevezas@gmail.com)
# 2018-05-18

import logging


def config_logger():
    logging.basicConfig(
        format='%(asctime)s army-ant: [%(name)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=logging.INFO)