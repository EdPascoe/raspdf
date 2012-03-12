#Building for distrbution.
ifndef VERSION
                VERSION := $(shell git describe | sed -e 's/^v//')
endif

dist:
	#!!!!WARNING!!! make uses rsync to build from any files in the current directory. Make sure you have commited or reverted all changes before running.
	rm -rf buildroot 2> /dev/null || true
	mkdir -p buildroot/raspdf
	git ls-files | egrep -v -e '^\.gitignore' > buildroot/filelist
	rsync -a --files-from=buildroot/filelist .  buildroot/raspdf/
	sed -e 's/__VERSION__/$(VERSION)/' lib/RasPDF.py  > buildroot/raspdf/lib/RasPDF.py
	cd buildroot/raspdf
	cd buildroot && tar -czvf raspdf.$(VERSION).tar.gz raspdf
        
help:
	@echo "Usage: make VERSION=d.d.ddd dist"
	@echo "Eg - make VERSION=3.4.1017 dist"
	@echo "Or just:"
	@echo "     make dist"
	@echo "To build with a git describe tag"
	@exit 0
