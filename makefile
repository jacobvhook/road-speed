generate: src/data_generator.py
	@(cd src && python data_generator.py)

generate-force-download: src/data_generator.py
	@(cd src && python data_generator.py -f)

clean:
	@rm data/*.pkl
