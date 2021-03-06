#!/usr/bin/env python
#This version of raspdf will run using the default version of python and try to activate itself.
import sys
import os, os.path 

#If this is a softlink to somewhere else we need real file location.
root = os.path.abspath(__file__)
while os.path.islink(root): root = os.readlink(root)
root = os.path.abspath(os.path.dirname(root))

activateloc = os.path.join(root, "ENV/bin/activate_this.py")
if not os.path.exists(activateloc):
  os.system(os.path.join(root,"install.py"))

execfile(activateloc, dict(__file__=activateloc))
sys.path.append(os.path.join(root,'lib'))

import RasPDF
RasPDF.main()
