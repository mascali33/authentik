---
title: Bookstack
---

## What is Bookstack

From https://en.wikipedia.org/wiki/BookStack

:::note
BookStack is a free and open-source wiki software aimed for a simple, self-hosted, and easy-to-use platform. Based on Laravel, a PHP framework, BookStack is released under the MIT License. It uses the ideas of books to organise pages and store information. BookStack is multilingual and available in over thirty languages. For the simplicity, BookStack is considered as suitable for smaller businesses or freelancers.
:::

:::note
This is based on authentik 2021.7.2 and BookStack V21.05.3. Instructions may differ between versions.
:::

## Preparation

The following placeholders will be used:

- `book.company` is the FQDN of BookStack.
- `authentik.company` is the FQDN of authentik.
- `METADATAURL` is the url for the SAML metadata from authentik

### Step 1

In authentik, under _Providers_, create a _SAML Provider_ with these settings:

**Protocol Settings**
- Name: Bookstack
- ACS URL: https://book.company/saml2/acs
- Issuer: https://authentik.company
- Service Provider Binding: Post
- Audience: https://book.company/saml2/metadata

**Advanced protocol settings**
- Signing Certificate:  Choose your certificate or the default authentik Self-signed Certificate
All other options as default.

![](./authentik_saml_bookstack.png)

Save your settings, and obtain your Metadata URL from Authentik.

1. Click on the BookStack Provider
2. Click the Metadata Tab
3. Click Copy download URL (This URL is the `METADATAURL` required in Step 2)

![](./metadataurl.png)

### Step 2

Edit the `.env` file inside of the `www` folder of Bookstack.

Modify the following Example SAML config and paste incorporate into your `.env` file

```bash
# Set authentication method to be saml2
AUTH_METHOD=saml2
# Set the display name to be shown on the login button.
# (Login with <name>)
SAML2_NAME=Authentik
# Name of the attribute which provides the user's email address
SAML2_EMAIL_ATTRIBUTE=email
# Name of the attribute to use as an ID for the SAML user.
SAML2_EXTERNAL_ID_ATTRIBUTE=uid
# Name of the attribute(s) to use for the user's display name
# Can have mulitple attributes listed, separated with a '|' in which
# case those values will be joined with a space.
# Example: SAML2_DISPLAY_NAME_ATTRIBUTES=firstName|lastName
# Defaults to the ID value if not found.
SAML2_DISPLAY_NAME_ATTRIBUTES=Name
# Identity Provider entityID URL
SAML2_IDP_ENTITYID=METADATAURL
 # Auto-load metatadata from the IDP
# Setting this to true negates the need to specify the next three options
SAML2_AUTOLOAD_METADATA=true

```

:::note
Bookstack Reference link: https://www.bookstackapp.com/docs/admin/saml2-auth/
:::

### Step 3

In authentik, create an application which uses this provider. Optionally apply access restrictions to the application using policy bindings.

- Name: Bookstack
- Slug: bookstack
- Provider: Bookstack
- Launch URL: https://book.company

## Notes

:::note
BookStack will attempt to match the SAML user to an existing BookStack user based on a stored external id attribute otherwise, if not found, BookStack will effectively auto-register that user to provide a seamless access experience.
:::

:::note
SAML Group Sync is supported by Bookstack.  Review the BookStack documention on the required Environment variables.  https://www.bookstackapp.com/docs/admin/saml2-auth/
:::