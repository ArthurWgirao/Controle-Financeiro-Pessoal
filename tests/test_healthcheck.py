def test_healthcheck_publico_minimo(cliente_anonimo, monkeypatch):
    def consulta_proibida(*args, **kwargs):
        raise AssertionError("O healthcheck não deve consultar o banco")

    monkeypatch.setattr("extensions.db.session.execute", consulta_proibida)
    resposta = cliente_anonimo.get("/health")
    assert resposta.status_code == 200
    assert resposta.is_json
    assert resposta.get_json() == {
        "service": "controle-financeiro", "status": "ok"
    }
    corpo = resposta.get_data(as_text=True).lower()
    assert not any(valor in corpo for valor in ("database", "secret", "version", "environment"))


def test_healthcheck_rejeita_metodos_mutaveis(cliente_anonimo):
    for metodo in ("post", "put", "patch", "delete"):
        assert getattr(cliente_anonimo, metodo)("/health").status_code == 405
