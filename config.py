# coding=utf-8
import logging
import sys
import os
import logging.config


def cur_file_dir():
    path = sys.path[0]
    if os.path.isdir(path):
        return path
    elif os.path.isfile(path):
        return os.path.dirname(path)


klazz_path = cur_file_dir()
sys.path.append(klazz_path)
logging.config.fileConfig(os.path.join(klazz_path, 'logging.ini'))
