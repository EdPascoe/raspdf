#!/usr/bin/env python
# -*- coding: utf-8 -*-
# © Ed Pascoe 2011. All rights reserved.
"""
Converts rascal reports in this format to a pdf. ALL tags start with "{$"
                                                               {$PIC("nac.jpg",158,93)}

{$SETCOLOR(0,1,1)}
{$SF(18)}National Airways Corporation (Pty) Ltd.{$SF(12)}
{$SF(8)}Reg No 1945/019919/07                                             VAT Reg. 4090107188{$SF(10)}
{$SETCOLOR(0,0,0)}

{$SF(10)}10 Point abcdefghijklmno
{$SF(12)}12 Point abcdefghijklmno
{$SF(14)}14 Point abcdefghijklmno
{$SF(16)}16 Point abcdefghijklmno
{$SF(18)}18 Point abcdefghijklmno
{$SF(10)}Normal text {$BOLDON}Bold on{$BOLDOFF}{$ITALICON}Italic on{$ITALICOFF}{$BOLDON}{$ITALICON}Italic and BOLD {$BOLDOFF}{$ITALICOFF}
{$BOXS(5)}                                                          {$L1(2)}

"""
__author__ = "Ed Pascoe <ed@pascoe.co.za>"
__format__ = "plaintext"
__version__ = "$Id$"
__copyright__ = "Ed Pascoe 2011. All rights reserved."
__license__ = "GNU LGPL version 2"
__status__ = "Production"

from reportlab.pdfgen import canvas
import reportlab.lib.pagesizes
from reportlab.platypus.flowables import Image
from reportlab.lib.units import inch
from Point import Point, FontTracker
import logging
cm = inch / 2.54

log = logging.getLogger()

import re, os, os.path, sys, tempfile
from copy import copy, deepcopy
from reportlab.pdfbase.pdfmetrics import stringWidth
from RasConfig import fileLocate

cnstNORMAL = 0
cnstBOLD = 1
cnstITALIC = 2

_ISYAMLTEMPLATE = 99 #Internal use only.

class RascalPDFException(Exception):
  """Errors thrown by the PDF system"""

class RascalPDF:
  """PDF library for use with rascal. Tries to be a compatible with the old perl xxpdf library"""
  canvas = None
  #Margins
  lmargin = 0.7 * cm
  tmargin = 0.75 * cm
  bmargin = 1 * cm
  lmarginDefault = None
  line = "NOT YET INITITALIZED"
  linenumber = -1

  reporttitle = "Rascal Report";

  def  __init__(self, pdffile, pagesize=reportlab.lib.pagesizes.A4, isLandscape=False):
    self.pdffile = pdffile
    if isLandscape:
      pagesize = reportlab.lib.pagesizes.landscape(pagesize)
    else:
      pagesize = reportlab.lib.pagesizes.portrait(pagesize)

    self.canvas = canvas.Canvas(self.pdffile, pagesize, verbosity=0)
    self.canvas.setPageCompression(True)

    self.info = self.canvas._doc.info #The PDF document info
    self.pagesize = pagesize

    self.pos = Point(x=self.lmargin, y=self.pagesize[1] - self.tmargin)
    self.font = FontTracker(fileLocator=fileLocate)

    self.boxlist = {} # for drawing boxes
    self.linelist = {} # for drawing lines

    self.start_newpage = 1;
    self.printingBegun = False
    self.showPageNeeded = False #Next output command should do a show page

    self.picturelist_key = {}
    self.picturelist_h = {}
    self.picturelist_w = {}

    self.functions = {}

    # Prepare  fonts
    self.courier = self.helvetica = {}
    self.courier[cnstNORMAL] = 'Courier';
    self.courier[cnstBOLD] = 'Courier-Bold';
    self.courier[cnstITALIC] = 'Courier-Oblique';
    self.courier[cnstBOLD + cnstITALIC] = 'Courier-BoldOblique';
    self.helvetica[cnstNORMAL] = 'Helvetica';
    self.helvetica[cnstBOLD] = 'Helvetica-Bold';
    self.helvetica[cnstITALIC] = 'Helvetica-Oblique';
    self.helvetica[cnstBOLD + cnstITALIC] = 'Helvetica-BoldOblique';
    self.__registerkeys()
    self.linenumber = -1

  def fnexec(self, fnname, *params, **kwargs):
    """Lookup fnname in the functions list and execute the given function call."""
    self.linenumber += 1
    try:
      fn = self.functions[fnname]
    except KeyError:
      raise RascalPDFException("Function %s has not been registered" % (fnname))

    try:
      return fn(*params, **kwargs)
    except:
      log.error("Failure executing %s(%s) Command stack line number: %s Params: %s KWargs: %s" , fnname, params, self.linenumber, params, kwargs)
      raise

  def save(self):
    self.canvas.save()

  def _regfnFontSetBoldTrue(self):
    """For registerkeys, set bold on"""
    self.font.set(bold=True)

  def _regfnFontSetBoldFalse(self):
    """For registerkeys, set bold off"""
    self.font.set(bold=False)

  def _regfnFontSetItalicTrue(self):
    """For registerkeys, set italic on"""
    self.font.set(italic=True)

  def _regfnFontSetItalicFalse(self):
    """For registerkeys, set italic on"""
    self.font.set(italic=False)

  def _regfnFontSetSize16(self):
    """For registerkeys, set font size"""
    self.font.set(size=16)

  def _regfnFontSetSize12(self):
    """For registerkeys, set font size"""
    self.font.set(size=12)

  def _regfnFontSetSize10(self):
    """For registerkeys, set font size"""
    self.font.set(size=10)

  def _regfnFontSetSize8(self):
    """For registerkeys, set font size"""
    self.font.set(size=8)

  def _regfnFontSetSize6(self):
    """For registerkeys, set font size"""
    self.font.set(size=6)

  def _regfnFontSetSizex(self, size):
    """For registerkeys, set font size"""
    self.font.set(size=int(size))

  def _regfnFontSetName(self, name):
    """For registerkeys, set font name"""
    name = self.stripQuotes(name)

    self.font.set(fontname=name)

  def stripQuotes(self, msg):
    """Removes and quotes surrounding given string"""
    if msg[0] == '"' and msg[-1] == '"': #Filename has quotes around it which need to be removed.
      msg = msg[1:-1]
    return msg

  def _regfnFontSetColor(self, r, g, b):
    """For registerkeys, set font color"""
    self.canvas.setFillColorRGB(float(r), float(g), float(b))

  def _regfnCopiesSet(self, numcopies):
    """For registerkeys, set number of copies"""
    self.numcopies = numcopies

  def __registerkeys(self):
    """Create all the function mappings for lookups later."""
    self.functions = {}
    self.functions["PRINTINIT"] = self.printinit
    self.functions["PRINTEND"] = self.printend
    self.functions["LEND"] = self.textlineend #Called at auto at end of line

    self.functions["LMARGIN"] = self.setLeftMargin
    self.functions["PUSHPOS"] = self.savePos
    self.functions["POPPOS"] = self.restorePos

    self.functions["BOLDON"] = self._regfnFontSetBoldTrue
# sub{ $fontSTYLE = $fontSTYLE | $cnstBOLD; });
    self.functions["B1"] = self._regfnFontSetBoldTrue
    self.functions["BOLDOFF"] = self._regfnFontSetBoldFalse
    self.functions["B0"] = self._regfnFontSetBoldFalse
    self.functions["ITALICON"] = self._regfnFontSetItalicTrue
    self.functions["I1"] = self._regfnFontSetItalicTrue
    self.functions["ITALICOFF"] = self._regfnFontSetItalicFalse
    self.functions["I0"] = self._regfnFontSetItalicFalse

    self.functions["SETFONT16"] = self._regfnFontSetSize16
    self.functions["SETFONT12"] = self._regfnFontSetSize12
    self.functions["SETFONT10"] = self._regfnFontSetSize10
    self.functions["SETFONT8"] = self._regfnFontSetSize8
    self.functions["SETFONT6"] = self._regfnFontSetSize6
    self.functions["SETFONT"] = self._regfnFontSetSizex
    self.functions["SF"] = self._regfnFontSetSizex

    self.functions["FONTNAME"] = self._regfnFontSetName
    self.functions["SETCOLOR"] = self._regfnFontSetColor

    self.functions["COPIES"] = self._regfnCopiesSet

    self.functions["BOXS"] = self.boxstart #Mark the top left corner of a box
    self.functions["BOXE"] = self.boxend
    self.functions["RBOXS"] = self.boxstart #Mark the top left corner of a box
    self.functions["RBOXE"] = self.boxendround

    self.functions["LINES"] = self.linestart
    self.functions["L1"] = self.linestart
    self.functions["LINEE"] = self.lineend
    self.functions["L0"] = self.lineend

    self.functions["LINEWIDTH"] = self.linewidth
    self.functions["LW"] = self.linewidth

    self.functions["NEWPAGE"] = self.newPage
    self.functions["SHOWLINE"] = self.output

    self.functions["PIC"] = self.picture

    self.functions["UP"] = self.up
    self.functions["DOWN"] = self.down

    self.functions["MA"] = self.moveabsolute
    self.functions["MR"] = self.moverelative
    self.functions["RIGHT"] = self.right

    self.functions["printstring"] = self.output
    self.functions["newline"] = self.newline

  def up(self, lines, fsize=None):
    lines = int(lines)
    if fsize is None: fsize = self.font.size
    self.pos.y = self.pos.y + (lines * fsize)
    self.pos.x = self.lmargin;

  def down(self, lines, fsize=None):
    lines = int(lines)
    if fsize is None: fsize = self.font.size
    self.pos.y = self.pos.y - (lines * int(fsize))
    self.pos.x = self.lmargin;

  def right(self, c):
    c = int(c)  #Zero based to match xxpdf
    if c < 0: c = 0
    self.pos.x = int(self.lmargin + self.calcWidth("_" * c))

  def setLeftMargin(self, margin=None):
    """Set the left margin (indent level) in cm for future text. Default is to reset to starting margin."""
    if self.lmarginDefault is None: self.lmarginDefault = self.lmargin
    if margin is None:
      self.lmargin = self.lmarginDefault
    else:
      self.lmargin = float(margin) * cm

  def savePos(self):
    """Save the current cursor location """
    self.pos.push()

  def restorePos(self):
    """"Restore cursor location"""
    try:
      self.pos.pop()
    except IndexError:
      print >> sys.stderr, "Could not restore position because nothing has been saved"
      sys.exit(5)

  def moverelative(self, x, y):
    self.pos.x += int(x);
    self.pos.y -= int(y);

  def moveabsolute(self, x=None, y=None):
    """Move to given spot on page. x and y in cm"""
    if x: self.pos.x = float(x) * cm;
    if y: self.pos.y = self.pagesize[1] - float(y) * cm;

  def printinit(self):
    """Initialize printing system"""
    log.debug("Inititializing")
    self.pos = Point(x=self.lmargin, y=self.pagesize[1] - self.tmargin)

  def printend(self):
    """End printing system"""

  def textlineend(self):
    """Called at line end."""
    #log.debug("textlineend")
    if self.pos.y <= self.font.size + self.bmargin:
      log.debug("Curent pos %s <= %s, new page", self.pos.y, self.font.size)
      self.newPage()
    else:
      self.pos.y -= self.font.size;
      self.pos.x = self.lmargin;

  def newline(self):
    """handle \n"""
    self.textlineend()

  def boxstart(self, boxname=0):
    """Remember the posistion of the start of a box."""
    self.boxlist[boxname] = copy(self.pos)
    log.debug("box start Position: %s", self.pos)

  def  boxend(self, boxname=0):
    self.showPageIfNeeded()
    if not self.boxlist.has_key(boxname):
      return
    s = self.boxlist[boxname]
    e = self.pos
    self.canvas.rect(s.x, e.y, (e.x - s.x), (s.y - e.y), stroke=1, fill=0)

    log.debug("box end Position: %s", e)

  def boxendround(self, boxname=0):
    """Complete a box with rounded corners"""
    self.showPageIfNeeded()
    if not self.boxlist.has_key(boxname): return

    s = self.boxlist[boxname]
    e = self.pos
    log.debug("boxendround end box from %s to %s", s, e)
    u = inch / 10.0
    self.canvas.roundRect(s.x, e.y, (e.x - s.x), (s.y - e.y), 1.5 * u, stroke=1, fill=0)
    return

  def linestart(self, linename=0):  #Remember the posistion of the start of a line.
    self.linelist[linename] = deepcopy(self.pos)

  def lineend(self, linename=0):
    self.showPageIfNeeded()
    s = self.linelist.get(linename, None)
    if s is None: return
    x1 = s.x
    y1 = s.y
    x2 = self.pos.x
    y2 = self.pos.y

    path = self.canvas.beginPath()
    path.moveTo(x1, y1);
    path.lineTo(x2, y2);
    self.canvas.drawPath(path, stroke=1, fill=1)

  def linewidth(self, width):
    self.canvas.setLineWidth(width)

  def output(self, line):
    if len(line) == 0: return

    if line[-1] != "\n":
      self.print_string(line)
      self.pos.x += self.calcWidth(line)
      return

    r = re.search(r'(.*?)\cL(.*)', line)
    if self.pos.y <= self.font.size:
      self.newPage();
      self.pos.y = self.font.size - self.tmargin
      self.print_string(line)
      self.pos.x = self.lmargin
      self.pos.y -= self.font.size

    elif r: #Form Feed
      self.print_string(r.group(1));
      self.newPage();
      self.pos.y = self.font.size - self.tmargin
      self.pos.x = self.lmargin
      self.print_string(r.group(2))
      self.pos.y - self.fint.szie
    else:
       self.print_string(line);
       self.pos.y -= self.font.size
       self.pos.x = self.lmargin

  def startDoc(self):
    self.newpage();
    self.start_newpage = 0;
    self.pos.set(x=self.lmargin, y=0)

  def newPage(self):
    """Set the flag so that the next write to the screen will create a new page"""
    self.start_newpage = 1
    self.pos = Point(x=self.lmargin, y=self.pagesize[1] - self.tmargin)
    log.debug("newPage %s", self.pos)
    if self.printingBegun:
      self.showPageNeeded = True #Next output command should generate a showpage.
      self.printingBegun = False;
    else:
      log.debug("newPage called but nothing has been printed on this page so far")

  def showPageIfNeeded(self):
    """ This is needed to prevent blank pages at end of doc. 
        Typically a final newPage gets called but there is nothing waiting.
    """
    if self.showPageNeeded:
      self.showPageNeeded = False
      self.canvas.showPage()
    else:
      self.printingBegun = True

  def calcTextWidth(self, line):
    return self.calcWidth(line);

  def calcWidth(self, text):
    """Return width of give line of text
From: http://two.pairlist.net/pipermail/reportlab-users/2010-January/009208.html
If you text is one line string then you can use 
from reportlab.pdfbase.pdfmetrics import stringWidth 
textWidth = stringWidth(text, fontName, fontSize) 

If your text was multi-lines, assuming you are working in a rectangular area with defined width, 
then do 

from reportlab.lib.utils import simpleSplit 
lines = simpleSplit(text, fontName, fontSize, maxWidth) 

lines is a list of all the lines of your paragraph, if you know the line spacing value then the 
height of the paragraph can be calculated as lineSpacing*len(lines) 

    """
    return int(stringWidth(text, self.font.getFontName(), self.font.size))

  def useFont(self, textobject, font):
    textobject.setFont("Helvetica-Oblique", 14)

  def print_string(self, msg):
    """Prints string on page at current cursor location."""
    self.showPageIfNeeded()

    textobject = self.canvas.beginText()
    self.canvas.setFont(self.font.getFontName(), self.font.size)
    log.debug(" self.canvas.drawText%s, %s)", self.pos, msg)
    self.canvas.drawString(self.pos.x, self.pos.y, msg)

  def picture(self, fname, imgwidth=None, imgheight=None):
    """Insert picture into pdf. If imgwidth and imgheight are not none they will be used to reposition the cursor after the insert."""
    self.showPageIfNeeded()
    x = int(self.pos.x)
    y = int(self.pos.y)
    if imgwidth:
      imgwidth = int(imgwidth)
    if imgheight:
      imgheight = int(imgheight)
      y = y - imgheight

    fname = fileLocate(fname)
    self.canvas.drawImage(fname, x, y, imgwidth, imgheight)

class _Parser:
  """Contains the print job broken into an array of python function calls.
    Usage:  p = _Parser()
            for line in file("Blah"): p.parseLine(line)
            print "Function calls: ", print p.cmdlist
  """
  def __init__(self):
    self.cmdlist = []

  def parseLine(self, line):
    if len(line) == 0: return  #Blank line
    hasnewline = line[-1] == "\n"
    line = line.rstrip()
    r = re.search(r'^(.*?){\$(.*?)}(.*)$', line)
    if r:
      leadtext = r.group(1)
      cmd = r.group(2)
      restofline = r.group(3)
      self.cmdlist.append(("printstring", u'line="' + leadtext.replace(r'"', r'\\"') + '"'))
      self.addCommand(cmd)
      self.parseLine(restofline)
    else:
      self.cmdlist.append(("printstring", u'line="' + line.replace(r'"', r'\\"') + '"'))

    if hasnewline:
      self.cmdlist.append(("newline",))

  def addCommand(self, command):
    command = command.strip()
    cmdname = None
    cmdparams = []
    p = command.find("(") #Find the start of any parameters
    if p == -1: #No parameters
      return self.cmdlist.append([command.strip(), ])
    cmdname = command[:p]
    params = command[p + 1:]
    params = re.sub(r'\s*\)\s*$', '', params)
    params = [ x.strip() for x in params.split(",") if len(x.strip()) > 0]
    if cmdname == "INCLUDE":
      includefile = list(params)[0]
      includefile = fileLocate(includefile)
      log.debug("Including %s", includefile)
      for line in file(includefile):
        self.parseLine(line)
    else:
      return self.cmdlist.append([ cmdname, ] + list(params))
class PrintJob:
  """Controls the output and setup of a print job. """
  rascalpdf = None
  parser = None
  output = None
  landscape = False

  def __init__(self, output=None, pagesize=reportlab.lib.pagesizes.A4, landscape=False):
    """ fhandle should be a file like object. 
    """
    self.pagesize = pagesize
    self.landscape = landscape

    if output:
      if isinstance(output, basestring): #String means its a filename
        self.pdffile = file(output, "w+")
      else:
        self.pdffile = output #Must be a file handle or some other object that has a write method.
    else:
      self.pdffile = None

  def ontty(self):
    """ontty is needed because Rascal does some very non standard things with 
       The environment and the shell
    """
    return "TODO"

  def feed(self, fhandle=None):
    """Feed data to the pdf job"""
    if not self.pdffile:
      self.pdffile = tempfile.NamedTemporaryFile(suffix='_auto.pdf') #Temporary file with the work auto in it to force auto starting in terraterm.
    result = self._1stParse(fhandle)
    if result == _ISYAMLTEMPLATE:
      import YamlOffice  #Import as late as possible so we don't crash if openoffice is not installed.
      #The old perl system used this: system("/usr/local/rascalprinting_test/yamloffice -o $t $vvv < $tf");
      if hasattr(self.pdffile, 'name'):
        return YamlOffice.run(inputh=fhandle, output=self.pdffile.name)
      else: #Must be a stringIO buffer. Create a temp file then read it back into the buffer.
        t = tempfile.NamedTemporaryFile(suffix='.pdf')
        ret = YamlOffice.run(inputh=fhandle, output=t.name)
        t.seek(0)
        self.pdffile.truncate()
        self.pdffile.write(t.read())
        t.close()
        self.pdffile.seek(0)
        return ret
    else:
      self.rascalpdf = RascalPDF(self.pdffile, pagesize=self.pagesize, isLandscape=self.landscape)

      self.rascalpdf.info.producer = "Raspdf by Ed Pascoe <ed@pascoe.co.za>"
      self.rascalpdf.info.tile = "Rascal document"
      self.rascalpdf.info.subject = "Rascal document"

      self._2ndParse()
      self.rascalpdf.canvas.save()
      self.pdffile.flush()
    return True

  def _1stParse(self, fhandle):
    """Converts the incoming document into a series of functions to be executed"""
    self.parser = None
    line = fhandle.readline()

    if line.find("YMLTEMPLATE") > -1:
      return _ISYAMLTEMPLATE

    self.parser = _Parser()
    self.parser.addCommand('PRINTINIT')
    while len(line) > 0 :
      # -------- Strip any control characters -----------
      line = line.replace(chr(0x0f), '') # ^O
      line = line.replace(chr(0x1b), '') # ^[ Escape
      line = line.replace(chr(0x12), '') # ^R
      try: line = line.decode("utf-8")
      except UnicodeDecodeError: #Drop any non-readable characters.
        line = line.decode("utf-8", "replace") #Convert to unicode. Leaving out any characters that would cause issues.
        line = line.replace(u'\ufffd', '') #Remove the unicode unknown character from the text.

      # convert the line into function calls for 2nd parse later.
      self.parser.parseLine(line)
      line = fhandle.readline() #Get the next line.
    self.parser.addCommand('PRINTEND')
    lineno = 0
    for cmd in self.parser.cmdlist:
      log.debug("Cmd: %s Line: %s", cmd, lineno)
      lineno += 1
    return True

  def _2ndParse(self):
    """Generate the actual print job."""
    fncall = None
    partams = None
    lineno = 0
    for cmd in  self.parser.cmdlist:
      try:
        fncall = cmd[0]
        if len(cmd) > 1:
          params, kwargs = self.__args2kw(cmd[1:])
          self.rascalpdf.fnexec(fncall, *params, **kwargs)
        else:
          self.rascalpdf.fnexec(fncall)
        lineno += 1
      except:
        log.error("Failure on command %s line %s", cmd, lineno)
        raise
    log.debug("_2ndParse showPage")
    self.rascalpdf.canvas.showPage()

  def __args2kw(self, params):
    """For converting the xxpdf format parameters to arguments. 
       Converts params to a a tuple: (<array of non kw args>, <dict of kw args>)
    """
    args = []
    kw = {}
    for p in params:
      p = str(p)
      equalpos = p.find("=")
      if equalpos == -1 or p[0] == "=" or p[0] == '"' or p[0] == "'": #Be really sure this is not string we are mistaking for a named argument.
        args.append(p)
      else:
        k = p[:equalpos]
        if k.find(" ") > -1: #A space in the keyword part of the name means this is NOT a named argument
          args.append(p)
          continue
        else:
          v = p[equalpos + 1:].strip()
          if v[0] == '"' and v[-1] == '"': #Chop off any quotations around the entire string.
            v = v[1:-1]
          elif v[0] == "'" and v[-1] == "'": #Chop off any quotations around the entire string.
            v = v[1:-1]

          kw[k.strip()] = v
    return (args, kw)

if __name__ == "__main__":
  #Enable logging
  formatter = logging.Formatter("%(levelname)s %(module)s:%(lineno)d: %(message)s")
  output = logging.StreamHandler()
  output.setFormatter(formatter)
  log.addHandler(output)
  log.setLevel(logging.DEBUG)

  c = PrintJob(output="/tmp/a.pdf")
  c.feed(sys.stdin)


