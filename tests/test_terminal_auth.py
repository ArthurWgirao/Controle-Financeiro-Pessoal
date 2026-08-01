import main


def test_terminal_autentica_sem_expor_senha(caminho_banco, usuario, monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda mensagem: usuario.email)
    monkeypatch.setattr(main, "getpass", lambda mensagem: "senha-segura")
    assert main.autenticar_terminal() == usuario.id
    assert "senha-segura" not in capsys.readouterr().out


def test_terminal_nao_inicia_menu_com_login_invalido(caminho_banco, monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda mensagem: "ausente@example.test")
    monkeypatch.setattr(main, "getpass", lambda mensagem: "incorreta")
    monkeypatch.setattr(main, "menu", lambda: (_ for _ in ()).throw(AssertionError("menu não deve abrir")))
    main.main()
    assert "inválidos" in capsys.readouterr().out
