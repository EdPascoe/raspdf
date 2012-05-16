
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import reportlab.pdfbase.ttfonts
import logging

log = logging.getLogger('root')
#BITWISE fields for toggling the font.
BOLD = 1
ITALIC = 2

  #Format: font: [ 'normal name', 'Bold name', 'italic name', 'italicbold name'
fonts = {
  'courier': [ 'Courier', 'Courier-Bold', 'Courier-Oblique', 'Courier-BoldOblique'],
  'helvetica': [ 'Helvetica', 'Helvetica-Bold', 'Helvetica-Oblique', 'Helvetica-BoldOblique'],
  'symbol': ['Symbol'],
  'times' : [ 'Times-Roman', 'Times-Bold', 'Times-Italic', 'Times-BoldItalic' ],
  'dingbat': [ 'ZapfDingbats' ]
}

class Point:
  """Tracks x and y coordinates"""
  x = 0
  y = 0
  saved = []

  def __init__(self,x=0,y=0):
    self.x = x
    self.y = y
    self.saved = []

  def set(self, x=None, y=None, p=None):
    """Set x and y coords. P if used is a tuple (x,y) as returned by a previous call to get."""
    if x is not None: self.x = int(x)
    if y is not None: self.y = int(y)
    if isinstance(p, list) or isinstance(p, tuple):
      self.x = p[0]
      self.y = p[1]
  
  def get(self):
    """Returns a tuple of current position: (x,y)"""
    return (self.x, self.y)

  def push(self):
    """Saves the current location(pushes to the internal stack"""
    self.saved.append((self.x, self.y))

  def pop(self):
    """Restores the current location from the internal stack. 
       Raises IndexError if stack is empty
    """
    try:
      p = self.saved.pop()
      self.x , self.y = p
    except IndexError:
      raise IndexError("There are no saved locations to restore")
 
  def __unicode__(self):
    return u"Point(%s,%s)" % (self.x, self.y)

  def __str__(self):
    return unicode(self).encode('utf-8')

class FontTracker:
  """Handle fonts, sizes italic etc."""
  italic = False
  bold = False
  size = 10
  fontname = "courier"
  fileLocator = None

  def __init__(self, **args):
    for k in args.keys():
      setattr(self, k, args[k])
    self.fonts = fonts[self.fontname]
  
  def set(self, bold=None, italic=None, fontname=None, size=None):
    if bold is not None: self.bold = bold
    if italic is not None: self.italic = italic
    if fontname is not None: 
      self.fontname = fontname
      if not fonts.has_key(fontname):
        self._loadFont(fontname)
      self.fonts = fonts[fontname]
    if size is not None: self.size = size

  def _loadFont(self, fontname):
    global fonts
    if self.fileLocator: 
      fontfile = self.fileLocator(fontname)
    else:
      fontfile = fontname
    log.debug("TTFont(%s, %s)", fontname, fontfile)
    try:
      font = TTFont(fontname, fontfile)
    except reportlab.pdfbase.ttfonts.TTFError, e: 
      if str(e).find("Font does not allow subsetting/embedding") > -1:
        print ""
        print "The font you are trying to load is set to not allow embedding. Use another font or edit"
        print "The file ttfonts.py mentioned below, go to the mentioned line and comment out the "
        print "raise line and the 'if' statement above it. (Probably line 527 and 528)"
        print ""
      raise

    log.debug("Font: %s", font)
    pdfmetrics.registerFont(font)
    fonts[fontname] = [ fontname, fontname, fontname, fontname ]  #Use the same font no matter what styles are specified

  def getFontName(self):
    """Name of font to use."""
    fontnumber = 0
    if self.italic: fontnumber = fontnumber | ITALIC
    if self.bold: fontnumber = fontnumber | BOLD
    return self.fonts[fontnumber]

if __name__ == "__main__":
  f= FontTracker(fontname='times', size=10)
  print dir(f)
  f.set(bold=True, italic=True)
  print f.size, f.getFontName()

