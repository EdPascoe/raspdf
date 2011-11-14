#!/usr/bin/env python
# -*- coding: utf-8 -*-
# © Ed Pascoe 2011. All rights reserved.
"""
The email sending module of raspdf
Replacement for the old xxpdf program.
"""
__author__ = "Ed Pascoe <ed@pascoe.co.za>"
__format__ = "plaintext"
__version__ = "$Id$"
__copyright__ = "Ed Pascoe 2011. All rights reserved."
__license__ = "GNU LGPL version 2"
__status__ = "Production"


try:
  from email.message import Message
except  ImportError:
  from email.Message import Message
from email.Header import Header
from email.MIMEText import MIMEText
try:
  from email.mime.multipart import MIMEMultipart
except ImportError:
  from email.MIMEMultipart import MIMEMultipart
from email.MIMENonMultipart import MIMENonMultipart
from email.Encoders import encode_base64
import RasConfig, html2text
import time, logging, socket
import smtplib

log = logging.getLogger("config")


def h2text(data):
  if not isinstance(data,unicode):
    try: data = data.decode('utf-8')
    except UnicodeDecodeError:
      try: data = data.decode('latin1')
      except UnicodeDecodeError, e:
        print "Could not convert the given file to unicode. %s" % (e)
        print "Aborting"
        sys.exit(1)
  baseurl="."

  return  html2text.html2text(data, baseurl)
  #return  html2text.wrapwrite(html2text.html2text(data, baseurl))

def createEmail(mailfrom, destemail, subject, mfrom=None, bodyhtml=None, bodytext=None):
  """returns a mime email object that can have attachments added to it
     bodytxt and bodyhtml are the contents of the message.
     If bodytext is None it will be created by converting bodyhtml.
  """
  if subject is None or len(subject) < 1:
    subject = RasConfig.get_default('global', 'subject','Rascal Report')


  #Load the email message from the given text file. If 
  
  if bodyhtml is None:
    messagefile = RasConfig.get_default('global','emailmessage', None)
  if messagefile is None:
    bodyhtml = bodytext  = RasConfig.get_default('global', 'message', 'Your report should be attached.')
  else:
    bodyhtml = file(messagefile).read()
  if bodytext is None: bodytext = h2text(bodyhtml) #Convert the html message to text

  msg = MIMEMultipart('mixed')
  msg["Subject"] = subject
  msg["To"] = ", ".join(destemail)
  msg["From"] = mailfrom     
  msg['Message-ID']= "<%s@%s>" % (time.time(), socket.gethostname())
  msg["X-Mailer"] = "RasPDF report generator"
  msg.preamble = "Rascal Report.\nIf you are seeing this you must have the only mailreader on the planet that can't view mime\n\n"""

  mtxt=MIMEText(bodytext, 'plain')
  mtxt['charset']="UTF-8"
  if bodyhtml is not None:
    msgalt = MIMEMultipart('alternative')
    msgalt.attach(mtxt)
    mhtml=MIMEText(bodyhtml ,'html')
    mhtml['charset']="UTF-8"
    msgalt.attach(mhtml)
    msg.attach(msgalt)
  else: #Plain text only. Does not need an fancy multi-part mime wrapper.
    msg.attach(mtxt)

  return msg

def mailFile(tolist, subject, bodyhtml, *args):
  """Email the current PDF file to everyone on tolist
     Subject is email subject.
     bodyhtml is the html message to in the message body. Set it to None to use the defaults.
     each following arg should be a tuple: (filecontents/filehandle, nameof the file, mimetype)
      eg: mailFile('a@b.com,c@d.com', "Test message", None, (fh, 'report.pdf', 'application/pdf'))
     
  """

  if isinstance(tolist, basestring): tolist=[tolist,]
  mailfrom = RasConfig.get('global', 'from')
  destemail = []
  for addr in tolist:
    destemail = destemail + list([x.strip() for x in addr.split(',')])

  msg = createEmail(mailfrom, tolist, subject)
  for fh, fname, mimetype in args:
    print "FH: %s Fname: %s, mime: %s" % ( fh, fname, mimetype)
    if isinstance(fh, str):
      contents = fh
    elif isinstance(fh, unicode):
      contents = fh.encode('utf-8')
    else: #Must be a file handle.
      contents = fh.read()
  
    mimemajor, mimeminor = mimetype.split('/')
    msgdata = MIMENonMultipart(mimemajor, mimeminor, name=fname)
    msgdata.set_payload(contents)
    encode_base64(msgdata)
    msgdata.add_header('Content-Disposition', 'attachment', filename = fname)
    msg.attach(msgdata)

  #print msg.as_string() ; sys.exit(1)

  smtpserver = RasConfig.get('global', 'smtpserver')
  s = smtplib.SMTP(smtpserver)
  #s.set_debuglevel(2)
  s.sendmail(mailfrom, destemail, msg.as_string())
  s.quit()

if __name__=="__main__":
  fh = file("/etc/hosts")
  mailFile('ed.pascoe@gmail.com', "Test subject", None, 
      (file('/usr/share/pixmaps/faces/sky.jpg'), 'sky.jpg', 'image/jpeg'),
      (file('/usr/share/doc/systemtap-0.9.7/tutorial.pdf'), 'tutorial.pdf', 'application/pdf')
    )
  
  

