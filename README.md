# Sistema de Controle Financeiro Pessoal

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

## Migrações

Para criar um banco novo já no esquema final:

```bash
flask --app app db upgrade
```

As revisões são:

- `0001_legacy`: esquema SQLite antigo, usado como baseline;
- `0002_orm`: valida e converte dinheiro para `Numeric(12, 2)`, datas para
  `Date` e adiciona unicidade às categorias de metas.

Um banco legado existente exige um procedimento deliberado:

1. faça e valide um backup;
2. trabalhe primeiro em uma cópia;
3. inspecione duplicidades, datas e valores inválidos;
4. marque a cópia com `flask --app app db stamp 0001_legacy`;
5. aplique `flask --app app db upgrade`;
6. valide esquema, contagens, IDs e valores.

Não aplique `stamp`, `upgrade` ou `downgrade` ao banco real sem revisar a cópia
e autorizar explicitamente a operação.

Para reverter tecnicamente a conversão em um banco de teste:

```bash
flask --app app db downgrade 0001_legacy
```

O downgrade volta datas a `DD/MM/AAAA` e números a `REAL`, portanto só deve ser
usado com backup e após avaliar a perda de garantias de tipo.

## Execução e testes

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
python app.py
python main.py
```

Os testes usam bancos SQLite isolados. Os testes comuns criam diretamente o
esquema ORM temporário; os testes de migração executam Alembic em bancos
temporários novos ou legados construídos pela própria suíte.
