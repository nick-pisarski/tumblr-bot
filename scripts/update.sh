scripts/build.sh

aws lambda update-function-code --function-name TumblrBot --zip-file fileb://function.zip

echo "Update complete"