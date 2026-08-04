# Transferência SQLite para PostgreSQL

A ferramenta exige um snapshot SQLite absoluto, íntegro e na revisão
`0004_auth_ownership_required`. A origem é aberta somente para leitura.

O destino é fornecido exclusivamente pela variável local
`POSTGRES_TRANSFER_DATABASE_URL`. Não coloque URLs com senha no comando, no Git
ou em logs. O PostgreSQL deve estar em `0004` e com `usuarios`, `transacoes` e
`metas` vazias.

Validação sem escrita:

```powershell
flask --app app transfer-sqlite-to-postgres --source C:\caminho\snapshot.db --dry-run
```

Transferência explicitamente autorizada:

```powershell
flask --app app transfer-sqlite-to-postgres --source C:\caminho\snapshot.db --confirm-transfer
```

O processo mantém advisory lock e locks de tabela, insere tudo em uma única
transação, compara o conteúdo e ajusta as sequences PostgreSQL. Em falha, os
registros sofrem rollback e as sequences são restauradas e validadas
separadamente.

Nunca use um destino preenchido. A ferramenta não oferece limpeza, `--force` ou
sobrescrita. A transferência de dados reais exige nova autorização, backup e um
ensaio prévio sobre cópia.
