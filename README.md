<div align="center">

# Controle Financeiro Pessoal

<p><strong>Uma aplicação web multiusuário para organizar receitas, despesas e metas e transformar movimentações em uma visão clara do orçamento.</strong></p>

![Python](https://img.shields.io/badge/Python-Backend-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Web-000000?style=flat-square&logo=flask&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Banco%20principal-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![Status](https://img.shields.io/badge/Status-Vers%C3%A3o%20local%20conclu%C3%ADda-2EA44F?style=flat-square)

</div>

## Visão geral

O **Controle Financeiro Pessoal** centraliza as principais informações do orçamento em uma interface simples e acessível. Cada pessoa visualiza apenas os dados da própria conta e pode acompanhar entradas, gastos, metas mensais e resultados por período para tomar decisões financeiras mais conscientes.

A página inicial funciona como um Dashboard financeiro completo, reunindo indicadores, filtros e visualizações gráficas em um único ambiente.

## Principais funcionalidades

- cadastro, login e logout de usuários;
- gerenciamento completo de receitas e despesas;
- categorias financeiras predefinidas e validadas;
- Dashboard com filtro por mês e ano;
- indicadores de receitas, despesas, saldo e movimentações;
- evolução financeira dos últimos seis meses;
- gráficos de receitas e despesas por categoria;
- criação e acompanhamento de metas mensais;
- comparação gráfica entre gastos e limites das metas;
- análises financeiras por período;
- isolamento integral dos dados de cada usuário;
- validações no servidor e mensagens de erro compreensíveis;
- interface responsiva e acessível para diferentes tamanhos de tela.

## Diferenciais técnicos

- Application Factory e configuração separada por ambiente;
- autenticação com Flask-Login;
- proteção CSRF com Flask-WTF;
- autorização por usuário em consultas e operações financeiras;
- persistência com SQLAlchemy;
- migrations versionadas com Alembic e Flask-Migrate;
- PostgreSQL como banco principal, executado localmente com Docker Compose;
- compatibilidade controlada com SQLite;
- histórico de migração reproduzível entre SQLite e PostgreSQL;
- ferramenta dedicada para transferência validada de dados;
- cálculos financeiros com `Decimal`;
- tratamento seguro de conflitos e rollback;
- testes automatizados com bancos temporários isolados;
- inicialização local automatizada no Windows.

## Dashboard financeiro

O Dashboard concentra as principais análises do sistema assim que o usuário acessa sua conta.

Ele apresenta:

- totais de receitas e despesas;
- saldo do período;
- quantidade de movimentações;
- filtro por mês e ano;
- evolução de receitas e despesas nos últimos seis meses;
- distribuição de despesas por categoria;
- distribuição de receitas por categoria;
- acompanhamento das metas do mês atual;
- estados vazios e links de ação quando ainda não existem dados.

As visualizações são geradas com Chart.js e acompanhadas por tabelas e descrições textuais acessíveis.

## Arquitetura

As rotas Flask coordenam os módulos de autenticação, transações, metas, relatórios e validações. Os modelos SQLAlchemy representam os dados financeiros, enquanto migrations versionadas controlam a evolução do schema.

A lógica de análise permanece separada da interface: os módulos de domínio realizam consultas e cálculos, enquanto os templates Jinja apresentam os resultados e o Chart.js renderiza as visualizações gráficas.

O PostgreSQL é a persistência principal do ambiente local. A suíte de testes utiliza bancos isolados e mecanismos de proteção para evitar alterações nos dados persistentes durante as verificações.

## Tecnologias

| Área | Tecnologias |
|---|---|
| Back-end | Python, Flask e Flask-Login |
| Segurança web | Flask-WTF e CSRF |
| Persistência | SQLAlchemy, Alembic e Flask-Migrate |
| Bancos de dados | PostgreSQL e SQLite |
| Interface | Jinja, HTML, CSS, JavaScript e Chart.js |
| Servidor local | Waitress |
| Infraestrutura local | Docker Compose |
| Qualidade | Pytest |

O projeto também preserva uma interface legada de terminal, que utiliza Matplotlib para uma visualização local de despesas.

## Qualidade e segurança

As senhas são armazenadas como hash, os formulários mutáveis recebem proteção CSRF e todas as consultas financeiras aplicam isolamento por usuário.

Valores monetários são validados no servidor e tratados com `Decimal`. As operações de persistência possuem rollback em caso de falha, enquanto migrations e testes com bancos temporários ajudam a preservar a consistência dos dados entre SQLite e PostgreSQL.

Na execução local, a aplicação e o PostgreSQL são vinculados exclusivamente ao endereço `127.0.0.1`, evitando exposição desnecessária para outros dispositivos da rede.

## Execução local no Windows

A aplicação pode ser utilizada como um programa local por meio de dois atalhos na Área de Trabalho:

- **Controle Financeiro**, responsável por iniciar Docker, PostgreSQL e Waitress e abrir a aplicação no Microsoft Edge em modo aplicativo;
- **Encerrar Controle Financeiro**, responsável por finalizar o servidor local e parar com segurança o PostgreSQL quando ele tiver sido iniciado pelo launcher.

A inicialização não depende da ativação manual da `.venv`, e os dados permanecem armazenados no volume persistente do PostgreSQL após o encerramento.

As instruções operacionais estão disponíveis em [Uso local no Windows](docs/uso-local-windows.md).

## Situação do projeto

A versão local da aplicação está concluída, funcional e validada com PostgreSQL como banco principal.

O sistema pode ser utilizado diariamente no Windows por meio dos atalhos locais, sem necessidade de executar manualmente os comandos de inicialização. O SQLite permanece disponível como compatibilidade controlada e recurso de recuperação.

O código está preparado para apresentação pública no GitHub. Um futuro deploy em nuvem e uma página demonstrativa no GitHub Pages permanecem como possibilidades de evolução, sem impedir o uso completo da versão local.

## Autor

Desenvolvido por **Arthur Girão**.

[![GitHub](https://img.shields.io/badge/ArthurWgirao-181717?style=flat-square&logo=github&logoColor=white)](https://github.com/ArthurWgirao)

## Licença

Este projeto é disponibilizado sob a [Licença MIT](LICENSE).