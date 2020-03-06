#!/bin/bash
if [ -z $1 ]
then
    echo "Usage: $0 [mysqldump arguments...]"
    echo "Example: $0 -u root -ppassword ping"
    exit 1
fi
mysqldump -d "$@" | grep -v ^-- | sed 's/ AUTO_INCREMENT=[0-9]*\b//' | sed '/^$/d' | grep -v "^DROP TABLE"
echo "DELETE FROM version;"
mysqldump "$@" --skip-extended-insert --table version | grep ^INSERT | head -1
