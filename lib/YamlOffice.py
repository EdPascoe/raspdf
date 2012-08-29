#!/usr/bin/python
# -*- coding: utf-8 -*-
# © Ed Pascoe 2012. All rights reserved.
"""
Module for handling yamloffice documents. Replaces the yamloffice binary in the
old perl xxpdf printing system.

Given a yaml file will attempt to contact a running python openoffice converter process (unoconv)
and ask that process to open the template file specified by the yaml file.
Data supplied in the yml file will be used to update the document.
Finally the document will be  converted into a new format (by default PDF) and
saved as sent to stdout.

The actual pyuno part of this program is a straight copy of  Dag Wieers's unoconv
"""
__author__ = "Ed Pascoe <ed@pascoe.co.za>"
__format__ = "plaintext"
__version__ = "$Id$"
__copyright__ = "Ed Pascoe 2011. All rights reserved."
__license__ = "GNU LGPL version 2"
__status__ = "Production"


### This program is free software; you can redistribute it and/or modify
### it under the terms of the GNU General Public License as published by
### the Free Software Foundation; version 2 only
###
### This program is distributed in the hope that it will be useful,
### but WITHOUT ANY WARRANTY; without even the implied warranty of
### MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
### GNU General Public License for more details.
###
### You should have received a copy of the GNU General Public License
### along with this program; if not, write to the Free Software
### Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
### Copyright 2007-2010 Dag Wieers <dag@wieers.com>

import getopt, sys, os, glob, time, socket, subprocess

#TSF Imports
import types, logging
log = logging.getLogger("YamlOfice")

global convertor, oobin, oobinpath, oolibpath, ooproc

class YamlOfficeException(Exception):
  """Thrown on Fatal exceptions"""

### The first thing we ought to do is find a suitable OpenOffice installation
### with a compatible pyuno library that we can import.
extrapaths = glob.glob('/usr/lib*/openoffice*/program') + \
             glob.glob('/usr/lib*/openoffice*/basis*/program') + \
             glob.glob('/usr/lib*/ooo*/program') + \
             glob.glob('/usr/lib*/ooo*/basis*/program') + \
             glob.glob('/usr/local/openoffice*/program') + \
             glob.glob('/usr/local/openoffice*/basis*/program') + \
             glob.glob('/usr/local/ooo*/program') + \
             glob.glob('/usr/local/ooo*/basis*/program') + \
             glob.glob('/opt/openoffice*/program') + \
             glob.glob('/opt/openoffice*/basis*/program') + \
             glob.glob('/Applications/OpenOffice.org.app/Contents/program') + \
             glob.glob('/Applications/OpenOffice.org.app/Contents/basis-link/program') + \
             glob.glob('/Applications/NeoOffice.app/Contents/program') + \
             glob.glob('/Applications/NeoOffice.app/Contents/basis-link/program') + \
             glob.glob('/usr/bin') + \
             glob.glob('/usr/local/bin') + \
             glob.glob('/opt/bin')

if 'ProgramFiles' in os.environ.keys():
  extrapaths += glob.glob(os.environ['ProgramFiles'] + '\\OpenOffice.org*\\URE\\bin') + \
                glob.glob(os.environ['ProgramFiles'] + '\\OpenOffice.org*\\program') + \
                glob.glob(os.environ['ProgramFiles'] + '\\OpenOffice.org*\\Basis*\\program')

if 'ProgramFiles(x86)' in os.environ.keys():
  extrapaths += glob.glob(os.environ['ProgramFiles(x86)'] + '\\OpenOffice.org*\\URE\\bin') + \
                glob.glob(os.environ['ProgramFiles(x86)'] + '\\OpenOffice.org*\\program') + \
                glob.glob(os.environ['ProgramFiles(x86)'] + '\\OpenOffice.org*\\Basis*\\program')

binaries = ('soffice.bin', 'soffice', 'soffice.exe')

try:
  import uno, unohelper
except ImportError:
  for oolibpath in extrapaths:
    if os.path.exists(os.path.join(oolibpath, "pyuno.so")):
      filename = "pyuno.so"
    elif os.path.exists(os.path.join(oolibpath, "pyuno.pyd")):
      filename = "pyuno.pyd"
    else:
      continue
    try:
      sys.path.append(oolibpath)
      import uno, unohelper
      ### Export an environment that OpenOffice is pleased to work with
      os.environ['LD_LIBRARY_PATH'] = oolibpath + os.pathsep + os.environ['LD_LIBRARY_PATH']
      break
    except ImportError, e:
      sys.path.remove(oolibpath)
      print >> sys.stderr, e
      print >> sys.stderr, "WARNING: Found %s in %s, but could not import it." % (filename, oolibpath)
      continue
  else:
    print >> sys.stderr, "unoconv: Cannot find the pyuno library in sys.path and known paths."
    print >> sys.stderr, "ERROR: Please locate this library and send your feedback to: <tools@lists.rpmforge.net>."
    sys.exit(1)

oobin = None
for oobinpath in extrapaths:
  for binary in binaries:
    bin = os.path.join(oobinpath, binary)
    if os.path.exists(bin):
      sys.path.append(oobinpath)
      oobin = bin
      break
  if oobin:
    break
else:
  print >> sys.stderr, "unoconv: Cannot find the soffice binary in sys.path and known paths."
  print >> sys.stderr, "ERROR: Please locate this binary and send your feedback to: <tools@lists.rpmforge.net>."
  sys.exit(1)

### Export an environment that OpenOffice is pleased to work with
os.environ['PATH'] = oobinpath + os.pathsep + os.environ['PATH']

### Now that we have found a working pyuno library, let's import some classes
from com.sun.star.beans import PropertyValue
from com.sun.star.connection import NoConnectException
from com.sun.star.lang import DisposedException
from com.sun.star.io import IOException, XOutputStream
from com.sun.star.script import CannotConvertException
from com.sun.star.uno import Exception as UnoException

__version__ = "$Revision$"
# $Source$

VERSION = '0.4'

doctypes = ('document', 'graphics', 'presentation', 'spreadsheet')

ooproc = None
exitcode = 0

class Fmt:
  def __init__(self, doctype, name, extension, summary, filter):
    self.doctype = doctype
    self.name = name
    self.extension = extension
    self.summary = summary
    self.filter = filter

  def __str__(self):
    return "%s [.%s]" % (self.summary, self.extension)

  def __repr__(self):
    return "%s/%s" % (self.name, self.doctype)

class FmtList:
  def __init__(self):
    self.list = []

  def add(self, doctype, name, extension, summary, filter):
    self.list.append(Fmt(doctype, name, extension, summary, filter))

  def byname(self, name):
    ret = []
    for fmt in self.list:
      if fmt.name == name:
        ret.append(fmt)
    return ret

  def byextension(self, extension):
    ret = []
    for fmt in self.list:
      if os.extsep + fmt.extension == extension:
        ret.append(fmt)
    return ret

  def bydoctype(self, doctype, name):
    ret = []
    for fmt in self.list:
      if fmt.name == name and fmt.doctype == doctype:
        ret.append(fmt)
    return ret

  def display(self, doctype):
    print >> sys.stderr, "The following list of %s formats are currently available:\n" % doctype
    for fmt in self.list:
      if fmt.doctype == doctype:
        print >> sys.stderr, "  %-8s - %s" % (fmt.name, fmt)
    print >> sys.stderr

class OutputStream(unohelper.Base, XOutputStream):
  def __init__(self):
    self.closed = 0

  def closeOutput(self):
    self.closed = 1

  def writeBytes(self, seq):
    sys.stdout.write(seq.value)

  def flush(self):
    pass

fmts = FmtList()

#oFF = createUnoService( "com.sun.star.document.FilterFactory" )
#oFilterNames = oFF.getElementNames()

### TextDocument
fmts.add('document', 'bib', 'bib', 'BibTeX', 'BibTeX_Writer') ### 22
fmts.add('document', 'doc', 'doc', 'Microsoft Word 97/2000/XP', 'MS Word 97') ### 29
fmts.add('document', 'doc6', 'doc', 'Microsoft Word 6.0', 'MS WinWord 6.0') ### 24
fmts.add('document', 'doc95', 'doc', 'Microsoft Word 95', 'MS Word 95') ### 28
fmts.add('document', 'docbook', 'xml', 'DocBook', 'DocBook File') ### 39
fmts.add('document', 'html', 'html', 'HTML Document (OpenOffice.org Writer)', 'HTML (StarWriter)') ### 3
fmts.add('document', 'odt', 'odt', 'ODF Text Document', 'writer8') ### 10
fmts.add('document', 'ott', 'ott', 'Open Document Text', 'writer8_template') ### 21
fmts.add('document', 'ooxml', 'xml', 'Microsoft Office Open XML', 'MS Word 2003 XML') ### 11
#fmts.add('document', 'pdb', 'pdb', 'AportisDoc (Palm)', 'AportisDoc Palm DB')
fmts.add('document', 'pdf', 'pdf', 'Portable Document Format', 'writer_pdf_Export') ### 18
#fmts.add('document', 'psw', 'psw', 'Pocket Word', 'PocketWord File')
fmts.add('document', 'rtf', 'rtf', 'Rich Text Format', 'Rich Text Format') ### 16
fmts.add('document', 'latex', 'ltx', 'LaTeX 2e', 'LaTeX_Writer') ### 31
fmts.add('document', 'sdw', 'sdw', 'StarWriter 5.0', 'StarWriter 5.0') ### 23
fmts.add('document', 'sdw4', 'sdw', 'StarWriter 4.0', 'StarWriter 4.0') ### 2
fmts.add('document', 'sdw3', 'sdw', 'StarWriter 3.0', 'StarWriter 3.0') ### 20
fmts.add('document', 'stw', 'stw', 'Open Office.org 1.0 Text Document Template', 'writer_StarOffice_XML_Writer_Template') ### 9
fmts.add('document', 'sxw', 'sxw', 'Open Office.org 1.0 Text Document', 'StarOffice XML (Writer)') ### 1
fmts.add('document', 'text', 'txt', 'Text Encoded', 'Text (encoded)') ### 26
fmts.add('document', 'mediawiki', 'txt', 'MediaWiki', 'MediaWiki')
fmts.add('document', 'txt', 'txt', 'Text', 'Text') ### 34
fmts.add('document', 'uot', 'uot', 'Unified Office Format text', 'UOF text') ### 27
fmts.add('document', 'vor', 'vor', 'StarWriter 5.0 Template', 'StarWriter 5.0 Vorlage/Template') ### 6
fmts.add('document', 'vor4', 'vor', 'StarWriter 4.0 Template', 'StarWriter 4.0 Vorlage/Template') ### 5
fmts.add('document', 'vor3', 'vor', 'StarWriter 3.0 Template', 'StarWriter 3.0 Vorlage/Template') ### 4
fmts.add('document', 'xhtml', 'html', 'XHTML Document', 'XHTML Writer File') ### 33

### WebDocument
fmts.add('web', 'html', 'html', 'HTML Document', 'HTML') ### 2
fmts.add('web', 'sdw3', 'sdw', 'StarWriter 3.0 (OpenOffice.org Writer/Web)', 'StarWriter 3.0 (StarWriter/Web)') ### 3
fmts.add('web', 'sdw4', 'sdw', 'StarWriter 4.0 (OpenOffice.org Writer/Web)', 'StarWriter 4.0 (StarWriter/Web)') ### 4
fmts.add('web', 'sdw', 'sdw', 'StarWriter 5.0 (OpenOffice.org Writer/Web)', 'StarWriter 5.0 (StarWriter/Web)') ### 5
fmts.add('web', 'vor4', 'vor', 'StarWriter/Web 4.0 Template', 'StarWriter/Web 4.0 Vorlage/Template') ### 6
fmts.add('web', 'vor', 'vor', 'StarWriter/Web 5.0 Template', 'StarWriter/Web 5.0 Vorlage/Template') ### 7
fmts.add('web', 'text', 'txt', 'Text (OpenOffice.org Writer/Web)', 'Text (StarWriter/Web)') ### 8
fmts.add('web', 'mediawiki', 'txt', 'MediaWiki', 'MediaWiki_Web') ### 9
fmts.add('web', 'pdf', 'pdf', 'PDF - Portable Document Format', 'writer_web_pdf_Export') ### 10
fmts.add('web', 'html10', 'html', 'OpenOffice.org 1.0 HTML Template', 'writer_web_StarOffice_XML_Writer_Web_Template') ### 11
fmts.add('web', 'txt', 'txt', 'OpenOffice.org Text (OpenOffice.org Writer/Web)', 'writerweb8_writer') ### 12
fmts.add('web', 'html', 'html', 'HTML Document Template', 'writerweb8_writer_template') ### 13
fmts.add('web', 'etext', 'txt', 'Text Encoded (OpenOffice.org Writer/Web)', 'Text (encoded) (StarWriter/Web)') ### 14
fmts.add('web', 'text10', 'txt', 'OpenOffice.org 1.0 Text Document (OpenOffice.org Writer/Web)', 'writer_web_StarOffice_XML_Writer') ### 15

### Spreadsheet
fmts.add('spreadsheet', 'csv', 'csv', 'Text CSV', 'Text - txt - csv (StarCalc)') ### 16
fmts.add('spreadsheet', 'dbf', 'dbf', 'dBASE', 'dBase') ### 22
fmts.add('spreadsheet', 'dif', 'dif', 'Data Interchange Format', 'DIF') ### 5
fmts.add('spreadsheet', 'html', 'html', 'HTML Document (OpenOffice.org Calc)', 'HTML (StarCalc)') ### 7
fmts.add('spreadsheet', 'ods', 'ods', 'ODF Spreadsheet', 'calc8') ### 15
fmts.add('spreadsheet', 'ooxml', 'xml', 'Microsoft Excel 2003 XML', 'MS Excel 2003 XML') ### 23
fmts.add('spreadsheet', 'ots', 'ots', 'ODF Spreadsheet Template', 'calc8_template') ### 14
fmts.add('spreadsheet', 'pdf', 'pdf', 'Portable Document Format', 'calc_pdf_Export') ### 34
#fmts.add('spreadsheet', 'pxl', 'pxl', 'Pocket Excel', 'Pocket Excel')
fmts.add('spreadsheet', 'sdc', 'sdc', 'StarCalc 5.0', 'StarCalc 5.0') ### 31
fmts.add('spreadsheet', 'sdc4', 'sdc', 'StarCalc 4.0', 'StarCalc 4.0') ### 11
fmts.add('spreadsheet', 'sdc3', 'sdc', 'StarCalc 3.0', 'StarCalc 3.0') ### 29
fmts.add('spreadsheet', 'slk', 'slk', 'SYLK', 'SYLK') ### 35
fmts.add('spreadsheet', 'stc', 'stc', 'OpenOffice.org 1.0 Spreadsheet Template', 'calc_StarOffice_XML_Calc_Template') ### 2
fmts.add('spreadsheet', 'sxc', 'sxc', 'OpenOffice.org 1.0 Spreadsheet', 'StarOffice XML (Calc)') ### 3
fmts.add('spreadsheet', 'uos', 'uos', 'Unified Office Format spreadsheet', 'UOF spreadsheet') ### 9
fmts.add('spreadsheet', 'vor3', 'vor', 'StarCalc 3.0 Template', 'StarCalc 3.0 Vorlage/Template') ### 18
fmts.add('spreadsheet', 'vor4', 'vor', 'StarCalc 4.0 Template', 'StarCalc 4.0 Vorlage/Template') ### 19
fmts.add('spreadsheet', 'vor', 'vor', 'StarCalc 5.0 Template', 'StarCalc 5.0 Vorlage/Template') ### 20
fmts.add('spreadsheet', 'xhtml', 'xhtml', 'XHTML', 'XHTML Calc File') ### 26
fmts.add('spreadsheet', 'xls', 'xls', 'Microsoft Excel 97/2000/XP', 'MS Excel 97') ### 12
fmts.add('spreadsheet', 'xls5', 'xls', 'Microsoft Excel 5.0', 'MS Excel 5.0/95') ### 8
fmts.add('spreadsheet', 'xls95', 'xls', 'Microsoft Excel 95', 'MS Excel 95') ### 10
fmts.add('spreadsheet', 'xlt', 'xlt', 'Microsoft Excel 97/2000/XP Template', 'MS Excel 97 Vorlage/Template') ### 6
fmts.add('spreadsheet', 'xlt5', 'xlt', 'Microsoft Excel 5.0 Template', 'MS Excel 5.0/95 Vorlage/Template') ### 28
fmts.add('spreadsheet', 'xlt95', 'xlt', 'Microsoft Excel 95 Template', 'MS Excel 95 Vorlage/Template') ### 21

### Graphics
fmts.add('graphics', 'bmp', 'bmp', 'Windows Bitmap', 'draw_bmp_Export') ### 21
fmts.add('graphics', 'emf', 'emf', 'Enhanced Metafile', 'draw_emf_Export') ### 15
fmts.add('graphics', 'eps', 'eps', 'Encapsulated PostScript', 'draw_eps_Export') ### 48
fmts.add('graphics', 'gif', 'gif', 'Graphics Interchange Format', 'draw_gif_Export') ### 30
fmts.add('graphics', 'html', 'html', 'HTML Document (OpenOffice.org Draw)', 'draw_html_Export') ### 37
fmts.add('graphics', 'jpg', 'jpg', 'Joint Photographic Experts Group', 'draw_jpg_Export') ### 3
fmts.add('graphics', 'met', 'met', 'OS/2 Metafile', 'draw_met_Export') ### 43
fmts.add('graphics', 'odd', 'odd', 'OpenDocument Drawing', 'draw8') ### 6
fmts.add('graphics', 'otg', 'otg', 'OpenDocument Drawing Template', 'draw8_template') ### 20
fmts.add('graphics', 'pbm', 'pbm', 'Portable Bitmap', 'draw_pbm_Export') ### 14
fmts.add('graphics', 'pct', 'pct', 'Mac Pict', 'draw_pct_Export') ### 41
fmts.add('graphics', 'pdf', 'pdf', 'Portable Document Format', 'draw_pdf_Export') ### 28
fmts.add('graphics', 'pgm', 'pgm', 'Portable Graymap', 'draw_pgm_Export') ### 11
fmts.add('graphics', 'png', 'png', 'Portable Network Graphic', 'draw_png_Export') ### 2
fmts.add('graphics', 'ppm', 'ppm', 'Portable Pixelmap', 'draw_ppm_Export') ### 5
fmts.add('graphics', 'ras', 'ras', 'Sun Raster Image', 'draw_ras_Export') ## 31
fmts.add('graphics', 'std', 'std', 'OpenOffice.org 1.0 Drawing Template', 'draw_StarOffice_XML_Draw_Template') ### 53
fmts.add('graphics', 'svg', 'svg', 'Scalable Vector Graphics', 'draw_svg_Export') ### 50
fmts.add('graphics', 'svm', 'svm', 'StarView Metafile', 'draw_svm_Export') ### 55
fmts.add('graphics', 'swf', 'swf', 'Macromedia Flash (SWF)', 'draw_flash_Export') ### 23
fmts.add('graphics', 'sxd', 'sxd', 'OpenOffice.org 1.0 Drawing', 'StarOffice XML (Draw)') ### 26
fmts.add('graphics', 'sxd3', 'sxd', 'StarDraw 3.0', 'StarDraw 3.0') ### 40
fmts.add('graphics', 'sxd5', 'sxd', 'StarDraw 5.0', 'StarDraw 5.0') ### 44
fmts.add('graphics', 'tiff', 'tiff', 'Tagged Image File Format', 'draw_tif_Export') ### 13
fmts.add('graphics', 'vor', 'vor', 'StarDraw 5.0 Template', 'StarDraw 5.0 Vorlage') ### 36
fmts.add('graphics', 'vor3', 'vor', 'StarDraw 3.0 Template', 'StarDraw 3.0 Vorlage') ### 35
fmts.add('graphics', 'wmf', 'wmf', 'Windows Metafile', 'draw_wmf_Export') ### 8
fmts.add('graphics', 'xhtml', 'xhtml', 'XHTML', 'XHTML Draw File') ### 45
fmts.add('graphics', 'xpm', 'xpm', 'X PixMap', 'draw_xpm_Export') ### 19

### Presentation
fmts.add('presentation', 'bmp', 'bmp', 'Windows Bitmap', 'impress_bmp_Export') ### 15
fmts.add('presentation', 'emf', 'emf', 'Enhanced Metafile', 'impress_emf_Export') ### 16
fmts.add('presentation', 'eps', 'eps', 'Encapsulated PostScript', 'impress_eps_Export') ### 17
fmts.add('presentation', 'gif', 'gif', 'Graphics Interchange Format', 'impress_gif_Export') ### 18
fmts.add('presentation', 'html', 'html', 'HTML Document (OpenOffice.org Impress)', 'impress_html_Export') ### 43
fmts.add('presentation', 'jpg', 'jpg', 'Joint Photographic Experts Group', 'impress_jpg_Export') ### 19
fmts.add('presentation', 'met', 'met', 'OS/2 Metafile', 'impress_met_Export') ### 20
fmts.add('presentation', 'odg', 'odg', 'ODF Drawing (Impress)', 'impress8_draw') ### 29
fmts.add('presentation', 'odp', 'odp', 'ODF Presentation', 'impress8') ### 9
fmts.add('presentation', 'otp', 'otp', 'ODF Presentation Template', 'impress8_template') ### 38
fmts.add('presentation', 'pbm', 'pbm', 'Portable Bitmap', 'impress_pbm_Export') ### 21
fmts.add('presentation', 'pct', 'pct', 'Mac Pict', 'impress_pct_Export') ### 22
fmts.add('presentation', 'pdf', 'pdf', 'Portable Document Format', 'impress_pdf_Export') ### 23
fmts.add('presentation', 'pgm', 'pgm', 'Portable Graymap', 'impress_pgm_Export') ### 24
fmts.add('presentation', 'png', 'png', 'Portable Network Graphic', 'impress_png_Export') ### 25
fmts.add('presentation', 'pot', 'pot', 'Microsoft PowerPoint 97/2000/XP Template', 'MS PowerPoint 97 Vorlage') ### 3
fmts.add('presentation', 'ppm', 'ppm', 'Portable Pixelmap', 'impress_ppm_Export') ### 26
fmts.add('presentation', 'ppt', 'ppt', 'Microsoft PowerPoint 97/2000/XP', 'MS PowerPoint 97') ### 36
fmts.add('presentation', 'pwp', 'pwp', 'PlaceWare', 'placeware_Export') ### 30
fmts.add('presentation', 'ras', 'ras', 'Sun Raster Image', 'impress_ras_Export') ### 27
fmts.add('presentation', 'sda', 'sda', 'StarDraw 5.0 (OpenOffice.org Impress)', 'StarDraw 5.0 (StarImpress)') ### 8
fmts.add('presentation', 'sdd', 'sdd', 'StarImpress 5.0', 'StarImpress 5.0') ### 6
fmts.add('presentation', 'sdd3', 'sdd', 'StarDraw 3.0 (OpenOffice.org Impress)', 'StarDraw 3.0 (StarImpress)') ### 42
fmts.add('presentation', 'sdd4', 'sdd', 'StarImpress 4.0', 'StarImpress 4.0') ### 37
fmts.add('presentation', 'sxd', 'sxd', 'OpenOffice.org 1.0 Drawing (OpenOffice.org Impress)', 'impress_StarOffice_XML_Draw') ### 31
fmts.add('presentation', 'sti', 'sti', 'OpenOffice.org 1.0 Presentation Template', 'impress_StarOffice_XML_Impress_Template') ### 5
fmts.add('presentation', 'svg', 'svg', 'Scalable Vector Graphics', 'impress_svg_Export') ### 14
fmts.add('presentation', 'svm', 'svm', 'StarView Metafile', 'impress_svm_Export') ### 13
fmts.add('presentation', 'swf', 'swf', 'Macromedia Flash (SWF)', 'impress_flash_Export') ### 34
fmts.add('presentation', 'sxi', 'sxi', 'OpenOffice.org 1.0 Presentation', 'StarOffice XML (Impress)') ### 41
fmts.add('presentation', 'tiff', 'tiff', 'Tagged Image File Format', 'impress_tif_Export') ### 12
fmts.add('presentation', 'uop', 'uop', 'Unified Office Format presentation', 'UOF presentation') ### 4
fmts.add('presentation', 'vor', 'vor', 'StarImpress 5.0 Template', 'StarImpress 5.0 Vorlage') ### 40
fmts.add('presentation', 'vor3', 'vor', 'StarDraw 3.0 Template (OpenOffice.org Impress)', 'StarDraw 3.0 Vorlage (StarImpress)') ###1
fmts.add('presentation', 'vor4', 'vor', 'StarImpress 4.0 Template', 'StarImpress 4.0 Vorlage') ### 39
fmts.add('presentation', 'vor5', 'vor', 'StarDraw 5.0 Template (OpenOffice.org Impress)', 'StarDraw 5.0 Vorlage (StarImpress)') ### 2
fmts.add('presentation', 'wmf', 'wmf', 'Windows Metafile', 'impress_wmf_Export') ### 11
fmts.add('presentation', 'xhtml', 'xml', 'XHTML', 'XHTML Impress File') ### 33
fmts.add('presentation', 'xpm', 'xpm', 'X PixMap', 'impress_xpm_Export') ### 10

class Options:
  def __init__(self, args):
    self.connection = None
    self.doctype = None
    self.exportfilter = []
    self.filenames = []
    self.format = None
    self.importfilter = ""
    self.listener = False
    self.outputpath = None
    self.pipe = None
    self.port = '2002'
    self.server = 'localhost'
    self.showlist = False
    self.stdout = False
    self.template = None
    self.timeout = 6
    self.verbose = 0
    self.yaml = None

    ### Get options from the commandline
    try:
      opts, args = getopt.getopt (args, 'c:d:e:f:hi:Llo:p:s:t:T:vy:',
          ['connection=', 'doctype=', 'export', 'format=', 'help',
           'import', 'listener', 'outputpath=', 'pipe=', 'port=',
           'server=', 'timeout=', 'show', 'stdout', 'template',
           'verbose', 'version'])
    except getopt.error, exc:
      print 'unoconv: %s, try unoconv -h for a list of all the options' % str(exc)
      sys.exit(255)

    for opt, arg in opts:
      if opt in ['-h', '--help']:
        self.usage()
        print
        self.help()
        sys.exit(1)
      elif opt in ['-c', '--connection']:
        self.connection = arg
      elif opt in ['-d', '--doctype']:
        self.doctype = arg
      elif opt in ['-e', '--export']:
        l = arg.split('=')
        if len(l) == 2:
          (name, value) = l
          if value in ('True', 'true'):
            self.exportfilter.append(PropertyValue(name, 0, True, 0))
          elif value in ('False', 'false'):
            self.exportfilter.append(PropertyValue(name, 0, False, 0))
          else:
            self.exportfilter.append(PropertyValue(name, 0, value, 0))
        else:
          print >> sys.stderr, 'Warning: Option %s cannot be parsed, ignoring.' % arg
      elif opt in ['-f', '--format']:
        self.format = arg
      elif opt in ['-i', '--import']:
        self.importfilter = arg
      elif opt in ['-l', '--listener']:
        self.listener = True
      elif opt in ['-o', '--outputpath']:
        self.outputpath = arg
      elif opt in ['--pipe']:
        self.pipe = arg
      elif opt in ['-p', '--port']:
        self.port = arg
      elif opt in ['-s', '--server']:
        self.server = arg
      elif opt in ['--show']:
        self.showlist = True
      elif opt in ['--stdout']:
        self.stdout = True
      elif opt in ['-y'] :
        self.yaml = arg
      elif opt in ['-t', '--template']:
        self.template = arg
      elif opt in ['-T', '--timeout']:
        self.timeout = int(arg)
      elif opt in ['-v', '--verbose']:
        self.verbose = self.verbose + 1
      elif opt in ['--version']:
        self.version()
        sys.exit(255)

    ### Enable verbosity
    if self.verbose >= 3:
      print >> sys.stderr, 'Verbosity set to level %d' % (self.verbose - 1)

    self.filenames = args

    if self.yaml is not None:
      self.loadyaml()

    if not self.listener and not self.showlist and self.doctype != 'list' and not self.filenames:
      print >> sys.stderr, 'unoconv: you have to provide a filename as argument'
      print >> sys.stderr, 'Try `unoconv -h\' for more information.'
      sys.exit(255)

    ### Set connection string
    if not self.connection:
      if not self.pipe:
        self.connection = "socket,host=%s,port=%s;urp;StarOffice.ComponentContext" % (self.server, self.port)
#               self.connection = "socket,host=%s,port=%s;urp;" % (self.server, self.port)
      else:
        self.connection = "pipe,name=%s;urp;StarOffice.ComponentContext" % (self.pipe)
      if self.verbose >= 3:
        print >> sys.stderr, 'Connection type: %s' % self.connection

    ### Make it easier for people to use a doctype (first letter is enough)
    if self.doctype:
      for doctype in doctypes:
        if doctype.startswith(self.doctype):
          self.doctype = doctype

    ### Check if the user request to see the list of formats
    if self.showlist or self.format == 'list':
      if self.doctype:
        fmts.display(self.doctype)
      else:
        for t in doctypes:
          fmts.display(t)
      sys.exit(0)

    ### If no format was specified, probe it or provide it
    if not self.format:
      l = sys.argv[0].split('2')
      if len(l) == 2:
        self.format = l[1]
      else:
        self.format = 'pdf'

  def version(self):
    print 'unoconv %s' % VERSION
    print 'Written by Dag Wieers <dag@wieers.com>'
    print 'Homepage at http://dag.wieers.com/home-made/unoconv/'
    print
    print 'platform %s/%s' % (os.name, sys.platform)
    print 'python %s' % sys.version
    print
    print 'build revision $Rev$'

  def usage(self):
    print >> sys.stderr, 'usage: unoconv [options] file [file2 ..]'

  def loadyaml(self):
    """Loads the yaml command file"""
    if self.listener or self.showlist: return #NO yaml in listen mode or list mode
    y = self.yaml
    if y == "-":
      self.yaml = yaml.load(sys.stdin)
    else:
      if isinstance(self.yaml, dict):
        pass #Already converted.
      else:
        import yaml
        if isinstance(self.yaml, file) or isinstance(self.yaml, object):
          self.yaml = yaml.load(self.yaml)
        else:
          f = file(self.yaml, "r")
          self.yaml = yaml.load(f)
          f.close()
    self.yaml = self.fixRascalYaml(self.yaml)
    if not self.filenames:
      if self.yaml.has_key('template'):
        self.filenames = [self.yaml['template']]

  def fixRascalYaml(self, data):
    """Rascal string handling is terrible so everything ends up getting quoted. This routine converts numbers back to numbers"""
    if not isinstance(data, dict):
      return data
    for key in data.keys():
      if not data[key]:continue
      if isinstance(data[key], types.ListType):
        fixedlist = []
        for v in data[key]:
          fixedlist.append(self.fixRascalYaml(v))
          data[key] = fixedlist
      elif isinstance(data[key], dict):
        data[key] = self.fixRascalYaml(data[key])
      else:
        v = data[key]
        try:
          v = float(v) #Convert to a floating point.
          if int(v) == v: v = int(v)  #We can actually use an integer
          data[key] = v
        except ValueError: continue #Must be a string
        except TypeError:
          sys.stderr.write("Oops. can't process key '%s' type: %s\n" % (key, type(v)))
          continue
    return data

  def help(self):
    print >> sys.stderr, """Convert from and to any format supported by OpenOffice
unoconv options:
-c, --connection=string  use a custom connection string
-d, --doctype=type       specify document type
                         (document, graphics, presentation, spreadsheet)
-e, --export=name=value  set export filter options
                         eg. -e PageRange=1-2
-f, --format=format      specify the output format
-i, --import=string      set import filter option string
                         eg. -i utf8
-l, --listener           start a listener to use by unoconv clients
-o, --outputpath=name    output directory
  --pipe=name          alternative method of connection using a pipe
-p, --port=port          specify the port (default: 2002)
                         to be used by client or listener
-s, --server=server      specify the server address (default: localhost)
                         to be used by client or listener
-t, --template=file      import the styles from template (.ott)
-T, --timeout=secs       timeout after secs if connections to OpenOffice fail
  --show               list the available output formats
  --stdout             write output to stdout
-v, --verbose            be more and more verbose
"""

class Convertor:
  docUpdateCallback = None
  def __init__(self):
    global exitcode, ooproc, oobin, oolibpath
    unocontext = None

    ### Do the OpenOffice component dance
    self.context = uno.getComponentContext()
    resolver = self.context.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", self.context)

    ### Test for an existing connection
    try:
      unocontext = resolver.resolve("uno:%s" % op.connection)
    except NoConnectException, e:
      info(3, "Existing listener not found.\n%s" % e)

      ### Start our own OpenOffice instance
      info(3, "Launching our own listener using %s." % oobin)
      try:
        ooproc = subprocess.Popen([oobin, "--headless", "--invisible", "--nocrashreport", "--nodefault", "--nofirststartwizard", "--nologo", "--norestore", "--accept=%s" % op.connection])
        info(2, 'OpenOffice listener successfully started. (pid=%s)' % ooproc.pid)

        ### Try connection to it for op.timeout seconds (flakky OpenOffice)
        timeout = 0
        while timeout <= op.timeout:
          ### Is it already/still running ?
          if ooproc.poll() != None:
            info(3, "Process %s (pid=%s) is not running." % (oobin, ooproc.pid))
            break
          try:
            unocontext = resolver.resolve("uno:%s" % op.connection)
            break
          except NoConnectException:
            time.sleep(0.5)
            timeout += 0.5
          except:
            raise
        else:
          error("Failed to connect to %s (pid=%s) in %d seconds.\n%s" % (oobin, ooproc.pid, op.timeout, e))
      except Exception, e:
        raise
        error("Launch of %s failed.\n%s" % (oobin, e))

    if not unocontext:
      die(251, "Unable to connect or start own listener. Aborting.")

    ### And some more OpenOffice magic
    unosvcmgr = unocontext.ServiceManager
    self.desktop = unosvcmgr.createInstanceWithContext("com.sun.star.frame.Desktop", unocontext)
    self.config = unosvcmgr.createInstanceWithContext("com.sun.star.configuration.ConfigurationProvider", unocontext)
    self.cwd = unohelper.systemPathToFileUrl(os.getcwd())

  def getformat(self, inputfn):
    doctype = None

    ### Get the output format from mapping
    if op.doctype:
      outputfmt = fmts.bydoctype(op.doctype, op.format)
    else:
      outputfmt = fmts.byname(op.format)

      if not outputfmt:
        outputfmt = fmts.byextension(os.extsep + op.format)

    ### If no doctype given, check list of acceptable formats for input file ext doctype
    ### FIXME: This should go into the for-loop to match each individual input filename
    if outputfmt:
      inputext = os.path.splitext(inputfn)[1]
      inputfmt = fmts.byextension(inputext)
      if inputfmt:
        for fmt in outputfmt:
          if inputfmt[0].doctype == fmt.doctype:
            doctype = inputfmt[0].doctype
            outputfmt = fmt
            break
        else:
          outputfmt = outputfmt[0]
  #       print >>sys.stderr, 'unoconv: format `%s\' is part of multiple doctypes %s, selecting `%s\'.' % (format, [fmt.doctype for fmt in outputfmt], outputfmt[0].doctype)
      else:
        outputfmt = outputfmt[0]

    ### No format found, throw error
    if not outputfmt:
      if doctype:
        print >> sys.stderr, 'unoconv: format [%s/%s] is not known to unoconv.' % (op.doctype, op.format)
      else:
        print >> sys.stderr, 'unoconv: format [%s] is not known to unoconv.' % op.format
      die(1)

    return outputfmt

  def convert(self, inputfn):
    global exitcode

    doc = None
    outputfmt = self.getformat(inputfn)

    if op.verbose > 0:
      print >> sys.stderr, 'Input file:', inputfn

    if not os.path.exists(inputfn):
      print >> sys.stderr, 'unoconv: file `%s\' does not exist.' % inputfn
      exitcode = 1

    try:
      ### Load inputfile
      inputprops = (
          PropertyValue("Hidden", 0, True, 0),
          PropertyValue("ReadOnly", 0, True, 0),
          PropertyValue("FilterOptions", 0, op.importfilter, 0),
      )

      inputurl = unohelper.absolutize(self.cwd, unohelper.systemPathToFileUrl(inputfn))
      doc = self.desktop.loadComponentFromURL(inputurl , "_blank", 0, inputprops)

      if not doc:
        raise UnoException("File could not be loaded by OpenOffice", None)

      ### Import style template
      if op.template:
        if os.path.exists(op.template):
          if op.verbose > 0:
            print >> sys.stderr, 'Template file:', op.template
          templateprops = (
              PropertyValue("OverwriteStyles", 0, True, 0),
          )
          templateurl = unohelper.absolutize(self.cwd, unohelper.systemPathToFileUrl(op.template))
          doc.StyleFamilies.loadStylesFromURL(templateurl, templateprops)
        else:
          print >> sys.stderr, 'unoconv: template file `%s\' does not exist.' % op.template
          exitcode = 1

      info(1, "Selected output format: %s" % outputfmt)
      info(1, "Selected ooffice filter: %s" % outputfmt.filter)
      info(1, "Used doctype: %s" % outputfmt.doctype)

      if self.docUpdateCallback:
        self.docUpdateCallback(doc)

      ### Update document links
      try:
        doc.updateLinks()
      except AttributeError:
        # the document doesn't implement the XLinkUpdate interface
        pass

      ### Update document indexes
      try:
        doc.refresh()
        indexes = doc.getDocumentIndexes()
      except AttributeError:
        # the document doesn't implement the XRefreshable and/or
        # XDocumentIndexesSupplier interfaces
        pass
      else:
        for i in range(0, indexes.getCount()):
          indexes.getByIndex(i).update()

      ### Write outputfile
      outputprops = [
#                PropertyValue( "FilterData" , 0, ( PropertyValue( "SelectPdfVersion" , 0, 1 , uno.getConstantByName( "com.sun.star.beans.PropertyState.DIRECT_VALUE" ) ) ), uno.getConstantByName( "com.sun.star.beans.PropertyState.DIRECT_VALUE" ) ),
          PropertyValue("FilterData", 0, uno.Any("[]com.sun.star.beans.PropertyValue", tuple(op.exportfilter),), 0),
          PropertyValue("FilterName", 0, outputfmt.filter, 0),
#                PropertyValue( "SelectionOnly", 0, True, 0 ),
          PropertyValue("OutputStream", 0, OutputStream(), 0),
          PropertyValue("Overwrite", 0, True, 0),
      ]

      if outputfmt.filter == 'Text (encoded)':
        outputprops.append(PropertyValue("FilterFlags", 0, "UTF8, LF", 0))

      if not op.stdout:
        (outputfn, ext) = os.path.splitext(inputfn)
        if not op.outputpath:
          outputfn = outputfn + os.extsep + outputfmt.extension
        else:
          if os.path.isdir(op.outputpath):
            outputfn = os.path.join(op.outputpath, os.path.basename(outputfn) + os.extsep + outputfmt.extension)
          else: #TSF
            outputfn = op.outputpath #TSF
            log.error("Outputfn: %s", outputfn) #TSF
        outputurl = unohelper.absolutize(self.cwd, unohelper.systemPathToFileUrl(outputfn))
        log.error("Storing to %s Outputfn: %s" , outputurl, outputfn)
        doc.storeToURL(outputurl, tuple(outputprops))
        info(1, "Output file: %s" % outputfn)
      else:
        doc.storeToURL("private:stream", tuple(outputprops))

      doc.dispose()
      doc.close(True)

    except SystemError, e:
      error("unoconv: SystemError during conversion: %s" % e)
      error("ERROR: The provided document cannot be converted to the desired format.")
      exitcode = 1

    except UnoException, e:
      error("unoconv: UnoException during conversion in %s: %s" % (repr(e.__class__), e.Message))
      error("ERROR: The provided document cannot be converted to the desired format. (code: %s)" % e.ErrCode)
      exitcode = e.ErrCode
      raise

    except IOException, e:
      error("unoconv: IOException during conversion: %s" % e.Message)
      error("ERROR: The provided document cannot be exported to %s." % outputfmt)
      exitcode = 3

    except CannotConvertException, e:
      error("unoconv: CannotConvertException during conversion: %s" % e.Message)
      exitcode = 4

class Listener:
  def __init__(self):
    info(1, "Start listener on %s:%s" % (op.server, op.port))
    try:
      subprocess.call([oobin, "-headless", "-invisible", "-nocrashreport", "-nodefault", "-nologo", "-nofirststartwizard", "-norestore", "-accept=%s" % op.connection])
    except Exception, e:
      error("Launch of %s failed.\n%s" % (oobin, e))
    else:
      die(253, "Existing listener found, aborting.")

class DocUpdater:
  data = {}
  converter = None
  def __init__(self, data, converter=None):
    self.data = data
    error('In DocUpdater init')
    if converter:
      self.converter = converter

  def getCurrentRegion(self, oRange):
    """Get current region around given range."""
    oCursor = oRange.getSpreadsheet().createCursorByRange(oRange)
    oCursor.collapseToCurrentRegion()
    return oCursor

  def getCurrentColumnsAddress(self, oRange):
    """Get address of intersection between range and current region's columns"""
    oCurrent = oRange #self.getCurrentRegion(oRange)
    oAddr = oRange.getRangeAddress()
    oCurrAddr = oCurrent.getRangeAddress()
    oAddr.StartColumn = oCurrAddr.StartColumn
    oAddr.EndColumn = oCurrAddr.EndColumn
    return oAddr

  def update(self, doc):
    log.debug("DocUpdater.update")
    if self.data.has_key('startsheet'):
      self.sheet = doc.getSheets().getByName(self.data['startsheet'])
    else:
      self.sheet = doc.getSheets().getByIndex(0) #Just use the first sheet. 
    if self.data.has_key('data'):
      for k in self.data['data']:
        self.fieldUpdate(self.sheet, k, self.data['data'][k])
    if self.data.has_key('insert'): #If we have a section with data to insert into the spreadsheet
      self.updateInserts(doc, self.data['insert'])
    log.debug("Looking for images")
    if self.data.has_key('images') and self.data['images'] is not None:
      log.debug("Has images")
      for imageDetails in self.data['images']:
        log.debug("Details: %s ", imageDetails)
        self.insertImage(doc, self.sheet, imageDetails['location'], imageDetails['filename'])

  def updateInserts(self, doc, insertdata):
    """Update the spreadsheet with any insert information"""
    if (isinstance(insertdata, types.DictionaryType)):
      return self.updateInserts(doc, [insertdata]) #Only a single insert, turn it into a list so we can standardise the code
    rowsinserted = 0
    for insertrecord in insertdata:
      sys.stderr.write("updateInserts: %s\n" % (type(insertrecord)))
      #Start inserting the data, Starting at top level (0)
      data = self.data[insertrecord['data']]
      if isinstance(data, types.ListType):
        currentsheet = self.sheet #Save the sheet so we can move around with out worrying
        if insertrecord.has_key("startsheet"): self.sheet = doc.getSheets().getByName(insertrecord['startsheet'])
        rowsinserted += self.updateInsertsSection(data, insertrecord, 0)
        self.sheet = currentsheet #Move back to the correct sheet incase it was changed
      else:
        sys.stderr.write("Could not handle record of type '%s'\n" % (type(data)))
        raise Exception("Bloody idiot")
    return rowsinserted
  def updateInsertsSection(self, data, insertrecord, grouplevel=0):
    sys.stderr.write("updateInsertsSection: %s len: %s\n" % (type(data), len(data)))
    rowsinserted = 0
    try:
      for datarow in data:
        sys.stderr.write("datarow: %s len: %s\n" % (type(datarow), len(datarow)))
        sys.stderr.write(yaml.dump(datarow))
        sys.stderr.write("\n\n")
        if isinstance(datarow, types.ListType):
            #One level down data, pass it down the chain:
          rowsinserted += self.updateInsertsSection(datarow, insertrecord, grouplevel + 1)
          continue

        #print "%s    Testing(%s): %s - %s" % ("-----" * grouplevel, grouplevel,type(datarow),insertrecord)
        if insertrecord.has_key("fields%s" % (grouplevel)):
          fieldlist = insertrecord["fields%s" % (grouplevel)] #fields we need to display
          if not isinstance(fieldlist, types.ListType): fieldlist = [fieldlist] #Change it from a string to a list
          oRange = self.sheet.getCellRangeByName(insertrecord['insertpoint']).getRangeAddress()
          #oSel = doc.getCurrentSelection()
          self.sheet.insertCells(oRange, ROWS) #Insert a blank row
          rowsinserted += 1  #Track the number of new rows inserted
          x = oRange.StartColumn
          y = oRange.StartRow
          offset = 0
          print "Fieldlist: %s" % (fieldlist)
          for fieldname in fieldlist: #Insert all the values
            self.fieldUpdateByPos(self.sheet, x + offset, y, datarow[fieldname])
            offset += 1

        else:
          sys.stderr.write("No fields for group %s\n" % (grouplevel))
    except ValueError, ex:
      sys.stderr.write("Data broken.\nInsertrecord:%s\nDataType:%s\n Grouplevel:%s\n" % (insertrecord, type(data), grouplevel))
      sys.stderr.write("%s\n\n" % (ex))
      raise ex

    #Code to group and hide rows
    if self._insertrecord_hasgroup(insertrecord, grouplevel):
      sys.stderr.write("Grouping level %s %s rows\n" % (grouplevel, rowsinserted))
      oRange = self.sheet.getCellRangeByName(insertrecord['insertpoint']).getRangeAddress()
      x = oRange.StartColumn
      y = oRange.StartRow
      groupRange = self.sheet.getCellRangeByName(insertrecord['insertpoint']).getRangeAddress()
      groupRange.StartRow = y - rowsinserted #The point where we started inserting data
      groupRange.EndColumn = y - 1 #Move up one row from the cell name
      self.sheet.group(groupRange, TABLEROWS)
      self.sheet.hideDetail(groupRange)

    return rowsinserted
  def _insertrecord_hasgroup(self, insertrecord, grouplevel):
    """Returns true if data at grouplevel should be grouped and hidden"""
    sys.stderr.write("_insertrecord_hasgroup GroupLevel: %s  Groups: %s\n" % (grouplevel, insertrecord['group']))
    if not insertrecord.has_key('group'): return False #Not group list so nothing must be grouped
    groups = insertrecord['group']
    if not isinstance(groups, types.ListType): groups = [groups] #Convert the groups to a list if needby
    try:
      i = groups.index(grouplevel)
    except TypeError:
      print "Failure, grouplevel: %s Type: %s Groups %s" % (grouplevel, type(grouplevel), groups)
      raise
    except ValueError: return False #We shouldn't group this level
    return True

  def fieldGoto(self, sheet, fieldname):
    return (sheet.getCellRangeByName(fieldname))

  def insertImage(self, doc, sheet, imageposition, filename):
    """Inserting an image into document"""
    if not os.path.exists(filename):
      print "File '%s' is missing!" % (filename)
      return False
    #sheet.getCellRangeByName(ipos).GoToCell()
    imgfile = unohelper.systemPathToFileUrl(filename)
    log.debug("doc: %s ", type(doc))
    log.debug("sheet: %s  " , type(sheet))
    log.debug("pos: %s fname: %s" , imageposition, filename)

    dispatcher = self.converter.unosvcmgr.createInstance('com.sun.star.frame.DispatchHelper')
    frame = doc.getCurrentController().getFrame()
    result = dispatcher.executeDispatch(frame, 'macro:///Standard.API.ImageFromURL("%s","%s")' % (imageposition, imgfile), '', 0, ())
    log.debug('macro:///Standard.API.ImageFromURL("%s","%s")' % (imageposition, imgfile))
    log.debug("Result: %s", result)
    log.debug("DISPATCHER: %s %s", dir(dispatcher), type(dispatcher))

  def fieldUpdateByPos(self, sheet, col, row, value):
    try:
      if isinstance(value, int) or isinstance(value, float):
        sheet.getCellByPosition(col, row).setValue(str(value))
      else:
        sheet.getCellByPosition(col, row).setString(str(value))
    except UnoException, e: #Probably means the cell name doesn't exist
      pass
  def fieldUpdate(self, sheet, fieldname, value):
    log.debug("Field update called(%s,%s,%s)", 'sheet', fieldname, value)
    try:
      if isinstance(value, int) or isinstance(value, float):
        sheet.getCellRangeByName(fieldname).setValue(str(value))
        log.debug("Field update %s - %s", fieldname, value)
      else:
        cell = sheet.getCellRangeByName(fieldname)
        log.debug("Cell %s", cell)
        log.debug("Get by string: cell: %s", cell.getString())
        cell.String = "zzzzzzzzzzzzzzzzzz"
        r = sheet.getCellRangeByName(fieldname).setString(str(value))
        r = sheet.getCellRangeByName(fieldname).setFormula("Boom goes the dynamite")
        log.debug("setString result: %s", r)
    except UnoException, e: #Probably means the cell name doesn't exist
      log.info("Could not find field %s value: %s Error %s", fieldname, value, e)
      pass

def error(str):
  "Output error message"
  print >> sys.stderr, str

def info(level, str):
  "Output info message"
  if not op.stdout and level <= op.verbose:
    print >> sys.stdout, str
  elif level <= op.verbose:
    print >> sys.stderr, str

def die(ret, str=None):
  "Print error and exit with errorcode"
  global convertor, ooproc, oobin

  if str:
    error('Error: %s' % str)

  ### Did we start an instance ?
  if ooproc and convertor:

    ### If there is a GUI now attached to the instance, disable listener
    if convertor.desktop.getCurrentFrame():
      try:
        subprocess.Popen([oobin, "-headless", "-invisible", "-nocrashreport", "-nodefault", "-nofirststartwizard", "-nologo", "-norestore", "-unaccept=%s" % op.connection])
        info(2, 'OpenOffice listener successfully disabled.')
        ooproc.wait()
      except Exception, e:
        error("Terminate using %s failed.\n%s" % (oobin, e))

    ### If there is no GUI attached to the instance, terminate instance
    else:
      try:
        convertor.desktop.terminate()
      except DisposedException:
        info(2, 'OpenOffice instance unsuccessfully closed, sending TERM signal.')
        try:
          ooproc.terminate()
        except AttributeError:
          os.kill(ooproc.pid, 15)
      ooproc.wait()

    ### OpenOffice processes may get stuck and we have to kill them
    ### Is it still running ?
    if ooproc.poll() == None:
      info(1, 'OpenOffice instance still running, please investigate...')
      ooproc.wait()
#            info(2, 'OpenOffice instance unsuccessfully terminated, sending KILL signal.')
#            try:
#                ooproc.kill()
#            except AttributeError:
#                os.kill(ooproc.pid, 9)
#            info(2, 'Waiting for OpenOffice with pid %s to disappear.' % ooproc.pid)
#            ooproc.wait()

  sys.exit(ret)

def main():
  global convertor, exitcode
  convertor = None

  try:
    if op.listener:
      listener = Listener()
    else:
      convertor = Convertor()
      #TSF code to add in fields.
      docupdate = DocUpdater(op.yaml, convertor)
      convertor.docUpdateCallback = docupdate.update
      #----------------

    for inputfn in op.filenames:
      convertor.convert(inputfn)

  except NoConnectException, e:
    error("unoconv: could not find an existing connection to Open Office at %s:%s." % (op.server, op.port))
    if op.connection:
      info(0, "Please start an OpenOffice instance on server '%s' by doing:\n\n    unoconv --listener --server %s --port %s\n\nor alternatively:\n\n    ooffice -nologo -nodefault -accept=\"%s\"" % (op.server, op.server, op.port, op.connection))
    else:
      info(0, "Please start an OpenOffice instance on server '%s' by doing:\n\n    unoconv --listener --server %s --port %s\n\nor alternatively:\n\n    ooffice -nologo -nodefault -accept=\"socket,host=%s,port=%s;urp;\"" % (op.server, op.server, op.port, op.server, op.port))
      info(0, "Please start an ooffice instance on server '%s' by doing:\n\n    ooffice -nologo -nodefault -accept=\"socket,host=localhost,port=%s;urp;\"" % (op.server, op.port))
    exitcode = 1
#    except UnboundLocalError:
#        die(252, "Failed to connect to remote listener.")
  except OSError:
    error("Warning: failed to launch OpenOffice. Aborting.")

def run(inputData, outputFileName):
  """Used when calling as a library from another module."""
  global op
  #op = Options([ "-o", outputFileName, '-y', inputh , '--pipe=aaa' ])
  op = Options([ "-o", outputFileName, '-y', inputData , '--port=8100'])
  try:
    main()
    log.debug("Finished")
  except KeyboardInterrupt, e:
    die(6, 'Exiting on user request')
  except Exception, e:
    log.exception("Major Error : '%s'", e)
    print "Doh!, Hit an exception"
    raise
  return True
### Main entrance
if __name__ == '__main__':
  exitcode = 0

  op = Options(sys.argv[1:])
  try:
    main()
  except KeyboardInterrupt, e:
    die(6, 'Exiting on user request')
  die(exitcode)
