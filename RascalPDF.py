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
from Point import Point, FontTracker

import re, os, os.path, sys, tempfile, copy


class RascalPDF:
  """PDF library for use with rascal. Tries to be a compatible with the old perl xxpdf library"""
  canvas = None
  font_size = 10 #Default font size
  #Margins
  lmargin = 20
  tmargin = 20
  imagedirs = [".", "./images"];

  reporttitle="Rascal Report";

  def  __init__(self, pdffile, pagesize=reportlab.lib.pagesizes.A4, isLandscape=False):
    if isLandscape:
      pagesize = reportlab.lib.pagesizes.landscape(pagesize)
    else:
      pagesize = reportlab.lib.pagesizes.portrait(pagesize)
    self.canvas = canvas.Canvas(pdffile, pagesize, verbosity=1)
    self.pagesize = pagesize

    self.pos = Point(x=self.lmargin, y= self.pagesize[1] - self.tmargin)
    self.font=FontTracker()

    self.boxlist  = {} # for drawing boxes
    self.linelist = {} # for drawing lines

    self.start_newpage = 1;
    self.printingbegun = undef;

    self.picturelist_key = {}
    self.picturelist_h = {}
    self.picturelist_w = {}

    self.imagedirs = copy.copy(self.imagedirs) #We don't want the class version of this so we can edit without worrying.
    self.functions = {}

    # Prepare  fonts
    self.courier[cnstNORMAL]               = 'Courier';
    self.courier[cnstBOLD]                 = 'Courier-Bold';
    self.courier[cnstITALIC]               = 'Courier-Oblique';
    self.courier[cnstBOLD + cnstITALIC]   = 'Courier-BoldOblique';
    self.helvetica[cnstNORMAL]             = 'Helvetica';
    self.helvetica[cnstBOLD]               = 'Helvetica-Bold';
    self.helvetica[cnstITALIC]             = 'Helvetica-Oblique';
    self.helvetica[cnstBOLD + cnstITALIC] = 'Helvetica-BoldOblique';


  def save(self):
    self.canvas.save()

  def __registerkeys(self):
    """Create all the function mappings for lookups later."""
    self.functions = {}
    self.functions["PRINTINIT"]= self.printinit
    self.functions["PRINTEND"]= self.printend
    self.functions["LEND"]=     self.textlineend #Called at auto at end of line

    self.functions["BOLDON"]=  lambda self: self.font.set(bold=True)
# sub{ $fontSTYLE = $fontSTYLE | $cnstBOLD; });
    self.functions["B1"]=   lambda self: self.font.set(bold=True)
    self.functions["BOLDOFF"]=  lambda self: self.font.set(bold=False)
    self.functions["B0"]= lambda self: self.font.set(bold=False)
    self.functions["ITALICON"]= lambda self: self.font.set(italc=True)
    self.functions["I1"]= lambda self: self.font.set(italc=True)
    self.functions["ITALICOFF"]=lambda self: self.font.set(italc=False)
    self.functions["I0"]=lambda self: self.font.set(italc=False)

    self.functions["SETFONT16"] = lambda self: self.font.set(size=16)
    self.functions["SETFONT12"] = lambda self: self.font.set(size=12)
    self.functions["SETFONT10"] = lambda self: self.font.set(size=10)
    self.functions["SETFONT8"]= lambda self: self.font.set(size=8)
    self.functions["SETFONT6"]= lambda self: self.font.set(size=6)
    self.functions["SETFONT"]= lambda self,x: self.font.set(size=x)
    self.functions["SF"]=  lambda self,x: self.font.set(size=x)     
    self.functions["FONTNAME"]= lambda self,x: self.font.set(fontname=x)     
    self.functions["SETCOLOR"]= lambda self,r,g,b: self.canvas.setFillColorRGB(r,g,b)

    self.functions["COPIES"]= lambda self,n: self.numcopies  = n

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

  def up(self, lines, fsize=None):
    if fsize is None: fsize = self.font.size
    self.pos.y =  self.pos.y + (lines * fsize) 
    self.pos.x =  self.lmargin; 

  def down(self, lines, fsize):
    if fsize is None: fsize = self.font.size
    self.pos.y =  self.pos.y - (lines * fsize) 
    self.pos.x =  self.lmargin; 

  def right(self, c): 
    self.xpos =  self.lmargin + self.calcWidth("_"  * c )
    
  def moverelative(self, x, y):
    self.pos.x += x;
    self.pos.y += y;

  def moveabsolute(self, x, y):
    self.pos.x = x;
    self.pos.y = y;

  def printinit(self):
    """Initialize printing system"""

  def printend(self):
    """End printing system"""
  
  def textlineend(self):
    """Called at line end."""
    r= re.search(r'(.*?)\cL(.*)', self.line)
    if self.pos.y <= self.font.size):
      self.newPage()
      self.pos.y = self.height - self.tmargin
      self.print_string(self.line)
      self.pos.x = self.lmargin
      self.pos.y -=  self.font.size;
    elif r:
      if len(r.group(1)) > 0:
        self.print_string(r.group(1))
      self.newPage();
      self.pos.y = self.height - self.tmargin
      self.pos.x = self.lmargin
      if len(r.group(2)) > 0:
        self.print_string(r.group(2))
        self.pos.y -=  self.font.size
    else:
       self.print_string(self.line)
       self.pos.y -= self.font.size;
       self.pos.x = self.lmargin;

  def boxstart(self, boxname):  
    """Remember the posistion of the start of a box."""
    self.boxlist[boxname]= self.pos.get()

  def  boxend(self, boxname):
    my ($x1,$x2,$y1,$y2);
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

    my ($x1,$x2,$y1,$y2);
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
  
  def linestart(self, linename) {  #Remember the posistion of the start of a line.
    self.linelist[linename] = self.pos.get()

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

  def output(line):
    if line[-1] != "\n":
     self.print_string(line);
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
      self.print_string(r.group(2));
      self.pos.y - $font_size;
    else:
       self.print_string(line);
       self.pos.y -= self.font.size;
       self.pos.x  = $lmargin;
 
  def startDoc(self):
    self.newpage(); 
    self.start_newpage = 0;
    self.pos.set(x=self.lmargin, y=0)
    #$pdf->info($reporttitle,"Auto generated", 'XMPrint by Ed Pascoe ed_xmprint@pascoe.co.za', "",""); 

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
    """TODO"""
    return 123;

  def calcWidth(self, line):
     w = $pdf->calcTextWidth($line);
     return $w;

  def useFont(self, textobject, font):
    textobject.setFont("Helvetica-Oblique", 14)


  def print_string(self, msg):
    """Prints string on page at current cursor location."""
    textobject = self.canvas.beginText()
    self.setfont(textobject) 
    textobject.textOut(line)
    self.canvas.drawText(textobject)
 
  def imageNameExpand(self, image):
    """Search  self.imagedirs for the image"""
    if os.path.exists(image): return image #Full path, already exists.
    for d in self.imagedirs:
      fname = os.path.join(d, image)
      if os.path.exists(fname): 
          return fname
    return None #Image not found

  def picture(fname, imgwidth=None, imgheight=None):
    """Insert picture into pdf"""
    fname=self.imageNameExpand(fname);
    if fname is None: return None #No picture no continue
    self.canvas.drawInlineImage(self, image, self.pos.x, self.pos.y, imgwidth, imgheight)

class PrintJob:
  """Controls the output and setup of a print job. """
  rascalpdf = None
  
  def __init__(self, landscape=False, fhandle ):
    """ fhandle should be a file like object. 
    """
    self.pdffile = tempfile.NamedTemporaryFile(suffix='_auto.pdf' ) #Temporary file with the work auto in it to force auto starting in terraterm.
    self.rascalpdf = (self.pdffile, pagesize=reportlab.lib.pagesizes.A4, isLandscape=landscape)
    self.__createPrintJob(fhandle)

  def ontty(self):
    """ontty is needed because Rascal does some very non standard things with 
       The environment and the shell
    """
    return "TODO"
  
  def _1stParse(self):
    """Converts the incoming document into a series of functions to be executed"""
    $self->{POUT}="";
    $self->_addtag('{$PRINTINIT}');
    my $handle=$self->{inhandle};
    for line in self.inhandle:
      _parseDoc($_);
    $self->_settag('{$PRINTEND}');

  def _parseLine(line):
    """Split line into _addtag statements"""
    p = 

  def _addtag(self, line){
     rvar="";
     fncall=""; #Was this a procedure call with parameters

     $line =~ s/^\{//; #Remove the curly brackets
     $line =~ s/\}$//;
     if ($line =~ /(.*?)(\(.*\))/){ #Extract the parameters
        $line=$1;
        $fncall=$2;
     }
     if ($line eq '$INCLUDE'){
        $self->_include($fncall);
        return;
     }
     my $l = _drvCnvt($line);
      
     $cmd="\$rvar=$l;";
     eval "$cmd";
     if ($@){
        die "Error on $cmd: $@";
     }
     if (ref($rvar) eq "CODE"){
        $self->{POUT}.="&$l$fncall;\n";
     } else {
        return if (length($rvar) ==0);
        $self->{POUT}.="\$self->{POUT} .= '$rvar';\n";
     }

  def __createPrintJob(self, fhandle): 
   """Expands the text into the final print job
   """
   self.inhandle = fhandle
   self._1stParse()
   self._2ndParse()
   return True

if __name__ == "__main__":
  c = printJob(sys.stdin)

