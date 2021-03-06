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

from ConfigParser import ParsingError, SafeConfigParser as ConfigParser, NoSectionError, NoOptionError
import os, os.path, sys
import logging

xmmail = {}

log = logging.getLogger("config")

searchLocations = ["images", "templates"]; #Locations to search for files

class RascalPDFException(Exception):
   """The base exception for any fatal RasPDF error"""

class RasConfigError(RascalPDFException):
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

def get(section, option, default=None):
  """Return the requested entry from the xmmail config file."""
  try:
    return xmmail.get(section, option)
  except NoOptionError:
    if default is not None: 
      return default
    else:
      raise

def get_default(section, option, default=None):
  """As for get but returns default if key does not exist"""
  if xmmail.has_option(section, option):
    return xmmail.get(section, option)
  else:
    return default

def set(section, option, value):
  """"Set the given option in the given section"""
  xmmail.set(section, option, str(value))

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
  if v == "false" or v == "0" or v == False or v == "no" or v == "off" or v == "disabled" or v == "None":
    return False
  else:
    return True

_initSearchLocations() #Build the search paths for finding files later.

def load(configfile='xmmail.conf', defaults={'smtpserver': '127.0.0.1', 'templates:':'/rascal/templates', 'filename': 'report.pdf'} ):
  global xmmail
  assert hasattr(defaults, 'items') #defaults MUST be a dict.
  #log.debug("load: Defaults: %s Type: %s", defaults, type(defaults))
  log.debug("Config file: %s", fileLocate(configfile))
  xmmail = ConfigParser(defaults)
  try:
    xmmail.readfp(file(fileLocate(configfile)))
  except ParsingError:  #The original xmmail.conf file has perl extentions which we just ignore.
    print >>sys.stderr, "The format of %s  is too old.\nPlease edit it and change the message option to a single line." % (fileLocate(configfile))
    sys.exit(1)
  except RasConfigNoSuchFileError:
    print >> sys.stderr, "Could not locate an %s file. Please create a file called /etc/%s that looks something like:" % (configfile, configfile)
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
  templates = '/rascal/templates'
  """ 
  rascfg = get('global','rascalcfg','rascal.cfg')
  if os.path.exists(rascfg):
    for line in file(rascfg):
      line=line.strip()
      if len(line) == 0  or line[0] == "#" or line[0] == ';': continue #Skip comments and blank lines.
      p = list( [ x.strip() for x in line.split('=',1) ] )
      if len(p) == 1: continue #We can't handle single words
      xmmail.set('global', p[0].lower(), p[1]) #Rascal has a creepy obsession with uppercase variables.


  templates =  get('global', 'templates', default='')
  destdirs = []
  for d in templates.split(":"): 
    d = d.strip()
    __appendIfNotExists(d, searchLocations) 

if __name__ == "__main__":
  #Enable logging
  formatter = logging.Formatter("%(levelname)s %(module)s:%(lineno)d: %(message)s")
  output = logging.StreamHandler()
  output.setFormatter(formatter)
  log.addHandler(output)
  log.setLevel(logging.DEBUG)

  load()
  print fileLocate("/etc/hosts")
  print fileLocate("passwd")
  print fileLocate("xmmail.conf")
  print get('global','smtpserver')
  print get('global','zzzsmtpserver', 'Nope')
  print get('global','azzzsmtpserver' , False)
  print get('global','templates' , False)
  print get('global','SERVER' , False)
  print "searchLocations: ", searchLocations


