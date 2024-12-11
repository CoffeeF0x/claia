# Clai

Clai is a CLI project for using and testing AI usecases. This project is primarily written in python.

To get started, create a .env file from the .env-sample and fill in the required, or desired fields (requirements will be noted in the sample .env file). If not using docker, these can be set as environment variables or as cli arguments preceded by `--` and swapping env variable underscores for dashes (ex, `TOKEN_OPENAI` would become `--token-openai`).

The docker compose file also includes filebrowser, since some usecases may require running clai on a remote server.
- https://github.com/filebrowser/filebrowser
- https://filebrowser.org/

~~Any audio streaming will be handled by a pulseaudio server.~~

## Design Goals

Clai's name is, perhaps obviously so, a portmanteu. It combines the terms for CLI and AI into a single word. This is also the focus of the program itself, while it may incorparate various hardware, it is at it's root a cli application.

Which brings up the next point. This program is meant to use command line interaction, and will be limited to that. If gui support is added, the gui will be interacting with and or rendering flat files produced by clai. Or it could be interacting with an api that uses clai on the backend. However, clai itself will not directly impliment gui or api tools. Support may be added to make integrating those elements easier, but won't be directly added to clai.

Clai's roadmap also includes plans to integrate with ScriptOS. ScriptOS is a package designed to simplify the deployment of scripts. Therefore, clai will be designed in such a way that increases portability and modularity to simplify deployment and integration. This may also make clai a useful tool for other scripts that wish to integrate it.

If Clai needs to advance beyond json files for storage, a SQLite database will be used. There are currently no plans to add support for other databases as more robust storage solutions should not be needed for the usecases clai is intended for.

## Environment Variables
