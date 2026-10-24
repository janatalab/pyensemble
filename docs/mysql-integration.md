# Optional MySQL integration

The normal `requirements.txt` supports local development with SQLite and does
not install `mysqlclient`. Install the optional driver only when configuring a
site to use MySQL:

```sh
pip install -r requirements-mysql.txt
```

The production settings read connection values from the private
`[django-db]` section of the site INI file. The database engine defaults to
`django.db.backends.mysql`; it can also be specified explicitly. Provide the
database host, name, user, password, and the SSL CA certificate settings
required by the deployment. Never commit database credentials.

## macOS build setup

`mysqlclient` compiles a native extension and needs MySQL client headers,
`pkg-config`, and a compiler toolchain. With Homebrew:

```sh
brew install mysql-client pkg-config
export PATH="$(brew --prefix mysql-client)/bin:$PATH"
export PKG_CONFIG_PATH="$(brew --prefix mysql-client)/lib/pkgconfig"
pip install -r requirements-mysql.txt
```

`mysql-client` is keg-only on some Homebrew setups. If pip cannot find
`mysql_config` or `pkg-config` metadata, verify that the Homebrew `bin` and
`lib/pkgconfig` paths for the installed client are active in the same shell
where pip runs.

## Dynamic library loading on macOS

A successful build does not guarantee that Python can load the extension at
runtime. An error such as `Library not loaded: ... libmysqlclient...` means
the dynamic loader cannot find the MySQL client library. Confirm the library
exists below `$(brew --prefix mysql-client)/lib`, then launch the Python
process from a shell where that directory is in the dynamic loader's search
path, for example:

```sh
export DYLD_LIBRARY_PATH="$(brew --prefix mysql-client)/lib${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"
python -c "import MySQLdb; print('mysqlclient loaded')"
```

Keep this environment adjustment scoped to the development shell or service
configuration that needs it rather than adding a machine-wide setting
unnecessarily. macOS security protections can affect how environment
variables are inherited by some launched services; if Apache or another
service cannot load the library, configure the runtime environment for that
service or install/link the client library using the platform's supported
method. Do not solve a loader issue by copying libraries into arbitrary system
directories.

If MySQL is not required for the task, use the local SQLite profile instead;
it avoids this native dependency.
