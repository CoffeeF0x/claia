# Zammad Module for CLAIA

This module provides integration with the Zammad ticketing system, allowing CLAIA to interact with tickets, process them, and apply AI-based tagging and analysis.

## Features

- List tickets based on predefined or custom queries
- Get detailed information about specific tickets
- Add and remove tags from tickets
- Automatically process tickets with AI tagging
- Process account management tickets and generate task lists

## Module Structure

The module has been structured according to the new CLAIA module system:

- `command.py` - Contains the `ZammadCommand` class implementing all commands
- `api.py` - Contains the `ZammadAPI` class for Zammad API interactions
- `settings.py` - Contains the `ZammadSettings` class for module configuration
- `constants.py` - Contains constants used throughout the module
- `prompts.py` - Contains AI prompts used for ticket processing
- `utils.py` - Contains utility functions and decorators

## Configuration

To use the Zammad module, you need to configure the following environment variables:

- `TOKEN_ZAMMAD` - API token for Zammad
- `ZAMMAD_BASEURL` - Base URL for the Zammad API

These can be set in your environment or in the CLAIA `.env` file.

## Commands

The module provides the following commands:

### List Tickets

```
zammad list [query]
```

Lists tickets from Zammad based on a query. Default is "open-tickets".

### Get Ticket Details

```
zammad details <ticket_id>
```

Retrieves detailed information about a specific ticket.

### Add Tag

```
zammad tag add <ticket_id> <tag>
```

Adds a tag to a specific ticket.

### Remove Tag

```
zammad tag remove <ticket_id> <tag>
```

Removes a tag from a specific ticket.

### Process Tickets

```
zammad process
```

Processes untagged tickets and adds AI-generated tags based on content analysis.

### Remove AI Tags

```
zammad untag
```

Removes all AI-generated tags from tagged tickets.

### Process Account Tickets

```
zammad account-management [output_file] [limit]
```

Processes tickets with account management tags and builds a list of accounts that need work.

## Using with CLAIA

You can use the Zammad module via:

1. CLI commands: `claia zammad [command]`
2. AI function calls: The functions are registered for AI use with the `ai_callable=True` property

## Dependencies

The module requires the following external packages:

- requests
- bs4 (BeautifulSoup)

It also optionally uses the AIA package for certificate handling if available. 