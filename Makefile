
install:
	git submodule init 
	git submodule update
	npm i -g relaxedjs

edit:
	rendercv render resume_int.json

edit-cover:
	python utils/cov.py	

clean:
	rm -rf resume_int.json
	rm -rf experiences2.json
	rm -rf output
	rm -rf remote-profile
	rm -rf .Rhistory
	rm -rf conversations
	rm -rf rendercv_output
	rm -rf company_research.txt
	rm -rf *.yaml
	rm -rf classic 
	rm -rf cover_letters

clean-test:
	rm -rf resume_int.json
	rm -rf experiences2.json
	rm -rf output
	rm -rf .tox
	rm -rf .Rhistory