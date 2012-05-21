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

def __splitMailAddresses(maillist):
  #maillist can be array of addresses or a string with addresses comma separated.
  if maillist is None: return []

  if isinstance(maillist, basestring): maillist=[maillist,]

  destemail = []
  for addr in maillist:
    destemail = destemail + list([x.strip() for x in addr.split(',')])
  return destemail

def createEmail(tolist, subject, mailfrom=None, bodyhtml=None, bodytext=None, readreceipt=False, cclist=None, bcclist=None):
  """returns a mime email object that can have attachments added to it
     bodytxt and bodyhtml are the contents of the message.
     If bodytext is None it will be created by converting bodyhtml.
     cclist is for entries on the Cc line..
     bcclist is not used here but is allowed for compatibility with sendEmail later.
  """
  if subject is None or len(subject) < 1:
    subject = RasConfig.get_default('global', 'subject','Rascal Report')
  if mailfrom is None or len(mailfrom) < 1:
    mailfrom = RasConfig.get('global', 'from')


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
  destemail = __splitMailAddresses(tolist)
  msg["To"] = ", ".join(destemail)
  msg["From"] = mailfrom     
  msg['Message-ID']= "<%s@%s>" % (time.time(), socket.gethostname())
  msg["X-Mailer"] = "RasPDF report generator"
  if readreceipt:
    msg['Disposition-Notification-To'] = mailfrom

  ccmail = __splitMailAddresses(cclist)
  if len(ccmail) > 0:
    msg["Cc"] = ", ".join(ccmail)

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

def addAttachements(msg, *attachments):
  """msg should be a mime email (can be created useing createEmail)
     each attachement should be a tuple of the form: (filecontents/filehandle, nameof the file, mimetype)
      eg: addAttachements(msg, (fh, 'report.pdf', 'application/pdf'))
  """
  for fh, fname, mimetype in attachments:
    log.debug("FH: %s Fname: %s, mime: %s" , fh, fname, mimetype)
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
  log.debug("returning from addAttachements")
  return msg

def sendMail(tolist, msg, mailfrom = None, cclist=None, bcclist=None):
  """Email the current PDF file to everyone on tolist
     msg should be a mime email (create using createEmail)
     if mailfrom is None will be looked up in config. 
  """

  if isinstance(tolist, basestring): tolist=[tolist,]
  if mailfrom is None: mailfrom = RasConfig.get('global', 'from')

  destemail = __splitMailAddresses(tolist) + __splitMailAddresses(cclist) + __splitMailAddresses(bcclist)
  
  smtpserver = RasConfig.get('global', 'smtpserver')
  log.debug("Connecting to smtp server %s", smtpserver)
  s = smtplib.SMTP(smtpserver)
  s.set_debuglevel(1)
  s.sendmail(mailfrom, destemail, msg.as_string())
  s.quit()

if __name__=="__main__":
  fh = file("/etc/hosts")
  msg = createEmail(tolist=['ed.pascoe@gmail.com', 'testing@pascoe.co.za'] , subject="Testing", readreceipt=True, cclist='president@419.co.za, bob@419.co.za')
  addAttachements(msg, (file('/usr/share/pixmaps/faces/sky.jpg'), 'sky.jpg', 'image/jpeg'),
                      (file('/etc/hosts'), 'hosts', 'text/plain')
                 )
  #print msg.as_string()
  sendMail('ed.pascoe@gmail.com', msg)

