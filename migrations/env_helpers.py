def obter_url_offline(engine):
    """Retorna a URL utilizável apenas para o modo offline do Alembic."""
    return engine.url.render_as_string(hide_password=False).replace("%", "%%")


def configurar_contexto_online(
    contexto,
    conexao,
    metadata,
    argumentos
):
    """Configura Alembic com uma conexão, sem copiar sua URI para Config."""
    contexto.configure(
        connection=conexao,
        target_metadata=metadata,
        **argumentos
    )
