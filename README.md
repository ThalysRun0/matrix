# Install

## Linux
Open Terminal

```bash
cd <wherever-you-can-write>
mkdir -p ./thalysrun0/

cd ./thalysrun0/
python3.11 -m venv matrix-venv
source matrix-venv/bin/activate
python -m pip install --upgrade pip

git clone git@github.com:ThalysRun0/matrix.git
cd matrix
python -m pip install -r requirements.txt
```

## Set screen resolution
Search for SCREEN_HEIGHT and SCREEN_WIDTH in `main.py`

```bash
sudo echo "0" # admin password
sudo tcpdump -l -nn -tt | python main.py
```
Like, Comment, Share