#!/bin/bash
python3 -m venv venv
sed -i 's|PS1="(venv) \$PS1"|PS1="(\$VIRTUAL_ENV_NICKNAME) \$PS1"|' venv/bin/activate
sed -i 's|\(export VIRTUAL_ENV$\)|\1\nVIRTUAL_ENV_NICKNAME='$(basename $(pwd))'|' venv/bin/activate
source venv/bin/activate
pip install -r requirements.txt
echo "Made virtual environment, activated venv and installed requirements."
echo "Use this command to enable the virtual environment:"
echo "source venv/bin/activate"
