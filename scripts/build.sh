echo "Build lambda function"
echo "Zipping up installed packages"

cd v-env/lib/python3.7/site-packages/

zip -r9 ../../../../function.zip . | pv -lep -s $(ls -RF1 ./ | egrep -vc '(.*\/.*)') > /dev/null
cd ./../../../../

echo "Zipping up custom packages"
zip -g -r function.zip ./lib/ | pv -lep -s $(($(ls -RF1 ./lib/ | egrep -vc '(.*\/.*)')+1))> /dev/null
zip -gq ./function.zip ./function.py

echo "Building complete."