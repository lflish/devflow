# Windows 版安装脚本：用目录联接（junction，不需要管理员权限）把 dev-* skills 装到
# Claude Code（%USERPROFILE%\.claude\skills）和 Codex（%USERPROFILE%\.codex\skills）。
# 用法（PowerShell）：
#   powershell -ExecutionPolicy Bypass -File .\install.ps1            安装
#   powershell -ExecutionPolicy Bypass -File .\install.ps1 status     查看
#   powershell -ExecutionPolicy Bypass -File .\install.ps1 uninstall  卸载
# 目标位置已有同名的普通目录时，先移到 %USERPROFILE%\.cache\devflow-backup\<时间>\。
param([ValidateSet('install', 'status', 'uninstall')][string]$Action = 'install')
$ErrorActionPreference = 'Stop'

$Repo = (Resolve-Path $PSScriptRoot).Path
$targets = @()
if (Test-Path (Join-Path $HOME '.claude')) { $targets += (Join-Path $HOME '.claude\skills') }
$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME '.codex' }
if (Test-Path $codexHome) { $targets += (Join-Path $codexHome 'skills') }
if ($targets.Count -eq 0) { Write-Host '没有找到 .claude 或 .codex，未安装。'; exit 1 }

$skills = Get-ChildItem -Path $Repo -Directory -Filter 'dev-*' | Where-Object { Test-Path (Join-Path $_.FullName 'SKILL.md') }
$backup = Join-Path $HOME ('.cache\devflow-backup\' + (Get-Date -Format 'yyyyMMdd-HHmmss'))

function Get-LinkTarget([string]$path) {
  $item = Get-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
  if ($item -and $item.LinkType) { return [string]($item.Target | Select-Object -First 1) }
  return $null
}
# 只删除联接本身，不会删掉联接指向的目录内容
function Remove-Link([string]$path) { [System.IO.Directory]::Delete($path, $false) }

foreach ($t in $targets) {
  if ($Action -eq 'install') { New-Item -ItemType Directory -Force -Path $t | Out-Null }
  if (-not (Test-Path $t)) { continue }
  Write-Host "== $t"
  foreach ($s in $skills) {
    $dest = Join-Path $t $s.Name
    $item = Get-Item -LiteralPath $dest -Force -ErrorAction SilentlyContinue
    $target = Get-LinkTarget $dest
    switch ($Action) {
      'install' {
        if ($target -eq $s.FullName) { Write-Host "  ✓ $($s.Name)"; continue }
        if ($item -and $item.LinkType) { Remove-Link $dest }
        elseif ($item) {
          $sub = Join-Path $backup (Split-Path (Split-Path $t -Parent) -Leaf)
          New-Item -ItemType Directory -Force -Path $sub | Out-Null
          Move-Item -LiteralPath $dest -Destination $sub
          Write-Host "  已备份 $dest → $sub"
        }
        New-Item -ItemType Junction -Path $dest -Target $s.FullName | Out-Null
        Write-Host "  ✓ $($s.Name)"
      }
      'uninstall' { if ($target -eq $s.FullName) { Remove-Link $dest; Write-Host "  已删除 $dest" } }
      'status' {
        if ($target -eq $s.FullName) { Write-Host "  ✓ $($s.Name)" }
        elseif ($item) { Write-Host "  ! $($s.Name)（存在，但不是指向本仓库的联接）" }
        else { Write-Host "  ✗ $($s.Name)（未安装）" }
      }
    }
  }
  # 清理指向本仓库、但目标已不存在的联接（skill 被删除或改名）
  if ($Action -ne 'status') {
    Get-ChildItem -LiteralPath $t -Force -Filter 'dev-*' -ErrorAction SilentlyContinue | ForEach-Object {
      $lt = Get-LinkTarget $_.FullName
      if ($lt -and $lt.StartsWith($Repo) -and -not (Test-Path -LiteralPath $lt)) { Remove-Link $_.FullName; Write-Host "  已清理失效联接 $($_.FullName)" }
    }
  }
}
if (Test-Path $backup) { Write-Host "旧版本备份在 $backup" }
