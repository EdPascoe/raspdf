#!/bin/bash
#Install all required libraries for raspdf
INSTDIR="../PYTHONINSTALL"
#INSTDIR="../pyinst"

cd `dirname $0`
cd install

if [ ! -d "$INSTDIR" ] ; then
  ./virtualenv.py --never-download  "$INSTDIR"
  $INSTDIR/bin/pip install -v reportlab*.gz
  $INSTDIR/bin/pip install -v Imaging*.gz
fi

PYBIN=$(cd $INSTDIR/bin && pwd)
RASPDF=$(cd ../lib && pwd)

cat > ../raspdf <<_EOM
#!$PYBIN/python
import sys
sys.path.append('$RASPDF')
import raspdf
raspdf.main()
_EOM
chmod +x ../raspdf
