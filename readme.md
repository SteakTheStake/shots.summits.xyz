
# Summit F2

A screenshot sharing site for Minecraft


## Run Locally

To run this project locally, first run these setup commands:

#### Install python virtualenv
```bash
  pip install virtualenv
```
#### Create your vitrual environtment
```bash
  python3 -m venv venv
```
#### Activate your virtual environtment
```bash
  source venv/bin/activate
```
#### Install the required dependencies
```bash
  pip install -r requirements.txt
```

#### Create your .env
 - create a **.env** file in the project folder and input your commands from the **Environment Variables** section below.

#### Run the development environtment:
```bash
  flask run
```

## Environment Variables

To run this project, you will need to add the following environment variables to your .env file

`FLASK_APP = "app.py"`

`DISCORD_CLIENT_ID`

`DISCORD_CLIENT_SECRET`

`DISCORD_REDIRECT_URI`

`DISCORD_API_BASE_URL`

`DISCORD_PUBLIC_KEY`

`DISCORD_BOT_TOKEN`

`DISCORD_WEBHOOK_URL`

`FLASK_SECRET_KEY`


`DATABASE_URL = "sqlite:///PATH/TO/DB"`

`DATABASE_PATH`
## Deployment

To deploy this project, first run these setup commands:

#### Install python virtualenv
```bash
  pip install virtualenv
```
#### Create your vitrual environtment
```bash
  python3 -m venv venv
```
#### Activate your virtual environtment
```bash
  source venv/bin/activate
```
#### Install the required dependencies
```bash
  pip install -r requirements.txt
```

#### Create your .env
 - create a **.env** file in the project folder and input your commands from the **Environment Variables** section below.

#### Run the development environtment:
```bash
  flask run
```

## Contributing

Contributions are always welcome!

Questions or concerns? Contact me on Discord: `stakethesteak`
Or join my [Discord Server](https://discord.gg/M9cmBBGKU8)
## Authors

- [@StakeTheSteak](https://github.com/SteakTheStake)


## License

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://choosealicense.com/licenses/mit/)