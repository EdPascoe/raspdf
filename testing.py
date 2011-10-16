import re

doc="""{$SETCOLOR(0,1,1)}
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

class P:
  def __init__(self):
    self.doc = []

  def parseLine(self, line):
    if len(line)==0: return  #Blank line
    hasnewline= line[-1] == "\n"
    line = line.strip()
    r=re.search(r'^(.*?){\$(.*?)}(.*)$', line)
    if r:
      leadtext=r.group(1)
      cmd=r.group(2)
      restofline = r.group(3)
      self.doc.append(("printstring", leadtext))
      self.addCommand(cmd)
      self.parseLine(restofline)
    else:
      self.doc.append(("printstring", line))

    if hasnewline:
      self.doc.append("newline")

  def addCommand(self, command):
    command = command.strip()
    cmdname = None
    cmdparams = []
    p = command.find("(") #Find the start of any parameters
    if p == -1: #No parameters
      return self.doc.append( [command.strip(),])
    cmdname = command[:p]
    params = command[p+1:]
    params = re.sub(r'\s*\)\s*$','',params)
    #TODO Check python 2.4???
    params = [ x.strip() for x in params.split(",") if len(x.strip()) > 0]
    return self.doc.append([ cmdname,] +  list(params) )
    

p = P()
for line in doc.split("\n"):
  p.parseLine(line)

for d in p.doc:
  #print "####--> ", d
  fnname = d[0]
  if len(d) > 1:
    params = d[1:]
  else:
    params = None
  print "FN: %s  Params: %s" % (fnname, params)
