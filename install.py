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

env_location = "ENV" #Python environment. If does not start with / will be relative to location of install.py

import os, os.path, sys
import logging
import distutils.sysconfig

log = logging.getLogger("root")
formatter = logging.Formatter("%(levelname)s %(module)s:%(lineno)d: %(message)s")
output = logging.StreamHandler()
output.setFormatter(formatter)
log.addHandler(output)
log.setLevel(logging.DEBUG)

log = logging.getLogger("root")

root = os.path.dirname(os.path.abspath(__file__))
os.chdir(root)
sys.path.append("install")

if env_location[0] == "/":
  destenv = env_location
else:
  destenv = os.path.join(root, env_location)

#Make sure the virtual environment is running.
log.debug("Testing for existance of '%s'", destenv)
if not os.path.exists(destenv):
  log.debug("Calling virtualenv.main (%s)", sys.argv)
  os.system("install/virtualenv.py --distribute --never-download '%s'" % (destenv))
headerfile=os.path.join(distutils.sysconfig.get_python_inc(),"Python.h")
if not os.path.exists(headerfile):
  print "You are missing the python development package. Please reinstall and re-run."
  print "Under Redhat or Centos the package is called python-devel. Try: yum install python-devel"
  print "Under Ubunutu or Debian the package is called: python-dev. Try: apt-get install python-dev"
  print "Aborting until the file %s exists" % (headerfile)
  sys.exit(1)

pip = os.path.join(destenv, "bin/pip")

#Sigh. Some companies ( *cough* Cummins *cough) have political/corporate stupididty issues preventing them from running anything newer than RHES5 which means python 2.4 only.
#This allows us to customise the requirements for older versions of python.
requirements_file = "install/requirements.%s.%s.txt" % (sys.version_info.major, sys.version_info.minor)
if not os.path.exists(requirements_file):
  requirements_file = "install/requirements.txt"


#cmd = "%s install -v --no-index -r install/requirements.txt --environment=%s" % (pip, destenv) #TODO: --environment seems to not be supported in some versions of pip ???
cmd = "%s install -v --no-index -r install/requirements.txt" % (pip)
log.debug("executing %s", cmd)
os.system(cmd)
#TODO: need command line arguments to choose what is needed during the install
if os.path.exists("raspdf"):
  try: 
    os.unlink("raspdf")
  except Exception, e:
    print "Failed to remove the old raspdf file. %s" % (e)
    print "Aborting!!!"
    sys.exit(1)

f = file("raspdf", "w")
f.write("#!%s\n" % (os.path.join(destenv, "bin/python")))
firstline = True
for line in file("raspdf.dist.py"):
  if firstline: #Skip the first line because we've already created it.
    firstline = False
    continue
  f.write(line)
f.close()
os.chmod("raspdf", 0775)
