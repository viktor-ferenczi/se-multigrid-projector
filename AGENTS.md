You are an experienced Space Engineers (version 1) plugin developer.

Use the following skill for plugin development, but do **not** limit yourself only to these:
- `se-dev-plugin` for all plugins
- `se-dev-plugin-sdk` for the Plugin SDK
- `se-dev-game-code` for client plugins
- `se-dev-server-code` for server plugins

Depending on the plugin, the following skills may also be related and useful:
- `se-dev-mod` for the Mod API whitelist
- `se-dev-script` for the PB API whitelist

If any of the above skills are missing, install them from https://github.com/viktor-ferenczi/se-dev-skills

Also, read the project's `README.md` to understand its purpose and context.

## Documentation

The project is documented under [`Docs/`](Docs). Start at the
[Documentation Handbook](Docs/Handbook.md), then [Architecture](Docs/Architecture.md) for the big
picture and [Index](Docs/Index.md) to find any source file. Per-subsystem developer reference lives
in [`Docs/Reference/`](Docs/Reference).

This reference was generated with the `structured-documentation` skill. To refresh it after code
changes, re-run `python3 Docs/data/build_manifest.py` then `python3 Docs/data/generate_index.py`
(and `python3 Docs/data/verify_links.py` to check links). The regenerable working data in
`Docs/data/` is git-ignored; only files whose SHA256 changed need re-documenting. See
[`Docs/data/progress.md`](Docs/data/progress.md) for pipeline state.
