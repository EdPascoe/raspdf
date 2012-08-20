#!/usr/bin/python
# -*- coding: utf-8 -*-
# © Ed Pascoe 2012. All rights reserved.
"""
Module for handling any YAMLTEMPLATE html files.
Uses calls to mkhtmltopdf 

"""
__author__ = "Ed Pascoe <ed@pascoe.co.za>"
__format__ = "plaintext"
__version__ = "$Id$"
__copyright__ = "Ed Pascoe 2011. All rights reserved."
__license__ = "GNU LGPL version 2"
__status__ = "Production"

import sys, os, os.path
import jinja2, jinja2.exceptions
import threading 
import tempfile
import RasConfig
import logging
log = logging.getLogger()

renderLock = threading.Lock() #Incase this module is ever used in a multithreaded environment.


templatedirectories = []
loader = jinja2.ChoiceLoader
environment = jinja2.environment



def updateTemplateLocations(relativeto=None, locations=["../etc/templates", "../etc", "..", "."], deleteOld=False):
  """Update the locations to search for templates.  If deleteOld is true then any exiting locations are removed.
  Each entry in the list locations is added and if relativeto is not none they are made relative to this location. 
  """
  global templatedirectories
  with renderLock:
    if deleteOld == True:
      templatedirectories = []
    if isinstance(locations, str) or isinstance(locations, unicode): #Convert to a list if a single directory is given.
      locations = [locations, ]
    for l in locations:
      if relativeto and l[0] != "/": #Fully qualified locations are not made relative.
        l = os.path.join(relativeto, l)
      if not l in templatedirectories:
        templatedirectories.append(os.path.abspath(l))


def getJinjaEnvironment(*templatefilelocations): 
  #--------- Build the Loader Object -----
  
  cloc = list([jinja2.FileSystemLoader(x) for x in templatedirectories])
  for location in templatefilelocations:
    cloc.append(jinja2.FileSystemLoader(location))
    
  loader = jinja2.loaders.ChoiceLoader(cloc) #Choice loader
  return  jinja2.Environment(loader=loader, undefined=jinja2.StrictUndefined)  #Comment out to stop undefineds throwing exeption:, undefined=jinja2.StrictUndefined)

def run(inputData, outputFileName):
  """Used when calling as a library from another module.
     inputData should be a dictionary containing at the least:
        a key called 'template' pointing to the jinja template to use.
        a key called 'data' which itself should be a dictionary of values to use.
     PDF will be written to outputFileName
  """

  templatefilename = inputData['template']
  templated = os.path.dirname(inputData['template'])
  templatef = os.path.basename(inputData['template'])
  inputData['data']['static'] = templated #To path relative file locations
  #curdir = os.path.abspath(os.curdir)
  #os.chdir(templated) #We need to change to the directory holding the base html file so that relative paths work.
  #sys.stderr.write("New dir: '%s" % (templated))
  #Create a jinja template
  td = RasConfig.get('global','templates','/rascal/templates')
  td = [ x.strip() for x in str(td).split(',')] #Convert the comma separated list of 
  
  updateTemplateLocations(os.path.dirname(__file__),['.','..','/etc'] + td)
  env = getJinjaEnvironment(templated)
  if templatefilename[0] == "/": #Is an absolute file location
    template = env.get_template(templatef)
  else:
    template = env.get_template(templatefilename)
  inputData['data']['SRC'] = os.path.dirname(template.filename) #Relative paths won't work because we are dealing with temp files.
  
  tempInput = tempfile.NamedTemporaryFile(suffix='.html')
  tempInput.write(template.render(**inputData['data'])) #Render the template to pure html.
  tempInput.flush()
  #tempInput.seek(0); print tempInput.read() #Uncomment for debugging.
  
  wkpdfHandle=os.system("wkhtmltopdf -q '%s' '%s' 2>/dev/null " % (tempInput.name, outputFileName))
  #os.chdir(curdir)
  return True
  

if __name__ == "__main__": #For testing only.
  import yaml
  data = yaml.load(file("/home/elp/workspace/raspdf/testdocs/thermo-datasheet.yml").read())
  
  run(data, sys.stdin)
  
  
  
