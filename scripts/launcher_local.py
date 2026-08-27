"""Inicialização local segura do Controle Financeiro no Windows."""

from __future__ import annotations

import argparse
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
import webbrowser

from dotenv import dotenv_values


HOST = "127.0.0.1"
PORT = 5000
BASE_URL = f"http://{HOST}:{PORT}"
SERVICE_ID = "controle-financeiro"
DOCKER_TIMEOUT = 180
POSTGRES_TIMEOUT = 90
APP_TIMEOUT = 60


class LauncherError(RuntimeError):
    pass


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def local_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        raise LauncherError("A pasta local de dados do Windows não está disponível.")
    return Path(base) / "ControleFinanceiroPessoal"


def configure_logging(state_dir: Path) -> logging.Logger:
    logs = state_dir / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("controle_financeiro_launcher")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    handler = RotatingFileHandler(
        logs / "launcher.log", maxBytes=512_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    return logger


def prepare_waitress_log(logs: Path) -> Path:
    log_file = logs / "waitress.log"
    previous = logs / "waitress.log.1"
    if log_file.exists() and log_file.stat().st_size >= 512_000:
        previous.unlink(missing_ok=True)
        log_file.replace(previous)
    return log_file


def run(command: list[str], root: Path, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        command, cwd=root, capture_output=True, text=True,
        timeout=timeout, shell=False, check=False
    )


def docker_available(root: Path) -> bool:
    try:
        return run(["docker", "info"], root, 15).returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def docker_desktop_candidates() -> list[Path]:
    candidates = []
    for variable in ("ProgramFiles", "ProgramFiles(x86)"):
        base = os.environ.get(variable)
        if base:
            candidates.append(Path(base) / "Docker" / "Docker" / "Docker Desktop.exe")
    return candidates


def wait_until(predicate, timeout: int, interval: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def ensure_docker(root: Path, logger: logging.Logger) -> None:
    if docker_available(root):
        logger.info("Docker Engine disponível.")
        return
    executable = next((path for path in docker_desktop_candidates() if path.is_file()), None)
    if not executable:
        raise LauncherError("Docker Desktop não foi encontrado nas localizações oficiais.")
    subprocess.Popen([str(executable)], shell=False)
    logger.info("Inicialização do Docker Desktop solicitada.")
    if not wait_until(lambda: docker_available(root), DOCKER_TIMEOUT):
        raise LauncherError("O Docker Engine não ficou disponível dentro do tempo esperado.")


def compose_command(root: Path, action: str) -> list[str]:
    env_file = root / ".env.postgres.local"
    if not env_file.is_file():
        raise LauncherError("A configuração local do PostgreSQL não foi encontrada.")
    if action == "up":
        return ["docker", "compose", "--env-file", str(env_file), "up", "-d", "postgres"]
    if action == "stop":
        return ["docker", "compose", "--env-file", str(env_file), "stop", "postgres"]
    raise ValueError("Ação Compose não permitida.")


def postgres_healthy(root: Path) -> bool:
    result = run(
        ["docker", "compose", "--env-file", str(root / ".env.postgres.local"),
         "ps", "-q", "postgres"], root
    )
    container_id = result.stdout.strip()
    if result.returncode or not container_id:
        return False
    status = run(
        ["docker", "inspect", "--format", "{{.State.Health.Status}}", container_id], root
    )
    return status.returncode == 0 and status.stdout.strip() == "healthy"


def ensure_postgres(root: Path, logger: logging.Logger) -> bool:
    already_running = postgres_healthy(root)
    if already_running:
        logger.info("PostgreSQL já estava saudável.")
        return False
    result = run(compose_command(root, "up"), root, 90)
    if result.returncode:
        raise LauncherError("Não foi possível iniciar o PostgreSQL do projeto.")
    if not wait_until(lambda: postgres_healthy(root), POSTGRES_TIMEOUT):
        raise LauncherError("O PostgreSQL não ficou saudável dentro do tempo esperado.")
    logger.info("PostgreSQL saudável.")
    return True


def healthcheck() -> bool:
    try:
        with urlopen(f"{BASE_URL}/health", timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return (
                response.status == 200
                and payload == {"service": SERVICE_ID, "status": "ok"}
            )
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return False


def port_in_use() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(1)
        return probe.connect_ex((HOST, PORT)) == 0


def waitress_executable(root: Path) -> Path:
    executable = root / ".venv" / "Scripts" / "waitress-serve.exe"
    if not executable.is_file():
        raise LauncherError("Waitress não está instalado na .venv do projeto.")
    return executable


def waitress_command(root: Path) -> list[str]:
    return [
        str(waitress_executable(root)), "--call", "--host=127.0.0.1",
        "--port=5000", "app:create_app"
    ]


def process_environment(root: Path) -> dict[str, str]:
    values = dotenv_values(root / ".env.postgres.local")
    environment = os.environ.copy()
    environment.update({key: value for key, value in values.items() if value is not None})
    return environment


def state_file(state_dir: Path) -> Path:
    return state_dir / "launcher-state.json"


def save_state(
    state_dir: Path, process: subprocess.Popen, root: Path,
    executable: Path, stop_postgres: bool
) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file(state_dir).write_text(json.dumps({
        "pid": process.pid, "root": str(root), "executable": str(executable),
        "stop_postgres": stop_postgres
    }), encoding="utf-8")


def load_state(state_dir: Path) -> dict | None:
    try:
        return json.loads(state_file(state_dir).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def process_details(pid: int) -> dict | None:
    if not isinstance(pid, int) or pid <= 0:
        return None
    command = [
        "powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
        f'$p=Get-CimInstance Win32_Process -Filter "ProcessId={pid}";'
        "if($p){$p|Select-Object ProcessId,ExecutablePath,CommandLine|ConvertTo-Json -Compress}"
    ]
    result = subprocess.run(command, capture_output=True, text=True, shell=False, check=False)
    if result.returncode or not result.stdout.strip():
        return None
    try:
        details = json.loads(result.stdout)
        return details if isinstance(details, dict) else None
    except json.JSONDecodeError:
        return None


def state_matches_process(state: dict, root: Path) -> bool:
    try:
        details = process_details(int(state["pid"]))
        expected_executable = str(waitress_executable(root).resolve()).casefold()
    except (KeyError, TypeError, ValueError, LauncherError):
        return False
    if not details:
        return False
    executable = str(details.get("ExecutablePath") or "").casefold()
    command_line = str(details.get("CommandLine") or "").casefold()
    return (
        executable == expected_executable
        and str(root.resolve()).casefold() in command_line
        and "app:create_app" in command_line
        and str(state.get("root", "")).casefold() == str(root).casefold()
    )


def find_edge() -> Path | None:
    located = shutil.which("msedge.exe")
    if located:
        return Path(located)
    for variable in ("ProgramFiles", "ProgramFiles(x86)"):
        base = os.environ.get(variable)
        if base:
            candidate = Path(base) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
            if candidate.is_file():
                return candidate
    return None


def open_application() -> None:
    edge = find_edge()
    if edge:
        subprocess.Popen([str(edge), f"--app={BASE_URL}"], shell=False)
    else:
        webbrowser.open(BASE_URL)


def start() -> int:
    root = project_root()
    state_dir = local_data_dir()
    logger = configure_logging(state_dir)
    if healthcheck():
        logger.info("Aplicação já estava ativa.")
        open_application()
        return 0
    if port_in_use():
        raise LauncherError("A porta local 5000 está ocupada por outro serviço.")
    ensure_docker(root, logger)
    stop_postgres = ensure_postgres(root, logger)
    executable = waitress_executable(root)
    logs = state_dir / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    output = open(prepare_waitress_log(logs), "a", encoding="utf-8")
    process = subprocess.Popen(
        waitress_command(root), cwd=root, env=process_environment(root),
        stdout=output, stderr=subprocess.STDOUT, shell=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
    )
    save_state(state_dir, process, root, executable, stop_postgres)
    if not wait_until(lambda: healthcheck() or process.poll() is not None, APP_TIMEOUT, 1):
        if state_matches_process(load_state(state_dir) or {}, root):
            process.terminate()
        raise LauncherError("A aplicação não ficou saudável dentro do tempo esperado.")
    if process.poll() is not None or not healthcheck():
        state_file(state_dir).unlink(missing_ok=True)
        raise LauncherError("A aplicação foi encerrada antes de ficar saudável.")
    logger.info("Aplicação iniciada em endereço exclusivamente local.")
    open_application()
    return 0


def stop(stop_postgres: bool | None = None) -> int:
    root = project_root()
    state_dir = local_data_dir()
    logger = configure_logging(state_dir)
    state = load_state(state_dir)
    if state and state_matches_process(state, root) and healthcheck():
        result = subprocess.run(
            ["taskkill.exe", "/PID", str(state["pid"]), "/T", "/F"],
            capture_output=True, text=True, shell=False, check=False
        )
        if result.returncode:
            raise LauncherError("Não foi possível encerrar o servidor local com segurança.")
        logger.info("Aplicação encerrada.")
        state_file(state_dir).unlink(missing_ok=True)
    elif state and not process_details(int(state.get("pid", 0))):
        state_file(state_dir).unlink(missing_ok=True)
        logger.info("Estado antigo do launcher removido.")
    elif state:
        raise LauncherError("O processo salvo não pôde ser identificado; nenhum processo foi encerrado.")
    should_stop_postgres = (
        bool(state.get("stop_postgres")) if stop_postgres is None and state
        else bool(stop_postgres)
    )
    if should_stop_postgres and docker_available(root):
        result = run(compose_command(root, "stop"), root, 90)
        if result.returncode:
            raise LauncherError("A aplicação parou, mas o PostgreSQL não pôde ser interrompido.")
        logger.info("Somente o serviço PostgreSQL do projeto foi parado.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Controle Financeiro local")
    parser.add_argument("modo", choices=("iniciar", "encerrar"))
    args = parser.parse_args(argv)
    try:
        return start() if args.modo == "iniciar" else stop()
    except LauncherError as error:
        try:
            configure_logging(local_data_dir()).error("Falha operacional: %s", error)
        except LauncherError:
            pass
        if sys.stderr:
            print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
