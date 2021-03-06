# SCF Utils
A simple flask app to take the extra clicks out of processing items in Alma.

## Setup
Setup python
```
virtualenv -p python3.6 ENV
source ENV/bin/activate
pip install -r requirements.txt
```

Set your local settings
```
cp settings.template.py settings.py
```
## Run (for development)
```
FLASK_ENV=development python app.py
```
## Deployment (for production)
Clone this repository and setup on the production server. After configuring deactivate and configure and startup your application container.

On WRLC servers this app runs in a Green Unicorn (Python WSGI HTTP Server) service. 
```
systemctl enable scf-utils.service
```
The daemon is started and stoped via systemd. The config is `/etc/systemd/system/scf-utils.service`

## Utilities
### /add-alt-call
Scan in an item, then scan in an alternative callnumber. scf-utils will update the alternative call number and bring you back to the beginning of the process.
