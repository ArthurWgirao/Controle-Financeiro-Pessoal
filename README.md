<div align="center">

# 💰 Controle Financeiro Pessoal

### Uma aplicação web para organizar finanças, acompanhar resultados e transformar dados em decisões mais conscientes.

![Python](https://img.shields.io/badge/Python-Backend-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Web-000000?style=for-the-badge&logo=flask&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-ORM-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)
![Pytest](https://img.shields.io/badge/Pytest-Tests-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)
![Status](https://img.shields.io/badge/Status-Em%20desenvolvimento-F2C94C?style=for-the-badge)

</div>

---

## 📌 Sobre o projeto

O **Controle Financeiro Pessoal** é uma aplicação desenvolvida para facilitar o registro, a organização e a análise de movimentações financeiras.

Mais do que armazenar receitas e despesas, o projeto busca apresentar as informações de forma clara por meio de indicadores, metas, relatórios e visualizações. Dessa forma, o usuário consegue compreender melhor seus hábitos financeiros e acompanhar sua evolução ao longo do tempo.

O sistema também funciona como um projeto prático de desenvolvimento de software, reunindo conceitos de back-end, front-end, banco de dados, testes automatizados, arquitetura e análise de dados.

## ✨ Principais recursos

- Gerenciamento de receitas e despesas;
- Organização das movimentações por categorias;
- Dashboard com indicadores financeiros;
- Definição e acompanhamento de metas de gastos;
- Relatórios por período e categoria;
- Gráficos para análise da evolução financeira;
- Validações para garantir a consistência dos dados;
- Persistência de dados com ORM e migrações versionadas;
- Configurações separadas por ambiente;
- Suíte de testes automatizados.

## 🎯 Objetivos

O projeto foi criado com os seguintes objetivos:

- aplicar conceitos de Python em um problema real;
- desenvolver uma aplicação web completa e evolutiva;
- praticar modelagem e manipulação de dados;
- construir indicadores e visualizações úteis;
- adotar boas práticas de organização, validação e testes;
- preparar a aplicação para execução em diferentes ambientes e futura publicação na nuvem.

## 🧰 Tecnologias

| Área | Tecnologias |
|---|---|
| Back-end | Python e Flask |
| Persistência | SQLAlchemy e Alembic/Flask-Migrate |
| Banco de dados | SQLite em desenvolvimento, com arquitetura preparada para outros bancos relacionais |
| Front-end | HTML, CSS, JavaScript e Jinja |
| Visualização | Chart.js e Matplotlib |
| Qualidade | Pytest e cobertura de testes |
| Versionamento | Git e GitHub |

## 🏗️ Organização e qualidade

A aplicação é organizada com separação entre interface web, regras de negócio, validações, modelos e persistência. Essa divisão reduz acoplamentos e facilita a manutenção e a evolução do sistema.

Entre as práticas adotadas estão:

- Application Factory do Flask;
- configurações por ambiente e variáveis de ambiente;
- modelos de dados com SQLAlchemy;
- migrações de banco versionadas;
- operações financeiras com precisão decimal;
- datas tratadas com tipos apropriados;
- consultas e regras de negócio desacopladas das rotas;
- testes isolados com bancos temporários;
- proteção do banco utilizado em desenvolvimento.

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

