zip -g function.zip function.py && aws lambda update-function-code --function-name TumblrBot --zip-file fileb://function.zip