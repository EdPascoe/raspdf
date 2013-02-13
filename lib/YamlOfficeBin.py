"""#Temporary hack to use known working copy of Yamloffice until we get the calc bug fixed.
"""

import getopt, sys, os, glob, time, socket, subprocess, os.path, tempfile

#TSF Imports
import types, logging
log = logging.getLogger("YamlOfice")

global convertor, oobin, oobinpath, oolibpath, ooproc
raw = None

class YamlOfficeBinException(Exception):
  """Thrown on Fatal exceptions"""

#WARNING!!! Not threadsafe. Be careful!
def setRaw(rawdata):
  global raw
  raw = rawdata
  

def run(inputData, outputFileName):
  """Used when calling as a library from another module."""
  if raw is None:
    raise YamlOfficeBinException("You need to call setRaw before calling this function")
  inputconf = tempfile.NamedTemporaryFile(suffix='.yml')
  inputconf.write(raw)
  inputconf.flush()
  inputconf.seek(0)
  #Relax the permissions or the libre office backend wont be able to write to the file.
  os.chmod(inputconf.name,0666)
  os.chmod(outputFileName,0666)
  exefile = os.path.join(os.path.dirname(__file__), "yamloffice.bin")
  os.system("%s -o %s < %s" % (exefile, outputFileName, inputconf.name ) )
  inputconf.close()
  return True

