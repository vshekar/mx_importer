# GUI for Automated puck loading software

Prototype for the puck loading software for the MX beamlines at NSLS-II.

## Requirements:
 - Install requirements.txt using `pip install --user -r requirements.txt` 
 - Compatible with LSDC GUI conda environments

## Usage:
 - Set up a configuration yaml file (Example configuration file provided in `config.yaml`)
 - Type `python start_importer.py path/to/yaml/config.yaml` to run the GUI
 - Change the master list of pucks by editing `masterlist.json`. Add or remove pucks in the list with the key `whitelist` or `blacklist`

## Purpose
 This software is designed to make the process of importing puck data easier and less error prone by providing validation and exact location of errors in the data.

##Rules implemented as of July 2023

### Preprocessing
 1. Imported file should contain the following column names, case is ignored
 	
	- puckname
	- position
	- samplename
	- model
	- sequence
	- proposalnum
 
 2. Only columns with the names above are imported every other column is ignored
 3. All values in the position and proposalnum should be numerical only. Alphabets and characters are automatically removed
 4. All whitespaces are stripped from data

### Validation checks
 1. Match puck names against the blacklist and whitelist. Blacklisted pucks highlighted in red and whitelisted pucks in yellow
 2. Sample names cannot exceed 25 characters and should only contain letters, numbers, dash `-` and underscore `_`
 3. Sample names cannot be empty
 4. Sample names cannot be repeated in the same column
 5. Proposal numbers must contain exactly 6 digits no alphabets or special characters
 6. Proposal numbers should all be the same
 7. Combination of puck name and position should be unique (For eg. two rows cannot have Puck-ABC with position 1)

Validation checks happen when the spreadsheet is first imported, manually triggered from the menu and just before submitting the data to the mongo db

## Configuration file
The following is an example of the configuration file that the software expects
```
admin_group: admin
beamline: TLA
database_host: localhost:8000
disable_blacklist: false
disable_whitelist: true
list_path: masterlist.json
```

`admin_group` : Specifies which user group the admin should belong to, only those part of the admin group can see the settings window
`beamline` : Three letter acronym for the beamline
`database_host` : Address of the amostra and conftrak mongo database
`disable_whitelist` : Choose whether to use or ignore whitelist during validation
`disable_blacklist` : Choose whether to use or ignore blacklist during validation
`list_path`: Path to json file that contains black and white lists
