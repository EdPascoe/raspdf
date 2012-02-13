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
import logging

log = logging.getLogger("root")
formatter = logging.Formatter("%(levelname)s %(module)s:%(lineno)d: %(message)s")
output = logging.StreamHandler()
output.setFormatter(formatter)
log.addHandler(output)
log.setLevel(logging.info)

log = logging.getLogger("root")

root = os.path.dirname(os.path.abspath(__file__))
os.chdir(root)
sys.path.append("install")

if env_location[0] == "/":
  destenv = env_location
else:
  destenv = os.path.join(root,env_location)

#Make sure the virtual environment is running.
log.debug("Testing for existance of '%s'", destenv)
if not os.path.exists(destenv):
  import virtualenv
  oldargv = sys.argv  #Save command line options 
  # '--never-download has been removed.
  sys.argv = [sys.argv[0], '--distribute', destenv] #We are going to let virtualenv think it is running on its own.
  log.debug("Calling virtualenv.main (%s)", sys.argv)
  virtualenv.main()
  sys.argv = oldargv #Restore command line options.

pip = os.path.join(destenv, "bin/pip")

cmd= "%s install -v --no-index -r install/requirements.txt --environment=%s" % (pip,  destenv)
log.debug("executing %s", cmd)
os.system(cmd)
if not os.path.exists("raspdf"):
  f=file("raspdf","w")
  f.write( "#!%s\n" % (os.path.join(destenv, "bin/python")) )
  firstline = True
  for line in file("raspdf.dist"):
    if firstline: #Skip the first line because we've already created it.
      firstline = False
      continue
    f.write(line)
  f.close()
  os.chmod("raspdf", 0775 )
