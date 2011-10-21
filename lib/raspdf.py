#!/usr/bin/env python
"""
Generate PDF reports designed to interact well with rascal.
Replacement for the old xxpdf program.
"""

import logging
import optparse
import os, sys, time, tempfile
from subprocess import *

import RascalPDF

def main():
  """Main harness. The actual work is all done in RascalPDF"""
  usage = "Usage: %prog [<options>] \n" + __doc__+"\n"
  parser = optparse.OptionParser(usage)
  parser.add_option("--sz", "--zmodem", dest="zmodem", action="store_true", help="After generating the pdf file transfer via zmodem")
  parser.add_option("-l", "--landscape", dest="landscape", action="store_true", default=False, help="Use landscape A4" )
  parser.add_option("--evince", dest="evince", action="store_true", help="After generating the pdf file display using evince")
  parser.add_option("-v", "--verbose", dest="verbose", action="store_true", help="Show debugging information")
  parser.add_option("--debug", dest="debug", action="store_true", help="Show debugging information")
  parser.add_option("-f", "--outputfile", dest="outputfile", type="string", help="Send output to file with given name instead of a temp file.")
  parser.add_option("--tty", dest="tty", type="string", help="The running TTY to conenct to for zmodem")
  parser.add_option("-r", "--reset", dest="reset", action="store_true", help="Reset the terminal after running.")

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
  outfile = options.outputfile
  if not options.outputfile:
    tf = tempfile.NamedTemporaryFile(suffix='_auto.pdf' ) #Temporary file with the work auto in it to force auto starting in terraterm.
    outfile = tf.name
    log.debug("Outfile: %s", outfile)
  c = RascalPDF.PrintJob(output=outfile, landscape=options.landscape )
    
  if args: c.feed(file(args[0]))
  else: c.feed(sys.stdin)

  stop = time.time()
  log.info("Render time: %s seconds" % (stop - start))
  

  if options.evince:
    os.system("evince %s" % (outfile))

  if options.zmodem:
    if not options.tty: options.tty=os.environ['TTY']
    if options.reset: #Complicated hack because sz has a habit of messing up the screen.
      resetstr = "; sleep 3 ; clear < %s > %s " % (options.tty, options.tty)
    else:
      resetstr = " "
    cmd = "sz -eq %s < %s > %s %s " % (outfile, options.tty, options.tty, resetstr)
    log.debug( cmd)
    os.system(cmd)
    if options.reset:
      for cmd in [ "reset", "tput rmacs", "tput krfr", "clear", "echo ' '"   ] :
	 cmdstr = cmd + " < %s > %s " % (options.tty, options.tty)
	 os.system(cmdstr)

