Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")

function Remove-SafePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    $Target = Resolve-Path -LiteralPath $Path
    if ($Target.Path -eq $Root.Path -or -not ($Target.Path -like "$($Root.Path)\*")) {
        throw "Refusing to delete unsafe path: $($Target.Path)"
    }

    Remove-Item -LiteralPath $Target.Path -Recurse -Force
}

Push-Location $Root
try {
    Remove-SafePath "build"
    Remove-SafePath "dist"
    Remove-SafePath ".pytest_cache"

    Get-ChildItem -Force -File -Filter "*.spec" |
        ForEach-Object { Remove-SafePath $_.FullName }

    Get-ChildItem -Recurse -Force -Directory -Filter "__pycache__" |
        ForEach-Object { Remove-SafePath $_.FullName }

    Write-Host "Clean complete. releases\ and settings.json were preserved."
}
finally {
    Pop-Location
}
