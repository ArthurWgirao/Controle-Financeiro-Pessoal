import importlib.util
import json
from pathlib import Path
import subprocess

import pytest


CAMINHO = Path(__file__).resolve().parents[1] / "scripts" / "launcher_local.py"
SPEC = importlib.util.spec_from_file_location("launcher_local", CAMINHO)
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)


def test_resolve_raiz_e_caminhos_com_espacos_e_acentos():
    assert launcher.project_root() == Path(__file__).resolve().parents[1]


def test_waitress_exige_executavel(tmp_path):
    with pytest.raises(launcher.LauncherError):
        launcher.waitress_executable(tmp_path)
    arquivo = tmp_path / ".venv/Scripts/waitress-serve.exe"
    arquivo.parent.mkdir(parents=True)
    arquivo.touch()
    comando = launcher.waitress_command(tmp_path)
    assert comando[0] == str(arquivo)
    assert "--host=127.0.0.1" in comando and "--port=5000" in comando
    assert "app:create_app" in comando
    assert all("debug" not in item and "reload" not in item for item in comando)


def test_docker_disponivel(monkeypatch, tmp_path):
    monkeypatch.setattr(launcher, "run", lambda *args: subprocess.CompletedProcess([], 0))
    assert launcher.docker_available(tmp_path)


def test_docker_inicia_e_respeita_timeout(monkeypatch, tmp_path):
    executavel = tmp_path / "Docker Desktop.exe"
    executavel.touch()
    monkeypatch.setattr(launcher, "docker_available", lambda root: False)
    monkeypatch.setattr(launcher, "docker_desktop_candidates", lambda: [executavel])
    iniciado = []
    monkeypatch.setattr(launcher.subprocess, "Popen", lambda args, **kwargs: iniciado.append(args))
    monkeypatch.setattr(launcher, "wait_until", lambda *args: False)
    with pytest.raises(launcher.LauncherError):
        launcher.ensure_docker(tmp_path, launcher.logging.getLogger("teste"))
    assert iniciado == [[str(executavel)]]


def test_compose_comandos_sao_restritos_ao_postgres(tmp_path):
    (tmp_path / ".env.postgres.local").touch()
    subir = launcher.compose_command(tmp_path, "up")
    parar = launcher.compose_command(tmp_path, "stop")
    assert subir[-3:] == ["-d", "postgres"] or subir[-2:] == ["-d", "postgres"]
    assert parar[-2:] == ["stop", "postgres"]
    texto = " ".join(subir + parar)
    assert "down" not in texto and "-v" not in texto and "volume" not in texto


def test_postgres_healthy_usa_container_do_servico(monkeypatch, tmp_path):
    chamadas = []
    def executar(command, root, timeout=30):
        chamadas.append(command)
        if "ps" in command:
            return subprocess.CompletedProcess(command, 0, stdout="container-id\n")
        return subprocess.CompletedProcess(command, 0, stdout="healthy\n")
    monkeypatch.setattr(launcher, "run", executar)
    assert launcher.postgres_healthy(tmp_path)
    assert chamadas[0][-2:] == ["-q", "postgres"]
    assert chamadas[1][-1] == "container-id"


def test_timeout_do_postgres_interrompe_sem_waitress(monkeypatch, tmp_path):
    (tmp_path / ".env.postgres.local").touch()
    monkeypatch.setattr(launcher, "run", lambda *args: subprocess.CompletedProcess([], 0))
    monkeypatch.setattr(launcher, "postgres_healthy", lambda root: False)
    monkeypatch.setattr(launcher, "wait_until", lambda *args: False)
    with pytest.raises(launcher.LauncherError):
        launcher.ensure_postgres(tmp_path, launcher.logging.getLogger("teste-postgres"))


def test_postgres_ja_ativo_nao_deve_ser_parado_depois(monkeypatch, tmp_path):
    monkeypatch.setattr(launcher, "postgres_healthy", lambda root: True)
    monkeypatch.setattr(launcher, "run", lambda *args: pytest.fail("Compose up não deveria ser chamado"))
    assert launcher.ensure_postgres(tmp_path, launcher.logging.getLogger("teste-postgres-ativo")) is False


def test_healthcheck_aprovado_e_invalido(monkeypatch):
    class Resposta:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): return None
        def read(self): return json.dumps({"service": launcher.SERVICE_ID, "status": "ok"}).encode()
    monkeypatch.setattr(launcher, "urlopen", lambda *args, **kwargs: Resposta())
    assert launcher.healthcheck()
    Resposta.read = lambda self: b'{}'
    assert not launcher.healthcheck()


def test_porta_ocupada_por_terceiro_interrompe(monkeypatch, tmp_path):
    (tmp_path / ".venv/Scripts").mkdir(parents=True)
    (tmp_path / ".venv/Scripts/waitress-serve.exe").touch()
    monkeypatch.setattr(launcher, "port_owner_pid", lambda: 123)
    monkeypatch.setattr(launcher, "is_project_waitress_process", lambda *args: False)
    with pytest.raises(launcher.LauncherError):
        launcher.liberar_porta_da_aplicacao(
            tmp_path, launcher.logging.getLogger("teste")
        )


def test_port_owner_pid_obtem_pid_do_netstat(monkeypatch):
    saida = "  TCP    127.0.0.1:5000   0.0.0.0:0   LISTENING   4321\n"
    resultado = subprocess.CompletedProcess([], 0, stdout=saida)
    monkeypatch.setattr(launcher.subprocess, "run", lambda *args, **kwargs: resultado)
    assert launcher.port_owner_pid() == 4321


def test_liberar_porta_encerra_apenas_waitress_confirmado(monkeypatch, tmp_path):
    pids = iter([4321, None])
    encerrados = []
    monkeypatch.setattr(launcher, "port_owner_pid", lambda: next(pids))
    monkeypatch.setattr(launcher, "is_project_waitress_process", lambda *args: True)
    monkeypatch.setattr(
        launcher, "terminate_project_process",
        lambda pid, root: encerrados.append((pid, root)) or True
    )
    launcher.liberar_porta_da_aplicacao(
        tmp_path, launcher.logging.getLogger("teste")
    )
    assert encerrados == [(4321, tmp_path)]


def test_localiza_wrapper_waitress_acima_do_processo_da_porta(
    monkeypatch, tmp_path
):
    executavel = tmp_path / ".venv/Scripts/waitress-serve.exe"
    executavel.parent.mkdir(parents=True)
    executavel.touch()
    detalhes = {
        30: {"ExecutablePath": "python.exe", "ParentProcessId": 20},
        20: {"ExecutablePath": str(executavel), "ParentProcessId": 10},
        10: {"ExecutablePath": "cmd.exe", "ParentProcessId": 0}
    }
    monkeypatch.setattr(launcher, "is_project_waitress_process", lambda *args: True)
    monkeypatch.setattr(launcher, "process_details", lambda pid: detalhes.get(pid))
    assert launcher.project_waitress_root_pid(30, tmp_path) == 20


def test_stop_encontra_waitress_orfao_pela_porta(monkeypatch, tmp_path):
    monkeypatch.setattr(launcher, "project_root", lambda: tmp_path)
    monkeypatch.setattr(launcher, "local_data_dir", lambda: tmp_path / "estado")
    monkeypatch.setattr(launcher, "port_owner_pid", lambda: 4321)
    monkeypatch.setattr(launcher, "is_project_waitress_process", lambda *args: True)
    encerrados = []
    monkeypatch.setattr(
        launcher, "terminate_project_process",
        lambda pid, root: encerrados.append((pid, root)) or True
    )
    assert launcher.stop(False) == 0
    assert encerrados == [(4321, tmp_path)]


def test_edge_e_fallback(monkeypatch, tmp_path):
    edge = tmp_path / "msedge.exe"; edge.touch(); chamadas = []
    monkeypatch.setattr(launcher, "find_edge", lambda: edge)
    monkeypatch.setattr(launcher.subprocess, "Popen", lambda args, **kwargs: chamadas.append(args))
    launcher.open_application()
    assert chamadas == [[str(edge), f"--app={launcher.BASE_URL}"]]
    monkeypatch.setattr(launcher, "find_edge", lambda: None)
    monkeypatch.setattr(launcher.webbrowser, "open", lambda url: chamadas.append(url))
    launcher.open_application()
    assert chamadas[-1] == launcher.BASE_URL


def test_estado_e_recusa_de_processo_desconhecido(monkeypatch, tmp_path):
    estado = {"pid": 123, "root": str(tmp_path), "executable": "invalido"}
    pasta = tmp_path / "estado"; pasta.mkdir()
    (pasta / "launcher-state.json").write_text(json.dumps(estado), encoding="utf-8")
    monkeypatch.setattr(launcher, "project_root", lambda: tmp_path)
    monkeypatch.setattr(launcher, "local_data_dir", lambda: pasta)
    monkeypatch.setattr(launcher, "process_details", lambda pid: {"ExecutablePath": "outro.exe", "CommandLine": "outro"})
    monkeypatch.setattr(launcher, "state_matches_process", lambda state, root: False)
    with pytest.raises(launcher.LauncherError):
        launcher.stop(False)


def test_process_details_rejeita_pid_invalido():
    assert launcher.process_details(0) is None
    assert launcher.process_details(-1) is None


def test_inicio_sempre_verifica_porta_antes_de_criar_waitress(monkeypatch, tmp_path):
    monkeypatch.setattr(launcher, "project_root", lambda: tmp_path)
    monkeypatch.setattr(launcher, "local_data_dir", lambda: tmp_path / "estado")
    (tmp_path / ".venv/Scripts").mkdir(parents=True)
    (tmp_path / ".venv/Scripts/waitress-serve.exe").touch()
    verificacoes = []
    monkeypatch.setattr(
        launcher, "liberar_porta_da_aplicacao",
        lambda root, logger: verificacoes.append(root)
    )
    monkeypatch.setattr(launcher, "healthcheck", lambda: True)
    monkeypatch.setattr(launcher, "ensure_docker", lambda *args: None)
    monkeypatch.setattr(launcher, "ensure_postgres", lambda *args: False)
    monkeypatch.setattr(launcher, "wait_until", lambda *args: True)
    monkeypatch.setattr(launcher, "open_application", lambda: None)

    class Processo:
        pid = 1
        def poll(self): return None

    monkeypatch.setattr(
        launcher.subprocess, "Popen", lambda *args, **kwargs: Processo()
    )
    assert launcher.start() == 0
    assert verificacoes == [tmp_path]


def test_encerramento_idempotente(monkeypatch, tmp_path):
    monkeypatch.setattr(launcher, "project_root", lambda: tmp_path)
    monkeypatch.setattr(launcher, "local_data_dir", lambda: tmp_path / "estado")
    assert launcher.stop(False) == 0


def test_scripts_criam_somente_dois_atalhos():
    texto = (CAMINHO.parent / "instalar_atalhos_windows.ps1").read_text(encoding="utf-8")
    assert '"Controle Financeiro" "iniciar"' in texto
    assert '"Encerrar Controle Financeiro" "encerrar"' in texto
    assert "pythonw.exe" in texto
    assert "C:\\Users\\" not in texto


def test_compose_restringe_postgres_ao_loopback_e_preserva_volume():
    compose = (CAMINHO.parents[1] / "compose.yaml").read_text(encoding="utf-8")
    assert "  postgres:" in compose
    assert '127.0.0.1:${POSTGRES_PORT:-5432}:5432' in compose
    assert '"${POSTGRES_PORT:-5432}:5432"' not in compose
    assert "0.0.0.0" not in compose
    assert "postgres_data:/var/lib/postgresql/data" in compose
    assert "healthcheck:" in compose
    assert not any(command in compose for command in ("down -v", "docker rm", "volume rm"))


def test_logs_possuem_rotacao_simples(tmp_path):
    logs = tmp_path / "logs"; logs.mkdir()
    atual = logs / "waitress.log"
    atual.write_bytes(b"x" * 512_000)
    assert launcher.prepare_waitress_log(logs) == atual
    assert (logs / "waitress.log.1").stat().st_size == 512_000
