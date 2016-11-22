#coding: utf-8
import os
import sys
import btsVob

def main():
    bc = btsVob.BtsController()
    bc.process_command(sys.argv[1:])

if __name__ == '__main__':
    main()
