# -*- coding: utf-8 -*-
# © Ed Pascoe 2011. All rights reserved.
"""Configuration information for raspdf. 
The original version of xxpdf used a broken config file called xmmail.conf. 
For consistency raspdf tries to get its config from the same place.

"""
__author__ = "Ed Pascoe <ed@pascoe.co.za>"
__format__ = "plaintext"
__version__ = "$Id$"
__copyright__ = "Ed Pascoe 2011. All rights reserved."
__license__ = "GNU LGPL version 2"
__status__ = "Production"

from ConfigParser import ParsingError, SafeConfigParser as ConfigParser, NoSectionError
import os, os.path, sys
import logging

log = logging.getLogger("config")

searchLocations = ["images", "templates"]; #Locations to search for files

class RasConfigError(Exception):
  """Thrown on configuration errors"""
class RasConfigNoSuchFileError(RasConfigError):
  """Thrown when fileLocate fails"""

def __appendIfNotExists(value, listobj):
  """Will append directory or file value to the list listobj if it does not already exist"""
  if value not in listobj:
    if os.path.exists(value):
      listobj.append(value)

def _initSearchLocations():
  """Build a list of directories to search for files in."""
  global searchLocations
  #Try build up a fairly detailed list of paths to search for files. 
  searchdirs = []
  curdir = os.path.abspath(os.curdir)
  __appendIfNotExists(curdir, searchdirs) #Always search the current directory first.
  __appendIfNotExists(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'), searchdirs)
  __appendIfNotExists(os.path.dirname(os.path.abspath(sys.argv[0])), searchdirs) #The executable directory.
  if os.path.islink(sys.argv[0]): #If the executable is really a soft link somewhere else.
    __appendIfNotExists(os.path.dirname(os.path.abspath(os.readlink(sys.argv[0]))), searchdirs)
  __appendIfNotExists('/etc', searchdirs) 
  __appendIfNotExists('/usr/local/etc', searchdirs)
  __appendIfNotExists(os.path.join(curdir,'..'), searchdirs)

  destdirs = []
  for d in searchdirs: 
    __appendIfNotExists(d, destdirs) 
    for i in searchLocations: #Expand every search path listed in the original searchLocation with each of the search directories above.
      __appendIfNotExists(os.path.join(d, i), destdirs)
    
  searchLocations = destdirs
  searchLocations.insert(0,'.')

def fileLocate(filename):
  """Search  self.searchLocations for the file name"""
  if filename[0] == '"' and filename[-1] == '"': #Filename has quotes around it which need to be removed.
    filename = filename[1:-1]
  if os.path.exists(filename): 
    return os.path.abspath(filename) #Full path, already exists.
  for d in searchLocations:
    try: 
      fname = os.path.join(d, filename)
    except SyntaxError, e:
      print e
      print d.encode('utf-8')
      print filename.encode('utf-8')
      raise
    if os.path.exists(fname): 
        return fname
  raise RasConfigNoSuchFileError("Could not find filename %s in any of the following directories: %s" % ( filename, " : ".join(searchLocations)))

def get(section, option):
  """Return the requested entry from the xmmail config file."""
  return xmmail.get(section, option)

def get_default(section, option, default=None):
  """As for get but returns default if key does not exist"""
  if xmmail.has_option(section, option):
    return xmmail.get(section, option)
  else:
    return default

def items(section, raw=False, vars=None):
  """Return all entries in given section"""
  try:
    return xmmail.items(section, raw, vars)
  except NoSectionError:
    return []

def getBool(section, option, default=False):
  """Returns a boolean from the config."""
  v = get_default(section,option, None) 
  if v is None:
    return default
  if isinstance(v, basestring): v= v.lower()
  if v == "false" or v == "0" or v == False or v == "no" or v == "off" or v == "disabled":
    return False
  else:
    return True

_initSearchLocations() #Build the search paths for finding files later.

xmmail = ConfigParser()
try:
  xmmail.readfp(file(fileLocate('xmmail.conf')))
except ParsingError: #The original xmmail.conf file has perl extentions which we just ignore.
  print >>sys.stderr, "The format of %s  is too old.\nPlease edit it and change the message option to a single line." % (fileLocate('xmmail.conf'))
  sys.exit(1)
except RasConfigNoSuchFileError:
  print >> sys.stderr, "Could not locate an xmmail.conf file. Please create a file called /etc/xmmail.conf that looks something like:"
  print >> sys.stderr, """[global]
smtpserver = localhost
from = <donotreply@pascoe.co.za>
subject = Generic rascal report
mime = application/octet-stream
filename = report.pdf
message = Your report should be attached.
;Ask for read receipts when sending mail.
readreceipt = True
;use the same broken page size code as xxpdf.
xxpdf = True
"""
  sys.exit(1)

#
#config = ConfigParser.ConfigParser()
#config.read(’example.cfg’)

if __name__ == "__main__":
  print fileLocate("/etc/hosts")
  print fileLocate("passwd")
  print fileLocate("xmmail.conf")
  print get('global','smtpserver')
  print get_default('global','zzzsmtpserver', 'Nope')

