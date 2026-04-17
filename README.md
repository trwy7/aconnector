# AuthBridge

A simple email -> openid connect bridge. Meant to be lighter then authentik in places where it's full functionality is not required (e.x. your school blocks google accounts from authenticating with unknown apps).

## Features

- Email authentication (passwordless)
- Compatible with most OIDC clients
- Easy to setup

## Usage

### Warning

This app is meant for use as a community service, where one person hosts it and everyone in a group can use it. This means every authenticated user can make their own OIDC app.

### Setup

A docker compose is provided, however you need to set some things yourself.

Create a file named docker-compose.override.yml and fill out these contents:

```yml
services:
  authbridge:
    environment:
      APP_NAME: AuthBridge # Used across the app, feel free to make it whatever
      EMAIL_PASSWORD: 123456 # SMTP information
      EMAIL_USERNAME: user # SMTP information
      EMAIL_HOST: mail.example.com # SMTP information
      EMAIL_PORT: 2525 # SMTP information
      EMAIL_FROM: authbridge@example.com # SMTP information
      OWNER_EMAIL: abadmin@trwy.net # Your personal email address, gets extra permissions
      VEMAIL_REGEX: ".*@.*\\..*" # The regex that all emails must follow.
      VEMAIL_MESSAGE: "" # The message that is shown on the login page, set this if you have a custom email regex
```

Run it with `docker compose up -d --build`. A reverse proxy that supports SSL is required, make it proxy to port 7035.
