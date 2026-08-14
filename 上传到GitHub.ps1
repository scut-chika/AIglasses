# 暖眸 · 上传到 GitHub 辅助脚本
#
# 用法：
#   1) 在 github.com 网页上新建一个空仓库（不要勾选 README / .gitignore），
#      例如仓库名 nuanmou-ai-glasses
#   2) 运行本脚本：
#      .\上传到GitHub.ps1 -RepoUrl "https://github.com/你的用户名/nuanmou-ai-glasses.git"
#
# 说明：本地仓库已由开发环境初始化并完成首次提交；
#       本脚本只负责添加远程地址并推送。推送需要你的 GitHub 凭据
#       （浏览器弹窗登录，或提前配置 Personal Access Token）。

param(
    [string]$RepoUrl = "https://github.com/scut-chika/nuanmou-ai-glasses.git"
)

$ErrorActionPreference = "Stop"
$git = "C:\Program Files\Git\cmd\git.exe"
Set-Location -LiteralPath $PSScriptRoot

if (-not (Test-Path -LiteralPath ".git")) {
    Write-Host "==> 初始化仓库并提交" -ForegroundColor Cyan
    & $git init -b main
    & $git add -A
    & $git commit -m "初赛提交：暖眸-居家养老AI眼镜智能体"
}

Write-Host "==> 添加远程地址：$RepoUrl" -ForegroundColor Cyan
& $git remote remove origin 2>$null
& $git remote add origin $RepoUrl

Write-Host "==> 推送 main 分支" -ForegroundColor Cyan
& $git push -u origin main

if ($LASTEXITCODE -eq 0) {
    $link = $RepoUrl -replace "\.git$", ""
    Write-Host "`n推送成功，仓库链接：$link" -ForegroundColor Green
} else {
    Write-Host "`n推送失败：请检查网络、凭据或仓库地址。" -ForegroundColor Red
}
