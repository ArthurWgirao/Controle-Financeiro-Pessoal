$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Pythonw = Join-Path $ProjectRoot ".venv\Scripts\pythonw.exe"
$Launcher = Join-Path $ProjectRoot "scripts\launcher_local.py"

if (-not (Test-Path -LiteralPath $Pythonw -PathType Leaf)) {
    throw "A .venv do projeto não foi encontrada."
}
if (-not (Test-Path -LiteralPath $Launcher -PathType Leaf)) {
    throw "O launcher local não foi encontrado."
}

$Desktop = [Environment]::GetFolderPath("Desktop")
$Shell = New-Object -ComObject WScript.Shell

function New-ControleFinanceiroShortcut($Name, $Mode) {
    $Shortcut = $Shell.CreateShortcut((Join-Path $Desktop "$Name.lnk"))
    $Shortcut.TargetPath = $Pythonw
    $Shortcut.Arguments = "`"$Launcher`" $Mode"
    $Shortcut.WorkingDirectory = $ProjectRoot
    $Shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,21"
    $Shortcut.Save()
}

New-ControleFinanceiroShortcut "Controle Financeiro" "iniciar"
New-ControleFinanceiroShortcut "Encerrar Controle Financeiro" "encerrar"
Write-Host "Atalhos criados na Área de Trabalho."
