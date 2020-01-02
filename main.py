# -*- coding: utf-8 -*-
import sys

sys.path.insert(0, 'py12306')


def main():
    version_check()
    from app.app import App
    App.start_run_loop()


def version_check():
    if sys.version_info.major < 3 or sys.version_info.minor < 6:
        sys.exit('# Pleause use a python version that must equal to or greater than 3.6 #')


if __name__ == '__main__':
    main()
