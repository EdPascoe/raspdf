#!/usr/bin/env python
# -*- coding: utf-8 -*-
# © Ed Pascoe 2012. All rights reserved.
"""Wrapper around the main RasPDF library"""
__author__ = "Ed Pascoe <ed@pascoe.co.za>"
__format__ = "plaintext"
__version__ = "$Id$"
__copyright__ = "Ed Pascoe 2012"
__license__ = "BSD"
__status__ = "Production"


import sys
import os, os.path 

#Setup system so we can find the libraries easily.
rd = __file__
while os.path.islink(rd): rd = os.path.abspath(os.readlink(rd))
rd = os.path.abspath(os.path.dirname(rd))
#Try calculate or guess a library path to use.
for d in [ os.path.join(rd, 'lib'), '/rascal/raspdf/lib', '/usr/local/raspdf/lib', '/usr/lib/raspdf' ]:
  if os.path.exists(d) and not d in sys.path:  
    sys.path.append(d)
    break #Use the first path that matches.

try:
  import RasPDF
except ImportError:
  print "Failed to load the main library."
  print "Application root: %s" % (rd)
  print "Looked in the following locations:"
  for d in sys.path: print "   %s" % (d)
  sys.exit(7)
  
try:
  RasPDF.main()
except KeyboardInterrupt:
  sys.exit(1)

#Testing
