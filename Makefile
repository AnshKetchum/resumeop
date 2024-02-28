
install:
	git submodule init 
	git submodule update

edit:
	rendercv render resume_int.json

clean:
	rm -rf resume_int.json
	rm -rf experiences2.json
	rm -rf output
	rm -rf remote-profile
	rm -rf .Rhistory

clean-test:
	rm -rf resume_int.json
	rm -rf experiences2.json
	rm -rf output
	rm -rf .tox
	rm -rf .Rhistory