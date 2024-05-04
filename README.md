# Clai

Clai is a CLI project for using and testing AI usecases. This project is primarily written in python.

To get started, create a .env file from the .env-sample and fill in the required, or desired fields (requirements will be noted in the sample .env file). If not using docker, ensure these environment variables are set, as the project loads these in directly from the environment.

To run the record test via docker, ensure that a pulseaudio server is setup.

This project has several test cases, mainly in the ./src/tests folder. Some of these are demos used from other code or repos, below is a list of all sources used.

- <https://github.com/techwithtim/AI-Agent-Code-Generator/tree/main>

## Design Goals

Clai's name is, perhaps obviously so, a portmanteu. It combines the terms for CLI and AI into a single word. This is also the focus of the program itself, while it may incorparate various hardware, it is at it's root a cli application.

Which brings up the next point. This program is meant to use command line interaction, and will be limited to that. If gui support is added, the gui will be interacting with and or rendering flat files produced by clai. Or it could be interacting with an api that uses clai on the backend. However, clai itself will not directly impliment gui or api tools. Support may be added to make integrating those elements easier, but won't be directly added to clai.

Any interaction with heavier software will be done through external apis. This means that things like local LLMs or other models will only be supported via a local server. This is to keep the file size and load times for clai minimal. No models should be packaged directly inside clai.

Clai will be designed to interact with scriptos. Scriptos is a package I designed to simplify the deployment of scripts. Therefore, clai will be designed in such a way that increases portability and modularity to simplify deployment and integration. This may also make clai a useful tool for other scripts that wish to integrate it.
