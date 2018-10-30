# SCF Utils
A simple flask app to take the extra clicks out of processing items in Alma.

## Setup
Setup python
```
virtualenv -p python3.6 ENV
source ENV/bin/activate
pip install -r requirements.txt
```

## Run (for development)
```
python app.py
```

## Utilities
### /add-alt-call
Scann in an item, then scan in an alternative callnumber. scf-utils will update the alternative call number and bring you back to the beginning of the process.
