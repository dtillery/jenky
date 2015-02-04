# Jenky - An Alfred workflow for Jenkins
Jenky is an [Alfred](http://www.alfredapp.com/) workflow that allows you to search and (eventually) control your [Jenkins CI](http://jenkins-ci.org/) instance in a pleasant and natural-feeling way.

## Features
* Search your Jenkins instance for jobs and launch them in your default browser.
* Cache jobs for more responsive searches.
* Save your credentials for continual use, including your API key securely in the systems Keychain.
* Coming soon: start builds directly from Alfred

## Installation
1. Download this repository by clicking [here](https://github.com/dtillery/jenky/archive/master.zip).
2. Double click on `jenky.alfredworkflow`, or drag it into your Alfred settings panel.
3. You're ready to go! Just open up Alfred like normal and type `jenky` to get started.
4. Though if you'd like to set up a hotkey for quick launch, you can do that while you're in the Alfred settings panel by going to the "Workflows" tab, selecting "jenky" from the list and double-clicking the box labeled "Hotkey" in the top-leftish.

## Setup
When you bring up Jenky for the first time, the setup should be pretty straightforwad. You'll need to set your Jenkins username, API Key and Hostname. You can find your Jenkins API Key on the "Configure" page.

Enter all three pieces of information and you're good to go!

## Usage

### Searching for and launching jobs
Just start typing the name of the job you're looking for!  When you find it, hit enter and the webpage for it will be opened.

### Clearing the job cache
By default Jenky caches your jobs list so that searching is as fast as possible.  Eventually we'll do some smart background updating, but in the meantime if you need to refresh your jobs list (if a new job has been added), just choose the "Clear Job Cache" option on the main menu.  Next time you launch Jenky, your jobs list will be repopulated from your instance.

## Acknowledgements
* **citelao** and the [Spotifious](https://github.com/citelao/Spotify-for-Alfred) Alfred workflow for inspiring the design patterns used here, and showing how a high quality workflow should be.
* **deanishe** for the super awesome [alfred-workflow](https://github.com/deanishe/alfred-workflow) python library.
* The [python-jenkins](https://python-jenkins.readthedocs.org/en/latest/) library and everyone who works on it.
