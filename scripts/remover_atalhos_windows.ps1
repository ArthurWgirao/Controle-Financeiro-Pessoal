$Desktop = [Environment]::GetFolderPath("Desktop")
@("Controle Financeiro.lnk", "Encerrar Controle Financeiro.lnk") | ForEach-Object {
    $Shortcut = Join-Path $Desktop $_
    if (Test-Path -LiteralPath $Shortcut -PathType Leaf) {
        Remove-Item -LiteralPath $Shortcut -Force
    }
}
Write-Host "Atalhos locais removidos."
