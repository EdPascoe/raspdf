#!/usr/bin/python
# -*- coding: utf-8 -*-
# © Ed Pascoe 2012. All rights reserved.
"""
Module for handling any YAMLTEMPLATE files.

Autodetects the handler to use. YamlOffice in the case of xls or other spreadsheets.
YamlHtml for html files.

"""
__author__ = "Ed Pascoe <ed@pascoe.co.za>"
__format__ = "plaintext"
__version__ = "$Id$"
__copyright__ = "Ed Pascoe 2011. All rights reserved."
__license__ = "GNU LGPL version 2"
__status__ = "Production"

import yaml, tempfile, os
import logging

log = logging.getLogger()

class YamlTemplateError(Exception):
  """Thrown when the template is valid but can't be used, or there is some other kind of error that
    Cannot be handled.
  """

def run(inputh, output):
  """Imports the yaml document and based on the document type hands the contents over to the correct module
     inputh should be a filehandle to read the yaml data from.
     output should be a filehandle. If it has the .name attrib (eg a NamedTemporaryFile) then this is 
     provided to the YamlHandler to write to. otherwise a temp file is used internally.  
  """
  rawdata = inputh.read()
  documentData = yaml.load(rawdata) #Read in everything from the yaml file and convert to a structure.
  #Only uncomment when doing some really low level debugging.
  #if log.level >= logging.DEBUG:
  #  f=file("/tmp/mytemplate.yml","w")
  #  f.write(rawdata)
  #  f.write("\n\n--------------------------------------------------------------------------\n\n")
  #  f.write(yaml.dump(documentData))
  #  f.close()
  #  os.chmod("/tmp/mytemplate.yml", 0666)
    
  if not documentData.has_key("template"):
      raise YamlTemplateError("The template file is valid YAML but does not have a key called 'template'")
  template = documentData['template']
  fatalException = YamlTemplateError
  if template.endswith("html"):
    import YamlHtml
    yamlHandler = YamlHtml
    fatalException = YamlHtml.YamlHtmlError
  else:    
      import YamlOffice  #Import as late as possible so we don't crash if openoffice is not installed.
      yamlHandler = YamlOffice
      fatalException = YamlOffice.YamlOfficeException
      #The old perl system used this: system("/usr/local/rascalprinting_test/yamloffice -o $t $vvv < $tf");
  try:
    if hasattr(output, 'name'):
      return yamlHandler.run(inputData=documentData, outputFileName=output.name)
    else: #Must be a stringIO buffer. Create a temp file then read it back into the buffer.
      t = tempfile.NamedTemporaryFile(suffix='.pdf')
      ret = yamlHandler.run(inputData=documentData, outputFileName=t.name)
      t.seek(0)
      output.truncate()
      output.write(t.read())
      t.close()
      output.seek(0)
      return ret
  except fatalException, e:
    raise YamlTemplateError(e)

