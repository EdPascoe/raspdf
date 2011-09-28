#!/usr/bin/env python
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
from reportlab.pdfgen import canvas
import reportlab.lib.pagesizes
from reportlab.platypus.flowables import Image
from Point import Point, FontTracker
import logging

log = logging.getLogger("root")

import re, os, os.path, sys, tempfile 
from copy import copy, deepcopy
from reportlab.pdfbase.pdfmetrics import stringWidth

cnstNORMAL = 0
cnstBOLD = 1
cnstITALIC = 2

class RascalPDFException(Exception):
  """Errors thrown by the PDF system"""

class RascalPDF:
  """PDF library for use with rascal. Tries to be a compatible with the old perl xxpdf library"""
  canvas = None
  font_size = 10 #Default font size
  #Margins
  lmargin = 20
  tmargin = 20
  line="NOT YET INITITALIZED"
  fileLocator = None

  reporttitle="Rascal Report";

  def  __init__(self, pdffile, pagesize=reportlab.lib.pagesizes.A4, isLandscape=False, fileLocator=None):
    self.pdffile = pdffile
    if isLandscape:
      pagesize = reportlab.lib.pagesizes.landscape(pagesize)
    else:
      pagesize = reportlab.lib.pagesizes.portrait(pagesize)

    self.fileLocator = fileLocator #function to call for locating files if they are not in current directory
    self.canvas = canvas.Canvas(self.pdffile, pagesize, verbosity=1)
    self.canvas.setPageCompression(1)

    self.info = self.canvas._doc.info #The PDF document info
    self.pagesize = pagesize

    self.pos = Point(x=self.lmargin, y= self.pagesize[1] - self.tmargin)
    self.font=FontTracker(fileLocator=self.fileLocator)

    self.boxlist  = {} # for drawing boxes
    self.linelist = {} # for drawing lines

    self.start_newpage = 1;
    self.printingbegun = False;

    self.picturelist_key = {}
    self.picturelist_h = {}
    self.picturelist_w = {}

    self.functions = {}

    # Prepare  fonts
    self.courier = self.helvetica = {}
    self.courier[cnstNORMAL]               = 'Courier';
    self.courier[cnstBOLD]                 = 'Courier-Bold';
    self.courier[cnstITALIC]               = 'Courier-Oblique';
    self.courier[cnstBOLD + cnstITALIC]   = 'Courier-BoldOblique';
    self.helvetica[cnstNORMAL]             = 'Helvetica';
    self.helvetica[cnstBOLD]               = 'Helvetica-Bold';
    self.helvetica[cnstITALIC]             = 'Helvetica-Oblique';
    self.helvetica[cnstBOLD + cnstITALIC] = 'Helvetica-BoldOblique';
    self.__registerkeys()


  def fnexec(self, fnname, *params):
    """Lookup fnname in the functions list and execute the given function call."""
    try:
      fn = self.functions[fnname]
    except KeyError:
      raise RascalPDFException("Function %s has not been registered" % (fnname))

    try:
      if len(params) == 0:
        return fn()
      else:
        return fn(*params)
    except:
      log.error("Failure executing %s(%s)" ,fnname, params)
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
    name= self.stripQuotes(name)

    self.font.set(fontname=name)     
  
  def stripQuotes(self, msg):
    """Removes and quotes surrounding given string"""
    if msg[0] == '"' and msg[-1] == '"': #Filename has quotes around it which need to be removed.
      msg = msg[1:-1]
    return msg

  def _regfnFontSetColor(self, r, g, b):
    """For registerkeys, set font color"""
    self.canvas.setFillColorRGB(r,g,b)

  def _regfnCopiesSet(self, numcopies):
    """For registerkeys, set number of copies"""
    self.numcopies = numcopies

  def __registerkeys(self):
    """Create all the function mappings for lookups later."""
    self.functions = {}
    self.functions["PRINTINIT"]= self.printinit
    self.functions["PRINTEND"]= self.printend
    self.functions["LEND"]=     self.textlineend #Called at auto at end of line

    self.functions["BOLDON"]=  self._regfnFontSetBoldTrue
# sub{ $fontSTYLE = $fontSTYLE | $cnstBOLD; });
    self.functions["B1"]=  self._regfnFontSetBoldTrue
    self.functions["BOLDOFF"]=  self._regfnFontSetBoldFalse
    self.functions["B0"]= self._regfnFontSetBoldFalse
    self.functions["ITALICON"]= self._regfnFontSetItalicTrue
    self.functions["I1"]= self._regfnFontSetItalicTrue
    self.functions["ITALICOFF"]=self._regfnFontSetItalicFalse
    self.functions["I0"]=self._regfnFontSetItalicFalse

    self.functions["SETFONT16"] = self._regfnFontSetSize16
    self.functions["SETFONT12"] = self._regfnFontSetSize12
    self.functions["SETFONT10"] = self._regfnFontSetSize10
    self.functions["SETFONT8"]= self._regfnFontSetSize8
    self.functions["SETFONT6"]= self._regfnFontSetSize6
    self.functions["SETFONT"]= self._regfnFontSetSizex
    self.functions["SF"]=  self._regfnFontSetSizex

    self.functions["FONTNAME"]= self._regfnFontSetName
    self.functions["SETCOLOR"]= self._regfnFontSetColor

    self.functions["COPIES"]= self._regfnCopiesSet

    self.functions["BOXS"]= self.boxstart #Mark the top left corner of a box
    self.functions["BOXE"]= self.boxend
    self.functions["RBOXS"]= self.boxstart #Mark the top left corner of a box
    self.functions["RBOXE"]= self.boxendround

    self.functions["LINES"]= self.linestart
    self.functions["L1"]=    self.linestart
    self.functions["LINEE"]= self.lineend
    self.functions["L0"]=    self.lineend

    self.functions["LINEWIDTH"]=self.linewidth
    self.functions["LW"]=       self.linewidth

    self.functions["NEWPAGE"] = self.newPage
    self.functions["SHOWLINE"] = self.output

    self.functions["PIC"] = self.picture

    self.functions["UP"] = self.up
    self.functions["DOWN"] = self.down
            
    self.functions["MA"] = self.moveabsolute
    self.functions["MR"] = self.moverelative
    self.functions["RIGHT"] = self.right

    self.functions["printstring"] = self.output
    self.functions["newline"]     = self.newline

  def up(self, lines, fsize=None):
    lines=int(lines)
    if fsize is None: fsize = self.font.size
    self.pos.y =  self.pos.y + (lines * fsize) 
    self.pos.x =  self.lmargin; 

  def down(self, lines, fsize=None):
    lines=int(lines)
    if fsize is None: fsize = self.font.size
    self.pos.y =  self.pos.y - (lines * int(fsize) )
    self.pos.x =  self.lmargin; 

  def right(self, c): 
    c= int(c)
    self.xpos =  self.lmargin + self.calcWidth("_"  * c )
    
  def moverelative(self, x, y):
    self.pos.x += int(x);
    self.pos.y += int(y);

  def moveabsolute(self, x, y):
    self.pos.x = int(x);
    self.pos.y = int(y);

  def printinit(self):
    """Initialize printing system"""
    log.debug("Inititializing")
    self.pos = Point(x=self.lmargin, y= self.pagesize[1] - self.tmargin)

  def printend(self):
    """End printing system"""
  
  def textlineend(self):
    """Called at line end."""
    #log.debug("textlineend")
    if self.pos.y <= self.font.size:
      log.debug("Curent pos %s <= %s, new page", self.pos.y, self.font.size)
      self.newPage()
      self.pos.y = self.height - self.tmargin
      #self.print_string(self.line)
      self.pos.x = self.lmargin
    else:
      self.pos.y -= self.font.size;
      self.pos.x = self.lmargin;
    
#    r= re.search(r'(.*?)\cL(.*)', self.line)
#    if self.pos.y <= self.font.size:
#      self.newPage()
#      self.pos.y = self.height - self.tmargin
#      self.print_string(self.line)
#      self.pos.x = self.lmargin
#      self.pos.y -=  self.font.size;
#    elif r:
#      if len(r.group(1)) > 0:
#        self.print_string(r.group(1))
#      self.newPage();
#      self.pos.y = self.height - self.tmargin
#      self.pos.x = self.lmargin
#      if len(r.group(2)) > 0:
#        self.print_string(r.group(2))
#        self.pos.y -=  self.font.size
#    else:
#       self.print_string(self.line)
#       self.pos.y -= self.font.size;
#       self.pos.x = self.lmargin;

  def newline(self):
    """handle \n"""
    self.textlineend() 

  def boxstart(self, boxname):  
    """Remember the posistion of the start of a box."""
    self.boxlist[boxname]= copy(self.pos)

  def  boxend(self, boxname):
    if not self.boxlist.has_key(boxname):
      return
    s = self.boxlist[boxname]
    e = self.pos
    path = self.canvas.beginPath()
    path.moveTo(s.x, s.y)
    path.lineTo(e.x, s.y)
    path.lineTo(e.x, e.y)
    path.lineTo(s.x, e.y)
    path.lineTo(s.x, e.y)
    self.canvas.drawPath(path, stroke=1, fill=1)

  def boxendround(self, boxname, offset=8):
    """Complete a box with rounded corners"""
    if not self.boxlist.has_key(boxname): return

    s = self.boxlist[boxname]
    e = self.pos

    path = self.canvas.beginPath()
    #Top
    path.moveTo(s.x+offset,s.y);  
    path.lineTo(e.x-offset,s.y);

    #Top Right Corner
    path.moveTo(e.x-offset,s.y);
    path.curveTo(e.x,s.y,e.x,s.y-offset,e.x,s.y-offset);

    #Right
    path.moveTo(e.x,s.y-offset); 
    path.lineTo(e.x,e.y+offset);

    #Bottom Right corner
    path.curveTo(e.x,e.y,e.x-offset,e.y,e.x-offset,e.y);

    #Bottom
    path.lineTo(s.x+offset,e.y);

    #Bottom Left Corner
    path.curveTo(s.x,e.y,s.x,e.y+offset,s.x,e.y+offset);

    #Left
    path.lineTo(s.x,s.y-offset);

    #Top Left Corner
    path.curveTo(s.x,s.y,s.x+offset,s.y,s.x+offset,s.y);

    self.canvas.drawPath(path, stroke=1, fill=1)
  
  def linestart(self, linename):  #Remember the posistion of the start of a line.
    self.linelist[linename] = deepcopy(self.pos)

  def lineend(self, linename):
    s= self.linelist.get(linename, None)
    if s is None: return
    x1 = s.x
    y1 = s.y
    x2 = self.pos.x
    y2 = self.pos.y

    path = self.canvas.beginPath()
    path.moveTo(x1,y1);
    path.lineTo(x2,y2);
    self.canvas.drawPath(path, stroke=1, fill=1)

  def linewidth(self, width):
    self.canvas.setLineWidth(width)

  def output(self, line):
    if len(line)==0: return

    if line[-1] != "\n":
      self.print_string(line)
      self.pos.x +=  self.calcWidth(line)
      return 

    r = re.search(r'(.*?)\cL(.*)', line)
    if self.pos.y <= self.font.size:
      self.newPage();
      self.pos.y = self.height - self.tmargin
      self.print_string(line)
      self.pos.x = self.lmargin
      self.pos.y -= self.font.size
    
    elif r: #Form Feed
      self.print_string(r.group(1));
      self.newPage();
      self.pos.y = self.height - self.tmargin
      self.pos.x = self.lmargin
      self.print_string(r.group(2))
      self.pos.y - self.fint.szie
    else:
       self.print_string(line);
       self.pos.y -= self.font.size
       self.pos.x  = self.lmargin
 
  def startDoc(self):
    self.newpage(); 
    self.start_newpage = 0;
    self.pos.set(x=self.lmargin, y=0)

  def newPage(self):
    """Set the flag so that the next write to the screen will create a new page"""
    self.start_newpage = 1
    self.pos.set(x=0, y=self.lmargin)

  def real_newPage(self):
    """This does the real newpage
    """
    self.start_newpage = 0;
    if (self.printingbegun):
     self.canvas.showPage()
    else:
     self.printingbegun=1;

  def calcTextWidth(self, line):
    return self.caclWidth(line);

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
    return stringWidth(text, self.font.getFontName(), self.font.size) 

  def useFont(self, textobject, font):
    textobject.setFont("Helvetica-Oblique", 14)

  def print_string(self, msg):
    """Prints string on page at current cursor location."""
    textobject = self.canvas.beginText()
    self.canvas.setFont(self.font.getFontName(), self.font.size) 
    #log.debug(" self.canvas.drawText(%s, %s, %s)", self.pos.x, self.pos.y, msg)
    self.canvas.drawString(self.pos.x, self.pos.y, msg)
 

  def picture(self, fname, imgwidth=None, imgheight=None):
    """Insert picture into pdf. If imgwidth and imgheight are not none they will be used to reposition the cursor after the insert."""
    x = int(self.pos.x)
    y = int(self.pos.y)
    if imgwidth:
      imgwidth = int(imgwidth)
    if imgheight:
      imgheight = int(imgheight)
      y = y -  imgheight 
    if self.fileLocator:
      fname=self.fileLocator(fname)
    
    if not os.path.exists(fname):
      raise RascalPDFException("Unable to location file %s" % (fname))
    self.canvas.drawImage(fname, x, y, imgwidth, imgheight)

  def pixels2Points(self, pixels):
    """returns the number of points taken up by given number of pixels
       1 point is 1/72 of an inch
    """


class _Parser:
  """Contains the print job broken into an array of python function calls.
    Usage:  p = _Parser()
            for line in file("Blah"): p.parseLine(line)
            print "Function calls: ", print p.cmdlist
  """
  fileLocator = None
  def __init__(self, fileLocator = None):
    self.cmdlist = []
    self.fileLocator = fileLocator

  def parseLine(self, line):
    if len(line)==0: return  #Blank line
    hasnewline= line[-1] == "\n"
    line = line.rstrip()
    r=re.search(r'^(.*?){\$(.*?)}(.*)$', line)
    if r:
      leadtext=r.group(1)
      cmd=r.group(2)
      restofline = r.group(3)
      self.cmdlist.append(("printstring", leadtext))
      self.addCommand(cmd)
      self.parseLine(restofline)
    else:
      self.cmdlist.append(("printstring", line))

    if hasnewline:
      self.cmdlist.append(("newline",))

  def addCommand(self, command):
    command = command.strip()
    cmdname = None
    cmdparams = []
    p = command.find("(") #Find the start of any parameters
    if p == -1: #No parameters
      return self.cmdlist.append( [command.strip(),])
    cmdname = command[:p]
    params = command[p+1:]
    params = re.sub(r'\s*\)\s*$','',params)
    params = [ x.strip() for x in params.split(",") if len(x.strip()) > 0]
    if cmdname == "INCLUDE":
      includefile = list(params)[0]
      if self.fileLocator:
        includefile = self.fileLocator(includefile)
      log.debug("Including %s", includefile)
      for line in file(includefile):
        self.parseLine(line)
    else:
      return self.cmdlist.append([ cmdname,] +  list(params) )
    

class PrintJob:
  """Controls the output and setup of a print job. """
  rascalpdf = None
  parser = None
  output = None
  landscape = False
  imagedirs = [".", "./images"];
  
  def __init__(self, output=None, landscape=False ):
    """ fhandle should be a file like object. 
    """
    self.landscape = landscape
    self.imagedirs = copy(self.imagedirs) #We don't want the class version of this so we can edit without worrying.
    if output:
      if isinstance(output, basestring): #String means its a filename
        self.pdffile = file(output,"w+")
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
      self.pdffile = tempfile.NamedTemporaryFile(suffix='_auto.pdf' ) #Temporary file with the work auto in it to force auto starting in terraterm.
    
    self._1stParse(fhandle)
    self.rascalpdf = RascalPDF(self.pdffile, pagesize=reportlab.lib.pagesizes.A4, isLandscape=self.landscape, fileLocator=self.fileLocator)

    self.rascalpdf.info.producer = "xxpdf2 by Ed.Pascoe <ed@pascoe.co.za>"
    self.rascalpdf.info.tile="Rascal document"
    self.rascalpdf.info.subject="Rascal document"

    self._2ndParse()
    self.rascalpdf.canvas.save()
    self.rascalpdf.fileLocator = None #Kill the circular reference so gc will work correctly.
    self.pdffile.flush()
    return True

  def _1stParse(self, fhandle):
    """Converts the incoming document into a series of functions to be executed"""
    self.parser = _Parser(fileLocator=self.fileLocator)
    self.parser.addCommand('PRINTINIT')
    for line in fhandle:
      self.parser.parseLine(line)
    self.parser.addCommand('PRINTEND')
    #for cmd in self.parser.cmdlist: log.debug("Cmd: %s", cmd)

  def _2ndParse(self):
    """Generate the actual print job."""
    fncall = None
    partams = None
    for cmd in  self.parser.cmdlist:
      fncall = cmd[0]
      if len(cmd) > 1:
        params = cmd[1:]
        self.rascalpdf.fnexec(fncall, *params)
      else:
        self.rascalpdf.fnexec(fncall)
    self.rascalpdf.canvas.showPage()

  def fileLocator(self, image):
    """Search  self.imagedirs for the image or file to include"""
    if image[0] == '"' and image[-1] == '"': #Filename has quotes around it which need to be removed.
      image = image[1:-1]
    if os.path.exists(image): 
      return image #Full path, already exists.
    for d in self.imagedirs:
      fname = os.path.join(d, image)
      if os.path.exists(fname): 
          return fname
    raise RascalPDFException("Could not find image or include file %s" % ( image))
    

if __name__ == "__main__":

  #Enable logging
  formatter = logging.Formatter("%(levelname)s %(module)s:%(lineno)d: %(message)s")
  output = logging.StreamHandler()
  output.setFormatter(formatter)
  log.addHandler(output)
  log.setLevel(logging.DEBUG)

  c = PrintJob(output="/tmp/a.pdf" )
  c.feed(sys.stdin)


