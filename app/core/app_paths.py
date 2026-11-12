# -*- coding: utf-8 -*-
"""运行路径：区分只读程序资源和可写的用户运行数据。"""
import os
import sys


def _source_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def resource_root():
    """PyInstaller 打包后的资源根目录；源码运行时为项目根目录。"""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
    return _source_root()


def runtime_root():
    """可写运行数据的根目录；打包后始终位于 exe 同级。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return _source_root()


def asset_path(*parts):
    return os.path.join(resource_root(), "assets", *parts)


def data_dir():
    return os.path.join(runtime_root(), "data")
