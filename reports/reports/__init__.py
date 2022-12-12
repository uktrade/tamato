import importlib
import os

for name in os.listdir(os.path.dirname(os.path.realpath(__file__))):
    if name.endswith(".py"):
        module = name[:-3]
        importlib.import_module(f"reports.reports.{module}")
