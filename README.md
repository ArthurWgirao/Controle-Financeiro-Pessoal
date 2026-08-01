<div align="center">

# 💰 Controle Financeiro Pessoal

Aplicação Flask com persistência em SQLAlchemy 2.x e migrações controladas por
Flask-Migrate/Alembic. Nesta etapa, o banco suportado continua sendo SQLite.

## Configuração

Copie apenas as variáveis necessárias de `.env.example`. `DATABASE_URL` aceita
uma URI completa e tem prioridade; `DATABASE_PATH` mantém a configuração
simples por caminho de arquivo SQLite. Quando ambos estão vazios ou ausentes em
desenvolvimento, o caminho padrão é `finance.db`.

As dependências de persistência são SQLAlchemy 2.x, Flask-SQLAlchemy,
Flask-Migrate e Alembic, todas fixadas em versões estáveis no
`requirements.txt`.

## 🚀 Execução local

Após clonar o repositório, crie e ative um ambiente virtual.

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### Linux ou macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Instale as dependências:

```bash
python -m pip install -r requirements.txt
```

Crie sua configuração local com base no arquivo `.env.example`, prepare o banco e execute a aplicação:

```bash
flask --app app db upgrade
python app.py
```

As configurações sensíveis devem permanecer apenas no arquivo `.env`, que não deve ser enviado ao repositório.

## 🧪 Testes automatizados

Para instalar também as dependências de desenvolvimento:

```bash
python -m pip install -r requirements-dev.txt
```

Execute a suíte com:

```bash
python -m pytest
```

Os testes utilizam bancos temporários e isolados, preservando os dados locais da aplicação.

## 📊 Visão do produto

O sistema foi pensado para evoluir de maneira incremental. Sua base permite incorporar novos recursos sem depender de uma reestruturação completa, mantendo o foco em usabilidade, segurança, qualidade dos dados e clareza das informações.

## 🚧 Status

O projeto está em desenvolvimento contínuo. A documentação será complementada com demonstração, capturas da interface e instruções de publicação quando a versão final estiver disponível.

## 👨‍💻 Autor

Desenvolvido por **Arthur Girão**.

[![GitHub](https://img.shields.io/badge/GitHub-ArthurWgirao-181717?style=for-the-badge&logo=github)](https://github.com/ArthurWgirao)

