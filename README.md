<div align="center">

# Controle Financeiro Pessoal

<p><strong>Uma aplicação web multiusuário para organizar receitas, despesas e metas e transformar movimentações em uma visão clara do orçamento.</strong></p>

![Python](https://img.shields.io/badge/Python-Backend-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Web-000000?style=flat-square&logo=flask&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Banco%20principal-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![Status](https://img.shields.io/badge/Status-Em%20desenvolvimento-F2C94C?style=flat-square)

</div>

## Visão geral

O **Controle Financeiro Pessoal** centraliza as principais informações do orçamento em uma interface simples. Cada pessoa acessa apenas os dados de sua própria conta e pode acompanhar entradas, gastos, limites mensais e resultados por período para tomar decisões financeiras mais conscientes.

## Principais funcionalidades

- cadastro, login e logout de usuários;
- gerenciamento de receitas e despesas com categorias predefinidas;
- dashboard com saldo e totais financeiros;
- criação e acompanhamento de metas mensais por categoria;
- relatórios por período e gráficos de evolução financeira;
- isolamento dos dados de cada usuário;
- validações no servidor e mensagens de erro compreensíveis.

## Diferenciais técnicos

- Application Factory e configuração por ambiente;
- autenticação com Flask-Login e proteção CSRF com Flask-WTF;
- autorização por usuário em consultas e operações financeiras;
- persistência com SQLAlchemy e migrations Alembic/Flask-Migrate;
- PostgreSQL como banco principal, executado localmente com Docker Compose;
- compatibilidade preservada com SQLite e histórico de migração reproduzível;
- ferramenta dedicada para transferência validada de dados entre SQLite e PostgreSQL;
- testes automatizados isolados, incluindo cenários com bancos temporários protegidos.

## Arquitetura

As rotas Flask coordenam módulos de autenticação, transações, metas, relatórios e validações. Modelos SQLAlchemy representam os dados financeiros, enquanto migrations versionadas mantêm a evolução do schema e templates Jinja compõem a interface web.

O PostgreSQL é a persistência principal do ambiente local. A suíte de testes utiliza bancos isolados e mecanismos de proteção para não alterar dados persistentes durante as verificações.

## Tecnologias

| Área | Tecnologias |
|---|---|
| Back-end | Python, Flask e Flask-Login |
| Segurança web | Flask-WTF e CSRF |
| Persistência | SQLAlchemy, Alembic e Flask-Migrate |
| Bancos de dados | PostgreSQL e SQLite |
| Interface | Jinja, HTML, CSS, JavaScript e Chart.js |
| Ambiente local | Docker Compose |
| Qualidade | Pytest |

O projeto também preserva uma interface legada de terminal, que utiliza Matplotlib para uma visualização local de despesas.

## Qualidade e segurança

As senhas são armazenadas como hash, os formulários mutáveis recebem proteção CSRF e as consultas financeiras aplicam isolamento por usuário. Valores monetários são validados no servidor e tratados com `Decimal`, enquanto migrations e testes com bancos temporários ajudam a preservar a consistência entre SQLite e PostgreSQL e a impedir operações cruzadas entre contas.

## Execução local

As dependências estão declaradas nos arquivos de requirements, as configurações esperadas são exemplificadas em `.env.example` e o PostgreSQL local pode ser iniciado com o `compose.yaml`. As migrations preparam o schema; procedimentos operacionais específicos permanecem documentados em `docs/`.

## Situação do projeto

A aplicação web está funcional localmente, com PostgreSQL como banco principal. O SQLite permanece disponível como compatibilidade controlada e recurso de recuperação. A próxima fase é preparar a aplicação para um deploy público com configuração e infraestrutura próprias de produção.

## Autor

Desenvolvido por **Arthur Girão**.

[GitHub — ArthurWgirao](https://github.com/ArthurWgirao)
