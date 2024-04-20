A configuration template for using mininet along with docker devcontainer.

## How to use?

* Install vs code
* Install docker desktop
* Install dev container extension in vs code
* Clone this repository and open in vs code
* Run dev container in this folder

It will setup the docker image automatically and start the dev container.

## How to test?

* After dev container starts, run the command `mn --custom topo.py --topo mytopo` to test mininet works.
* Ensure xterm and ping works.
* If xterm throws an error 'Display not found', ensure you have installed xming in your system. (For mac, it is Xming Quartz)

## How to setup intellisense?

* Install python vs code extension inside the dev container and intellisense should start working