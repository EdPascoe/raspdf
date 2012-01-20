#!/usr/bin/env python
# -*- coding: utf-8 -*-
# © Ed Pascoe 2012. All rights reserved.
"""
Setup the environment so that raspdf can work.
"""
__author__ = "Ed Pascoe <ed@pascoe.co.za>"
__format__ = "plaintext"
__version__ = "$Id$"
__copyright__ = "Ed Pascoe 2012"
__license__ = "BSD"
__status__ = "Production"

env_location="ENV" #Python environment. If does not start with / will be relative to location of install.py

import os, os.path, sys

root = os.path.dirname(os.path.abspath(__file__))
os.chdir(root)
sys.path.append("install")

if env_location[0] == "/":
  destenv = env_location
else:
  destenv = os.path.join(root,env_location)

#Make sure the virtual environment is running.
if not os.path.exists(destenv):
  import virtualenv
  oldargv = sys.argv  #Save command line options
  sys.argv = [sys.argv[0], '--never-download', '--distribute', destenv] #We are going to let virtualenv think it is running on its own.
  virtualenv.main()
  sys.argv = oldargv #Restore command line options.

pip = os.path.join(destenv, "bin/pip")

cmd= "%s install -v --no-index -r install/requirements.txt --environment=%s" % (pip,  destenv)
print cmd
os.system(cmd)

