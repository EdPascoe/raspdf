from reportlab.pdfgen import canvas
import reportlab.lib.pagesizes


class RascalPDF:
  canvas = None
  font_size = 10 #Default font size
  #Margins
  lmargin = 20
  tmargin = 20

  #Constants for the fonts
  cnstNORMAL=0;
  cnstBOLD=1;
  cnstITALIC=2;
  #Default fonts and sizes
  fontSTYLE=$cnstNORMAL;
  reporttitle="Rascal Report";
  self.boxlist  = {} # for drawing boxes
  self.linelist = {} # for drawing lines

  xpos = 0
  ypos = 0


  def  __init__(self, pdffile, pagesize=reportlab.lib.pagesizes.A4, isLandscape=False):
    if isLandscape:
      pagesize = reportlab.lib.pagesizes.landscape(pagesize))
    else:
      pagesize = reportlab.lib.pagesizes.portrait(pagesize))
    self.canvas = canvas.Canvas(pdffile, pagesize, verbosity=1)
    self.pagesize = pagesize

    self.xpos = self.lmargin
    self.ypos = self.pagesize[1] - self.tmargin
    self.boxlist = {}
    self.linelist = {}

    self.start_newpage = 1;
    self.printingbegun = undef;

    self.picturelist_key = {}
    self.picturelist_h = {}
    self.picturelist_w = {}
    self.IMAGEDIRS = []

  def save(self):
    self.canvas.save()


def hello(c):
  c.drawString(100,100,"Hello World")

c = canvas.Canvas("hello.pdf")
hello(c)
c.showPage()
c.save()
