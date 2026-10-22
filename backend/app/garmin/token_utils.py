"""Token path resolution — único sobrevivente do tokenstore de ARQUIVO
(era garmin_mcp; feature garmin-tokens-db removeu o resto). Usado pelo
CLI de importação do legado (``app.garmin.import_tokens``) para expandir
o ``~`` do ``--path``; nenhum caminho runtime lê arquivo de tokens — a
fonte única é o banco cifrado (tokens_store)."""

import os


def resolve_token_path(path: str) -> str:
    """Resolve environment variables and the user-home marker in a token path.

    Some MCP clients leave ``${HOME}`` unresolved when it comes from a nested
    user-config default. The explicit replacement also covers Windows, where
    ``HOME`` may be unset but Python can still resolve ``~`` via ``USERPROFILE``.
    """
    expanded = os.path.expandvars(path)
    expanded = expanded.replace("${HOME}", os.path.expanduser("~"))
    return os.path.expanduser(expanded)
