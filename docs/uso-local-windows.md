# Uso local no Windows

## Pré-requisitos

- Windows com Docker Desktop instalado;
- `.venv` preparada e dependências de `requirements.txt` instaladas;
- arquivos locais de ambiente já configurados;
- PostgreSQL definido como serviço `postgres` no Compose.

## Instalar os atalhos

Na raiz do projeto, execute uma vez:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\instalar_atalhos_windows.ps1
```

O `Bypass` vale somente para esse processo e não modifica a política global nem a do usuário. Os atalhos usam diretamente `pythonw.exe` da `.venv`, sem terminal visível e sem exigir ativação do ambiente.

## Iniciar e encerrar

Abra **Controle Financeiro** na Área de Trabalho. O launcher localiza ou inicia o Docker Desktop, aguarda o Engine, inicia somente o serviço PostgreSQL deste projeto, inicia Waitress em `127.0.0.1:5000` e abre o Edge em modo aplicativo. Se o Edge não estiver disponível, usa o navegador padrão.

Fechar a janela do navegador não encerra o servidor. Use **Encerrar Controle Financeiro** para parar o Waitress e somente o serviço PostgreSQL deste projeto. Docker Desktop permanece aberto para não afetar outros projetos.

Se a porta 5000 pertencer a outro serviço, o launcher não encerra o processo nem escolhe outra porta. Ele registra uma mensagem operacional e para.

Logs sanitizados e o estado mínimo ficam em `%LOCALAPPDATA%\ControleFinanceiroPessoal`. Eles não contêm credenciais ou dados financeiros.

Os dados permanecem no volume PostgreSQL. Fechar a janela, parar o serviço ou remover os atalhos não apaga dados. Nunca utilize `down -v`.

## Remover somente os atalhos

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\remover_atalhos_windows.ps1
```

## Diagnóstico manual

```powershell
.\.venv\Scripts\python.exe scripts\launcher_local.py iniciar
.\.venv\Scripts\python.exe scripts\launcher_local.py encerrar
```
