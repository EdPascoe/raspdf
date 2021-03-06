#!/usr/bin/env python
# -*- coding: utf-8 -*-
# © Ed Pascoe 2011. All rights reserved.
# $Id:$
"""
Generate PDF reports designed to interact well with rascal.
Replacement for the old xxpdf program.
"""
__author__ = "Ed Pascoe <ed@pascoe.co.za>"
__format__ = "plaintext"
__version__ = "__VERSION__"
__copyright__ = "Ed Pascoe 2011. All rights reserved."
__license__ = "GNU LGPL version 2"
__status__ = "Production"

import logging
import optparse
import os, sys, time, tempfile, os.path
import reportlab.lib.pagesizes
import smtplib, string, random
import socket
from subprocess import *
from cStringIO import StringIO

def getVersion():
  """Returns the current version if we are running out of a git repository"""
  import re
  def __searchOne(search,lines):
    """Returns the re info for the first line that matches"""
    r = re.compile(search)
    for line in lines:
      s = r.search(line)
      if s: return s
    return False

  root = os.path.join(os.path.dirname(__file__), "..")
  try:
    if os.path.exists(os.path.join(root,".git")):
      gitdir = "--git-dir=" + os.path.join(root, ".git")
      branch =  list([ x for x in os.popen("git %s branch -a --no-color " % (gitdir) ,"r").readlines() if x.find('*') > -1 ])[0].strip()[2:]
      version = re.sub(r'v','', os.popen("git describe", "r").read().strip())
      return "RasPDF PDF Library. Version: gitsrc-%s %s" % (branch, version) #Eg: RasPDF PDF Library. Version: gitsrc-master 1.0.6-2-gd335725
    elif os.path.exists(os.path.join(root,".hg")):
      summary = os.popen("cd %s && hg summary" % (root)).readlines()
      tip = __searchOne(r'^parent: (\d+):(\S+) tip\s*$', summary)
      return "RasPDF PDF Library. Version: hgsrc %s.%s" % (tip.group(1),tip.group(2))
  except:
    raise
  return "RasPDF PDF library. Exported Source No version number."

def pwgen(pwlen=16):
  l = len(string.ascii_letters) - 1
  return "".join([ string.ascii_letters[random.randint(0,l)] for i in xrange(pwlen) ])


def main():
  """Main harness. The actual work is all done in RascalPDF"""

  usage = "Usage: %prog [<options>] \n" + __doc__+"\n"
  parser = optparse.OptionParser(usage)
  parser.add_option("-C", "--config", dest="config", type="string", default="xmmail.conf", help="Config file location")
  parser.add_option("-z", "--sz", "--zmodem", dest="zmodem", action="store_true", help="After generating the pdf file transfer via zmodem")
  parser.add_option("-w", "--web", "--web", dest="web", action="store_true", help="After generating the pdf file upload to webdocs and show location.")
  parser.add_option("-l", "--landscape", dest="landscape", action="store_true", default=False, help="Use landscape A4" )
  parser.add_option("--evince", dest="evince", action="store_true", help="After generating the pdf file display using evince")
  parser.add_option("-v", "--verbose", dest="verbose", action="store_true", help="Show debugging information")
  parser.add_option("-V", "--version", dest="version", action="store_true", help="Show running version")
  parser.add_option("--debug", dest="debug", action="store_true", default=False, help="Show debugging information")
  parser.add_option("--dsave", dest="debugsave", action="store_true", default=False, help="Debug save -- Save incoming command stream")
  parser.add_option("-f", "--outputfile", "--file", dest="outputfile", type="string", help="Send output to file with given name instead of a temp file.")
  parser.add_option("--tty", dest="tty", type="string", help="The running TTY to conenct to for zmodem")
  parser.add_option("-x", "--xxpdf", dest="xxpdf", action="store_true", help='Use xxpdf defaults including the broken A4 page size of 8.19" x 12.36" instead of 8.27" x 11.69"  ')
  parser.add_option("-d", "--printer", dest="printer", type="string", help='Send the pdf to given cups printer')
  parser.add_option("-p", "--realprinter", dest="realprinter", type="string", default=False, help='The replacement for -d for use when called as: xxprint -p Stores -d pdfwrite')
  parser.add_option("--to", dest="to", action="append", help="Address to send the mail to. May be specified multiple times or addresses may be comma separated.")
  parser.add_option("--cc", dest="cc", action="append", help="Addresses for the cc list. Same usage as --to")
  parser.add_option("--bcc", dest="bcc", action="append", help="Addresses for the bcc list. Same usage as --to")
  parser.add_option("--from", dest="mailfrom", type="string", help="Address to send the mail from. Read receipts will be sent back here if requested.")
  parser.add_option("-s", "--s", "--subject", dest="subject", default="", help="Message subject")
  parser.add_option("-m", "--message", dest="message", default="", help="Message body (If starts with a slash will be taken as filename for html body)")
  parser.add_option("--rr", "--readreceipt", dest="readreceipt", action="store_true", help="Request a read receipt on any outgoing email.")
  parser.add_option("-n", "--noattach",  dest="noattach", action="store_true", help="Do not attach any pdf report. (For using as a command line email program) ")
  parser.add_option("--secure", dest="secure", action="store_true", help="Set flags preventing alteration and add a write password. **SNAKEOIL**")

  (options, args) = parser.parse_args()

  log = logging.getLogger()

  formatter = logging.Formatter("%(levelname)s %(module)s:%(lineno)d: %(message)s")
  output = logging.StreamHandler()
  output.setFormatter(formatter)
  log.addHandler(output)
  log.setLevel(logging.WARNING)

  if options.verbose:  log.setLevel(logging.INFO)
  if options.debug:  log.setLevel(logging.DEBUG)

  import RasConfig
  RasConfig.load(options.config, {'readreceipt': 'False', 'xxpdf': 'True', 'noterraterm': 'True', 'zmodemterm': 'vt220, vt220a, vt320', 'secure': 'False' } )
  if options.readreceipt is None:
    setattr(options,'readreceipt',RasConfig.getBool('global','readreceipt'))
  if options.xxpdf is None:
    setattr(options,'xxpdf', RasConfig.getBool('global','xxpdf'))
  if options.secure is None:
    setattr(options,'secure',RasConfig.getBool('global','secure'))


  #Do the imports AFTER logging has been set up.
  import RascalPDF, RasConfig 

  outfile = None
  if options.version:
    if __version__ == "__" + "VERSION__":  #Making this one string confuses the version replacement routine when building the dist package.
      print getVersion()
    else:
      print __version__
    sys.exit(0)

  RasConfig.set('global','debug', options.debug)
  RasConfig.set('global','debugsave', options.debugsave)
    
  if options.outputfile:
    outfile = options.outputfile
    outhandle = file(outfile,"w+")
  elif options.zmodem:
    tf = tempfile.NamedTemporaryFile(suffix='_auto.pdf' ) #Temporary file with the work auto in it to force auto starting in terraterm.
    outfile = tf.name
    log.debug("Temporary outfile: %s", outfile)
    outhandle = tf
  else:
    outhandle = StringIO() #Store the file in memory for speed.

  if options.xxpdf: pagesize = (590, 890) # Use the old incorect page sizes from xxpdf.
  else: pagesize = reportlab.lib.pagesizes.A4
  log.debug("Page site is %s A4 is %s", pagesize, reportlab.lib.pagesizes.A4)

  start= time.time()
  c = RascalPDF.PrintJob(output=outhandle, pagesize=pagesize, landscape=options.landscape)
    
  if args: c.feed(file(args[0]))
  else: c.feed(sys.stdin)

  stop = time.time()
  log.info("Render time: %s seconds" % (stop - start))

  if options.secure:
    outhandle.flush()
    prepdf = tempfile.NamedTemporaryFile(suffix='presecure.pdf' ) #Temporary file with the work auto in it to force auto starting in terraterm.
    postpdf = tempfile.NamedTemporaryFile(suffix='postecure.pdf' ) #Temporary file with the work auto in it to force auto starting in terraterm.
    outhandle.seek(0)
    prepdf.write(outhandle.read())
    prepdf.flush()
    os.system("pdftk %s output %s owner_pw %s allow printing 2>&1" % ( prepdf.name, postpdf.name, pwgen() ))
    
    outhandle.seek(0)
    outhandle.truncate()
    postpdf.seek(0)
    outhandle.write(postpdf.read())
    outhandle.flush()
    prepdf.close()
    postpdf.close()
  
  if options.evince:
    if outfile is None:
      tf = tempfile.NamedTemporaryFile(suffix='.pdf' ) #Create a temporary file name. (WARNING THERE Is a risk of a race condition here )
      outfile = tf.name
      log.debug("Temporary outfile: %s", outfile)
      tf.close()
      f=file(outfile,"w")
      outhandle.seek(0)
      f.write(outhandle.read())
      f.flush()
      f.close()
      
    log.debug("OUTFILE: %s", outfile)
    os.system("xdg-open %s" % (outfile))

  zmodemterms = [x.strip() for x in RasConfig.get('global','zmodemterm').split(",")]


  if options.web or (options.zmodem and RasConfig.getBool('global','noterraterm') and os.environ['TERM'] not in zmodemterms):
    import shutil, pwd
    uname = pwd.getpwuid(os.getuid())[0]
    dstdir = os.path.join(RasConfig.get('global','webdocs','/tmp'),uname)
    if not os.path.exists(dstdir): os.makedirs(dstdir,mode=0777)
    dstfile = os.path.join(dstdir,os.path.basename(outfile))
    dsturl = RasConfig.get('global','weburl','file://tmp')
    dsturl = dsturl + "/" + uname + "/" + os.path.basename(outfile)
    shutil.copy(outfile, dstfile) 
    os.chmod(dstfile, 0777)
    os.system("clear")
    print "\n" * 10
    print "Your report is available here:\n\n      %s" % (dsturl)
    print "\n" * 10
    print "Hit <enter> to continue"
    if not options.tty: options.tty=os.environ['TTY']
    f=file(options.tty)
    f.readline()
    os.system("clear")

  elif options.zmodem:
    if not options.tty: options.tty=os.environ['TTY']
    resetstr = "; sleep 3 ; clear < %s > %s " % (options.tty, options.tty) #Complicated hack because sz has a habit of messing up the screen.
    cmd = "sz -eq %s < %s > %s %s " % (outfile, options.tty, options.tty, resetstr)
    log.debug( cmd)
    os.system(cmd)
    for cmd in [ "tput rmacs", "tput krfr", "clear", "echo ' '"   ] :
      cmdstr = cmd + " < %s > %s " % (options.tty, options.tty)
      os.system(cmdstr)

  if options.printer or options.realprinter:
    printer = (options.realprinter, options.printer)[not options.realprinter] 
    pipe = Popen("lp -d %s -s " % (printer) , shell=True, stdin=PIPE).stdin
    outhandle.flush()
    outhandle.seek(0)
    pipe.write(outhandle.read())
    pipe.close()

  if options.to:
    import RasEmail
    outhandle.flush()
    outhandle.seek(0)
    ishtml = False
    if options.message: 
      if options.message[0] == "/": #Must be a filename
        bodyhtml = file(options.message).read()
      else:
        bodyhtml = "<pre>" + options.message + "</pre>"
    else:
      bodyhtml = None
    msg = RasEmail.createEmail(tolist=options.to, subject=options.subject, mailfrom=options.mailfrom, bodyhtml=bodyhtml, bodytext=options.message, readreceipt=options.readreceipt, cclist=options.cc, bcclist=options.bcc)
    if not options.noattach:
      RasEmail.addAttachements(msg, (outhandle, 'report.pdf', 'application/pdf'))
    RasEmail.sendMail(tolist=options.to, mailfrom=options.mailfrom, msg=msg, cclist=options.cc, bcclist=options.bcc)

