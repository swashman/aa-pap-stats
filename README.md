# Example plugin app for Alliance Auth - LAWN Version

This is an example plugin app for [Alliance Auth](https://gitlab.com/allianceauth/allianceauth) (AA) that can be used as starting point to develop custom plugins.
It is a modified version of [allianceauth-example-plugin](https://gitlab.com/ErikKalkoken/allianceauth-example-plugin), that has been modified to hold our preffered setup.
The instructions have been modified to fit our use case.

## Features

- The plugin can be installed, upgraded (and removed) into an existing AA installation using PyInstaller.
- It has it's own menu item in the sidebar.
- It has one view that shows a panel and some text
- Comes with CI pipeline pre-configured

## How to use it

To use this example as basis for your own development just clone it on your dev machine.

You then should rename the app and then you can install it into your AA dev installation.

### Cloning from repo

For this app we are assuming that you have all your AA projects, your virtual environnement and your AA installation under one top folder (e.g. aa-dev).

This should look something like this:

```plain
aa-dev
|- venv/
|- myauth/
|- aa_base_plugin
|- (other AA projects ...)

```

Then just cd into the top folder (e.g. aa-dev) and clone the repo. You can give the repo a new name right away (e.g. `allianceauth-your-app-name`).
You also want to create a new git repo for it. Finally, enable [pre-commit](https://pre-commit.com) to enable automatic code style checking.

```bash
git clone https://github.com/astrum-mechanica/aa-base-plugin.git your-app-name
cd your-app-name
rm -rf .git
git init
pre-commit install
```

### Renaming the app

Before installing this app into your dev AA you need to rename it to something suitable for your development project. Otherwise you risk not being able to install additional apps that might also be called example.

Here is an overview of the places that you need to edit to adopt the name.

Easiest is to just find & replace `aa_base_plugin` `aa-base-plugin` `aa base plugin` or various other combinations, with your new app name in all files listed below.

One small warning about picking names: Python is a bit particular about what special characters are allowed for names of modules and packages. To avoid any pitfalls I would therefore recommend to use only normal characters (a-z) in your app's name unless you know exactly what you are doing.

| Location                                              | Description                                                                            |
| ----------------------------------------------------- | -------------------------------------------------------------------------------------- |
| `/aa_base_plugin/`                                    | folder name                                                                            |
| `/aa_base_plugin/templates/aa_base_plugin/`           | folder name                                                                            |
| `/pyproject.toml`                                     | update module name for version import, update package name, update title, author, etc. |
| `/aa_base_plugin/apps.py`                             | app name                                                                               |
| `/aa_base_plugin/__init__.py`                         | app name                                                                               |
| `/aa_base_plugin/auth_hooks.py`                       | menu hook config incl. icon and label of your app's menu item appearing in the sidebar |
| `/aa_base_plugin/models.py`                           | app name                                                                               |
| `/aa_base_plugin/urls.py`                             | app name                                                                               |
| `/aa_base_plugin/views.py`                            | permission name and template path                                                      |
| `/aa_base_plugin/templates/aa_base_plugin/base.html`  | Title of your app to be shown in all views and as title in the browser tab             |
| `/aa_base_plugin/templates/aa_base_plugin/index.html` | template path                                                                          |
| `/testauth/settings/local.py`                         | app name                                                                               |
| `/.coveragerc`                                        | app name                                                                               |
| `/README.md`                                          | clear content                                                                          |
| `/tox.ini`                                            | app name                                                                               |

## Clearing migrations

Instead of renaming your app in the migrations its easier to just recreate them later in the process. For this to work you need to delete the old migration files in your migrations folder.

```bash
rm your-app-name/migrations/0001_initial.py
rm -rf your-app-name/migrations/_pycache
```

## Installing into your dev AA

Once you have cloned or copied all files into place and finished renaming the app you are ready to install it to your dev AA instance.

Make sure you are in your venv. Then install it with pip in editable mode:

```bash
pip install -e your-app-name
```

First add your app to the Django project by adding the name of your app to INSTALLED_APPS in `settings/local.py`.

Next we will create new migrations for your app:

```bash
python manage.py makemigrations
```

Then run a check to see if everything is setup correctly.

```bash
python manage.py check
```

In case they are errors make sure to fix them before proceeding.

Next perform migrations to add your model to the database:

```bash
python manage.py migrate
```

Finally restart your AA server and that's it.

## Running the test suite

This example app comes with a pre-configured test suite based on [tox](https://tox.wiki/en/).

First you need to install tox into your local Python environment:

```sh
pip install tox
```

Then you can run the test suite for a specific environment with:

```sh
tox -e py311-django42
```

You can use this command to see all configured test environments:

```sh
tox -l
```

## Pylint linter

The [pylint](https://pylint.readthedocs.io/en/stable/) linter is also pre-configured. Pylint is a popular linter that checks your app for common bugs, unidiomatic python code and makes suggestions for refactoring.

You can run the linter manually with:

```sh
tox -e pylint
```
