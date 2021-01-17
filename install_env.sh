export PYTHONPATH=$PYTHONPATH:./
python --version
yes | python -m pip install -r ./requirements.txt --user
cd ./models/ops
sh ./make.sh
cd -
