# AuthBridge

A simple email -> openid connect bridge. Meant to be lighter then authentik in places where it's full functionality is not required (e.x. your school blocks google accounts from authenticating with unknown apps).

## Features

- Email authentication
- Minimal user annoyance (Users should not need to interface with this site most of the time)
- Compatible with most OIDC libraries
- Simple to use
- Easy to setup and administer
- Limit signup to a specific email regex

## Docs

Some extra documentation is available in `app/pages/help`

## Usage

### Warning

**All cookes are stored with the secure header, reguardless of whether the request was made securly. You need a reverse proxy that supports SSL (like caddy), or logins will not work.**

### Setup

Create a folder, and create a `docker-compose.yml` within it with these contents:

```yml
services:
  authbridge:
    image: ghcr.io/trwy7/aconnector:1.0.0
    ports:
      - 7035:7035
    volumes:
      - acdata:/data
    hostname: authbridge
    stop_signal: SIGINT
    stop_grace_period: 1s
    environment:
      APP_NAME: AuthBridge # Used across the app, feel free to make it whatever
      EMAIL_PASSWORD: 123456 # SMTP information
      EMAIL_USERNAME: user # SMTP information
      EMAIL_HOST: mail.example.com # SMTP information
      EMAIL_PORT: 2525 # SMTP information
      EMAIL_FROM: authbridge@example.com # SMTP information
      OWNER_EMAIL: abadmin@example.com # Your personal admin email address, gets extra permissions
      CONTACT_EMAIL: contact@example.com # An email that is displayed on some access denied pages
      VEMAIL_REGEX: ".*@.*\\..*" # The regex that all emails must follow when creating an account, does not apply to existing users
      VEMAIL_MESSAGE: "" # A message that is shown on the login page, should be used to guide users if there is a custom email regex
      LOCK_NEW_APP_CREATE: true # Only affects new users, set to "false" to allow every newly created user to create their own OIDC client.

volumes:
  acdata:
```

Edit the file to fit your needs

Run it with `docker compose up -d --build`.

Set up a reverse proxy for port 7035 and make sure it has a valid certificate, proxying at a path will not work, it must be the root (e.g. `https://auth.example.com` or `https://example.com`, not `https://example.com/path/auth`, if you do not know what this means, you should be fine)

Go to your domain and login with the owner email you set earlier.

Congrats! Feel free to make an app or invite other users.

### Dev Setup

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
      OWNER_EMAIL: abadmin@example.com # Your personal admin email address, gets extra permissions
      CONTACT_EMAIL: contact@example.com # An email that is displayed on some access denied pages
      VEMAIL_REGEX: ".*@.*\\..*" # The regex that all emails must follow when creating an account, does not apply to existing users
      VEMAIL_MESSAGE: "" # A message that is shown on the login page, should be used to guide users if there is a custom email regex
      LOCK_NEW_APP_CREATE: true # Only affects new users, set to "false" to allow every newly created user to create their own OIDC client.
```

Run it with `docker compose up -d --build`. A reverse proxy that supports SSL is required, make it proxy to port 7035.
