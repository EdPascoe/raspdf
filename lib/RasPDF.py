#!/usr/bin/env python
# -*- coding: utf-8 -*-
# © Ed Pascoe 2011. All rights reserved.
"""
Generate PDF reports designed to interact well with rascal.
Replacement for the old xxpdf program.
"""
__author__ = "Ed Pascoe <ed@pascoe.co.za>"
__format__ = "plaintext"
__version__ = "$Id$"
__copyright__ = "Ed Pascoe 2011. All rights reserved."
__license__ = "GNU LGPL version 2"
__status__ = "Production"


import logging
import optparse
import os, sys, time, tempfile
import reportlab.lib.pagesizes
import smtplib
import socket
from subprocess import *
from cStringIO import StringIO

import RascalPDF, RasConfig

def main():
  """Main harness. The actual work is all done in RascalPDF"""
  usage = "Usage: %prog [<options>] \n" + __doc__+"\n"
  parser = optparse.OptionParser(usage)
  parser.add_option("-z", "--sz", "--zmodem", dest="zmodem", action="store_true", help="After generating the pdf file transfer via zmodem")
  parser.add_option("-l", "--landscape", dest="landscape", action="store_true", default=False, help="Use landscape A4" )
  parser.add_option("--evince", dest="evince", action="store_true", help="After generating the pdf file display using evince")
  parser.add_option("-v", "--verbose", dest="verbose", action="store_true", help="Show debugging information")
  parser.add_option("--debug", dest="debug", action="store_true", help="Show debugging information")
  parser.add_option("-f", "--outputfile", dest="outputfile", type="string", help="Send output to file with given name instead of a temp file.")
  parser.add_option("--tty", dest="tty", type="string", help="The running TTY to conenct to for zmodem")
  parser.add_option("-x", "--xxpdf", dest="xxpdf", action="store_true", help='Use xxpdf defaults including the broken A4 page size of 8.19" x 12.36" instead of 8.27" x 11.69" ')
  parser.add_option("-d", "--printer", dest="printer", type="string", help='Send the pdf to given cups printer')
  parser.add_option("--to", dest="to", action="append", help="Address to send the mail to. May be specified multiple times or addresses may be comma separated.")
  parser.add_option("--cc", dest="cc", action="append", help="Addresses for the cc list. Same usage as --to")
  parser.add_option("--bcc", dest="bcc", action="append", help="Addresses for the bcc list. Same usage as --to")
  parser.add_option("--from", dest="mailfrom", type="string", help="Address to send the mail from. Read receipts will be sent back here if requested.")
  parser.add_option("--subject", dest="subject", default="", help="Message subject")
  parser.add_option("--rr", "--readreceipt", dest="readreceipt", action="store_true", default=False, help="Request a read receipt on any outgoing email")

  (options, args) = parser.parse_args()

  log = logging.getLogger("root")

  formatter = logging.Formatter("%(levelname)s %(module)s:%(lineno)d: %(message)s")
  output = logging.StreamHandler()
  output.setFormatter(formatter)
  log.addHandler(output)
  log.setLevel(logging.WARNING)

  if options.verbose:  log.setLevel(logging.INFO)
  if options.debug:  log.setLevel(logging.DEBUG)

  start= time.time()
  outfile = None
  if options.outputfile:
    outfile = options.outputfile
    outhandle = file(outfile,"w")
  elif options.zmodem:
    tf = tempfile.NamedTemporaryFile(suffix='_auto.pdf' ) #Temporary file with the work auto in it to force auto starting in terraterm.
    outfile = tf.name
    log.debug("Temporary outfile: %s", outfile)
    outhandle = tf
  else:
    outhandle = StringIO() #Store the file in memory for speed.

  if options.xxpdf: pagesize = (590, 890) # Use the old incorect page sizes from xxpdf.
  else: pagesize = reportlab.lib.pagesizes.A4

  c = RascalPDF.PrintJob(output=outhandle, pagesize=pagesize, landscape=options.landscape)
    
  if args: c.feed(file(args[0]))
  else: c.feed(sys.stdin)

  stop = time.time()
  log.info("Render time: %s seconds" % (stop - start))
  
  if options.evince:
    os.system("evince %s" % (outfile))

  if options.zmodem:
    if not options.tty: options.tty=os.environ['TTY']
    resetstr = "; sleep 3 ; clear < %s > %s " % (options.tty, options.tty) #Complicated hack because sz has a habit of messing up the screen.
    cmd = "sz -eq %s < %s > %s %s " % (outfile, options.tty, options.tty, resetstr)
    log.debug( cmd)
    os.system(cmd)
    for cmd in [ "reset", "tput rmacs", "tput krfr", "clear", "echo ' '"   ] :
      cmdstr = cmd + " < %s > %s " % (options.tty, options.tty)
      os.system(cmdstr)

  if options.printer:
    pipe = Popen("lp -d %s" % (options.printer) , shell=True, stdin=PIPE).stdin
    outhandle.flush()
    outhandle.seek(0)
    pipe.write(outhandle.read())
    pipe.close()

  if options.to:
    import RasEmail
    outhandle.flush()
    outhandle.seek(0)
    msg = RasEmail.createEmail(tolist=options.to, subject=options.subject, mailfrom=options.mailfrom, bodyhtml=None, readreceipt=options.readreceipt, cclist=options.cc, bcclist=options.bcc)
    RasEmail.addAttachements(msg, (outhandle, 'report.pdf', 'application/pdf'))
    RasEmail.sendMail(tolist=options.to, mailfrom=options.mailfrom, msg=msg, cclist=options.cc, bcclist=options.bcc)
