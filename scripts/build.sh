echo "Build lambda function"
echo "Zipping up installed packages"
cd v-env/lib/python3.7/site-packages/ && zip -r9 ../../../../function.zip . && cd ./../../../../ && echo "Zipping up custom packages" && zip -g -r function.zip ./lib/ && zip -g ./function.zip ./function.py && echo "Building complete."